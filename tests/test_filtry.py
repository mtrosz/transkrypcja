from filtry import filtruj
from fragment import Fragment


def f(tekst, start=0.0, nsp=0.0, lp=0.0):
    return Fragment(start, start + 1, tekst, nsp, lp)


def test_zostawia_zwykle_fragmenty():
    wej = [f("Dzień dobry.", 0), f("Zaczynamy.", 1)]
    assert filtruj(wej) == wej


def test_odrzuca_brak_mowy_gdy_oba_progi_przekroczone():
    assert filtruj([f("Dziękuję za obejrzenie.", nsp=0.9, lp=-1.5)]) == []


def test_zostawia_gdy_przekroczony_tylko_jeden_prog():
    wej = [f("Tak.", 0, nsp=0.9, lp=-0.5), f("Nie.", 1, nsp=0.2, lp=-1.5)]
    assert filtruj(wej) == wej


def test_progi_sa_ostre():
    wej = [f("Graniczny.", nsp=0.6, lp=-1.5), f("Też.", 1, nsp=0.9, lp=-1.0)]
    assert filtruj(wej) == wej


def test_odrzuca_puste():
    assert filtruj([f("   "), f("")]) == []


def test_trzy_powtorzenia_z_rzedu_zostaje_pierwsze():
    wej = [f("Proszę.", 0), f("Proszę.", 1), f("Proszę.", 2), f("Dalej.", 3)]
    assert filtruj(wej) == [wej[0], wej[3]]


def test_dwa_powtorzenia_zostaja():
    wej = [f("Tak.", 0), f("Tak.", 1)]
    assert filtruj(wej) == wej


def test_powtorzenia_rozne_interpunkcja_i_wielkosc_liter():
    wej = [f("Dziękuję.", 0), f("dziękuję!", 1), f("Dziękuję", 2)]
    assert filtruj(wej) == [wej[0]]


def test_powtorzenia_nie_sasiadujace_zostaja():
    wej = [f("Tak.", 0), f("Nie.", 1), f("Tak.", 2), f("Nie.", 3), f("Tak.", 4)]
    assert filtruj(wej) == wej


def test_powtorzenia_liczone_po_odrzuceniu_pustych():
    wej = [f("Proszę.", 0), f(" ", 1), f("Proszę.", 2), f("Proszę.", 3)]
    assert filtruj(wej) == [wej[0]]


# --- przykłady z prawdziwych transkrypcji wykładu ---


def test_zapetlenie_wewnatrz_fragmentu_skracane_do_jednego():
    wej = [f("Natomiast rozwój prawa, w tym, w tym, w tym, w tym, w tym, w tym, w nie z narodowego.")]
    assert [x.tekst for x in filtruj(wej)] == ["Natomiast rozwój prawa, w tym, w nie z narodowego."]


def test_zapetlenie_pytania_i_na_koncu_tekstu():
    wej = [
        f("Z bezczyszczenia flagi? Z bezczyszczenia flagi? Z bezczyszczenia flagi? Z bezczyszczenia flagi? na zasadzie"),
        f("Do widzenia. Do widzenia. Do widzenia. Do widzenia. Do widzenia.", 1),
    ]
    assert [x.tekst for x in filtruj(wej)] == ["Z bezczyszczenia flagi? na zasadzie", "Do widzenia."]


def test_trzy_powtorzenia_wewnatrz_zostaja():
    wej = [f("No nie można, no nie można, no nie można.")]
    assert filtruj(wej) == wej


def test_odrzuca_fragment_z_obcym_pismem():
    wej = [
        f("Bartaryjan restored właśnie Fabianoчесkiego 살 Woah Dean Morning不會 Wycerza.", 0),
        f("Jaka książka?", 1),
    ]
    assert [x.tekst for x in filtruj(wej)] == ["Jaka książka?"]


def test_odrzuca_angielski_belkot():
    wej = [
        f("That's the same as the end of the world. So the end of the world.", 0),
        f("Human Rights Act został przyjęty przez parlament.", 1),
    ]
    assert [x.tekst for x in filtruj(wej)] == ["Human Rights Act został przyjęty przez parlament."]


def test_odrzuca_znane_halucynacje():
    wej = [
        f("Napisy by Jacek Makarewicz", 0),
        f("Napisy stworzone przez społeczność Amara.org", 1),
        f("Dziękuję za obejrzenie!", 2),
        f("Dziękuję za uwagę.", 3),
    ]
    assert [x.tekst for x in filtruj(wej)] == ["Dziękuję za uwagę."]


def test_odrzuca_fragment_bez_liter_i_cyfr():
    assert filtruj([f("!"), f("..."), f(" – ")]) == []


def test_zostawia_sama_liczbe():
    wej = [f("1945.")]
    assert filtruj(wej) == wej

