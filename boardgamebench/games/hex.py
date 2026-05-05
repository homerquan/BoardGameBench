from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from boardgamebench.games.base import GameSpec, GameState, Move, opponent


SIZE = 7
FILES = "abcdefg"
NEIGHBORS = ((-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0))


@dataclass(frozen=True)
class Hex:
    spec: GameSpec = GameSpec("hex_7x7", "Hex 7x7", 2, 2, 49)

    def initial_state(self) -> GameState:
        return HexState(tuple(tuple(0 for _ in range(SIZE)) for _ in range(SIZE)), 1)


@dataclass(frozen=True)
class HexState(GameState):
    board: tuple[tuple[int, ...], ...]
    current_player: int

    def legal_moves(self) -> list[Move]:
        moves = []
        for row in range(SIZE):
            for column in range(SIZE):
                if self.board[row][column] == 0:
                    moves.append(Move(f"{FILES[column]}{SIZE - row}", (row, column)))
        return moves

    def apply_move(self, move: Move) -> GameState:
        row, column = move.payload
        rows = [list(line) for line in self.board]
        rows[row][column] = self.current_player
        return HexState(tuple(tuple(line) for line in rows), opponent(self.current_player))

    def is_terminal(self) -> bool:
        return self.winner() != 0 or not self.legal_moves()

    def winner(self) -> int:
        if connected(self.board, 1):
            return 1
        if connected(self.board, -1):
            return -1
        return 0

    def evaluate(self, player: int) -> float:
        winner = self.winner()
        if winner == player:
            return 100000
        if winner == opponent(player):
            return -100000
        return connection_score(self.board, player) - connection_score(self.board, opponent(player))

    def render(self) -> str:
        symbols = {1: "X", -1: "O", 0: "."}
        rows = ["  " + " ".join(FILES)]
        for row in range(SIZE):
            indent = " " * row
            rows.append(f"{indent}{SIZE - row} " + " ".join(symbols[value] for value in self.board[row]))
        return "\n".join(rows)

    def rules(self) -> str:
        return (
            "Hex on a 7x7 board. X tries to connect west to east. O tries to connect north to south. "
            "Players alternate placing one stone on an empty hex. There are no captures and no draws. "
            "Moves use labels like d4."
        )


def connected(board: tuple[tuple[int, ...], ...], player: int) -> bool:
    queue = deque()
    seen = set()
    if player == 1:
        for row in range(SIZE):
            if board[row][0] == player:
                queue.append((row, 0))
                seen.add((row, 0))
        target = lambda r, c: c == SIZE - 1
    else:
        for column in range(SIZE):
            if board[0][column] == player:
                queue.append((0, column))
                seen.add((0, column))
        target = lambda r, c: r == SIZE - 1

    while queue:
        row, column = queue.popleft()
        if target(row, column):
            return True
        for dr, dc in NEIGHBORS:
            nr, nc = row + dr, column + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE and (nr, nc) not in seen and board[nr][nc] == player:
                seen.add((nr, nc))
                queue.append((nr, nc))
    return False


def connection_score(board: tuple[tuple[int, ...], ...], player: int) -> float:
    score = 0.0
    for row in range(SIZE):
        for column in range(SIZE):
            if board[row][column] != player:
                continue
            if player == 1:
                score += 8 - abs(column - SIZE // 2)
            else:
                score += 8 - abs(row - SIZE // 2)
            for dr, dc in NEIGHBORS:
                nr, nc = row + dr, column + dc
                if 0 <= nr < SIZE and 0 <= nc < SIZE and board[nr][nc] == player:
                    score += 2
    return score
