"""Unit tests for utils.datetime_parser.parse_datetime_arg."""
from datetime import datetime

from utils.datetime_parser import parse_datetime_arg


def test_format_yyyy_mm_dd_t_hh_mm_ss():
    assert parse_datetime_arg("2024-01-15T10:30:45") == datetime(2024, 1, 15, 10, 30, 45)


def test_format_yyyy_mm_dd_t_hh_mm():
    assert parse_datetime_arg("2024-01-15T10:30") == datetime(2024, 1, 15, 10, 30)


def test_format_yyyy_mm_dd_space_hh_mm_ss():
    assert parse_datetime_arg("2024-01-15 10:30:45") == datetime(2024, 1, 15, 10, 30, 45)


def test_format_yyyy_mm_dd_space_hh_mm():
    assert parse_datetime_arg("2024-01-15 10:30") == datetime(2024, 1, 15, 10, 30)


def test_none_returns_none():
    assert parse_datetime_arg(None) is None


def test_empty_string_returns_none():
    assert parse_datetime_arg("") is None


def test_invalid_datetime_returns_none():
    assert parse_datetime_arg("2024-13-40T99:99:99") is None


def test_malformed_input_returns_none():
    assert parse_datetime_arg("not-a-date") is None
    assert parse_datetime_arg("15/01/2024") is None
