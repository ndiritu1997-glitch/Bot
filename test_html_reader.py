"""Tests that code source files are read and typed with exact preservation."""

from __future__ import annotations

import pytest

import config
from document_readers import SourceError, read_code_file
from helpers import RecordingBackend, make_pacer, make_state
from typing_engine import type_text


SNIPPETS = {
    "html": "<div class=\"a\">\n  <p>hi &amp; bye</p>\n</div>\n",
    "css": ".x {\n    color: #fff;\n    margin: 0 auto;\n}\n",
    "js": "const f = (x) => { return x ** 2; };\n// comment\n",
    "php": "<?php\n$arr = ['a' => 1];\necho $arr['a'];\n?>\n",
}


@pytest.mark.parametrize("lang,code", SNIPPETS.items())
def test_read_code_file_roundtrip(tmp_path, lang, code):
    p = tmp_path / f"snippet.{lang}"
    p.write_text(code, encoding="utf-8")
    assert read_code_file(p) == code


@pytest.mark.parametrize("lang,code", SNIPPETS.items())
def test_typed_stream_matches_source(tmp_path, fast_timing, logger, lang, code):
    p = tmp_path / f"snippet.{lang}"
    p.write_text(code, encoding="utf-8")
    text = read_code_file(p)

    state = make_state(len(text))
    backend = RecordingBackend()
    pacer = make_pacer(state, logger)
    type_text(text, backend, pacer)

    # Exact reproduction: indentation, braces, quotes, newlines, order.
    assert backend.text == text


def test_shipped_fixtures_exist_and_are_nonempty():
    for key in ("html", "css", "js", "php"):
        path = config.INPUT_DIR / config.INPUT_FILES[key]
        assert path.exists(), f"missing fixture: {path}"
        assert read_code_file(path).strip() != ""


def test_missing_source_raises(tmp_path):
    with pytest.raises(SourceError):
        read_code_file(tmp_path / "nope.html")


def test_input_file_names_are_distinct():
    names = list(config.INPUT_FILES.values())
    assert len(names) == len(set(names))
