from __future__ import annotations

import json
import re
import threading
import time
from http.client import HTTPException
from pathlib import Path
from urllib import error, request

from boardgamebench.games.base import GameState, Move, labels, normalize_label
from boardgamebench.games.search import ranked_moves


MOVE_RE = re.compile(r"[A-Za-z]?\d+\s*,\s*\d+|[A-Za-z]\d+(?:-[A-Za-z]\d+)?|pass", re.IGNORECASE)


class LLMMoveError(RuntimeError):
    pass


class LLMRequestError(LLMMoveError):
    pass


class RequestRateLimiter:
    def __init__(self, rpm: int):
        self.interval = 60.0 / rpm
        self.next_request_at = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_request_at - now)
            self.next_request_at = max(now, self.next_request_at) + self.interval
        if delay:
            time.sleep(delay)


class LLMPlayer:
    def __init__(self, model_config, debug_http: bool = False, reasoning_log_path: Path | None = None):
        self.model_config = model_config
        self.debug_http = debug_http
        self.reasoning_log_path = Path(reasoning_log_path) if reasoning_log_path else None
        self.rate_limiter = RequestRateLimiter(model_config.rate_limit_rpm)

    def choose_move(self, game_name: str, state: GameState, llm_player: int, oracle_depth: int) -> tuple[Move, str]:
        last_error = None
        for attempt in range(1, 5):
            prompt = build_prompt(game_name, state, llm_player, oracle_depth, attempt, last_error)
            response_text = self._chat(prompt, attempt)
            move = parse_move_response(response_text, state.legal_moves())
            if move:
                return move, response_text
            last_error = f"Could not find an exact legal move label in response: {response_text!r}"
        raise LLMMoveError(last_error or "Model did not return a legal move.")

    def _chat(self, prompt: str, attempt: int) -> str:
        api_key = self.model_config.get_api_key()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": self.model_config.model_id,
            "messages": [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 1024,
        }
        payload.update(self.model_config.extra_body)
        self.rate_limiter.wait()
        response_body = self._post_json(f"{self.model_config.base_url}/chat/completions", headers, payload)
        message, reasoning = parse_chat_response(response_body)
        content = normalize_content(message.get("content"), reasoning)
        self._log(prompt, attempt, response_body, message, reasoning)
        return content

    def _post_json(self, endpoint: str, headers: dict[str, str], payload: dict) -> str:
        data = json.dumps(payload).encode("utf-8")
        http_request = request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=self.model_config.timeout_seconds) as response:
                return response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = ""
            if self.debug_http:
                try:
                    detail = "\n" + exc.read().decode("utf-8")
                except Exception:
                    detail = "\n<failed to read response body>"
            raise LLMRequestError(f"Request to {endpoint} failed: {exc}{detail}") from exc
        except (error.URLError, HTTPException, OSError) as exc:
            raise LLMRequestError(f"Request to {endpoint} failed: {exc}") from exc

    def _log(self, prompt: str, attempt: int, response_body: str, message: dict, reasoning: str):
        if not self.reasoning_log_path:
            return
        self.reasoning_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.reasoning_log_path.open("a", encoding="utf-8") as handle:
            json.dump(
                {
                    "model": self.model_config.model_id,
                    "attempt": attempt,
                    "prompt": prompt,
                    "message": message,
                    "reasoning": reasoning,
                    "raw_response": response_body,
                },
                handle,
            )
            handle.write("\n")


def system_prompt() -> str:
    return (
        "You are playing deterministic abstract board-game benchmark positions. "
        "Return exactly one legal move label at the start of your reply. Do not resign, pass unless pass is legal, "
        "or answer with analysis before the move."
    )


def build_prompt(
    game_name: str,
    state: GameState,
    llm_player: int,
    oracle_depth: int,
    attempt: int,
    last_error: str | None,
) -> str:
    legal = state.legal_moves()
    ranked = ranked_moves(state, oracle_depth, limit=min(36, len(legal)))
    legal_text = ", ".join(labels(legal))
    fallback = ranked[0].label if ranked else legal[0].label
    side = "X" if llm_player == 1 else "O"
    prompt = [
        f"Game: {game_name}",
        f"Your side: {side}.",
        f"Side to move now: {'X' if state.current_player == 1 else 'O'}.",
        "Choose the strongest legal move for the side to move.",
        state.rules(),
        "Current board:",
        state.render(),
        f"LEGAL_MOVES: {legal_text}",
        f"If unsure, choose this legal fallback move: {fallback}",
        "Critical response rule: the first characters of your reply must be exactly one label from LEGAL_MOVES.",
        "You may add short reasoning after the move, but no words or punctuation may appear before the move.",
    ]
    if last_error:
        prompt.extend(
            [
                "",
                f"Previous attempt {attempt - 1} was rejected: {last_error}",
                "Try again with one exact legal move label.",
            ]
        )
    return "\n".join(prompt)


def parse_move_response(response_text: str, legal_moves: list[Move]) -> Move | None:
    legal_by_label = {normalize_label(move.label): move for move in legal_moves}
    stripped = str(response_text).strip()
    for move in legal_moves:
        if normalize_label(stripped).startswith(normalize_label(move.label)):
            return move
    for match in MOVE_RE.finditer(stripped):
        move = legal_by_label.get(normalize_label(match.group(0)))
        if move:
            return move
    return None


def parse_chat_response(response_body: str) -> tuple[dict, str]:
    try:
        payload = json.loads(response_body)
        choice = payload["choices"][0]
        message = choice.get("message") or {"content": choice.get("text", "")}
        reasoning = message.get("reasoning") or choice.get("reasoning", "")
        return message, reasoning
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LLMRequestError(f"Unexpected model response: {response_body}") from exc


def normalize_content(content, reasoning: str = "") -> str:
    if isinstance(content, list):
        content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    content = "" if content is None else str(content).strip()
    return content or str(reasoning).strip()
