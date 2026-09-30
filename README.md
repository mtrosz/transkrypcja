# Transkrypcja

Aplikacja na Maca (Apple M1 lub nowszy), która przepisuje nagrania wykładów na tekst – lokalnie, bez internetu.

## Instalacja (raz)

1. Zaloguj się na Macu na **koncie osoby, która będzie używać aplikacji** – aplikacja instaluje się dla użytkownika, który uruchamia instalator.
2. Otwórz **Terminal** (Cmd + spacja, wpisz „Terminal”, Enter), wklej i zatwierdź Enterem:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/mtrosz/transkrypcja/main/instaluj.sh | bash
   ```
3. Poczekaj, aż pojawi się `INSTALACJA OK` (pobieranie modeli ok. 4,5 GB). Ikonka **Transkrypcja** pojawi się w Docku.

Instalacje sprzed wersji 1.0 (bez automatycznych aktualizacji) wymagają jeszcze raz tej jednolinijkowej instalacji.

Nowe wersje aplikacja instaluje sama – przy uruchomieniu zapyta „Jest nowa wersja Transkrypcji… Zainstalować teraz?”.

Instalacja z pobranego repozytorium (bez jednolinijkowca): w jego folderze `bash install.sh`.

## Użycie

Przeciągnij nagranie (lub kilka) na ikonkę w Docku albo kliknij ikonkę i wybierz plik. W oknie wybierz:

- **Format** – Tekst albo Word,
- **Tryb** – Dokładnie (ok. 10–15 min na godzinę nagrania) albo Szybko (ok. 4–5 min),
- **Zapisz w** – obok nagrania, na Biurku, w Dokumentach albo w wybranym folderze (**Inny folder…**; zapamiętany folder pojawia się potem na liście),
- **Znaczniki czasu** – każdy fragment w osobnej linii z czasem, np. `[00:04:12]`,

i kliknij **Generuj** (albo Enter – okno pamięta ostatnie ustawienia). Gotowy plik pojawi się w wybranym miejscu – jeśli folderu nie ma (np. odłączony pendrive), plik trafi na Biurko.

## Pierwsze uruchomienie – pytania o dostęp

Gdy nagranie pochodzi z Biurka, Pobranych, Dokumentów, iCloud Drive albo z pendrive'a, macOS za pierwszym razem zapyta, czy Transkrypcja może mieć do niego dostęp. Odpowiedz **„Pozwól”**. Jeśli odmówiono, popraw to w: Ustawienia systemowe → Prywatność i ochrona → Pliki i foldery → Transkrypcja. macOS może zapytać ponownie po każdej aktualizacji (aplikacja jest wtedy budowana od nowa) i po każdym ręcznym uruchomieniu `install.sh`.

## Słownik terminów

`~/Library/Application Support/Transkrypcja/silnik/slownik.txt` – tekst podpowiadany Whisperowi (maks. ok. 500 znaków – dłuższy tekst Whisper i tak obetnie). Pisz pełnymi zdaniami, bez skrótów typu „k.p.c.” – skróty Whisper potrafi potem wstawiać w przypadkowe miejsca transkrypcji. Dopisz nazwiska wykładowców i terminy, które są przekręcane. Automatyczne aktualizacje zostawiają Twój `slownik.txt` bez zmian; jeśli nowsze wydanie ma inny słownik domyślny, zapisują go jako `slownik-nowy.txt`. Ręczne `install.sh` zastępuje słownik wersją z repozytorium, a Twój zostawia jako `slownik-poprzedni.txt`.

## Gdy coś nie działa

Szczegóły błędów: `~/Library/Application Support/Transkrypcja/log.txt`.

## Odinstalowanie

Usuń `Transkrypcja.app` z folderu Aplikacje (i z Docka) oraz folder `~/Library/Application Support/Transkrypcja`.

## Wydawanie nowej wersji

Aplikacje u użytkowników pobierają tylko **wydania** (GitHub Releases) – zwykły `git push` do nich nie trafia.

1. Zmień numer w pliku `VERSION` (np. `1.3`).
2. `git commit -am "Wersja 1.3"` i `git push`.
3. Utwórz wydanie z tagiem `v1.3`: na stronie repozytorium **Releases → Draft a new release → Choose a tag: `v1.3` → Publish release** (albo `gh release create v1.3 --generate-notes`).
   Wydanie musi być opublikowane – nie szkic (draft) i nie oznaczone jako „pre-release”; inaczej aplikacje go nie zobaczą.

Przy najbliższym uruchomieniu aplikacja zaproponuje aktualizację. Nieudana aktualizacja przywraca poprzednią wersję; szczegóły w `log.txt`.

## Rozwój (Windows)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install "python-docx==1.1.2" pytest
.venv/Scripts/python -m pytest
```
