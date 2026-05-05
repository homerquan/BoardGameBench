from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from boardgamebench.games import DEFAULT_CURRICULUM, get_game_factory
from boardgamebench.games.base import Move
from boardgamebench.games.search import choose_engine_move
from boardgamebench.llm_player import LLMMoveError, LLMPlayer, LLMRequestError
from boardgamebench.model_config import load_model_config


BENCHMARK_DIR = Path.cwd() / "benchmarks"
REASONING_LOG_DIR = Path("/tmp/boardgamebench")


@dataclass
class BenchmarkSummary:
    llm_wins: int = 0
    engine_wins: int = 0
    draws: int = 0
    forfeits: int = 0
    games: int = 0
    score: float = 0.0
    by_game: dict[str, dict[str, float | int]] = field(default_factory=dict)


class BenchmarkLLMCallError(RuntimeError):
    pass


class BenchmarkRunner:
    def __init__(
        self,
        model_config,
        games: list[str] | None = None,
        rounds: int | None = None,
        llm_player: LLMPlayer | None = None,
        progress_callback=None,
        verbose: bool = False,
        debug_http: bool = False,
        run_id: str | None = None,
        stream=None,
    ):
        self.model_config = model_config
        self.game_ids = games or list(DEFAULT_CURRICULUM)
        self.rounds_override = rounds
        self.run_id = run_id or uuid4().hex
        self.reasoning_log_path = REASONING_LOG_DIR / f"{self.run_id}.log"
        self.llm_player = llm_player or LLMPlayer(
            model_config,
            debug_http=debug_http,
            reasoning_log_path=self.reasoning_log_path,
        )
        self.progress_callback = progress_callback
        self.verbose = verbose
        self.stream = stream or sys.stdout

    @property
    def total_rounds(self) -> int:
        total = 0
        for game_id in self.game_ids:
            spec = get_game_factory(game_id).spec
            total += self.rounds_override if self.rounds_override is not None else spec.default_rounds
        return total

    def run(self) -> dict:
        results = []
        summary = BenchmarkSummary()
        completed = 0
        self._report_progress(completed)

        for game_id in self.game_ids:
            factory = get_game_factory(game_id)
            rounds = self.rounds_override if self.rounds_override is not None else factory.spec.default_rounds
            for round_number in range(1, rounds + 1):
                llm_first = round_number % 2 == 1
                result = self._play_round(factory, round_number, rounds, llm_first)
                results.append(result)
                update_summary(summary, result)
                completed += 1
                self._report_progress(completed)

        report = {
            "model": self.model_config.model_id,
            "model_name": self.model_config.display_name,
            "provider": self.model_config.provider_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "reasoning_log": str(self.reasoning_log_path),
            "games_requested": self.game_ids,
            "rounds_per_game": self.rounds_override or "game_default",
            "summary": finalize_summary(summary),
            "games": results,
        }
        return report

    def _play_round(self, factory, round_number: int, rounds: int, llm_first: bool) -> dict:
        state = factory.initial_state()
        llm_side = 1 if llm_first else -1
        engine_side = -llm_side
        moves = []
        self._log(f"{factory.spec.name} round {round_number}/{rounds}: LLM is {'X' if llm_side == 1 else 'O'}.")
        self._log(state.render())

        while not state.is_terminal():
            if state.current_player == llm_side:
                try:
                    move, response_text = self.llm_player.choose_move(
                        factory.spec.name,
                        state,
                        llm_side,
                        factory.spec.oracle_depth,
                    )
                except LLMRequestError as error:
                    raise BenchmarkLLMCallError(f"Error calling LLM in {factory.spec.name}: {error}") from error
                except LLMMoveError as error:
                    return forfeit_result(factory, round_number, llm_first, llm_side, engine_side, moves, state, str(error))
                state = state.apply_move(move)
                moves.append(move_record("llm", llm_side, move, response_text))
                self._log(f"LLM plays {move.label}.")
            else:
                move, score = choose_engine_move(state, factory.spec.oracle_depth)
                if move is None:
                    break
                state = state.apply_move(move)
                moves.append(move_record("engine", engine_side, move, None, score))
                self._log(f"Engine plays {move.label}.")
            self._log(state.render())

        winner = state.winner()
        if winner == llm_side:
            outcome = "llm_win"
        elif winner == engine_side:
            outcome = "engine_win"
        else:
            outcome = "draw"
        return {
            "game_id": factory.spec.game_id,
            "game_name": factory.spec.name,
            "round": round_number,
            "rounds": rounds,
            "llm_first": llm_first,
            "llm_side": side_name(llm_side),
            "engine_side": side_name(engine_side),
            "outcome": outcome,
            "winner": side_name(winner) if winner else "none",
            "termination_reason": "terminal_position",
            "moves": moves,
            "final_board": state.render(),
        }

    def _report_progress(self, completed: int):
        if self.progress_callback:
            self.progress_callback(completed, self.total_rounds)

    def _log(self, message: str):
        if self.verbose:
            self.stream.write(f"{message}\n")
            self.stream.flush()


def move_record(player: str, side: int, move: Move, response: str | None = None, score: float | None = None) -> dict:
    record = {"player": player, "side": side_name(side), "move": move.label}
    if response is not None:
        record["response"] = response
    if score is not None:
        record["engine_score"] = score
    return record


def forfeit_result(factory, round_number, llm_first, llm_side, engine_side, moves, state, error):
    return {
        "game_id": factory.spec.game_id,
        "game_name": factory.spec.name,
        "round": round_number,
        "llm_first": llm_first,
        "llm_side": side_name(llm_side),
        "engine_side": side_name(engine_side),
        "outcome": "engine_win",
        "winner": side_name(engine_side),
        "termination_reason": "llm_forfeit",
        "error": error,
        "moves": moves,
        "final_board": state.render(),
    }


def update_summary(summary: BenchmarkSummary, result: dict):
    summary.games += 1
    game_id = result["game_id"]
    game_stats = summary.by_game.setdefault(
        game_id,
        {"games": 0, "llm_wins": 0, "engine_wins": 0, "draws": 0, "score": 0.0},
    )
    game_stats["games"] += 1
    if result["outcome"] == "llm_win":
        summary.llm_wins += 1
        summary.score += 1
        game_stats["llm_wins"] += 1
        game_stats["score"] += 1
    elif result["outcome"] == "draw":
        summary.draws += 1
        summary.score += 0.5
        game_stats["draws"] += 1
        game_stats["score"] += 0.5
    else:
        summary.engine_wins += 1
        game_stats["engine_wins"] += 1
        if result.get("termination_reason") == "llm_forfeit":
            summary.forfeits += 1


def finalize_summary(summary: BenchmarkSummary) -> dict:
    normalized = (summary.score / summary.games * 100) if summary.games else 0.0
    by_game = {}
    for game_id, stats in summary.by_game.items():
        games = int(stats["games"])
        by_game[game_id] = {
            **stats,
            "normalized_score": round(float(stats["score"]) / games * 100, 2) if games else 0.0,
        }
    return {
        "games": summary.games,
        "llm_wins": summary.llm_wins,
        "engine_wins": summary.engine_wins,
        "draws": summary.draws,
        "forfeits": summary.forfeits,
        "raw_score": summary.score,
        "max_score": summary.games,
        "normalized_score": round(normalized, 2),
        "by_game": by_game,
    }


def save_report(model_name: str, report: dict) -> Path:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    output_path = BENCHMARK_DIR / f"{model_name.replace('/', '_')}.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return output_path


def run_benchmark(args, progress_callback=None, start_callback=None):
    model_config = load_model_config(getattr(args, "model", None), getattr(args, "model_file", None))
    games = parse_games(getattr(args, "games", None))
    runner = BenchmarkRunner(
        model_config,
        games=games,
        rounds=getattr(args, "rounds", None),
        progress_callback=progress_callback,
        verbose=getattr(args, "verbose", False),
        debug_http=getattr(args, "debug_http", False),
    )
    if start_callback:
        start_callback(runner)
    report = runner.run()
    return save_report(model_config.config_name, report), report


def parse_games(raw_games: str | None) -> list[str] | None:
    if not raw_games:
        return None
    return [item.strip() for item in raw_games.split(",") if item.strip()]


def side_name(side: int) -> str:
    if side == 1:
        return "X"
    if side == -1:
        return "O"
    return "none"
