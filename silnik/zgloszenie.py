"""Zgłoszenie błędu mailem – gotowy link mailto: z wersją, systemem i końcówką log.txt.

Użycie: zgloszenie.py link – wypisuje adres mailto: (czysty ASCII); aplikacja otwiera go w programie pocztowym.
"""
import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ADRES = "mtroszgithub@gmail.com"
ZNAKI_LOGU = 1500


def koncowka_logu(log: Path, znaki: int = ZNAKI_LOGU) -> str:
    """Ostatnie ~znaki znaków logu, zaczynając od pełnej linii."""
    try:
        tekst = Path(log).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if len(tekst) <= znaki:
        return tekst
    koncowka = tekst[-znaki:]
    nowa_linia = koncowka.find("\n")
    return koncowka[nowa_linia + 1:] if nowa_linia >= 0 else koncowka


def _procesor() -> str:
    try:
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True,
                              timeout=5, check=True).stdout.strip() or "?"
    except Exception:
        return "?"


def link(wersja: str, log: Path, macos: str | None = None, procesor: str | None = None) -> str:
    temat = f"Transkrypcja – zgłoszenie błędu (wersja {wersja})"
    linie = [
        "Opisz proszę, co się działo, gdy wystąpił błąd:",
        "",
        "",
        "",
        "---",
        f"Wersja aplikacji: {wersja}",
        f"macOS: {macos if macos is not None else (platform.mac_ver()[0] or '?')}",
        f"Procesor: {procesor if procesor is not None else _procesor()}",
        "",
        "Ostatnie wpisy z log.txt:",
        koncowka_logu(log) or "(log jest pusty)",
    ]
    # mailto: wymaga końców linii CRLF (RFC 6068) – także wewnątrz wklejonego logu.
    tresc = "\n".join(linie).replace("\r\n", "\n").replace("\n", "\r\n")
    return f"mailto:{ADRES}?subject={quote(temat, safe='')}&body={quote(tresc, safe='')}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zgłoszenie błędu Transkrypcji.")
    parser.add_argument("polecenie", choices=["link"])
    parser.parse_args(argv)
    katalog = Path(os.environ.get("TRANSKRYPCJA_KATALOG") or Path(__file__).resolve().parent.parent)
    try:
        wersja = (katalog / "VERSION").read_text(encoding="utf-8").strip() or "?"
    except OSError:
        wersja = "?"
    print(link(wersja, katalog / "log.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
