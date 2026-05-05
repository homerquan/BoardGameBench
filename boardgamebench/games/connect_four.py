from __future__ import annotations

from dataclasses import dataclass

from boardgamebench.games.base import GameSpec, GameState, Move, opponent


ROWS = 6
COLUMNS = 7
WINDOWS = (
    [(0, 1), (0, 2), (0, 3)],
    [(1, 0), (2, 0), (3, 0)],
    [(1, 1), (2, 2), (3, 3)],
    [(1, -1), (2, -2), (3, -3)],
)


@dataclass(frozen=True)
class ConnectFour:
    spec: GameSpec = GameSpec("connect_four", "Connect Four", 4, 6, 42)

    def initial_state(self) -> GameState:
        return ConnectFourState(tuple(tuple(0 for _ in range(COLUMNS)) for _ in range(ROWS)), 1)


@dataclass(frozen=True)
class ConnectFourState(GameState):
    board: tuple[tuple[int, ...], ...]
    current_player: int

    def legal_moves(self) -> list[Move]:
        return [
            Move(f"C{column + 1}", column)
            for column in range(COLUMNS)
            if self.board[0][column] == 0
        ]

    def apply_move(self, move: Move) -> GameState:
        column = int(move.payload)
        rows = [list(row) for row in self.board]
        for row in range(ROWS - 1, -1, -1):
            if rows[row][column] == 0:
                rows[row][column] = self.current_player
                break
        return ConnectFourState(tuple(tuple(row) for row in rows), opponent(self.current_player))

    def is_terminal(self) -> bool:
        return self.winner() != 0 or not self.legal_moves()

    def winner(self) -> int:
        for row in range(ROWS):
            for column in range(COLUMNS):
                player = self.board[row][column]
                if player == 0:
                    continue
                for window in WINDOWS:
                    if all(
                        0 <= row + dr < ROWS
                        and 0 <= column + dc < COLUMNS
                        and self.board[row + dr][column + dc] == player
                        for dr, dc in window
                    ):
                        return player
        return 0

    def evaluate(self, player: int) -> float:
        winner = self.winner()
        if winner == player:
            return 100000
        if winner == opponent(player):
            return -100000

        score = 0.0
        center_count = sum(1 for row in range(ROWS) if self.board[row][COLUMNS // 2] == player)
        score += center_count * 3
        for cells in all_lines(self.board):
            score += score_line(cells, player)
        return score

    def render(self) -> str:
        symbols = {1: "X", -1: "O", 0: "."}
        header = " ".join(f"C{column + 1}" for column in range(COLUMNS))
        rows = [" ".join(symbols[value] for value in row) for row in self.board]
        return "\n".join([header, *rows])

    def rules(self) -> str:
        return (
            "Connect Four. Players drop one disc into a non-full column. "
            "X and O alternate. The disc falls to the lowest empty cell in that column. "
            "Four in a row horizontally, vertically, or diagonally wins. Legal moves are C1 through C7."
        )


def all_lines(board: tuple[tuple[int, ...], ...]) -> list[list[int]]:
    lines = []
    for row in range(ROWS):
        for column in range(COLUMNS):
            for offsets in WINDOWS:
                cells = [(row, column), *((row + dr, column + dc) for dr, dc in offsets)]
                if all(0 <= r < ROWS and 0 <= c < COLUMNS for r, c in cells):
                    lines.append([board[r][c] for r, c in cells])
    return lines


def score_line(cells: list[int], player: int) -> float:
    mine = cells.count(player)
    theirs = cells.count(opponent(player))
    empty = cells.count(0)
    if mine and theirs:
        return 0
    if mine == 3 and empty == 1:
        return 80
    if mine == 2 and empty == 2:
        return 12
    if theirs == 3 and empty == 1:
        return -90
    if theirs == 2 and empty == 2:
        return -10
    return 0
