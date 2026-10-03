import datetime
import json
from pathlib import Path

import historia

TERAZ = datetime.datetime(2026, 10, 3, 14, 20, 5)
DZIS = datetime.date(2026, 10, 3)


def zywy(pid):
    return True


def martwy(pid):
    return False


def test_dodaj_tworzy_wpis_w_trakcie(tmp_path):
    plik = tmp_path / "historia.json"
    id_wpisu = historia.dodaj(plik, tmp_path / "Wykład 3.m4a", pid=123, teraz=TERAZ)
    wpisy = historia.wczytaj(plik)
    assert wpisy == [{
        "id": id_wpisu, "data": "2026-10-03T14:20:05", "nagranie": str(tmp_path / "Wykład 3.m4a"),
        "status": "w_trakcie", "pid": 123, "wynik": "", "blad": "",
    }]


def test_zakoncz_gotowe_i_blad(tmp_path):
    plik = tmp_path / "historia.json"
    a = historia.dodaj(plik, tmp_path / "a.m4a", pid=1, teraz=TERAZ)
    b = historia.dodaj(plik, tmp_path / "b.m4a", pid=2, teraz=TERAZ)
    historia.zakoncz(plik, a, "gotowe", wynik=tmp_path / "a.docx")
    historia.zakoncz(plik, b, "blad", blad="W nagraniu „b.m4a” nie wykryto mowy.")
    wpisy = {w["id"]: w for w in historia.wczytaj(plik)}
    assert wpisy[a]["status"] == "gotowe"
    assert wpisy[a]["wynik"] == str(tmp_path / "a.docx")
    assert wpisy[b]["status"] == "blad"
    assert wpisy[b]["blad"] == "W nagraniu „b.m4a” nie wykryto mowy."


def test_identyfikatory_sa_unikalne(tmp_path):
    plik = tmp_path / "historia.json"
    ids = {historia.dodaj(plik, tmp_path / "a.m4a", pid=1, teraz=TERAZ) for _ in range(3)}
    assert len(ids) == 3


def test_zakoncz_nieznanego_wpisu_nic_nie_robi(tmp_path):
    plik = tmp_path / "historia.json"
    historia.dodaj(plik, tmp_path / "a.m4a", pid=1, teraz=TERAZ)
    historia.zakoncz(plik, "nie-ma", "gotowe", wynik=tmp_path / "a.txt")
    assert historia.wczytaj(plik)[0]["status"] == "w_trakcie"


def test_limit_wpisow(tmp_path):
    plik = tmp_path / "historia.json"
    for i in range(historia.MAKS_WPISOW + 5):
        historia.dodaj(plik, tmp_path / f"{i}.m4a", pid=1, teraz=TERAZ)
    wpisy = historia.wczytaj(plik)
    assert len(wpisy) == historia.MAKS_WPISOW
    assert wpisy[-1]["nagranie"] == str(tmp_path / f"{historia.MAKS_WPISOW + 4}.m4a")
    assert wpisy[0]["nagranie"] == str(tmp_path / "5.m4a")


def test_brak_pliku_to_pusta_historia(tmp_path):
    assert historia.wczytaj(tmp_path / "historia.json") == []


def test_uszkodzony_plik_odkladany_na_bok(tmp_path):
    plik = tmp_path / "historia.json"
    plik.write_text("{to nie json", encoding="utf-8")
    assert historia.wczytaj(plik) == []
    historia.dodaj(plik, tmp_path / "a.m4a", pid=1, teraz=TERAZ)
    assert len(historia.wczytaj(plik)) == 1
    assert (tmp_path / "historia-uszkodzona.json").read_text(encoding="utf-8") == "{to nie json"


def test_zapis_atomowy_nie_zostawia_pliku_tymczasowego(tmp_path):
    plik = tmp_path / "historia.json"
    historia.dodaj(plik, tmp_path / "a.m4a", pid=1, teraz=TERAZ)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["historia.json"]
    json.loads(plik.read_text(encoding="utf-8"))


def test_stan_przerwane_gdy_proces_nie_zyje(tmp_path):
    wpis = {"status": "w_trakcie", "pid": 5}
    assert historia.stan(wpis, zyje=martwy) == "przerwane"
    assert historia.stan(wpis, zyje=zywy) == "w_trakcie"
    assert historia.stan({"status": "gotowe", "pid": 5}, zyje=martwy) == "gotowe"
    assert historia.stan({"status": "blad", "pid": 5}, zyje=martwy) == "blad"


def _historia_z(tmp_path, *wpisy):
    plik = tmp_path / "historia.json"
    for nagranie, status, wynik, blad in wpisy:
        id_wpisu = historia.dodaj(plik, nagranie, pid=1, teraz=TERAZ)
        if status != "w_trakcie":
            historia.zakoncz(plik, id_wpisu, status, wynik=wynik, blad=blad)
    return historia.wczytaj(plik)


def test_lista_html_pusta_historia():
    assert historia.lista_html([], zyje=martwy, dzis=DZIS) == ""


def test_lista_html_gotowe_z_linkami(tmp_path):
    nagranie = tmp_path / "Wykład 3.m4a"
    nagranie.write_bytes(b"a")
    wynik = tmp_path / "Wykład 3.docx"
    wynik.write_bytes(b"d")
    html = historia.lista_html(_historia_z(tmp_path, (nagranie, "gotowe", wynik, "")), zyje=martwy, dzis=DZIS)
    assert f'href="{wynik.as_uri()}"' in html
    assert f'href="{tmp_path.as_uri()}/"' in html
    assert "3 pa&#378;, 14:20" in html
    assert "&#9989;" in html  # ✅


def test_lista_html_tylko_ascii(tmp_path):
    # do shell script w AppleScripcie nie gwarantuje UTF-8 – polskie znaki i emoji idą jako encje.
    html = historia.lista_html(_historia_z(tmp_path, (tmp_path / "Zażółć.m4a", "w_trakcie", "", "")),
                               zyje=martwy, dzis=DZIS)
    assert html.isascii()
    assert "Za&#380;&#243;&#322;&#263;.m4a" in html


def test_lista_html_bledy_przerwane_i_brakujace_pliki(tmp_path):
    wpisy = _historia_z(
        tmp_path,
        (tmp_path / "a.m4a", "blad", "", "W nagraniu „a.m4a” nie wykryto mowy."),
        (tmp_path / "b.m4a", "w_trakcie", "", ""),
        (tmp_path / "c.m4a", "gotowe", tmp_path / "c.txt", ""),
    )
    html = historia.lista_html(wpisy, zyje=martwy, dzis=DZIS)
    assert "&#10060;" in html and "nie wykryto mowy" in html  # ❌
    assert "&#9888;" in html and "przerwane" in html  # ⚠️
    assert "href" not in html
    assert html.count("(plik przeniesiony)") == 4  # trzy nagrania i transkrypcja c.txt


def test_lista_html_najnowsze_na_gorze_i_limit(tmp_path):
    wpisy = _historia_z(tmp_path, *[(tmp_path / f"nr{i}.m4a", "w_trakcie", "", "") for i in range(35)])
    html = historia.lista_html(wpisy, zyje=martwy, dzis=DZIS)
    assert html.index("nr34.m4a") < html.index("nr33.m4a")
    assert "nr5.m4a" in html
    assert "nr4.m4a" not in html


def test_lista_html_escapuje_nazwy(tmp_path):
    html = historia.lista_html(_historia_z(tmp_path, (tmp_path / "<b>&.m4a", "w_trakcie", "", "")),
                               zyje=martwy, dzis=DZIS)
    assert "&lt;b&gt;&amp;.m4a" in html


def test_lista_html_rok_tylko_dla_starszych_wpisow(tmp_path):
    wpisy = _historia_z(tmp_path, (tmp_path / "a.m4a", "w_trakcie", "", ""))
    assert "3 pa&#378; 2026, 14:20" in historia.lista_html(wpisy, zyje=martwy, dzis=datetime.date(2027, 1, 5))


def test_czy_problemy(tmp_path):
    ok = _historia_z(tmp_path, (tmp_path / "a.m4a", "gotowe", tmp_path / "a.txt", ""))
    assert not historia.czy_problemy(ok, zyje=martwy)
    przerwane = ok + [{"status": "w_trakcie", "pid": 9}]
    assert historia.czy_problemy(przerwane, zyje=martwy)
    assert not historia.czy_problemy(przerwane, zyje=zywy)
    assert historia.czy_problemy(ok + [{"status": "blad", "pid": 9}], zyje=zywy)


def test_main_lista_i_czy_problemy(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TRANSKRYPCJA_KATALOG", str(tmp_path))
    assert historia.main(["lista"]) == 0
    assert historia.main(["czy-problemy"]) == 0
    assert capsys.readouterr().out == "\nnie\n"

    plik = tmp_path / "historia.json"
    id_wpisu = historia.dodaj(plik, tmp_path / "a.m4a", pid=1, teraz=TERAZ)
    historia.zakoncz(plik, id_wpisu, "blad", blad="Błąd.")
    historia.main(["lista"])
    historia.main(["czy-problemy"])
    wyjscie = capsys.readouterr().out
    assert "a.m4a" in wyjscie
    assert wyjscie.endswith("tak\n")
