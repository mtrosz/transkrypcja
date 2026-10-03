#!/bin/bash
# Instalator / naprawa aplikacji Transkrypcja na Macu z Apple Silicon.
# Uruchom w Terminalu z katalogu repozytorium:  bash install.sh
# Opcje: --aktualizacja (bez zmian w Docku; używa tego aktualizuj.sh), --wersja X.Y (numer do zapisania w VERSION).
set -euo pipefail

APP_DIR="$HOME/Library/Application Support/Transkrypcja"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$APP_DIR/venv/bin/python"

AKTUALIZACJA=0
WERSJA_INSTALOWANA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --aktualizacja) AKTUALIZACJA=1 ;;
    --wersja) WERSJA_INSTALOWANA="${2:-}"; shift ;;
    *) printf 'Nieznana opcja: %s\n' "$1" >&2; exit 1 ;;
  esac
  shift
done
[ -n "$WERSJA_INSTALOWANA" ] || WERSJA_INSTALOWANA="$(tr -d '[:space:]' < "$REPO_DIR/VERSION")"

krok() { printf '\n==> %s\n' "$1"; }
blad() { printf '\nBŁĄD: %s\n' "$1" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || blad "Ten instalator działa tylko na macOS."
[ "$(uname -m)" = "arm64" ] || blad "Ta aplikacja wymaga Maca z procesorem Apple (M1 lub nowszym)."

mkdir -p "$APP_DIR/bin"
export UV_PYTHON_INSTALL_DIR="$APP_DIR/python"
export UV_CACHE_DIR="$APP_DIR/cache"
export UV_PYTHON_PREFERENCE=only-managed

krok "Instaluję uv (menedżer Pythona)"
if [ ! -x "$APP_DIR/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$APP_DIR/bin" UV_NO_MODIFY_PATH=1 sh
fi

krok "Tworzę środowisko Pythona i instaluję biblioteki"
"$PY" -c 'import sys' 2>/dev/null || "$APP_DIR/bin/uv" venv --clear --python 3.12 "$APP_DIR/venv"
# --only-binary: bez gotowej paczki arm64 imageio-ffmpeg buduje się ze źródeł, bez ffmpeg w środku.
"$APP_DIR/bin/uv" pip install --python "$PY" --only-binary imageio-ffmpeg \
  "mlx-whisper==0.4.2" "python-docx==1.1.2" "imageio-ffmpeg==0.6.0"

krok "Podłączam ffmpeg"
FFMPEG="$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
ln -sf "$FFMPEG" "$APP_DIR/bin/ffmpeg"

krok "Kopiuję silnik"
mkdir -p "$APP_DIR/silnik"
rm -f "$APP_DIR"/silnik/*.py
cp "$REPO_DIR"/silnik/*.py "$APP_DIR/silnik/"
SLOWNIK="$APP_DIR/silnik/slownik.txt"
if [ "$AKTUALIZACJA" = 1 ] && [ -f "$SLOWNIK" ]; then
  # Aktualizacja w aplikacji nie nadpisuje słownika użytkownika.
  if ! cmp -s "$SLOWNIK" "$REPO_DIR/silnik/slownik.txt"; then
    cp "$REPO_DIR/silnik/slownik.txt" "$APP_DIR/silnik/slownik-nowy.txt"
    printf 'Twój słownik zostawiono bez zmian; nowszy słownik z wydania zapisano jako slownik-nowy.txt.\n'
  fi
else
  if [ -f "$SLOWNIK" ] && ! cmp -s "$SLOWNIK" "$REPO_DIR/silnik/slownik.txt"; then
    cp "$SLOWNIK" "$APP_DIR/silnik/slownik-poprzedni.txt"
    printf 'Nowy słownik zainstalowany; poprzedni zapisano jako slownik-poprzedni.txt (przenieś z niego swoje dopiski).\n'
  fi
  cp "$REPO_DIR/silnik/slownik.txt" "$SLOWNIK"
fi
cp "$REPO_DIR/aktualizuj.sh" "$APP_DIR/aktualizuj.sh"

krok "Pobieram modele (ok. 4,5 GB – to potrwa)"
HF_HOME="$APP_DIR/modele" PYTHONPATH="$APP_DIR/silnik" "$PY" -c '
from huggingface_hub import snapshot_download
from whisper_mlx import MODELE
for repo in MODELE.values():
    print("Pobieram", repo)
    snapshot_download(repo)
'

krok "Buduję aplikację Transkrypcja.app"
if [ -w /Applications ]; then APLIKACJE="/Applications"; else APLIKACJE="$HOME/Applications"; mkdir -p "$APLIKACJE"; fi
APP_PATH="$APLIKACJE/Transkrypcja.app"
rm -rf "$APP_PATH"
# osacompile nie zawsze rozpoznaje UTF-8 – UTF-16 z BOM gwarantuje poprawne polskie znaki w okienkach
# (kodek utf-16 w Pythonie zawsze zapisuje BOM, w przeciwieństwie do iconv).
ZRODLO="$(mktemp -d)/Transkrypcja.applescript"
"$PY" -c 'import sys; open(sys.argv[2], "w", encoding="utf-16").write(open(sys.argv[1], encoding="utf-8").read())' "$REPO_DIR/app/Transkrypcja.applescript" "$ZRODLO"
osacompile -o "$APP_PATH" "$ZRODLO"
rm -rf "$(dirname "$ZRODLO")"
printf '%s\n' "$APP_PATH" > "$APP_DIR/sciezka-aplikacji.txt"

if [ "$AKTUALIZACJA" = 0 ]; then
  krok "Dodaję ikonkę do Docka"
  if ! defaults read com.apple.dock persistent-apps 2>/dev/null | grep -q "Transkrypcja.app"; then
    defaults write com.apple.dock persistent-apps -array-add \
      "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$APP_PATH</string><key>_CFURLStringType</key><integer>0</integer></dict></dict></dict>"
    killall Dock 2>/dev/null || true
  fi
fi

krok "Test: przepisuję krótkie nagranie próbne"
TEST_DIR="$(mktemp -d)"
if say -v Zosia "Sąd Najwyższy oddalił kasację." -o "$TEST_DIR/test.aiff" 2>/dev/null; then
  "$PY" "$APP_DIR/silnik/transcribe.py" "$TEST_DIR/test.aiff" --format txt --tryb szybko \
    --status "$TEST_DIR/status.json" --bez-historii || true
  if grep -q "ajwyższ" "$TEST_DIR/test.txt" 2>/dev/null && grep -q "kasacj" "$TEST_DIR/test.txt"; then
    printf '\nINSTALACJA OK. Wynik testu: %s\n' "$(cat "$TEST_DIR/test.txt")"
  else
    printf '\nTest NIE przeszedł.\nStatus: %s\n' "$(cat "$TEST_DIR/status.json" 2>/dev/null || echo brak)"
    printf 'Wynik: %s\n' "$(cat "$TEST_DIR/test.txt" 2>/dev/null || echo brak)"
    printf 'Ostatnie linie logu:\n'
    tail -n 30 "$APP_DIR/log.txt" 2>/dev/null || true
    rm -rf "$TEST_DIR"
    exit 1
  fi
else
  printf '\nTest pominięty – sprawdź ręcznie, przeciągając dowolne nagranie na ikonkę.\n'
fi
rm -rf "$TEST_DIR"

# Wersję zapisujemy na końcu – nieudana instalacja zostawia poprzedni numer.
printf '%s\n' "$WERSJA_INSTALOWANA" > "$APP_DIR/VERSION"
printf 'Zainstalowana wersja: %s\n' "$WERSJA_INSTALOWANA"
