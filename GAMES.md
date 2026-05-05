# Game Curriculum

## Implemented Default Set

| Game | Id | Why it is first |
|---|---|---|
| Connect Four | `connect_four` | Clean move labels, short games, tactical traps, solved-game lineage. |
| Gomoku 19x19 | `gomoku_19x19` | Baseline from GomokuBench with familiar 1-based coordinate labels and threat reasoning. |
| Breakthrough 6x6 | `breakthrough_6x6` | Very small rules surface with sharp tactical race reasoning. |
| Dots and Boxes 3x3 | `dots_and_boxes_3x3` | Sacrifice/control reasoning and extra-turn planning. |
| Othello 6x6 | `othello_6x6` | Compact flip tactics and stable legal move generation. |
| Othello 8x8 | `othello_8x8` | Richer positional evaluation after the 6x6 warmup. |
| Hex 7x7 | `hex_7x7` | Connection planning with no draws. |

## Planned Oracle Upgrades

The current engines are bundled deterministic alpha-beta/search opponents. The benchmark interface is intentionally small so stronger external oracles can replace them game by game:

| Game | Stronger source direction |
|---|---|
| Connect Four | Pascal Pons style perfect solver or table-backed alpha-beta. |
| Gomoku | Reuse or directly wrap the GomokuBench alpha-beta engine for exact parity. |
| Othello/Reversi | Edax integration, first for 6x6 and then 8x8. |
| Dots and Boxes | Barker/Korf style solved small-board databases or stronger endgame search. |
| Breakthrough | Proof-number/search database for 6x6 variants. |
| Hex | MoHex/Benzene for small boards. |
| Nine Men's Morris | Retrograde database adapter. |
| Kalah/Mancala | Variant-specific full-game database or alpha-beta solver. |
| Ostle | Published retrograde output adapter. |
| Clobber | CGT/endgame database adapter. |
| Mijnlieff | Alpha-beta solved-position adapter. |
