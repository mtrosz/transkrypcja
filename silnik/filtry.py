"""Usuwanie typowych halucynacji Whispera: ciszy, pętli, bełkotu w obcych językach i znanych wstawek."""
import re
import unicodedata
from dataclasses import replace

from fragment import Fragment

PROG_NO_SPEECH = 0.6
PROG_LOGPROB = -1.0
MIN_POWTORZEN = 3

# Fraza (1–8 słów) powtórzona pod rząd co najmniej 4 razy – zostaje jedno wystąpienie.
ZAPETLENIE = re.compile(r"((?:\S+\s+){1,8}?)\1{3,}")
# Udział liter spoza alfabetu łacińskiego (chińskie, koreańskie, cyrylica…), od którego fragment to bełkot.
PROG_OBCE_PISMO = 0.03
# Angielski bełkot: co najmniej tyle słów, z czego taki udział to typowe angielskie słowa (nieistniejące po polsku).
MIN_SLOW_ANGIELSKI = 4
PROG_ANGIELSKI = 0.3
SLOWA_ANGIELSKIE = {
    "the", "of", "and", "is", "are", "you", "that", "that's", "this", "with", "what", "so", "it", "be",
    "for", "world", "i'm",
}
# Wstawki, których Whisper nauczył się z napisów do filmów.
ZNANE_HALUCYNACJE = re.compile(
    r"napisy (by|stworzone|wykonane|przygotowane)|amara\.org|dziękuję za obejrzenie|subskrybuj",
    re.IGNORECASE,
)


def filtruj(fragmenty: list[Fragment]) -> list[Fragment]:
    zostaja = []
    for f in fragmenty:
        if f.no_speech_prob > PROG_NO_SPEECH and f.avg_logprob < PROG_LOGPROB:
            continue
        f = replace(f, tekst=skroc_zapetlenia(f.tekst))
        if not _to_belkot(f.tekst):
            zostaja.append(f)
    return _usun_powtorzenia(zostaja)


def skroc_zapetlenia(tekst: str) -> str:
    return ZAPETLENIE.sub(r"\1", tekst.strip() + " ").strip()


def _to_belkot(tekst: str) -> bool:
    if not any(z.isalnum() for z in tekst):
        return True
    litery = [z for z in tekst if z.isalpha()]
    if not litery:
        return False
    obce = sum(1 for z in litery if not unicodedata.name(z, "").startswith("LATIN"))
    if obce / len(litery) >= PROG_OBCE_PISMO:
        return True
    slowa = re.findall(r"[\w']+", tekst.lower())
    angielskie = sum(1 for s in slowa if s in SLOWA_ANGIELSKIE)
    if len(slowa) >= MIN_SLOW_ANGIELSKI and angielskie / len(slowa) >= PROG_ANGIELSKI:
        return True
    return bool(ZNANE_HALUCYNACJE.search(tekst))


def _normalizuj(tekst: str) -> str:
    return re.sub(r"^\W+|\W+$", "", tekst.strip().lower())


def _usun_powtorzenia(fragmenty: list[Fragment]) -> list[Fragment]:
    wynik: list[Fragment] = []
    i = 0
    while i < len(fragmenty):
        klucz = _normalizuj(fragmenty[i].tekst)
        j = i
        while j + 1 < len(fragmenty) and _normalizuj(fragmenty[j + 1].tekst) == klucz:
            j += 1
        seria = fragmenty[i : j + 1]
        wynik.extend(seria[:1] if len(seria) >= MIN_POWTORZEN else seria)
        i = j + 1
    return wynik
