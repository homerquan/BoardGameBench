from __future__ import annotations

import argparse

from boardgamebench.benchmark import BenchmarkLLMCallError, run_benchmark
from boardgamebench.games import DEFAULT_CURRICULUM, GAME_FACTORIES, get_game_factory
from boardgamebench.games.search import choose_engine_move
from boardgamebench.progress import BenchmarkProgress


def run_cli(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list-games":
        return list_games()
    if args.command == "play":
        return play_engine(args)
    if args.command == "benchmark":
        return benchmark_command(args)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run multi-game LLM board-game benchmarks.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-games", help="Show available benchmark games.")

    play_parser = subparsers.add_parser("play", help="Watch the built-in engine play one game against itself.")
    play_parser.add_argument("--game", choices=tuple(GAME_FACTORIES), default="connect_four")
    play_parser.add_argument("--depth", type=int, default=None)

    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark an LLM across several games.")
    model_group = benchmark_parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument("--model", help="Model config name in the models folder.")
    model_group.add_argument("--model-file", help="Path to a custom model JSON config file.")
    benchmark_parser.add_argument(
        "--games",
        help=f"Comma-separated game ids. Default: {','.join(DEFAULT_CURRICULUM)}",
    )
    benchmark_parser.add_argument(
        "-r",
        "--rounds",
        type=int,
        default=None,
        help="Rounds per selected game. Defaults to each game's curriculum setting.",
    )
    benchmark_parser.add_argument("-v", "--verbose", action="store_true", help="Print boards and moves.")
    benchmark_parser.add_argument("--debug-http", action="store_true", help="Print provider HTTP error detail.")
    return parser


def list_games() -> int:
    print("Available games:")
    for game_id, factory in GAME_FACTORIES.items():
        spec = factory.spec
        marker = "*" if game_id in DEFAULT_CURRICULUM else " "
        print(f"{marker} {game_id}: {spec.name}, default rounds={spec.default_rounds}, engine depth={spec.oracle_depth}")
    print("* = default curriculum")
    return 0


def play_engine(args) -> int:
    factory = get_game_factory(args.game)
    depth = args.depth or factory.spec.oracle_depth
    state = factory.initial_state()
    print(factory.spec.name)
    print(state.render())
    while not state.is_terminal():
        move, score = choose_engine_move(state, depth)
        if move is None:
            break
        print(f"\n{'X' if state.current_player == 1 else 'O'} plays {move.label} ({score:.1f})")
        state = state.apply_move(move)
        print(state.render())
    print(f"\nWinner: {winner_text(state.winner())}")
    return 0


def benchmark_command(args) -> int:
    total = estimate_total(args)
    progress = BenchmarkProgress(total)
    try:
        output_path, report = run_benchmark(
            args,
            progress_callback=lambda completed, total_rounds: progress.update(completed),
            start_callback=lambda runner: print(f"LLM reasoning process log in: {runner.reasoning_log_path}"),
        )
    except BenchmarkLLMCallError as error:
        progress.newline()
        print(error)
        print("Benchmark was not saved.")
        return 1
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        progress.newline()
        print(error)
        return 1
    progress.finish()
    summary = report["summary"]
    print(f"Saved benchmark to {output_path}")
    print(
        f"Score: {summary['normalized_score']} "
        f"({summary['raw_score']}/{summary['max_score']}), "
        f"LLM wins: {summary['llm_wins']}, "
        f"engine wins: {summary['engine_wins']}, "
        f"draws: {summary['draws']}"
    )
    return 0


def estimate_total(args) -> int:
    if args.games:
        game_ids = [item.strip() for item in args.games.split(",") if item.strip()]
    else:
        game_ids = DEFAULT_CURRICULUM
    total = 0
    for game_id in game_ids:
        spec = get_game_factory(game_id).spec
        total += args.rounds if args.rounds is not None else spec.default_rounds
    return total


def winner_text(winner: int) -> str:
    if winner == 1:
        return "X"
    if winner == -1:
        return "O"
    return "draw"
