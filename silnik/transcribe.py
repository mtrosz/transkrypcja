"""Silnik transkrypcji – uruchamiany przez Transkrypcja.app w tle.

Użycie: transcribe.py <nagranie> --format {txt,docx} [--czas] --tryb {dokladnie,szybko} --status <status.json> [--folder <katalog>]
Wynik i błędy trafiają do pliku status.json (patrz status.py); kod wyjścia 0 = sukces, 1 = błąd.
"""
import argparse
import datetime
import os
import signal
import sys
import traceback
from pathlib import Path

from filtry import filtruj
from status import Status
from zapis import zapisz

KOMUNIKAT_ODCZYT = "Nie udało się odczytać pliku „{nazwa}”. Czy to na pewno nagranie?"
KOMUNIKAT_CISZA = "W nagraniu „{nazwa}” nie wykryto mowy."
KOMUNIKAT_NAPRAWA = "Coś poszło nie tak przy pliku „{nazwa}”. Aplikacja wymaga naprawy – poproś o pomoc."
KOMUNIKAT_DOSTEP = "macOS nie pozwolił otworzyć pliku „{nazwa}”. Otwórz Ustawienia systemowe → Prywatność i ochrona → Pliki i foldery, włącz dostęp dla aplikacji Transkrypcja i spróbuj ponownie."
UWAGA_BIURKO = "Plik zapisano na Biurku."
SLOWNIK = Path(__file__).resolve().parent / "slownik.txt"


def wczytaj_podpowiedz(sciezka: Path) -> str | None:
    try:
        tekst = sciezka.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return tekst or None


def zaloguj(log: Path, nagranie: Path) -> None:
    """Dopisuje bieżący wyjątek z pełnym tracebackiem do log.txt."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as plik:
        plik.write(f"--- {datetime.datetime.now():%Y-%m-%d %H:%M:%S} {nagranie}\n{traceback.format_exc()}\n")


def sprawdz_dostep(nagranie: Path) -> None:
    """Otwiera plik do odczytu – macOS (TCC) odmawia dostępu właśnie tutaj, jeśli użytkowniczka nie pozwoliła."""
    with nagranie.open("rb"):
        pass


def uruchom(nagranie: Path, format: str, tryb: str, status: Status, silnik, podpowiedz: str | None,
            log: Path, biurko: Path, czas: bool = False, folder: Path | None = None) -> int:
    nazwa = nagranie.name
    try:
        status.etap("wczytywanie")
        try:
            sprawdz_dostep(nagranie)
        except PermissionError:
            zaloguj(log, nagranie)
            status.blad(KOMUNIKAT_DOSTEP.format(nazwa=nazwa))
            return 1
        try:
            audio = silnik.wczytaj_audio(nagranie)
        except Exception:
            zaloguj(log, nagranie)
            status.blad(KOMUNIKAT_ODCZYT.format(nazwa=nazwa))
            return 1

        status.etap("transkrypcja")
        fragmenty = filtruj(silnik.transkrybuj(audio, tryb, podpowiedz, lambda ulamek: status.postep(ulamek * 100)))
        if not fragmenty:
            status.blad(KOMUNIKAT_CISZA.format(nazwa=nazwa))
            return 1

        status.etap("zapis")
        wynik = zapisz(fragmenty, nagranie, format, biurko, czas=czas, folder=folder)
        oczekiwany = folder if folder is not None else nagranie.parent
        uwaga = UWAGA_BIURKO if wynik.parent.resolve() != oczekiwany.resolve() else ""
        status.wynik(wynik, uwaga)
        return 0
    except Exception:
        zaloguj(log, nagranie)
        status.blad(KOMUNIKAT_NAPRAWA.format(nazwa=nazwa))
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transkrypcja nagrania wykładu.")
    parser.add_argument("nagranie", type=Path)
    parser.add_argument("--format", choices=["txt", "docx"], required=True)
    parser.add_argument("--czas", action="store_true", help="znaczniki czasu przy każdym fragmencie")
    parser.add_argument("--tryb", choices=["dokladnie", "szybko"], required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--folder", type=Path, help="folder na wynik (domyślnie obok nagrania)")
    args = parser.parse_args(argv)

    # Anuluj w okienku wysyła SIGTERM – zamieniamy go na wyjątek, żeby zapis.py posprzątał plik częściowy.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    katalog = Path(os.environ.get("TRANSKRYPCJA_KATALOG") or Path(__file__).resolve().parent.parent)
    os.environ["PATH"] = f"{katalog / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"
    os.environ["HF_HOME"] = str(katalog / "modele")
    os.environ["HF_HUB_OFFLINE"] = "1"

    status = Status(args.status)
    log = katalog / "log.txt"
    try:
        import whisper_mlx as silnik
    except Exception:
        zaloguj(log, args.nagranie)
        status.blad(KOMUNIKAT_NAPRAWA.format(nazwa=args.nagranie.name))
        return 1

    return uruchom(args.nagranie, args.format, args.tryb, status, silnik,
                   wczytaj_podpowiedz(SLOWNIK), log, Path.home() / "Desktop", czas=args.czas,
                   folder=args.folder)


if __name__ == "__main__":
    sys.exit(main())
