"""Adapter mlx-whisper. Jedyny moduł, który importuje mlx – działa tylko na Macu z Apple Silicon."""
import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import mlx_whisper
from mlx_whisper.audio import load_audio

from fragment import Fragment, z_segmentow
from pasek import fabryka_paska

MODELE = {
    "dokladnie": "mlx-community/whisper-large-v3-mlx",
    "szybko": "mlx-community/whisper-large-v3-turbo",
}

_modul_transcribe = importlib.import_module("mlx_whisper.transcribe")


def wczytaj_audio(sciezka: Path):
    return load_audio(str(sciezka))


def transkrybuj(audio, tryb: str, podpowiedz: str | None, postep: Callable[[float], None]) -> list[Fragment]:
    oryginalny_tqdm = _modul_transcribe.tqdm
    _modul_transcribe.tqdm = SimpleNamespace(tqdm=fabryka_paska(postep))
    try:
        wynik = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=MODELE[tryb],
            language="pl",
            initial_prompt=podpowiedz,
            condition_on_previous_text=False,
            # Pomija ciszę dłuższą niż 2 s zamiast pozwalać Whisperowi ją „dopowiadać” (wymaga znaczników słów).
            word_timestamps=True,
            hallucination_silence_threshold=2.0,
            verbose=False,
        )
    finally:
        _modul_transcribe.tqdm = oryginalny_tqdm
    return z_segmentow(wynik["segments"])
