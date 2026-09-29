from fragment import Fragment, z_segmentow


def test_z_segmentow_mapuje_pola_i_przycina_tekst():
    segmenty = [
        {
            "start": 0.0,
            "end": 2.5,
            "text": " Dzień dobry.",
            "no_speech_prob": 0.1,
            "avg_logprob": -0.3,
            "tokens": [1, 2, 3],
        }
    ]
    assert z_segmentow(segmenty) == [Fragment(0.0, 2.5, "Dzień dobry.", 0.1, -0.3)]


def test_z_segmentow_brakujace_metryki_maja_wartosci_domyslne():
    assert z_segmentow([{"start": 1, "end": 2, "text": "a"}]) == [
        Fragment(1.0, 2.0, "a", 0.0, 0.0)
    ]


def test_z_segmentow_pusta_lista():
    assert z_segmentow([]) == []
