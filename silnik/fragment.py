"""Fragment transkrypcji – wspólny typ dla silnika, filtrów i zapisu."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Fragment:
    start: float
    koniec: float
    tekst: str
    no_speech_prob: float = 0.0
    avg_logprob: float = 0.0


def z_segmentow(segmenty: list[dict]) -> list[Fragment]:
    """Zamienia segmenty zwrócone przez Whispera na fragmenty."""
    return [
        Fragment(
            start=float(s["start"]),
            koniec=float(s["end"]),
            tekst=s["text"].strip(),
            no_speech_prob=float(s.get("no_speech_prob", 0.0)),
            avg_logprob=float(s.get("avg_logprob", 0.0)),
        )
        for s in segmenty
    ]
