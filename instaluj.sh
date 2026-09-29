#!/bin/bash
# Pierwsza instalacja Transkrypcji z najnowszego wydania na GitHubie. Uruchom w Terminalu:
#   curl -fsSL https://raw.githubusercontent.com/mtrosz/transkrypcja/main/instaluj.sh | bash
set -euo pipefail

# Całość w main(), wywoływanym na samym końcu: przy „curl | bash” urwane pobieranie nie uruchomi połowy skryptu.
main() {
  TMP=""
  local REPO="mtrosz/transkrypcja" TAG WERSJA KATALOG
  blad() { printf '\nBŁĄD: %s\n' "$1" >&2; exit 1; }

  TMP="$(mktemp -d)"  # nie local: pułapka EXIT odpala się już po powrocie z main
  trap 'rm -rf "$TMP"' EXIT

  printf '==> Sprawdzam najnowszą wersję Transkrypcji\n'
  curl -fsSL --connect-timeout 20 "https://api.github.com/repos/$REPO/releases/latest" -o "$TMP/wydanie.json" \
    || blad "Nie udało się pobrać informacji o wydaniu z GitHuba – sprawdź internet albo czy wydanie istnieje."
  TAG="$(sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' "$TMP/wydanie.json" | head -n 1)"
  [ -n "$TAG" ] || blad "Nie znaleziono żadnego wydania Transkrypcji."
  WERSJA="${TAG#v}"

  printf '==> Pobieram wersję %s\n' "$WERSJA"
  curl -fsSL --connect-timeout 20 --max-time 900 "https://github.com/$REPO/archive/refs/tags/$TAG.zip" -o "$TMP/wydanie.zip" \
    || blad "Nie udało się pobrać wersji $WERSJA."
  ditto -x -k "$TMP/wydanie.zip" "$TMP/rozpakowane" \
    || blad "Nie udało się rozpakować pobranego wydania."
  KATALOG="$(find "$TMP/rozpakowane" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$KATALOG" ] || blad "Pobrane wydanie jest puste."

  # </dev/null: przy „curl … | bash” standardowe wejście to ten skrypt – instalator nie może go czytać.
  bash "$KATALOG/install.sh" --wersja "$WERSJA" </dev/null
}

main "$@"
