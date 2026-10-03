"""Historia transkrypcji – plik historia.json w katalogu aplikacji (obok log.txt).

Silnik (transcribe.py) dodaje wpis na starcie każdego nagrania i kończy go wynikiem albo błędem.
Wpis, który został „w trakcie”, choć jego proces już nie żyje, pokazujemy jako przerwany.

Użycie: historia.py lista        – wypisuje HTML z ostatnimi transkrypcjami (pusty, gdy historii brak)
        historia.py czy-problemy – wypisuje „tak”, gdy na liście jest błąd albo przerwane nagranie, inaczej „nie”
"""
import argparse
import datetime
import html
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Callable

MAKS_WPISOW = 200
POKAZYWANE = 30
MIESIACE = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]
IKONY = {"gotowe": "✅", "blad": "❌", "przerwane": "⚠️", "w_trakcie": "⏳"}


def wczytaj(plik: Path) -> list[dict]:
    """Brak pliku albo plik uszkodzony → pusta historia."""
    try:
        wpisy = json.loads(Path(plik).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [w for w in wpisy if isinstance(w, dict)] if isinstance(wpisy, list) else []


def _wczytaj_do_zmiany(plik: Path) -> list[dict]:
    """Jak wczytaj, ale uszkodzony plik odkłada jako historia-uszkodzona.json, zanim zostanie nadpisany."""
    try:
        wpisy = json.loads(plik.read_text(encoding="utf-8"))
        if isinstance(wpisy, list):
            return [w for w in wpisy if isinstance(w, dict)]
    except FileNotFoundError:
        return []
    except ValueError:
        pass
    os.replace(plik, plik.with_name("historia-uszkodzona.json"))
    return []


def _zapisz(plik: Path, wpisy: list[dict]) -> None:
    tymczasowy = plik.with_name(plik.name + ".tmp")
    tymczasowy.write_text(json.dumps(wpisy[-MAKS_WPISOW:], ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tymczasowy, plik)


def dodaj(plik: Path, nagranie: Path, pid: int | None = None, teraz: datetime.datetime | None = None) -> str:
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    wpisy = _wczytaj_do_zmiany(plik)
    id_wpisu = uuid.uuid4().hex
    wpisy.append({
        "id": id_wpisu,
        "data": (teraz or datetime.datetime.now()).isoformat(timespec="seconds"),
        "nagranie": str(nagranie),
        "status": "w_trakcie",
        "pid": os.getpid() if pid is None else pid,
        "wynik": "",
        "blad": "",
    })
    _zapisz(plik, wpisy)
    return id_wpisu


def zakoncz(plik: Path, id_wpisu: str, status: str, wynik: Path | str = "", blad: str = "") -> None:
    plik = Path(plik)
    wpisy = _wczytaj_do_zmiany(plik)
    for wpis in wpisy:
        if wpis.get("id") == id_wpisu:
            wpis.update(status=status, wynik=str(wynik), blad=blad)
            _zapisz(plik, wpisy)
            return


def proces_zyje(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, TypeError, ValueError):
        return False
    return True


def stan(wpis: dict, zyje: Callable[[int], bool] = proces_zyje) -> str:
    status = wpis.get("status")
    if status == "w_trakcie" and not zyje(wpis.get("pid")):
        return "przerwane"
    return status


def czy_problemy(wpisy: list[dict], zyje: Callable[[int], bool] = proces_zyje) -> bool:
    return any(stan(w, zyje) in ("blad", "przerwane") for w in wpisy[-POKAZYWANE:])


def _data(tekst: str, dzis: datetime.date) -> str:
    try:
        d = datetime.datetime.fromisoformat(tekst)
    except (TypeError, ValueError):
        return ""
    rok = "" if d.year == dzis.year else f" {d.year}"
    return f"{d.day} {MIESIACE[d.month - 1]}{rok}, {d:%H:%M}"


def _link(sciezka: Path, tekst: str, adres: str) -> str:
    if not sciezka.exists():
        return f"{html.escape(tekst)} (plik przeniesiony)"
    return f'<a href="{html.escape(adres)}">{html.escape(tekst)}</a>'


def _pozycja(wpis: dict, zyje: Callable[[int], bool], dzis: datetime.date) -> str:
    s = stan(wpis, zyje)
    nagranie = Path(wpis.get("nagranie", ""))
    # Link do folderu nagrania – otwiera go w Finderze.
    czesci = [IKONY.get(s, ""), html.escape(_data(wpis.get("data", ""), dzis)),
              _link(nagranie, nagranie.name, nagranie.parent.as_uri() + "/" if nagranie.is_absolute() else ""), "→"]
    if s == "gotowe":
        wynik = Path(wpis.get("wynik", ""))
        czesci.append(_link(wynik, wynik.name, wynik.as_uri() if wynik.is_absolute() else ""))
    elif s == "blad":
        czesci.append(html.escape(f"błąd: {wpis.get('blad', '')}"))
    elif s == "przerwane":
        czesci.append("przerwane")
    else:
        czesci.append("w trakcie")
    return '<p style="margin:0 0 6px 0">' + " ".join(czesci) + "</p>"


def lista_html(wpisy: list[dict], zyje: Callable[[int], bool] = proces_zyje,
               dzis: datetime.date | None = None) -> str:
    """Najnowsze POKAZYWANE wpisów jako HTML w czystym ASCII (reszta jako encje) – pusty tekst, gdy brak wpisów."""
    if not wpisy:
        return ""
    dzis = dzis or datetime.date.today()
    pozycje = [_pozycja(w, zyje, dzis) for w in reversed(wpisy[-POKAZYWANE:])]
    tresc = '<div style="font-family:-apple-system,Helvetica Neue,sans-serif;font-size:13px">' + "".join(pozycje) + "</div>"
    return tresc.encode("ascii", "xmlcharrefreplace").decode("ascii")


def plik_historii() -> Path:
    katalog = Path(os.environ.get("TRANSKRYPCJA_KATALOG") or Path(__file__).resolve().parent.parent)
    return katalog / "historia.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Historia transkrypcji.")
    parser.add_argument("polecenie", choices=["lista", "czy-problemy"])
    args = parser.parse_args(argv)
    wpisy = wczytaj(plik_historii())
    if args.polecenie == "lista":
        print(lista_html(wpisy))
    else:
        print("tak" if czy_problemy(wpisy) else "nie")
    return 0


if __name__ == "__main__":
    sys.exit(main())
