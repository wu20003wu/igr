"""Unit tests for utils.fix_parser.extract_tag_value."""
from utils.fix_parser import extract_tag_value


def test_tag_exists():
    assert extract_tag_value("8=FIX.4.2|35=D|49=SENDER", "35") == "D"


def test_tag_at_beginning():
    assert extract_tag_value("35=D|49=SENDER|56=TARGET", "35") == "D"


def test_tag_in_middle():
    assert extract_tag_value("8=FIX.4.2|35=8|49=SENDER", "35") == "8"


def test_tag_at_end():
    assert extract_tag_value("8=FIX.4.2|49=SENDER|35=D", "35") == "D"


def test_tag_does_not_exist():
    assert extract_tag_value("8=FIX.4.2|49=SENDER|56=TARGET", "35") is None


def test_similar_tag_numbers_do_not_falsely_match():
    # "35" must not match "135" or "350"
    assert extract_tag_value("135=X|350=Y|49=Z", "35") is None
    assert extract_tag_value("8=FIX|350=Y|35=D", "35") == "D"
    assert extract_tag_value("8=FIX|35=D|350=Y", "350") == "Y"


def test_empty_fix_string():
    assert extract_tag_value("", "35") is None
