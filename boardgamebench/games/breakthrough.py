from __future__ import annotations

from dataclasses import dataclass

from boardgamebench.games.base import GameSpec, GameState, Move, opponent


SIZE = 6
FILES = "abcdef"


@dataclass(frozen=True)
class Breakthrough:
    spec: GameSpec = GameSpec("breakthrough_6x6", "Breakthrough 6x6", 4, 4)

    def initial_state(self) -> GameState:
        rows = []
        for row in range(SIZE):
            if row < 2:
                rows.append(tuple(-1 for _ in range(SIZE)))
            elif row >= SIZE - 2:
                rows.append(tuple(1 for _ in range(SIZE)))
            else:
                rows.append(tuple(0 for _ in range(SIZE)))
        return BreakthroughState(tuple(rows), 1)


@dataclass(frozen=True)
class BreakthroughState(GameState):
    board: tuple[tuple[int, ...], ...]
    current_player: int

    def legal_moves(self) -> list[Move]:
        direction = -1 if self.current_player == 1 else 1
        moves = []
        for row in range(SIZE):
            for column in range(SIZE):
                if self.board[row][column] != self.current_player:
                    continue
                next_row = row + direction
                if not 0 <= next_row < SIZE:
                    continue
                if self.board[next_row][column] == 0:
                    moves.append(make_move(row, column, next_row, column))
                for next_column in (column - 1, column + 1):
                    if 0 <= next_column < SIZE and self.board[next_row][next_column] == opponent(self.current_player):
                        moves.append(make_move(row, column, next_row, next_column))
        return moves

    def apply_move(self, move: Move) -> GameState:
        start, end = move.payload
        rows = [list(row) for row in self.board]
        sr, sc = start
        er, ec = end
        rows[er][ec] = rows[sr][sc]
        rows[sr][sc] = 0
        return BreakthroughState(tuple(tuple(row) for row in rows), opponent(self.current_player))

    def is_terminal(self) -> bool:
        return self.winner() != 0 or not self.legal_moves()

    def winner(self) -> int:
        if any(value == 1 for value in self.board[0]):
            return 1
        if any(value == -1 for value in self.board[SIZE - 1]):
            return -1
        if not any(value == 1 for row in self.board for value in row):
            return -1
        if not any(value == -1 for row in self.board for value in row):
            return 1
        return 0

    def evaluate(self, player: int) -> float:
        winner = self.winner()
        if winner == player:
            return 100000
        if winner == opponent(player):
            return -100000
        score = 0.0
        for row in range(SIZE):
            for column in range(SIZE):
                value = self.board[row][column]
                if value == 0:
                    continue
                advance = (SIZE - 1 - row) if value == 1 else row
                piece_score = 10 + advance * advance
                score += piece_score if value == player else -piece_score
        return score

    def render(self) -> str:
        symbols = {1: "X", -1: "O", 0: "."}
        rows = ["  " + " ".join(FILES)]
        for row in range(SIZE):
            rank = SIZE - row
            rows.append(f"{rank} " + " ".join(symbols[value] for value in self.board[row]))
        return "\n".join(rows)

    def rules(self) -> str:
        return (
            "Breakthrough on a 6x6 board. X starts at ranks 1-2 and moves upward toward rank 6. "
            "O starts at ranks 5-6 and moves downward toward rank 1. A piece moves one step straight "
            "forward into an empty square, or one step diagonally forward to capture. First player to "
            "reach the far rank, or capture all opposing pieces, wins. Moves use algebraic labels like a2-a3."
        )


def make_move(sr: int, sc: int, er: int, ec: int) -> Move:
    return Move(f"{FILES[sc]}{SIZE - sr}-{FILES[ec]}{SIZE - er}", ((sr, sc), (er, ec)))
