"""Enchanter list helpers."""

from app.managers.enchanter_list import (
    append_uid,
    dumps,
    parse_list,
    remove_uid,
)


def test_append_remove_roundtrip():
    cur = append_uid([], 5)
    cur = append_uid(cur, "7")
    assert cur == ["5", "7"]
    assert remove_uid(cur, 5) == ["7"]
    assert parse_list(dumps(cur)) == ["5", "7"]


def test_parse_empty():
    assert parse_list(None) == []
    assert parse_list("bad") == []
