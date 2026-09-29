-- Transkrypcja.app – okno i uruchamianie silnika. Całą pracę wykonuje silnik w Pythonie (silnik/transcribe.py),
-- który zgłasza postęp, wynik i błędy (po polsku) przez plik status.json.
use AppleScript version "2.4"
use scripting additions
use framework "Foundation"
use framework "AppKit"

property ETYKIETY_FORMATOW : {"Tekst", "Word"}
property KODY_FORMATOW : {"txt", "docx"}
property KLUCZE_TRYBOW : {"Dokładnie", "Szybko"}
property OPISY_TRYBOW : {"Dokładnie (10–15 min na godzinę)", "Szybko (4–5 min na godzinę)"}
property KODY_TRYBOW : {"dokladnie", "szybko"}
property TYTUL : "Transkrypcja"

on run
	if not przygotuj(true) then return
	try
		set pliki to choose file with prompt "Wybierz nagranie do przepisania:" with multiple selections allowed
	on error number -128
		return
	end try
	przetworz(pliki)
end run

on open pliki
	if not przygotuj(false) then return
	przetworz(pliki)
end open

-- Kroki przed oknem transkrypcji. Zwraca false, gdy aplikacja ma się zakończyć.
-- poKliknieciu: true przy uruchomieniu ikonką – po komunikacie o wyniku aktualizacji nie otwieramy wtedy wyboru pliku.
on przygotuj(poKliknieciu)
	if trwaAktualizacja() then
		activate
		display dialog "Trwa aktualizacja Transkrypcji. Aplikacja otworzy się sama, gdy się skończy." buttons {"OK"} default button "OK" with title TYTUL with icon note giving up after 10
		return false
	end if
	if trwaTranskrypcja() then
		activate
		display dialog "Trwa już transkrypcja. Poczekaj, aż się skończy." buttons {"OK"} default button "OK" with title TYTUL with icon caution
		return false
	end if
	if pokazWynikAktualizacji() and poKliknieciu then return false
	if zaproponujAktualizacje() then return false
	return true
end przygotuj

on przetworz(pliki)
	set wybor to oknoTranskrypcji(pliki)
	set kodFormatu to item 1 of wybor
	set kodTrybu to item 2 of wybor
	set opcjaCzasu to ""
	if item 3 of wybor then set opcjaCzasu to " --czas"

	set katalog to katalogAplikacji()
	set python to katalog & "venv/bin/python"
	set skrypt to katalog & "silnik/transcribe.py"
	set tmp to do shell script "mktemp -d"
	set statusPlik to tmp & "/status.json"
	set liczba to count of pliki
	set wyniki to {}
	set komunikaty to {}

	set progress total steps to 100
	repeat with i from 1 to liczba
		set pid to ""
		try
			set plik to POSIX path of (item i of pliki)
			set progress description to "Plik " & i & " z " & liczba & ": " & nazwaPliku(plik)
			set progress additional description to "Przygotowuję nagranie… Nie zamykaj klapy laptopa."
			set progress completed steps to 0
			do shell script "rm -f " & quoted form of statusPlik

			set pid to do shell script quoted form of python & " " & quoted form of skrypt & " " & quoted form of plik & ¬
				" --format " & kodFormatu & opcjaCzasu & " --tryb " & kodTrybu & " --status " & quoted form of statusPlik & ¬
				" >/dev/null 2>&1 & p=$!; caffeinate -i -w $p >/dev/null 2>&1 & echo $p"

			set etap to czekaj(pid, statusPlik)

			if etap is "gotowe" then
				set end of wyniki to czytajStatus(statusPlik, "wynik")
				set uwaga to czytajStatus(statusPlik, "uwaga")
				if uwaga is not "" and komunikaty does not contain uwaga then set end of komunikaty to uwaga
			else if etap is "blad" then
				set end of komunikaty to czytajStatus(statusPlik, "blad")
			else
				set end of komunikaty to "Coś poszło nie tak przy pliku „" & nazwaPliku(plik) & "”. Aplikacja wymaga naprawy – poproś o pomoc."
			end if
		on error errMsg number n
			if n is -128 then
				if pid is not "" then do shell script "kill " & pid & " 2>/dev/null"
				do shell script "rm -rf " & quoted form of tmp
				return
			end if
			error errMsg number n
		end try
	end repeat

	do shell script "rm -rf " & quoted form of tmp
	pokazPodsumowanie(wyniki, komunikaty)
end przetworz

-- Jedno okno: format, tryb i znaczniki czasu, z zapamiętanymi ostatnimi wyborami (defaults pl.transkrypcja).
-- Zwraca {kod formatu, kod trybu, czas (true/false)}. „Anuluj” → błąd -128, aplikacja kończy się po cichu.
on oknoTranskrypcji(pliki)
	set ostatniFormat to odczytajUstawienie("format", "Word")
	set ostatniTryb to odczytajUstawienie("tryb", "Dokładnie")
	set ostatniCzas to odczytajUstawienie("czas", "0")
	if ostatniFormat is "Tekst z czasem" then
		set ostatniFormat to "Tekst"
		set ostatniCzas to "1"
	end if
	set nrFormatu to indeksNa(ostatniFormat, ETYKIETY_FORMATOW, 2)
	set nrTrybu to indeksNa(ostatniTryb, KLUCZE_TRYBOW, 1)

	set widok to current application's NSView's alloc()'s initWithFrame:{{0, 0}, {380, 112}}
	widok's addSubview:(my etykieta("Format:", {{0, 86}, {60, 20}}, 13))
	set listaFormatow to current application's NSPopUpButton's alloc()'s initWithFrame:{{64, 82}, {312, 26}} pullsDown:false
	listaFormatow's addItemsWithTitles:ETYKIETY_FORMATOW
	listaFormatow's selectItemAtIndex:(nrFormatu - 1)
	widok's addSubview:listaFormatow
	widok's addSubview:(my etykieta("Tryb:", {{0, 56}, {60, 20}}, 13))
	set listaTrybow to current application's NSPopUpButton's alloc()'s initWithFrame:{{64, 52}, {312, 26}} pullsDown:false
	listaTrybow's addItemsWithTitles:OPISY_TRYBOW
	listaTrybow's selectItemAtIndex:(nrTrybu - 1)
	widok's addSubview:listaTrybow
	set poleCzasu to current application's NSButton's checkboxWithTitle:"Znaczniki czasu" target:(missing value) action:(missing value)
	poleCzasu's setFrame:{{62, 24}, {300, 22}}
	if ostatniCzas is "1" then poleCzasu's setState:1
	widok's addSubview:poleCzasu
	widok's addSubview:(my etykieta("wersja " & wersjaAplikacji(), {{0, 0}, {200, 16}}, 10))

	set okno to current application's NSAlert's alloc()'s init()
	okno's setMessageText:"Transkrypcja nagrania"
	okno's setInformativeText:(opisPlikow(pliki))
	okno's setAccessoryView:widok
	okno's addButtonWithTitle:"Generuj"
	set przyciskAnuluj to okno's addButtonWithTitle:"Anuluj"
	przyciskAnuluj's setKeyEquivalent:(character id 27)
	activate
	set odpowiedz to (okno's runModal()) as integer
	if odpowiedz is not 1000 then error number -128

	set nrFormatu to ((listaFormatow's indexOfSelectedItem()) as integer) + 1
	set nrTrybu to ((listaTrybow's indexOfSelectedItem()) as integer) + 1
	set czas to ((poleCzasu's state()) as integer) is 1
	zapiszUstawienie("format", item nrFormatu of ETYKIETY_FORMATOW)
	zapiszUstawienie("tryb", item nrTrybu of KLUCZE_TRYBOW)
	if czas then
		zapiszUstawienie("czas", "1")
	else
		zapiszUstawienie("czas", "0")
	end if
	return {item nrFormatu of KODY_FORMATOW, item nrTrybu of KODY_TRYBOW, czas}
end oknoTranskrypcji

on etykieta(tekst, ramka, rozmiar)
	set pole to current application's NSTextField's labelWithString:tekst
	pole's setFrame:ramka
	pole's setFont:(current application's NSFont's systemFontOfSize:rozmiar)
	if rozmiar < 12 then pole's setTextColor:(current application's NSColor's secondaryLabelColor())
	return pole
end etykieta

on indeksNa(wartosc, lista, domyslny)
	repeat with i from 1 to count of lista
		if item i of lista is wartosc then return i
	end repeat
	return domyslny
end indeksNa

-- „Wykład 3.m4a” albo „5 nagrań: a.m4a, b.m4a, c.m4a…”.
on opisPlikow(pliki)
	set liczba to count of pliki
	if liczba is 1 then return nazwaPliku(POSIX path of (item 1 of pliki))
	set nazwy to {}
	repeat with i from 1 to liczba
		if i > 3 then exit repeat
		set end of nazwy to nazwaPliku(POSIX path of (item i of pliki))
	end repeat
	set AppleScript's text item delimiters to ", "
	set lista to nazwy as text
	set AppleScript's text item delimiters to ""
	if liczba > 3 then set lista to lista & "…"
	set jednosci to liczba mod 10
	set setki to liczba mod 100
	if jednosci ≥ 2 and jednosci ≤ 4 and not (setki ≥ 12 and setki ≤ 14) then
		set slowo to "nagrania"
	else
		set slowo to "nagrań"
	end if
	return (liczba as text) & " " & slowo & ": " & lista
end opisPlikow

-- Pokazuje wynik aktualizacji zapisany przez aktualizuj.sh (i usuwa go). Zwraca true, jeśli coś pokazano.
on pokazWynikAktualizacji()
	set plik to katalogAplikacji() & "wynik-aktualizacji.txt"
	try
		set wynik to do shell script "cat " & quoted form of plik & " && rm -f " & quoted form of plik
	on error errMsg number n
		if n is -128 then error number -128
		return false
	end try
	activate
	if wynik starts with "ok " then
		display dialog "Zaktualizowano do wersji " & (text 4 thru -1 of wynik) & "." buttons {"OK"} default button "OK" with title TYTUL with icon note
	else
		display dialog "Nie udało się zaktualizować. Aplikacja działa w poprzedniej wersji – spróbuj później albo poproś o pomoc." buttons {"OK"} default button "OK" with title TYTUL with icon caution
	end if
	return true
end pokazWynikAktualizacji

-- Pyta o nowszą wersję z GitHuba. Zwraca true, gdy uruchomiono aktualizację (aplikacja ma się zakończyć).
on zaproponujAktualizacje()
	set katalog to katalogAplikacji()
	try
		set nowa to do shell script quoted form of (katalog & "venv/bin/python") & " " & quoted form of (katalog & "silnik/wersja.py") & " sprawdz"
	on error errMsg number n
		if n is -128 then error number -128
		return false
	end try
	if nowa is "" then return false
	activate
	set odpowiedz to button returned of (display dialog "Jest nowa wersja Transkrypcji (" & nowa & "). Zainstalować teraz?" buttons {"Później", "Zainstaluj"} default button "Zainstaluj" with title TYTUL with icon note)
	if odpowiedz is "Później" then return false
	do shell script "nohup /bin/bash " & quoted form of (katalog & "aktualizuj.sh") & " " & quoted form of nowa & " >/dev/null 2>&1 &"
	display dialog "Aktualizuję Transkrypcję. Aplikacja otworzy się sama za 1–2 minuty." buttons {"OK"} default button "OK" with title TYTUL with icon note giving up after 10
	return true
end zaproponujAktualizacje

on katalogAplikacji()
	return (POSIX path of (path to application support folder from user domain)) & "Transkrypcja/"
end katalogAplikacji

on wersjaAplikacji()
	try
		return do shell script "cat " & quoted form of (katalogAplikacji() & "VERSION")
	on error
		return "?"
	end try
end wersjaAplikacji

-- Czeka na koniec pracy silnika, aktualizując pasek postępu. Zwraca etap: "gotowe", "blad" albo inny/pusty etap, jeśli proces padł bez wyniku.
on czekaj(pid, statusPlik)
	repeat
		delay 1
		set etap to czytajStatus(statusPlik, "etap")
		if etap is "gotowe" or etap is "blad" then return etap
		if (do shell script "kill -0 " & pid & " 2>/dev/null && echo tak || echo nie") is "nie" then
			return czytajStatus(statusPlik, "etap")
		end if
		if etap is "transkrypcja" then
			try
				set procent to (czytajStatus(statusPlik, "procent")) as integer
				set progress completed steps to procent
				set progress additional description to (procent as text) & "%. Nie zamykaj klapy laptopa."
			on error errMsg number n
				if n is -128 then error number -128
			end try
		else if etap is "zapis" then
			set progress additional description to "Zapisuję plik…"
		end if
	end repeat
end czekaj

on pokazPodsumowanie(wyniki, komunikaty)
	activate
	set tekst to ""
	if (count of wyniki) is 1 then
		set tekst to "Gotowe! Zapisano plik:" & return & nazwaPliku(item 1 of wyniki)
	else if (count of wyniki) > 1 then
		set tekst to "Gotowe! Zapisano pliki: " & (count of wyniki)
	end if
	repeat with komunikat in komunikaty
		if tekst is "" then
			set tekst to (contents of komunikat)
		else
			set tekst to tekst & return & return & (contents of komunikat)
		end if
	end repeat

	if (count of wyniki) > 0 then
		set odpowiedz to button returned of (display dialog tekst buttons {"OK", "Pokaż plik"} default button "Pokaż plik" with title TYTUL with icon note)
		if odpowiedz is "Pokaż plik" then do shell script "open -R " & quoted form of (item 1 of wyniki)
	else
		display dialog tekst buttons {"OK"} default button "OK" with title TYTUL with icon stop
	end if
end pokazPodsumowanie

on odczytajUstawienie(klucz, domyslna)
	try
		return do shell script "defaults read pl.transkrypcja " & klucz
	on error
		return domyslna
	end try
end odczytajUstawienie

on zapiszUstawienie(klucz, wartosc)
	do shell script "defaults write pl.transkrypcja " & klucz & " " & quoted form of wartosc
end zapiszUstawienie

on czytajStatus(statusPlik, klucz)
	try
		return do shell script "plutil -extract " & klucz & " raw -o - " & quoted form of statusPlik
	on error errMsg number n
		if n is -128 then error number -128
		return ""
	end try
end czytajStatus

on trwaTranskrypcja()
	return (do shell script "pgrep -f '[T]ranskrypcja/silnik/transcribe.py' >/dev/null && echo tak || echo nie") is "tak"
end trwaTranskrypcja

on trwaAktualizacja()
	set plik to katalogAplikacji() & "aktualizacja.lock/pid"
	return (do shell script "p=$(cat " & quoted form of plik & " 2>/dev/null) && kill -0 \"$p\" 2>/dev/null && ps -p \"$p\" -o command= 2>/dev/null | grep -q aktualizuj && echo tak || echo nie") is "tak"
end trwaAktualizacja

on nazwaPliku(sciezka)
	return do shell script "basename " & quoted form of sciezka
end nazwaPliku
