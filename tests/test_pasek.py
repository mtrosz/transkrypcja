from pasek import fabryka_paska


def test_pasek_raportuje_ulamek():
    wartosci = []
    Pasek = fabryka_paska(wartosci.append)
    with Pasek(total=200, unit="frames", disable=False) as p:
        p.update(50)
        p.update(150)
    assert wartosci == [0.25, 1.0]


def test_pasek_nie_przekracza_jedynki():
    wartosci = []
    fabryka_paska(wartosci.append)(total=100).update(150)
    assert wartosci == [1.0]


def test_pasek_bez_total_nie_raportuje():
    wartosci = []
    p = fabryka_paska(wartosci.append)(total=0)
    p.update(10)
    p.close()
    assert wartosci == []
