import json
import re
import subprocess
from pathlib import Path

import pytest

import wersja


@pytest.mark.parametrize(
    "nowa, zainstalowana, oczekiwane",
    [
        ("1.3", "1.2", True),
        ("1.10", "1.9", True),
        ("2.0", "1.99.9", True),
        ("1.2", "1.2", False),
        ("1.3.0", "1.3", False),
        ("1.3", "1.3.1", False),
        ("1.1", "1.2", False),
        ("śmieci", "1.2", False),
        ("", "1.2", False),
        (None, "1.2", False),
        ("1.3", "zepsuta", False),
        ("1.-3", "1.2", False),
        ("+2.0", "1.2", False),
        ("1. 3", "1.2", False),
        ("١.٣", "1.2", False),
    ],
)
def test_jest_nowsza(nowa, zainstalowana, oczekiwane):
    assert wersja.jest_nowsza(nowa, zainstalowana) is oczekiwane


def test_jest_nowsza_bez_zainstalowanej():
    assert wersja.jest_nowsza("1.3", None) is False


def odpowiedz(dane):
    return lambda adres: json.dumps(dane)


def test_najnowsze_wydanie_zdejmuje_v():
    adresy = []

    def pobierz(adres):
        adresy.append(adres)
        return json.dumps({"tag_name": "v1.3", "name": "Wersja 1.3"})

    assert wersja.najnowsze_wydanie(pobierz) == "1.3"
    assert adresy == ["https://api.github.com/repos/mtrosz/transkrypcja/releases/latest"]


def test_najnowsze_wydanie_bez_v():
    assert wersja.najnowsze_wydanie(odpowiedz({"tag_name": "1.4"})) == "1.4"


def blad_sieci(adres):
    raise subprocess.CalledProcessError(22, ["curl"])


def limit_czasu(adres):
    raise subprocess.TimeoutExpired(["curl"], 5)


@pytest.mark.parametrize(
    "pobierz",
    [
        blad_sieci,
        limit_czasu,
        lambda adres: "<html>Rate limit</html>",
        odpowiedz({"message": "Not Found"}),
        odpowiedz({"tag_name": None}),
        odpowiedz(["lista"]),
    ],
)
def test_najnowsze_wydanie_bledy(pobierz):
    assert wersja.najnowsze_wydanie(pobierz) is None


def test_zainstalowana_wersja(tmp_path):
    plik = tmp_path / "VERSION"
    plik.write_text("1.2\n", encoding="utf-8")
    assert wersja.zainstalowana_wersja(plik) == "1.2"
    assert wersja.zainstalowana_wersja(tmp_path / "brak") is None


def test_zainstalowana_wersja_invalid_utf8(tmp_path, capsys):
    plik = tmp_path / "VERSION"
    plik.write_bytes(b"\xff\xfe\x00")
    assert wersja.zainstalowana_wersja(plik) is None
    kod = wersja.main(["sprawdz"], pobierz=odpowiedz({"tag_name": "v1.3"}), plik_wersji=plik)
    assert kod == 0
    assert capsys.readouterr().out == ""


def test_adres_zip():
    assert wersja.adres_zip("1.3") == "https://github.com/mtrosz/transkrypcja/archive/refs/tags/v1.3.zip"


def test_cli_sprawdz_wypisuje_nowsza(tmp_path, capsys):
    plik = tmp_path / "VERSION"
    plik.write_text("1.2", encoding="utf-8")
    kod = wersja.main(["sprawdz"], pobierz=odpowiedz({"tag_name": "v1.3"}), plik_wersji=plik)
    assert kod == 0
    assert capsys.readouterr().out == "1.3\n"


@pytest.mark.parametrize("pobierz", [odpowiedz({"tag_name": "v1.2"}), blad_sieci])
def test_cli_sprawdz_milczy(tmp_path, capsys, pobierz):
    plik = tmp_path / "VERSION"
    plik.write_text("1.2", encoding="utf-8")
    assert wersja.main(["sprawdz"], pobierz=pobierz, plik_wersji=plik) == 0
    assert capsys.readouterr().out == ""


def test_cli_adres_zip(capsys):
    assert wersja.main(["adres-zip", "1.3"]) == 0
    assert capsys.readouterr().out == "https://github.com/mtrosz/transkrypcja/archive/refs/tags/v1.3.zip\n"


def test_plik_version_w_repo_ma_poprawny_format():
    tekst = (Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+(\.\d+)?", tekst)
