from __future__ import annotations

import sys


class BenchmarkProgress:
    def __init__(self, total: int):
        self.total = total

    def update(self, completed: int):
        width = 28
        ratio = completed / self.total if self.total else 1
        filled = int(width * ratio)
        bar = "#" * filled + "-" * (width - filled)
        sys.stdout.write(f"\r[{bar}] {completed}/{self.total}")
        sys.stdout.flush()

    def finish(self):
        self.update(self.total)
        self.newline()

    def newline(self):
        sys.stdout.write("\n")
        sys.stdout.flush()
