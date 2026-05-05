from __future__ import annotations

from dataclasses import dataclass

from boardgamebench.games.base import GameSpec, GameState, Move, opponent


DIRECTIONS = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)
FILES = "abcdefgh"


@dataclass(frozen=True)
class Othello:
    size: int = 6

    @property
    def spec(self) -> GameSpec:
        if self.size == 6:
            return GameSpec("othello_6x6", "Othello 6x6", 4, 4, 38)
        return GameSpec("othello_8x8", "Othello 8x8", 2, 3, 66)

    def initial_state(self) -> GameState:
        middle = self.size // 2
        rows = [[0 for _ in range(self.size)] for _ in range(self.size)]
        rows[middle - 1][middle - 1] = -1
        rows[middle][middle] = -1
        rows[middle - 1][middle] = 1
        rows[middle][middle - 1] = 1
        return OthelloState(tuple(tuple(row) for row in rows), 1, self.size, passes=0)


@dataclass(frozen=True)
class OthelloState(GameState):
    board: tuple[tuple[int, ...], ...]
    current_player: int
    size: int
    passes: int = 0

    def legal_moves(self) -> list[Move]:
        moves = []
        for row in range(self.size):
            for column in range(self.size):
                if self.board[row][column] == 0 and self.flips_for(row, column, self.current_player):
                    moves.append(Move(f"{FILES[column]}{self.size - row}", (row, column)))
        if not moves:
            moves.append(Move("pass", None))
        return moves

    def apply_move(self, move: Move) -> GameState:
        if move.payload is None:
            return OthelloState(self.board, opponent(self.current_player), self.size, self.passes + 1)
        row, column = move.payload
        rows = [list(line) for line in self.board]
        rows[row][column] = self.current_player
        for fr, fc in self.flips_for(row, column, self.current_player):
            rows[fr][fc] = self.current_player
        return OthelloState(tuple(tuple(line) for line in rows), opponent(self.current_player), self.size, 0)

    def is_terminal(self) -> bool:
        return self.passes >= 2 or all(value != 0 for line in self.board for value in line)

    def winner(self) -> int:
        if not self.is_terminal():
            return 0
        total = sum(value for line in self.board for value in line)
        if total > 0:
            return 1
        if total < 0:
            return -1
        return 0

    def evaluate(self, player: int) -> float:
        winner = self.winner()
        if winner == player:
            return 100000
        if winner == opponent(player):
            return -100000
        if self.is_terminal():
            return 0
        discs = sum(value for line in self.board for value in line) * player
        mobility = len(real_moves(self, player)) - len(real_moves(self, opponent(player)))
        corners = corner_score(self, player)
        return discs + mobility * 5 + corners * 25

    def render(self) -> str:
        symbols = {1: "X", -1: "O", 0: "."}
        rows = ["  " + " ".join(FILES[: self.size])]
        for row in range(self.size):
            rows.append(f"{self.size - row} " + " ".join(symbols[value] for value in self.board[row]))
        return "\n".join(rows)

    def rules(self) -> str:
        return (
            f"Othello/Reversi on a {self.size}x{self.size} board. X moves first. Place a disc on an empty square "
            "that brackets one or more opponent discs in a straight line; bracketed discs flip to your color. "
            "If you have no legal placement, play pass. When both players pass or the board fills, the side with "
            "more discs wins. Moves use labels like d3."
        )

    def flips_for(self, row: int, column: int, player: int) -> list[tuple[int, int]]:
        if self.board[row][column] != 0:
            return []
        flips = []
        for dr, dc in DIRECTIONS:
            ray = []
            r, c = row + dr, column + dc
            while 0 <= r < self.size and 0 <= c < self.size and self.board[r][c] == opponent(player):
                ray.append((r, c))
                r += dr
                c += dc
            if ray and 0 <= r < self.size and 0 <= c < self.size and self.board[r][c] == player:
                flips.extend(ray)
        return flips


def real_moves(state: OthelloState, player: int) -> list[Move]:
    probe = OthelloState(state.board, player, state.size, state.passes)
    return [move for move in probe.legal_moves() if move.payload is not None]


def corner_score(state: OthelloState, player: int) -> int:
    corners = (
        state.board[0][0],
        state.board[0][state.size - 1],
        state.board[state.size - 1][0],
        state.board[state.size - 1][state.size - 1],
    )
    return sum(1 if value == player else -1 if value == opponent(player) else 0 for value in corners)
