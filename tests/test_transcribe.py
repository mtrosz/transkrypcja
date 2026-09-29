import json
import re
import os
import sys
import types
from pathlib import Path

import pytest
import transcribe
import zapis
from fragment import Fragment
from status import Status

FRAGMENTY = [Fragment(0, 2, "Dzień dobry."), Fragment(2.5, 4, "Zaczynamy wykład.")]
NAPRAWA = "Coś poszło nie tak przy pliku „Wykład 3.m4a”. Aplikacja wymaga naprawy – poproś o pomoc."


class AtrapaSilnika:
    def __init__(self, fragmenty=None, blad_odczytu=None, blad_transkrypcji=None, status_plik=None):
        self.fragmenty = fragmenty or []
        self.blad_odczytu = blad_odczytu
        self.blad_transkrypcji = blad_transkrypcji
        self.status_plik = status_plik
        self.wywolanie = None
        self.status_w_trakcie = None

    def wczytaj_audio(self, sciezka):
        if self.blad_odczytu:
            raise self.blad_odczytu
        return "AUDIO"

    def transkrybuj(self, audio, tryb, podpowiedz, postep):
        self.wywolanie = (audio, tryb, podpowiedz)
        postep(0.5)
        if self.status_plik:
            self.status_w_trakcie = json.loads(self.status_plik.read_text(encoding="utf-8"))
        if self.blad_transkrypcji:
            raise self.blad_transkrypcji
        return self.fragmenty


def odpal(tmp_path, silnik, format="txt", nazwa="Wykład 3.m4a", podpowiedz="Wykład z prawa.", czas=False):
    nagranie = tmp_path / nazwa
    nagranie.write_bytes(b"audio")
    status_plik = tmp_path / "status.json"
    log = tmp_path / "log.txt"
    biurko = tmp_path / "Biurko"
    biurko.mkdir(exist_ok=True)
    kod = transcribe.uruchom(
        nagranie, format, "dokladnie", Status(status_plik, odstep_s=0), silnik, podpowiedz, log, biurko, czas=czas
    )
    return kod, json.loads(status_plik.read_text(encoding="utf-8")), log


def test_sukces_zapisuje_plik_i_status(tmp_path):
    kod, st, _ = odpal(tmp_path, AtrapaSilnika(FRAGMENTY))
    assert kod == 0
    assert st["etap"] == "gotowe"
    assert st["wynik"] == str(tmp_path / "Wykład 3.txt")
    assert st["uwaga"] == ""
    assert Path(st["wynik"]).read_text(encoding="utf-8") == "Dzień dobry. Zaczynamy wykład.\n"


def test_przekazuje_tryb_i_podpowiedz(tmp_path):
    silnik = AtrapaSilnika(FRAGMENTY)
    odpal(tmp_path, silnik)
    assert silnik.wywolanie == ("AUDIO", "dokladnie", "Wykład z prawa.")


def test_postep_trafia_do_statusu(tmp_path):
    silnik = AtrapaSilnika(FRAGMENTY, status_plik=tmp_path / "status.json")
    odpal(tmp_path, silnik)
    assert silnik.status_w_trakcie["etap"] == "transkrypcja"
    assert silnik.status_w_trakcie["procent"] == 50


def test_blad_odczytu(tmp_path):
    kod, st, log = odpal(tmp_path, AtrapaSilnika(blad_odczytu=RuntimeError("ffmpeg: Invalid data")))
    assert kod == 1
    assert st["etap"] == "blad"
    assert st["blad"] == "Nie udało się odczytać pliku „Wykład 3.m4a”. Czy to na pewno nagranie?"
    assert "ffmpeg: Invalid data" in log.read_text(encoding="utf-8")


def test_cisza_nie_tworzy_pliku(tmp_path):
    cisza = [Fragment(0, 30, "Dziękuję za obejrzenie.", 0.95, -1.8)]
    kod, st, _ = odpal(tmp_path, AtrapaSilnika(cisza))
    assert kod == 1
    assert st["blad"] == "W nagraniu „Wykład 3.m4a” nie wykryto mowy."
    assert not (tmp_path / "Wykład 3.txt").exists()


def test_nieoczekiwany_blad(tmp_path):
    kod, st, log = odpal(tmp_path, AtrapaSilnika(blad_transkrypcji=ValueError("model zepsuty")))
    assert kod == 1
    assert st["blad"] == NAPRAWA
    assert "model zepsuty" in log.read_text(encoding="utf-8")


def test_filtruje_powtorzenia(tmp_path):
    fr = [Fragment(0, 1, "Proszę."), Fragment(1, 2, "Proszę."), Fragment(2, 3, "Proszę."), Fragment(3, 4, "Dalej.")]
    _, st, _ = odpal(tmp_path, AtrapaSilnika(fr))
    assert Path(st["wynik"]).read_text(encoding="utf-8") == "Proszę.\n\nDalej.\n"


def test_uwaga_o_biurku(tmp_path, monkeypatch):
    monkeypatch.setattr(zapis.os, "access", lambda sciezka, tryb: Path(sciezka) != tmp_path)
    _, st, _ = odpal(tmp_path, AtrapaSilnika(FRAGMENTY))
    assert st["wynik"] == str(tmp_path / "Biurko" / "Wykład 3.txt")
    assert st["uwaga"] == "Plik zapisano na Biurku."


def test_polskie_znaki_w_nazwie(tmp_path):
    _, st, _ = odpal(tmp_path, AtrapaSilnika(FRAGMENTY), format="docx", nazwa="Prawo – wykład „zobowiązania”.m4a")
    assert Path(st["wynik"]).name == "Prawo – wykład „zobowiązania”.docx"
    assert Path(st["wynik"]).exists()


def test_wczytaj_podpowiedz(tmp_path):
    p = tmp_path / "slownik.txt"
    p.write_text("  Wykład z prawa.\n", encoding="utf-8")
    assert transcribe.wczytaj_podpowiedz(p) == "Wykład z prawa."
    p.write_text("\n", encoding="utf-8")
    assert transcribe.wczytaj_podpowiedz(p) is None
    assert transcribe.wczytaj_podpowiedz(tmp_path / "brak.txt") is None


def test_slownik_w_repo_miesci_sie_w_limicie():
    tekst = transcribe.wczytaj_podpowiedz(transcribe.SLOWNIK)
    assert tekst and len(tekst) <= 500


def test_slownik_w_repo_bez_skrotow():
    # Skróty typu "k.p.c." Whisper przepisywał potem do transkrypcji w przypadkowych miejscach.
    tekst = transcribe.wczytaj_podpowiedz(transcribe.SLOWNIK)
    assert not re.search(r"\w{1,3}\.\w{1,3}\.", tekst)


def test_brak_dostepu_do_pliku(tmp_path, monkeypatch):
    def odmow(sciezka):
        raise PermissionError("Operation not permitted")

    silnik = AtrapaSilnika(FRAGMENTY)
    wywolano = []
    silnik.wczytaj_audio = lambda sciezka: wywolano.append(sciezka)
    monkeypatch.setattr(transcribe, "sprawdz_dostep", odmow)
    kod, st, log = odpal(tmp_path, silnik)
    assert kod == 1
    assert st["etap"] == "blad"
    assert st["blad"] == (
        "macOS nie pozwolił otworzyć pliku „Wykład 3.m4a”. Otwórz Ustawienia systemowe → "
        "Prywatność i ochrona → Pliki i foldery, włącz dostęp dla aplikacji Transkrypcja i spróbuj ponownie."
    )
    assert "PermissionError" in log.read_text(encoding="utf-8")
    assert wywolano == []


def test_main_bez_mlx_zglasza_naprawe(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSKRYPCJA_KATALOG", str(tmp_path))
    for zmienna in ("PATH", "HF_HOME", "HF_HUB_OFFLINE"):
        monkeypatch.setenv(zmienna, os.environ.get(zmienna, ""))
    monkeypatch.setitem(sys.modules, "whisper_mlx", None)
    monkeypatch.setattr(transcribe.signal, "signal", lambda *a: None)
    nagranie = tmp_path / "Wykład 3.m4a"
    nagranie.write_bytes(b"audio")
    status_plik = tmp_path / "status.json"

    kod = transcribe.main([str(nagranie), "--format", "txt", "--tryb", "szybko", "--status", str(status_plik)])

    assert kod == 1
    assert json.loads(status_plik.read_text(encoding="utf-8"))["blad"] == NAPRAWA
    assert (tmp_path / "log.txt").exists()
    assert os.environ["HF_HOME"] == str(tmp_path / "modele")
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["PATH"].startswith(str(tmp_path / "bin") + os.pathsep)


def test_uruchom_ze_znacznikami_czasu(tmp_path):
    _, st, _ = odpal(tmp_path, AtrapaSilnika(FRAGMENTY), format="txt", czas=True)
    assert Path(st["wynik"]).read_text(encoding="utf-8") == (
        "[00:00:00] Dzień dobry.\n[00:00:02] Zaczynamy wykład.\n"
    )


def test_main_przekazuje_czas(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSKRYPCJA_KATALOG", str(tmp_path))
    for zmienna in ("PATH", "HF_HOME", "HF_HUB_OFFLINE"):
        monkeypatch.setenv(zmienna, os.environ.get(zmienna, ""))
    monkeypatch.setitem(sys.modules, "whisper_mlx", types.ModuleType("whisper_mlx"))
    monkeypatch.setattr(transcribe.signal, "signal", lambda *a: None)
    wywolania = []
    monkeypatch.setattr(transcribe, "uruchom", lambda *a, **k: wywolania.append((a, k)) or 0)
    nagranie = tmp_path / "Wykład 3.m4a"
    nagranie.write_bytes(b"audio")

    kod = transcribe.main([str(nagranie), "--format", "docx", "--czas", "--tryb", "szybko",
                           "--status", str(tmp_path / "status.json")])

    assert kod == 0
    argumenty, nazwane = wywolania[0]
    assert argumenty[1] == "docx"
    assert nazwane["czas"] is True


def test_main_odrzuca_stary_format_txt_czas(tmp_path):
    with pytest.raises(SystemExit):
        transcribe.main([str(tmp_path / "a.m4a"), "--format", "txt_czas", "--tryb", "szybko",
                         "--status", str(tmp_path / "status.json")])
