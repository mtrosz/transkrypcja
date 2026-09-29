"""Zamiennik tqdm.tqdm: mlx-whisper raportuje postęp paskiem tqdm, a my przekazujemy go do postep(ułamek)."""
from typing import Callable


def fabryka_paska(postep: Callable[[float], None]) -> type:
    class Pasek:
        def __init__(self, *args, total=None, **kwargs):
            self.total = total or 0
            self.n = 0

        def update(self, n=1):
            self.n += n
            if self.total:
                postep(min(1.0, self.n / self.total))

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *wyjatek):
            return False

    return Pasek
