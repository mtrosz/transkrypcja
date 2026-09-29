"""Plik status.json – jedyny kanał informacji z silnika do okienek (AppleScript czyta go przez plutil)."""
import json
import os
import time
from pathlib import Path
from typing import Callable


class Status:
    def __init__(self, sciezka: Path, zegar: Callable[[], float] = time.monotonic, odstep_s: float = 2.0):
        self._sciezka = Path(sciezka)
        self._zegar = zegar
        self._odstep_s = odstep_s
        self._ostatni_postep: float | None = None

    def etap(self, nazwa: str) -> None:
        self._zapisz(etap=nazwa)

    def postep(self, procent: float) -> None:
        procent = max(0, min(100, int(procent)))
        teraz = self._zegar()
        if (
            self._ostatni_postep is not None
            and teraz - self._ostatni_postep < self._odstep_s
            and procent < 100
        ):
            return
        self._ostatni_postep = teraz
        self._zapisz(etap="transkrypcja", procent=procent)

    def wynik(self, sciezka: Path, uwaga: str = "") -> None:
        self._zapisz(etap="gotowe", procent=100, wynik=str(sciezka), uwaga=uwaga)

    def blad(self, komunikat: str) -> None:
        self._zapisz(etap="blad", blad=komunikat)

    def _zapisz(self, etap: str, procent: int = 0, wynik: str = "", blad: str = "", uwaga: str = "") -> None:
        dane = {"etap": etap, "procent": procent, "wynik": wynik, "blad": blad, "uwaga": uwaga}
        tymczasowy = self._sciezka.with_name(self._sciezka.name + ".tmp")
        tymczasowy.write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")
        os.replace(tymczasowy, self._sciezka)
