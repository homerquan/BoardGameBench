from boardgamebench.games.breakthrough import Breakthrough
from boardgamebench.games.connect_four import ConnectFour
from boardgamebench.games.dots_and_boxes import DotsAndBoxes
from boardgamebench.games.gomoku import Gomoku
from boardgamebench.games.hex import Hex
from boardgamebench.games.othello import Othello


GAME_FACTORIES = {
    "connect_four": ConnectFour(),
    "gomoku_19x19": Gomoku(),
    "breakthrough_6x6": Breakthrough(),
    "dots_and_boxes_3x3": DotsAndBoxes(),
    "othello_6x6": Othello(6),
    "othello_8x8": Othello(8),
    "hex_7x7": Hex(),
}

DEFAULT_CURRICULUM = [
    "connect_four",
    "gomoku_19x19",
    "breakthrough_6x6",
    "dots_and_boxes_3x3",
    "othello_6x6",
    "othello_8x8",
    "hex_7x7",
]


def get_game_factory(game_id: str):
    try:
        return GAME_FACTORIES[game_id]
    except KeyError as exc:
        available = ", ".join(sorted(GAME_FACTORIES))
        raise ValueError(f"Unknown game {game_id!r}. Available games: {available}") from exc
