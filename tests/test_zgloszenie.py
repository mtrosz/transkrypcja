from urllib.parse import parse_qs, unquote, urlsplit

import zgloszenie


def rozbierz(adres):
    czesci = urlsplit(adres)
    pola = {k: v[0] for k, v in parse_qs(czesci.query).items()}
    return czesci.scheme, unquote(czesci.path), pola


def test_adresat_temat_i_dane(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("--- 2026-10-03 14:20:00 /Users/a/Wykład.m4a\nTraceback: błąd\n", encoding="utf-8")
    schemat, adresat, pola = rozbierz(zgloszenie.link("1.2", log, macos="14.5", procesor="Apple M1"))
    assert schemat == "mailto"
    assert adresat == "mtroszgithub@gmail.com"
    assert pola["subject"] == "Transkrypcja – zgłoszenie błędu (wersja 1.2)"
    tresc = pola["body"]
    assert "Wersja aplikacji: 1.2" in tresc
    assert "macOS: 14.5" in tresc
    assert "Procesor: Apple M1" in tresc
    assert "Traceback: błąd" in tresc
    assert "\r\n" in tresc


def test_link_tylko_ascii(tmp_path):
    assert zgloszenie.link("1.2", tmp_path / "brak.txt", macos="14.5", procesor="M1").isascii()


def test_brak_logu(tmp_path):
    _, _, pola = rozbierz(zgloszenie.link("1.2", tmp_path / "brak.txt", macos="14.5", procesor="M1"))
    assert "(log jest pusty)" in pola["body"]


def test_koncowka_logu_od_pelnej_linii(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("".join(f"linia numer {i:04d}\n" for i in range(1000)), encoding="utf-8")
    koncowka = zgloszenie.koncowka_logu(log, znaki=100)
    assert len(koncowka) <= 100
    assert koncowka.startswith("linia numer ")
    assert koncowka.endswith("linia numer 0999")


def test_koncowka_krotkiego_logu_w_calosci(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("jedna linia\n", encoding="utf-8")
    assert zgloszenie.koncowka_logu(log) == "jedna linia"


def test_main_wypisuje_link(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TRANSKRYPCJA_KATALOG", str(tmp_path))
    (tmp_path / "VERSION").write_text("1.2\n", encoding="utf-8")
    assert zgloszenie.main(["link"]) == 0
    _, _, pola = rozbierz(capsys.readouterr().out.strip())
    assert pola["subject"].endswith("(wersja 1.2)")
