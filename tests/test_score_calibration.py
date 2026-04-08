from src.recommendation.score_calibration import list_confidence_from_raw


def test_calibration_empty():
    assert list_confidence_from_raw([]) == []


def test_calibration_single():
    assert list_confidence_from_raw([0.1]) == [0.9]


def test_calibration_equal_spread():
    out = list_confidence_from_raw([0.4, 0.4, 0.4])
    assert len(out) == 3
    assert all(x == 0.86 for x in out)


def test_calibration_min_max_stretch():
    out = list_confidence_from_raw([0.1, 0.5, 0.9])
    assert out[0] < out[1] < out[2]
    assert abs(out[0] - 0.55) < 1e-9
    assert abs(out[2] - 0.98) < 1e-9
