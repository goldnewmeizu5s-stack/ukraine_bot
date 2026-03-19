import pytest
from datetime import datetime, timedelta


SRS_INTERVALS = [60, 600, 86400, 259200, 604800, 1209600, 2592000]


def calculate_next_review(comfort_level: int, correct: bool) -> tuple[int, datetime]:
    if correct:
        new_level = min(comfort_level + 1, 6)
    else:
        new_level = max(0, comfort_level - 2)

    interval_seconds = SRS_INTERVALS[min(new_level, len(SRS_INTERVALS) - 1)]
    next_review = datetime.utcnow() + timedelta(seconds=interval_seconds)
    return new_level, next_review


def test_correct_answer_increases_level():
    new_level, _ = calculate_next_review(0, correct=True)
    assert new_level == 1


def test_correct_answer_max_level():
    new_level, _ = calculate_next_review(6, correct=True)
    assert new_level == 6


def test_incorrect_answer_decreases_level():
    new_level, _ = calculate_next_review(3, correct=False)
    assert new_level == 1


def test_incorrect_answer_min_level():
    new_level, _ = calculate_next_review(0, correct=False)
    assert new_level == 0


def test_incorrect_from_level_1():
    new_level, _ = calculate_next_review(1, correct=False)
    assert new_level == 0


def test_review_interval_level_0():
    _, next_review = calculate_next_review(0, correct=True)
    expected_min = datetime.utcnow() + timedelta(seconds=SRS_INTERVALS[1] - 5)
    expected_max = datetime.utcnow() + timedelta(seconds=SRS_INTERVALS[1] + 5)
    assert expected_min <= next_review <= expected_max


def test_review_interval_level_0_incorrect():
    _, next_review = calculate_next_review(0, correct=False)
    expected_min = datetime.utcnow() + timedelta(seconds=SRS_INTERVALS[0] - 5)
    expected_max = datetime.utcnow() + timedelta(seconds=SRS_INTERVALS[0] + 5)
    assert expected_min <= next_review <= expected_max


def test_all_levels_correct_progression():
    level = 0
    for i in range(6):
        level, _ = calculate_next_review(level, correct=True)
        assert level == i + 1

    level, _ = calculate_next_review(6, correct=True)
    assert level == 6


def test_srs_intervals_increasing():
    for i in range(len(SRS_INTERVALS) - 1):
        assert SRS_INTERVALS[i] < SRS_INTERVALS[i + 1]
