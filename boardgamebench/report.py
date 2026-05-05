from __future__ import annotations

import json
import math
from pathlib import Path


GAME_WEIGHTS = {
    "connect_four": 1.10,
    "gomoku_19x19": 1.20,
    "breakthrough_6x6": 1.10,
    "dots_and_boxes_3x3": 1.25,
    "othello_6x6": 1.00,
    "othello_8x8": 1.30,
    "hex_7x7": 1.25,
}


def generate_report(benchmarks_dir: str | Path = "benchmarks") -> None:
    benchmark_path = Path(benchmarks_dir)
    if not benchmark_path.exists():
        print("No benchmarks folder found.")
        return

    reports = []
    for benchmark_file in sorted(benchmark_path.glob("*.json")):
        try:
            data = json.loads(benchmark_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not is_boardgame_benchmark(data):
            continue

        summary = data["summary"]
        reasoning_index = boardgamebench_reasoning_index(summary)
        reports.append(
            {
                "model": data.get("model_name") or data.get("model") or benchmark_file.stem,
                "games": int(summary.get("games", 0)),
                "wins": int(summary.get("llm_wins", 0)),
                "losses": int(summary.get("engine_wins", 0)),
                "draws": int(summary.get("draws", 0)),
                "forfeits": int(summary.get("forfeits", 0)),
                "raw_score": float(summary.get("raw_score", 0.0)),
                "max_score": float(summary.get("max_score", 0.0)),
                "normalized_score": float(summary.get("normalized_score", 0.0)),
                "bri": reasoning_index,
            }
        )

    if not reports:
        print("No benchmark result files found.")
        return

    reports.sort(key=lambda item: (item["bri"], item["normalized_score"]), reverse=True)

    print("| Model | Games | Wins | Losses | Draws | Forfeits | Raw Score | Normalized | BRI |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for report in reports:
        print(
            f"| {report['model']} "
            f"| {report['games']} "
            f"| {report['wins']} "
            f"| {report['losses']} "
            f"| {report['draws']} "
            f"| {report['forfeits']} "
            f"| {format_raw_score(report['raw_score'], report['max_score'])} "
            f"| {report['normalized_score']:.2f} "
            f"| {report['bri']:.1f} |"
        )


def is_boardgame_benchmark(data: dict) -> bool:
    summary = data.get("summary")
    games = data.get("games")
    if not isinstance(summary, dict) or not isinstance(games, list):
        return False
    return {"llm_wins", "engine_wins", "draws", "raw_score", "max_score"}.issubset(summary)


def boardgamebench_reasoning_index(summary: dict) -> float:
    per_game_scores = normalized_per_game_scores(summary)
    if not per_game_scores:
        return float(summary.get("normalized_score", 0.0)) * 10

    arithmetic = weighted_mean(per_game_scores)
    geometric = weighted_geometric_mean(per_game_scores)
    core_score = 0.70 * arithmetic + 0.30 * geometric
    consistency_bonus = 0.05 * consistency(per_game_scores, arithmetic)
    return round(1000 * clamp(core_score + consistency_bonus), 1)


def normalized_per_game_scores(summary: dict) -> dict[str, float]:
    by_game = summary.get("by_game")
    if not isinstance(by_game, dict):
        return {}

    scores = {}
    for game_id, stats in by_game.items():
        if not isinstance(stats, dict):
            continue
        games = float(stats.get("games", 0) or 0)
        if games <= 0:
            continue
        scores[game_id] = clamp(float(stats.get("score", 0.0)) / games)
    return scores


def weighted_mean(scores: dict[str, float]) -> float:
    total_weight = sum(weight_for(game_id) for game_id in scores)
    if total_weight <= 0:
        return 0.0
    return sum(score * weight_for(game_id) for game_id, score in scores.items()) / total_weight


def weighted_geometric_mean(scores: dict[str, float]) -> float:
    total_weight = sum(weight_for(game_id) for game_id in scores)
    if total_weight <= 0:
        return 0.0
    log_sum = sum(weight_for(game_id) * math.log(max(score, 0.05)) for game_id, score in scores.items())
    return math.exp(log_sum / total_weight)


def consistency(scores: dict[str, float], mean: float) -> float:
    total_weight = sum(weight_for(game_id) for game_id in scores)
    if total_weight <= 0:
        return 0.0
    variance = sum(weight_for(game_id) * (score - mean) ** 2 for game_id, score in scores.items()) / total_weight
    return clamp(1.0 - math.sqrt(variance))


def weight_for(game_id: str) -> float:
    return GAME_WEIGHTS.get(game_id, 1.0)


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def format_raw_score(raw_score: float, max_score: float) -> str:
    max_text = str(int(max_score)) if max_score.is_integer() else f"{max_score:.2f}"
    return f"{raw_score:.2f}/{max_text}"
