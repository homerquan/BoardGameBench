# BoardGameBench

BoardGameBench is a GomokuBench-style benchmark for testing LLM move quality across a curriculum of compact deterministic board games.
It is an extension of [GomokuBench](https://github.com/homerquan/GomokuBench), generalizing the same search-vs-LLM idea from one game to a multi-game score.

Instead of scoring a model on one game, BoardGameBench runs the same model through several games and reports a normalized aggregate score:

- win = 1 point
- draw = 0.5 points
- loss or illegal-move forfeit = 0 points

The current default curriculum follows the first strong multi-game set:

1. Connect Four
2. Gomoku 19x19
3. Breakthrough 6x6
4. Dots and Boxes 3x3
5. Othello 6x6
6. Othello 8x8
7. Hex 7x7

Each game has exact legal move generation, terminal-state detection, deterministic state updates, and a built-in alpha-beta style search opponent with game-specific evaluation. The engine is intentionally simple and auditable, so every result can be replayed from the saved JSON.

## Quick Start

From this folder:

```bash
pip install .
boardgamebench list-games
boardgamebench play --game connect_four
boardgamebench benchmark --model-file ./models/example-openai-compatible.json -r 2
```

After installation:

```bash
pip install .
boardgamebench benchmark --model my-model -r 4
```

## Model Configs

Model configs use the same OpenAI-compatible shape as GomokuBench:

```json
{
  "provider": {
    "openrouter": {
      "name": "OpenRouter",
      "options": {
        "baseURL": "https://openrouter.ai/api/v1",
        "apiKeyEnv": "OPENROUTER_API_KEY"
      },
      "models": {
        "my-model": {
          "name": "My Model",
          "model": "provider/model-id",
          "rate_limit_rpm": 30,
          "timeout_seconds": 120
        }
      }
    }
  }
}
```

Put configs in `models/<name>.json` and run:

```bash
boardgamebench benchmark --model <name>
```

or pass a file directly:

```bash
boardgamebench benchmark --model-file /path/to/model.json
```

## Choosing Games

Run the default curriculum:

```bash
boardgamebench benchmark --model my-model
```

Run a subset:

```bash
boardgamebench benchmark --model my-model --games connect_four,breakthrough_6x6,othello_6x6 -r 4
```

Available game ids:

- `connect_four`
- `gomoku_19x19`
- `breakthrough_6x6`
- `dots_and_boxes_3x3`
- `othello_6x6`
- `othello_8x8`
- `hex_7x7`

See `GAMES.md` for the implemented curriculum and the planned stronger-oracle roadmap for the larger game list.

## Outputs

Reports are saved in `benchmarks/<model>.json` and include:

- model and provider metadata
- aggregate score and per-game scores
- every move by the LLM and engine
- raw LLM responses
- final board states
- a reasoning/API log path under `/tmp/boardgamebench`

## Notes

This repo is a benchmark harness, not a claim that the bundled engines are perfect solvers for every game. The design keeps the oracle interface pluggable so stronger sources can be dropped in later, such as Pascal Pons for Connect Four, Edax for Othello, MoHex/Benzene for Hex, or retrograde/proof databases for solved small variants.
