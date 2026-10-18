"""Tests for Word/PowerPoint reading, ordering, and project wiring."""

from __future__ import annotations

import importlib

import pytest

import config
from document_readers import (
    SourceError,
    detect_unsupported_docx,
    read_docx_text,
)

docx = pytest.importorskip("docx", reason="python-docx not installed")


def test_docx_paragraph_order_preserved(tmp_path):
    doc = docx.Document()
    for line in ["First", "Second", "Third", "Fourth"]:
        doc.add_paragraph(line)
    p = tmp_path / "d.docx"
    doc.save(str(p))

    text = read_docx_text(p)
    assert text.splitlines() == ["First", "Second", "Third", "Fourth"]


def test_docx_unicode_preserved(tmp_path):
    doc = docx.Document()
    doc.add_paragraph("Café — naïve — Nairobi — 90%")
    p = tmp_path / "u.docx"
    doc.save(str(p))
    assert "Café — naïve — Nairobi — 90%" in read_docx_text(p)


def test_docx_table_triggers_warning(tmp_path):
    doc = docx.Document()
    doc.add_paragraph("Body")
    doc.add_table(rows=2, cols=2)
    p = tmp_path / "wt.docx"
    doc.save(str(p))
    warnings = detect_unsupported_docx(p)
    assert any("table" in w.lower() for w in warnings)


def test_docx_missing_file_raises(tmp_path):
    with pytest.raises(SourceError):
        read_docx_text(tmp_path / "nope.docx")


def test_pptx_slide_order_preserved(tmp_path):
    pptx = pytest.importorskip("pptx", reason="python-pptx not installed")
    from powerpoint_reader import read_pptx_slides

    prs = pptx.Presentation()
    titles = ["Alpha", "Beta", "Gamma"]
    for t in titles:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = t
        slide.placeholders[1].text = f"body of {t}"
    p = tmp_path / "deck.pptx"
    prs.save(str(p))

    slides = read_pptx_slides(p)
    assert [s.title for s in slides] == titles
    assert slides[0].body.startswith("body of Alpha")


# --- project wiring: imports and input-file mapping ---------------------

ENTRY_TO_INPUT = {
    "filedocx": "inputdocx.docx",
    "filecsv": "inputcsv.csv",
    "fileppt": "inputppt.pptx",
    "filehtml": "inputhtml.html",
    "filecss": "inputcss.css",
    "filejs": "inputjs.js",
    "filephp": "inputphp.php",
}


@pytest.mark.parametrize("entry", list(ENTRY_TO_INPUT))
def test_entry_modules_import_cleanly(entry):
    """Catches broken imports / wrong relative paths across the project."""
    mod = importlib.import_module(entry)
    assert hasattr(mod, "main")


def test_config_maps_each_filetype():
    for _entry, filename in ENTRY_TO_INPUT.items():
        assert filename in config.INPUT_FILES.values()
