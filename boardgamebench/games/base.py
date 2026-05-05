from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class Move:
    label: str
    payload: object


@dataclass(frozen=True)
class GameSpec:
    game_id: str
    name: str
    default_rounds: int
    oracle_depth: int
    max_moves: int = 100


class GameState(ABC):
    current_player: int

    @abstractmethod
    def legal_moves(self) -> list[Move]:
        raise NotImplementedError

    @abstractmethod
    def apply_move(self, move: Move) -> GameState:
        raise NotImplementedError

    @abstractmethod
    def is_terminal(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def winner(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, player: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def rules(self) -> str:
        raise NotImplementedError

    def move_by_label(self, label: str) -> Move | None:
        normalized = normalize_label(label)
        for move in self.legal_moves():
            if normalize_label(move.label) == normalized:
                return move
        return None


class GameFactory(Protocol):
    spec: GameSpec

    def initial_state(self) -> GameState:
        ...


def normalize_label(label: str) -> str:
    return "".join(str(label).strip().lower().split())


def opponent(player: int) -> int:
    return -player


def labels(moves: Iterable[Move]) -> list[str]:
    return [move.label for move in moves]
