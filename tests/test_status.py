import json
from pathlib import Path

from status import Status


def czytaj(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_etap_zapisuje_wszystkie_klucze(tmp_path):
    p = tmp_path / "status.json"
    Status(p).etap("wczytywanie")
    assert czytaj(p) == {"etap": "wczytywanie", "procent": 0, "wynik": "", "blad": "", "uwaga": ""}


def test_postep_jest_dlawiony(tmp_path):
    p = tmp_path / "status.json"
    czas = [0.0]
    s = Status(p, zegar=lambda: czas[0], odstep_s=2.0)
    s.postep(10)
    assert czytaj(p)["procent"] == 10
    assert czytaj(p)["etap"] == "transkrypcja"
    czas[0] = 1.0
    s.postep(20)
    assert czytaj(p)["procent"] == 10
    czas[0] = 2.5
    s.postep(30)
    assert czytaj(p)["procent"] == 30


def test_postep_100_zawsze_zapisany(tmp_path):
    p = tmp_path / "status.json"
    s = Status(p, zegar=lambda: 0.0)
    s.postep(10)
    s.postep(100)
    assert czytaj(p)["procent"] == 100


def test_postep_przycina_i_obcina_ulamki(tmp_path):
    p = tmp_path / "status.json"
    s = Status(p, odstep_s=0)
    s.postep(42.9)
    assert czytaj(p)["procent"] == 42
    s.postep(-5)
    assert czytaj(p)["procent"] == 0
    s.postep(150)
    assert czytaj(p)["procent"] == 100


def test_wynik_z_polskimi_znakami(tmp_path):
    p = tmp_path / "status.json"
    plik = Path("/Users/ola/Wykłady/Wykład „3”.docx")
    Status(p).wynik(plik, "Plik zapisano na Biurku.")
    assert "Wykład „3”" in p.read_text(encoding="utf-8")
    assert czytaj(p) == {
        "etap": "gotowe",
        "procent": 100,
        "wynik": str(plik),
        "blad": "",
        "uwaga": "Plik zapisano na Biurku.",
    }


def test_blad(tmp_path):
    p = tmp_path / "status.json"
    Status(p).blad('W nagraniu „a.m4a" nie wykryto mowy.')
    assert czytaj(p)["etap"] == "blad"
    assert czytaj(p)["blad"] == 'W nagraniu „a.m4a" nie wykryto mowy.'


def test_nie_zostawia_plikow_tymczasowych(tmp_path):
    p = tmp_path / "status.json"
    s = Status(p, odstep_s=0)
    s.etap("wczytywanie")
    s.postep(50)
    s.wynik(tmp_path / "x.txt")
    assert [x.name for x in tmp_path.iterdir()] == ["status.json"]
