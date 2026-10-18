"""Reader + typing orchestration for PowerPoint presentations.

Reading (cross-platform, via python-pptx) extracts slide titles and body text
in slide order. It never modifies the source .pptx.

Typing into PowerPoint (Windows only) uses COM automation for ONE thing:
creating each new slide and selecting the placeholder to type into. The slide
text itself is then entered with simulated keystrokes, so the activity is
observable and recorded like any other typing. COM is not used to bulk-insert
the finished text.

This is the most environment-sensitive part of the project. If COM is not
available, fileppt.py falls back to a guided keyboard-only mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from document_readers import SourceError


@dataclass
class Slide:
    title: str
    body: str  # body lines joined with "\n"


def read_pptx_slides(path: Path) -> List[Slide]:
    """Extract (title, body) for each slide, in order."""
    if not path.exists():
        raise SourceError(f"Input file not found: {path}")
    try:
        from pptx import Presentation  # python-pptx  # type: ignore
    except ImportError as exc:
        raise SourceError(
            "python-pptx is not installed. Run: pip install python-pptx"
        ) from exc

    try:
        prs = Presentation(str(path))
    except Exception as exc:
        raise SourceError(f"Could not open presentation {path}: {exc}") from exc

    slides: List[Slide] = []
    for slide in prs.slides:
        title = ""
        body_lines: List[str] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            is_title = False
            try:
                if shape.is_placeholder and shape.placeholder_format.idx == 0:
                    is_title = True
            except Exception:
                is_title = False

            text = "\n".join(p.text for p in shape.text_frame.paragraphs)
            if is_title and not title:
                title = text.strip()
            else:
                if text.strip():
                    body_lines.append(text)
        slides.append(Slide(title=title, body="\n".join(body_lines)))

    if not slides:
        raise SourceError(f"No slides found in {path}.")
    return slides


def detect_unsupported_pptx(path: Path) -> List[str]:
    """Warn about content this version does not reproduce."""
    warnings: List[str] = []
    try:
        from pptx import Presentation  # type: ignore
        from pptx.util import Emu  # noqa: F401

        prs = Presentation(str(path))
    except Exception:
        return warnings

    has_pictures = False
    has_tables = False
    has_charts = False
    for slide in prs.slides:
        for shape in slide.shapes:
            st = str(shape.shape_type)
            if "PICTURE" in st:
                has_pictures = True
            if getattr(shape, "has_table", False):
                has_tables = True
            if getattr(shape, "has_chart", False):
                has_charts = True
    if has_pictures:
        warnings.append("Picture(s) found - images will NOT be reproduced.")
    if has_tables:
        warnings.append("Table(s) found - table content will NOT be typed.")
    if has_charts:
        warnings.append("Chart(s) found - charts will NOT be reproduced.")
    warnings.append(
        "Themes, animations, transitions and exact formatting are not reproduced."
    )
    return warnings


# ---------------------------------------------------------------------------
# COM typing session (Windows + pywin32 only)
# ---------------------------------------------------------------------------


class PowerPointComError(Exception):
    pass


class PowerPointComSession:
    """Drives the running PowerPoint instance to create slides and select the
    placeholder to type into. Keystrokes are sent by the caller's backend."""

    # PpSlideLayout: 2 = Title and Content (ppLayoutText).
    _LAYOUT_TITLE_AND_CONTENT = 2

    def __init__(self) -> None:
        try:
            import win32com.client  # type: ignore
        except ImportError as exc:
            raise PowerPointComError(
                "pywin32 is not installed. Run: pip install pywin32"
            ) from exc

        self._win32com = win32com.client
        try:
            self.app = win32com.client.GetActiveObject("PowerPoint.Application")
        except Exception as exc:
            raise PowerPointComError(
                "Could not attach to a running PowerPoint. "
                "Open PowerPoint with a presentation before running."
            ) from exc

        if self.app.Presentations.Count == 0:
            raise PowerPointComError(
                "PowerPoint is open but has no presentation. "
                "Create or open one, then run again."
            )
        self.presentation = self.app.ActivePresentation

    def activate(self) -> None:
        """Bring PowerPoint to the foreground so keystrokes land there."""
        try:
            self.app.Activate()
        except Exception:
            pass

    def add_slide(self):
        """Append a new 'Title and Content' slide and return it, selected."""
        index = self.presentation.Slides.Count + 1
        slide = self.presentation.Slides.Add(index, self._LAYOUT_TITLE_AND_CONTENT)
        slide.Select()
        # Make the slide the active one in the editing window.
        try:
            self.app.ActiveWindow.View.GotoSlide(index)
        except Exception:
            pass
        return slide

    def select_title_placeholder(self, slide) -> bool:
        return self._select_placeholder(slide, want_title=True)

    def select_body_placeholder(self, slide) -> bool:
        return self._select_placeholder(slide, want_title=False)

    def _select_placeholder(self, slide, *, want_title: bool) -> bool:
        """Select a placeholder shape and enter text-edit mode via F2.

        Returns True if a suitable placeholder was found and selected.
        """
        target = None
        for shape in slide.Shapes:
            try:
                if not shape.Type == 14 and not shape.HasTextFrame:
                    # 14 == msoPlaceholder; also accept text frames.
                    pass
            except Exception:
                pass
            try:
                is_title = shape.PlaceholderFormat.Type in (1, 13)  # title types
            except Exception:
                is_title = False
            if want_title and is_title:
                target = shape
                break
            if not want_title and not is_title and shape.HasTextFrame:
                target = shape
                break

        if target is None:
            return False
        try:
            target.Select()
        except Exception:
            return False
        return True
