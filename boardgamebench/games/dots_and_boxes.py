from __future__ import annotations

from dataclasses import dataclass

from boardgamebench.games.base import GameSpec, GameState, Move, opponent


BOXES = 3


@dataclass(frozen=True)
class DotsAndBoxes:
    spec: GameSpec = GameSpec("dots_and_boxes_3x3", "Dots and Boxes 3x3", 4, 4, 24)

    def initial_state(self) -> GameState:
        h = tuple(tuple(0 for _ in range(BOXES)) for _ in range(BOXES + 1))
        v = tuple(tuple(0 for _ in range(BOXES + 1)) for _ in range(BOXES))
        owners = tuple(tuple(0 for _ in range(BOXES)) for _ in range(BOXES))
        return DotsAndBoxesState(h, v, owners, 1)


@dataclass(frozen=True)
class DotsAndBoxesState(GameState):
    h_edges: tuple[tuple[int, ...], ...]
    v_edges: tuple[tuple[int, ...], ...]
    owners: tuple[tuple[int, ...], ...]
    current_player: int

    def legal_moves(self) -> list[Move]:
        moves = []
        for row in range(BOXES + 1):
            for column in range(BOXES):
                if self.h_edges[row][column] == 0:
                    moves.append(Move(f"H{row + 1},{column + 1}", ("H", row, column)))
        for row in range(BOXES):
            for column in range(BOXES + 1):
                if self.v_edges[row][column] == 0:
                    moves.append(Move(f"V{row + 1},{column + 1}", ("V", row, column)))
        return moves

    def apply_move(self, move: Move) -> GameState:
        kind, row, column = move.payload
        h_rows = [list(line) for line in self.h_edges]
        v_rows = [list(line) for line in self.v_edges]
        owner_rows = [list(line) for line in self.owners]
        if kind == "H":
            h_rows[row][column] = 1
        else:
            v_rows[row][column] = 1

        completed = 0
        for box_row, box_column in affected_boxes(kind, row, column):
            if owner_rows[box_row][box_column] == 0 and box_complete(h_rows, v_rows, box_row, box_column):
                owner_rows[box_row][box_column] = self.current_player
                completed += 1

        next_player = self.current_player if completed else opponent(self.current_player)
        return DotsAndBoxesState(
            tuple(tuple(line) for line in h_rows),
            tuple(tuple(line) for line in v_rows),
            tuple(tuple(line) for line in owner_rows),
            next_player,
        )

    def is_terminal(self) -> bool:
        return not self.legal_moves()

    def winner(self) -> int:
        if not self.is_terminal():
            return 0
        score = sum(value for line in self.owners for value in line)
        if score > 0:
            return 1
        if score < 0:
            return -1
        return 0

    def evaluate(self, player: int) -> float:
        winner = self.winner()
        if winner == player:
            return 100000
        if winner == opponent(player):
            return -100000
        owned = sum(value for line in self.owners for value in line) * player
        danger = 0
        chances = 0
        h_rows = [list(line) for line in self.h_edges]
        v_rows = [list(line) for line in self.v_edges]
        for row in range(BOXES):
            for column in range(BOXES):
                if self.owners[row][column] != 0:
                    continue
                sides = count_sides(h_rows, v_rows, row, column)
                if sides == 3:
                    chances += 1 if self.current_player == player else -1
                elif sides == 2:
                    danger -= 0.5
        return owned * 20 + chances * 8 + danger

    def render(self) -> str:
        lines = []
        for row in range(BOXES + 1):
            top = []
            for column in range(BOXES):
                top.append("+")
                top.append("---" if self.h_edges[row][column] else "   ")
            top.append("+")
            lines.append("".join(top))
            if row < BOXES:
                middle = []
                for column in range(BOXES + 1):
                    middle.append("|" if self.v_edges[row][column] else " ")
                    if column < BOXES:
                        owner = self.owners[row][column]
                        middle.append(" X " if owner == 1 else " O " if owner == -1 else "   ")
                lines.append("".join(middle))
        return "\n".join(lines)

    def rules(self) -> str:
        return (
            "Dots and Boxes on a 3x3 box grid. Players draw one undrawn edge. Completing a box claims it "
            "and gives the same player another move. When all edges are drawn, the player with more boxes wins. "
            "Horizontal edge labels look like H1,1; vertical edge labels look like V2,4."
        )


def affected_boxes(kind: str, row: int, column: int) -> list[tuple[int, int]]:
    boxes = []
    if kind == "H":
        if row > 0:
            boxes.append((row - 1, column))
        if row < BOXES:
            boxes.append((row, column))
    else:
        if column > 0:
            boxes.append((row, column - 1))
        if column < BOXES:
            boxes.append((row, column))
    return boxes


def box_complete(h_edges, v_edges, row: int, column: int) -> bool:
    return (
        h_edges[row][column]
        and h_edges[row + 1][column]
        and v_edges[row][column]
        and v_edges[row][column + 1]
    )


def count_sides(h_edges, v_edges, row: int, column: int) -> int:
    return sum(
        (
            h_edges[row][column],
            h_edges[row + 1][column],
            v_edges[row][column],
            v_edges[row][column + 1],
        )
    )
