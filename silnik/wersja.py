"""Sprawdzanie nowszej wersji Transkrypcji na GitHubie (tylko biblioteka standardowa).

Użycie: wersja.py sprawdz       – wypisuje numer nowszej wersji albo nic (zawsze kod 0)
        wersja.py adres-zip X.Y – wypisuje adres ZIP wydania vX.Y
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

REPO = "mtrosz/transkrypcja"
ADRES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
PLIK_WERSJI = Path(__file__).resolve().parent.parent / "VERSION"


def _pobierz_curl(adres: str) -> str:
    # curl korzysta z certyfikatów systemu macOS, więc nie zależy od konfiguracji SSL Pythona.
    wynik = subprocess.run(
        ["curl", "-fsSL", "--max-time", "3", "-H", "Accept: application/vnd.github+json", adres],
        capture_output=True, text=True, timeout=5, check=True,
    )
    return wynik.stdout


def _liczby(wersja: str) -> tuple[int, ...]:
    stripped = wersja.strip()
    if not re.fullmatch(r"\d+(\.\d+)*", stripped, re.ASCII):
        raise ValueError(f"Invalid version format: {wersja}")
    return tuple(int(czesc) for czesc in stripped.split("."))


def jest_nowsza(nowa: str | None, zainstalowana: str | None) -> bool:
    """Nieczytelna albo nieznana wersja (którakolwiek) oznacza: nie proponuj aktualizacji."""
    try:
        n = _liczby(nowa)
        z = _liczby(zainstalowana)
    except (ValueError, AttributeError):
        return False
    dlugosc = max(len(n), len(z))
    return n + (0,) * (dlugosc - len(n)) > z + (0,) * (dlugosc - len(z))


def najnowsze_wydanie(pobierz: Callable[[str], str] = _pobierz_curl) -> str | None:
    try:
        tag = json.loads(pobierz(ADRES_API))["tag_name"]
    except Exception:
        return None
    if not isinstance(tag, str) or not tag:
        return None
    return tag[1:] if tag.startswith("v") else tag


def zainstalowana_wersja(plik: Path = PLIK_WERSJI) -> str | None:
    try:
        return plik.read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


def adres_zip(wersja: str) -> str:
    return f"https://github.com/{REPO}/archive/refs/tags/v{wersja}.zip"


def main(argv: list[str] | None = None, pobierz: Callable[[str], str] = _pobierz_curl,
         plik_wersji: Path = PLIK_WERSJI) -> int:
    parser = argparse.ArgumentParser(description="Wersje Transkrypcji na GitHubie.")
    polecenia = parser.add_subparsers(dest="polecenie", required=True)
    polecenia.add_parser("sprawdz")
    zip_parser = polecenia.add_parser("adres-zip")
    zip_parser.add_argument("wersja")
    args = parser.parse_args(argv)

    if args.polecenie == "sprawdz":
        nowa = najnowsze_wydanie(pobierz)
        if jest_nowsza(nowa, zainstalowana_wersja(plik_wersji)):
            print(nowa)
    else:
        print(adres_zip(args.wersja))
    return 0


if __name__ == "__main__":
    sys.exit(main())
