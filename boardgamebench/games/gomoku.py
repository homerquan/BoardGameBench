from __future__ import annotations

from dataclasses import dataclass

from boardgamebench.games.base import GameSpec, GameState, Move, opponent


SIZE = 19
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


@dataclass(frozen=True)
class Gomoku:
    spec: GameSpec = GameSpec("gomoku_19x19", "Gomoku 19x19", 2, 2, 361)

    def initial_state(self) -> GameState:
        return GomokuState(tuple(tuple(0 for _ in range(SIZE)) for _ in range(SIZE)), 1)


@dataclass(frozen=True)
class GomokuState(GameState):
    board: tuple[tuple[int, ...], ...]
    current_player: int

    def legal_moves(self) -> list[Move]:
        occupied = [
            (row, column)
            for row in range(SIZE)
            for column in range(SIZE)
            if self.board[row][column] != 0
        ]
        if not occupied:
            center = SIZE // 2
            return [make_move(center, center)]

        candidates = set()
        for row, column in occupied:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = row + dr, column + dc
                    if 0 <= nr < SIZE and 0 <= nc < SIZE and self.board[nr][nc] == 0:
                        candidates.add((nr, nc))
        return [make_move(row, column) for row, column in sorted(candidates)]

    def apply_move(self, move: Move) -> GameState:
        row, column = move.payload
        rows = [list(line) for line in self.board]
        rows[row][column] = self.current_player
        return GomokuState(tuple(tuple(line) for line in rows), opponent(self.current_player))

    def is_terminal(self) -> bool:
        return self.winner() != 0 or all(value != 0 for line in self.board for value in line)

    def winner(self) -> int:
        for row in range(SIZE):
            for column in range(SIZE):
                player = self.board[row][column]
                if player == 0:
                    continue
                for dr, dc in DIRECTIONS:
                    if has_five(self.board, row, column, dr, dc, player):
                        return player
        return 0

    def evaluate(self, player: int) -> float:
        winner = self.winner()
        if winner == player:
            return 100000
        if winner == opponent(player):
            return -100000
        return evaluate_player(self.board, player) - evaluate_player(self.board, opponent(player))

    def render(self) -> str:
        symbols = {1: "X", -1: "O", 0: "."}
        cell_width = 3
        header = " " * 4 + "".join(f"{column + 1:<{cell_width}}" for column in range(SIZE))
        rows = [header]
        for row in range(SIZE):
            cells = "".join(f"{symbols[self.board[row][column]]:<{cell_width}}" for column in range(SIZE))
            rows.append(f"{row + 1:>2}  {cells}")
        return "\n".join(rows)

    def rules(self) -> str:
        return (
            "Gomoku on a 19x19 board. X and O alternate placing one stone on an empty intersection. "
            "Five or more stones in a row horizontally, vertically, or diagonally wins. There are no captures, "
            "forbidden moves, swap rules, or pass moves. Moves use 1-based x,y coordinates, for example 10,10."
        )


def make_move(row: int, column: int) -> Move:
    return Move(f"{column + 1},{row + 1}", (row, column))


def has_five(board: tuple[tuple[int, ...], ...], row: int, column: int, dr: int, dc: int, player: int) -> bool:
    for step in range(5):
        nr, nc = row + dr * step, column + dc * step
        if not (0 <= nr < SIZE and 0 <= nc < SIZE) or board[nr][nc] != player:
            return False
    return True


def evaluate_player(board: tuple[tuple[int, ...], ...], player: int) -> float:
    score = 0.0
    for row in range(SIZE):
        for column in range(SIZE):
            for dr, dc in DIRECTIONS:
                cells = []
                for step in range(5):
                    nr, nc = row + dr * step, column + dc * step
                    if not (0 <= nr < SIZE and 0 <= nc < SIZE):
                        break
                    cells.append(board[nr][nc])
                if len(cells) == 5:
                    score += score_window(cells, player)
    return score


def score_window(cells: list[int], player: int) -> float:
    mine = cells.count(player)
    theirs = cells.count(opponent(player))
    empty = cells.count(0)
    if mine and theirs:
        return 0
    if mine == 5:
        return 100000
    if mine == 4 and empty == 1:
        return 10000
    if mine == 3 and empty == 2:
        return 1000
    if mine == 2 and empty == 3:
        return 50
    if mine == 1 and empty == 4:
        return 2
    return 0
