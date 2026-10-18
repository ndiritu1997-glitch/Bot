"""Tests for CSV reading and cell-by-cell typing order."""

from __future__ import annotations

import pytest

from document_readers import SourceError
from excel_reader import count_cells, read_csv_rows
from helpers import RecordingBackend, make_pacer, make_state
from typing_engine import type_rows


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_rows_columns_and_blanks_preserved(tmp_path):
    csv_text = "a,b,c\n1,,3\n,,\nx,y,z\n"
    rows = read_csv_rows(_write(tmp_path, "t.csv", csv_text))
    assert rows == [
        ["a", "b", "c"],
        ["1", "", "3"],
        ["", "", ""],
        ["x", "y", "z"],
    ]


def test_quoted_field_with_comma(tmp_path):
    csv_text = 'name,note\nDan,"Covers A, B and C"\n'
    rows = read_csv_rows(_write(tmp_path, "q.csv", csv_text))
    assert rows[1] == ["Dan", "Covers A, B and C"]


def test_count_cells_counts_blank_row_as_one(tmp_path):
    rows = [["a", "b"], [], ["c"]]
    assert count_cells(rows) == 2 + 1 + 1


def test_missing_file_raises(tmp_path):
    with pytest.raises(SourceError):
        read_csv_rows(tmp_path / "nope.csv")


def test_empty_file_raises(tmp_path):
    with pytest.raises(SourceError):
        read_csv_rows(_write(tmp_path, "empty.csv", "   \n"))


def test_typing_navigation_tabs_within_row_enter_between_rows(fast_timing, logger):
    rows = [["a", "b"], ["c", "d"]]
    state = make_state(count_cells(rows))
    backend = RecordingBackend()
    pacer = make_pacer(state, logger)

    type_rows(rows, backend, pacer)

    # a <tab> b <enter> c <tab> d <enter>
    assert backend.text == "a\tb\nc\td\n"


def test_typing_preserves_empty_cells(fast_timing, logger):
    rows = [["x", "", "z"]]
    state = make_state(count_cells(rows))
    backend = RecordingBackend()
    pacer = make_pacer(state, logger)

    type_rows(rows, backend, pacer)

    # x <tab> (empty) <tab> z <enter>  -> empty cell is just a tab.
    assert backend.text == "x\t\tz\n"
