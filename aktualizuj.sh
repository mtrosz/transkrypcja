#!/bin/bash
# Aktualizacja Transkrypcji do wersji X.Y – uruchamiana w tle przez Transkrypcja.app („Zainstaluj”).
# Robi kopię zapasową, instaluje wydanie z GitHuba, przy błędzie przywraca kopię, na koniec otwiera aplikację.
set -uo pipefail

# install.sh nadpisuje ten plik w trakcie – bash czyta skrypt kawałkami, więc pracujemy na kopii.
if [ -z "${AKTUALIZUJ_Z_KOPII:-}" ]; then
  KOPIA_SKRYPTU="$(mktemp -t aktualizuj)"
  cp "$0" "$KOPIA_SKRYPTU"
  AKTUALIZUJ_Z_KOPII=1 exec /bin/bash "$KOPIA_SKRYPTU" "$@"
fi
# Tu $0 to tymczasowa kopia skryptu – sprzątamy ją przy wyjściu.
trap 'rm -f "$0"' EXIT

export HF_HUB_DISABLE_PROGRESS_BARS=1

WERSJA="${1:?Użycie: aktualizuj.sh X.Y}"
APP_DIR="$HOME/Library/Application Support/Transkrypcja"
PY="$APP_DIR/venv/bin/python"
LOG="$APP_DIR/log.txt"
KOPIA="$APP_DIR/kopia"
WYNIK="$APP_DIR/wynik-aktualizacji.txt"
APP_PATH="$(cat "$APP_DIR/sciezka-aplikacji.txt" 2>/dev/null || echo /Applications/Transkrypcja.app)"

loguj() { printf -- '--- %s aktualizacja do %s: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$WERSJA" "$1" >> "$LOG"; }

# Blokada z numerem procesu: po awarii, zaniku prądu albo SIGKILL zostaje nieaktualna – wtedy ją usuwamy.
BLOKADA="$APP_DIR/aktualizacja.lock"
if ! mkdir "$BLOKADA" 2>/dev/null; then
  STARY_PID="$(cat "$BLOKADA/pid" 2>/dev/null || true)"
  if [ -n "$STARY_PID" ] && kill -0 "$STARY_PID" 2>/dev/null \
     && ps -p "$STARY_PID" -o command= 2>/dev/null | grep -q aktualizuj; then
    exit 0   # inna aktualizacja naprawdę trwa – ona otworzy aplikację
  fi
  loguj "usuwam nieaktualną blokadę"
  rm -rf "$BLOKADA"
  mkdir "$BLOKADA" || { open "$APP_PATH"; exit 1; }
fi
echo $$ > "$BLOKADA/pid"
# Pułapka dopiero po zdobyciu blokady, żeby nie usunąć cudzej.
trap 'rm -f "$0"; rm -rf "$BLOKADA"' EXIT
TMP="$(mktemp -d)"

# Czekamy, aż aplikacja się zamknie (najwyżej 30 s).
for _ in $(seq 1 30); do
  pgrep -f 'Transkrypcja.app/Contents/MacOS' >/dev/null || break
  sleep 1
done

loguj "start"
# Kopia zapasowa jest wszystko albo nic – bez pełnej kopii nie instalujemy.
if ! { rm -rf "$KOPIA" && mkdir -p "$KOPIA" \
  && cp -R "$APP_DIR/silnik" "$KOPIA/silnik" \
  && { [ ! -f "$APP_DIR/VERSION" ] || cp "$APP_DIR/VERSION" "$KOPIA/VERSION"; } \
  && cp "$APP_DIR/aktualizuj.sh" "$KOPIA/aktualizuj.sh" \
  && { [ ! -d "$APP_PATH" ] || ditto "$APP_PATH" "$KOPIA/Transkrypcja.app"; }; } >> "$LOG" 2>&1; then
  loguj "nie udało się zrobić kopii zapasowej – przerywam"
  printf 'blad\n' > "$WYNIK"
  rm -rf "$KOPIA" "$TMP"
  rm -rf "$BLOKADA"
  open "$APP_PATH"
  exit 1
fi

zainstaluj() {
  local adres katalog
  adres="$("$PY" "$APP_DIR/silnik/wersja.py" adres-zip "$WERSJA")" || return 1
  curl -fsSL --connect-timeout 20 --max-time 900 "$adres" -o "$TMP/wydanie.zip" || return 1
  ditto -x -k "$TMP/wydanie.zip" "$TMP/rozpakowane" || return 1
  katalog="$(find "$TMP/rozpakowane" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$katalog" ] || return 1
  bash "$katalog/install.sh" --aktualizacja --wersja "$WERSJA" </dev/null
}

if zainstaluj >> "$LOG" 2>&1; then
  loguj "ok"
  printf 'ok %s\n' "$WERSJA" > "$WYNIK"
  rm -rf "$KOPIA"
else
  loguj "nieudana – przywracam poprzednią wersję"
  if { rm -rf "$APP_DIR/silnik" && cp -R "$KOPIA/silnik" "$APP_DIR/silnik" \
    && { [ ! -f "$KOPIA/VERSION" ] || cp "$KOPIA/VERSION" "$APP_DIR/VERSION"; } \
    && cp "$KOPIA/aktualizuj.sh" "$APP_DIR/aktualizuj.sh" \
    && { [ ! -d "$KOPIA/Transkrypcja.app" ] || { rm -rf "$APP_PATH" && ditto "$KOPIA/Transkrypcja.app" "$APP_PATH"; }; }; } >> "$LOG" 2>&1; then
    rm -rf "$KOPIA"
  else
    loguj "przywracanie nie powiodło się – kopia zachowana w $KOPIA"
  fi
  printf 'blad\n' > "$WYNIK"
fi

rm -rf "$TMP"
rm -rf "$BLOKADA"
# install.sh mógł wybrać inne miejsce aplikacji.
APP_PATH="$(cat "$APP_DIR/sciezka-aplikacji.txt" 2>/dev/null || echo /Applications/Transkrypcja.app)"
open "$APP_PATH"
