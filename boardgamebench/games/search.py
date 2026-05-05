from __future__ import annotations

import math

from boardgamebench.games.base import GameState, Move


def choose_engine_move(state: GameState, depth: int) -> tuple[Move | None, float]:
    moves = state.legal_moves()
    if not moves:
        return None, state.evaluate(state.current_player)

    player = state.current_player
    best_move = moves[0]
    best_score = -math.inf
    alpha = -math.inf
    beta = math.inf

    ordered_moves = sorted(
        moves,
        key=lambda move: state.apply_move(move).evaluate(player),
        reverse=True,
    )
    for move in ordered_moves:
        score = minimax(state.apply_move(move), depth - 1, alpha, beta, player)
        if score > best_score:
            best_score = score
            best_move = move
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return best_move, best_score


def ranked_moves(state: GameState, depth: int, limit: int = 32) -> list[Move]:
    player = state.current_player
    scored = []
    for move in state.legal_moves():
        score = minimax(state.apply_move(move), max(0, depth - 1), -math.inf, math.inf, player)
        scored.append((score, move))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [move for _, move in scored[:limit]]


def minimax(state: GameState, depth: int, alpha: float, beta: float, root_player: int) -> float:
    if state.is_terminal() or depth <= 0:
        return state.evaluate(root_player)

    moves = state.legal_moves()
    if not moves:
        return state.evaluate(root_player)

    if state.current_player == root_player:
        value = -math.inf
        for move in moves:
            value = max(value, minimax(state.apply_move(move), depth - 1, alpha, beta, root_player))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    value = math.inf
    for move in moves:
        value = min(value, minimax(state.apply_move(move), depth - 1, alpha, beta, root_player))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value
