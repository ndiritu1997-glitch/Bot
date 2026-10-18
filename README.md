# Typing Simulator

A modular Python tool that reproduces the contents of a source file by sending
**individual keyboard events** into a desktop application, with human-like
timing, long breaks, progress reporting, a safe stop, and resume-after-stop.

It was built to test a **screen/input-activity recorder** — software that logs
keystrokes and mouse activity. Running this tool produces a stream of real OS
keyboard events for that recorder to capture.

## What this is (and isn't)

- It types **character by character** using OS key events (via `pynput`, which
  calls Windows `SendInput`). It does **not** paste from the clipboard.
- On Windows, events generated this way are flagged by the OS as **injected**
  (`LLKHF_INJECTED`). This tool does **not** alter or hide that flag. A recorder
  that inspects it can tell these events are software-generated — which is the
  correct, honest behaviour. If your goal is to confirm your recorder *detects*
  synthetic input, this tool exercises exactly that path.
- "Human-like" refers to variable timing, pauses, and breaks — not to defeating
  detection.

## Supported / not supported

| Area | Supported | Not supported (this version) |
|------|-----------|------------------------------|
| Word (`.docx`) | Body paragraph text, order, line breaks, Unicode | Tables, images, headers/footers, footnotes, styling |
| Excel (`.csv`) | Cell-by-cell typing, row/col order, empty cells, blank rows, quoted fields, delimiter sniffing | Real formulas (values starting `= + - @` are typed as **text**) |
| PowerPoint (`.pptx`) | Slide title + body text, slide order | Images, charts, tables, themes, animations, transitions, layout |
| VS Code (`.html/.css/.js/.php`) | Exact characters, indentation, blank lines, comments, order | — |

When a source contains unsupported content, the script prints a warning before
the countdown.

## Project layout

```
typing_simulator/
├── filedocx.py  filecsv.py  fileppt.py        # entry scripts (one per type)
├── filehtml.py  filecss.py  filejs.py  filephp.py
├── config.py                                  # all settings
├── typing_engine.py                           # keystrokes, delays, breaks
├── controller.py                              # shared run flow
├── application_checks.py                      # best-effort app detection
├── document_readers.py  excel_reader.py  powerpoint_reader.py
├── state_manager.py                           # resume/recovery state
├── logging_config.py
├── make_fixtures.py                           # builds the .docx/.pptx samples
├── requirements.txt   README.md   .gitignore
├── inputs/   # inputhtml.html, inputcss.css, inputjs.js, inputphp.php,
│             # inputcsv.csv ship ready; run make_fixtures.py for docx+pptx
├── logs/
└── tests/
```

## Install (Windows, PowerShell)

```powershell
cd typing_simulator
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `Activate.ps1` is blocked, allow scripts for this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Prepare the input files

The text samples (`inputhtml.html`, `inputcss.css`, `inputjs.js`,
`inputphp.php`, `inputcsv.csv`) are already in `inputs/`. Build the two binary
samples once:

```powershell
python make_fixtures.py
```

Replace any `inputs/*` file with your own content — keep the same filename, or
change the names in `config.py` (`INPUT_FILES`).

## Run

Open the **target application first**, then run the matching script:

```powershell
python filedocx.py     # -> Microsoft Word
python filecsv.py      # -> Microsoft Excel
python fileppt.py      # -> Microsoft PowerPoint
python filehtml.py     # -> VS Code (HTML)
python filecss.py      # -> VS Code (CSS)
python filejs.py       # -> VS Code (JavaScript)
python filephp.py      # -> VS Code (PHP)
```

Flags (all scripts): `--dry-run` (report, send no keys), `--fresh` (ignore saved
resume state), `--yes` (auto-confirm resume), `--typos` (occasional
type-and-correct; final text is unchanged).

Preview safely first:

```powershell
python filehtml.py --dry-run
```

## The 30-second countdown — prepare the destination

Each run shows what it will do, warns about unsupported content, then counts
down **30 seconds** (set by `STARTUP_DELAY_SECONDS`). During that window:

- **Word / VS Code:** open an **empty** destination document/file and click in
  it so the cursor is where typing should begin.
- **Excel:** click the start cell (default `A1`) in an empty area.
- **PowerPoint:** leave PowerPoint in **Normal** view, in the foreground. The
  tool adds new slides at the end and types into their placeholders.

If you're not ready, press the stop key during the countdown to cancel before
any typing starts. The tool does not repeatedly grab focus.

## Stopping — two ways

- **Global hotkey `Ctrl+Alt+Shift+S`** — works from **any** window, including
  while the tool is actively typing into Word/Excel/VS Code. This is the one to
  use mid-run. It's a deliberately unusual combo so it won't clash with app
  shortcuts, and it's harmless if the keystroke also reaches the app.
- **`Ctrl+C` in the terminal** — works only when the PowerShell/VS Code terminal
  is the focused window (while typing, the target app has focus, so the hotkey
  is what you want then).

Either way the tool releases any held keys, saves progress, and prints where it
stopped. Change the hotkey via `STOP_HOTKEY` / `STOP_HOTKEY_HUMAN` in
`config.py`.

## Breaks (rest like a human)

After **90–120 minutes** of active typing (randomised), the tool pauses for
**10–20 minutes** (randomised), then continues on its own. Progress is saved at
the start of every break, so a crash or exit during a break still resumes.
Tune with `BREAK_AFTER_*` and `BREAK_LENGTH_*` in `config.py`.

## Resume after stopping (state folder)

Progress is saved to **`C:\contenttypingsim`** (one small JSON file per script).
On the next run of the same script, if the saved progress matches the current
source file (checked by SHA-256), the tool offers to resume from where it left
off. During that run's countdown, put the cursor at the **end** of the text
already typed. A clean finish clears the state. If the source file changed, the
tool starts fresh rather than typing mismatched content.

Override the folder with the `CONTENTTYPINGSIM_STATE_DIR` environment variable
(on non-Windows systems it defaults to a local `contenttypingsim/` folder).

## Code indentation note (VS Code)

The tool types literal characters, including leading spaces, and presses Enter
for new lines. Editors with **auto-indent / format-on-type** may add their own
indentation on Enter, doubling it. For exact reproduction, either disable those
while running:

```json
// VS Code settings.json
"editor.autoIndent": "none",
"editor.formatOnType": false
```

…or accept the editor's reformatting. The source file is never modified.

## PowerPoint note

Entering text into specific slide placeholders by keyboard alone is unreliable,
so for PowerPoint the tool uses **COM automation** (via `pywin32`) for one
narrow job: creating each new blank slide and selecting the title/body
placeholder. The **text is still typed with simulated keystrokes** — COM is not
used to bulk-insert content. Keep PowerPoint focused while it runs. If `pywin32`
or a running PowerPoint isn't available, use `--dry-run` to preview.

## Logging

Logs go to `logs/<script>_<date>.log`: run metadata, config, warnings, progress,
and completion/interruption status. Individual keystrokes are **not** logged, and
window contents / passwords are never logged.

## Tests

```powershell
pip install pytest
python -m pytest tests/      # run from the project root
```

Tests cover exact character preservation (html/css/js/php), CSV row/column and
blank-cell handling, Word paragraph order, PowerPoint slide order, formula-cell
escaping, missing-file errors, configurable startup delay, the stop mechanism,
and that dry-run sends no real input. They use a recording backend and need no
real application window.

## Troubleshooting

- **Nothing types / wrong window** — the target wasn't focused when the
  countdown ended. Stop, refocus the destination, run again (resume continues).
- **`ModuleNotFoundError`** — activate the venv and `pip install -r requirements.txt`.
- **PowerPoint: "Could not attach to a running PowerPoint"** — open PowerPoint
  with a presentation first; install `pywin32`.
- **Code indentation doubled** — disable auto-indent/format-on-type (above).
- **Hotkey does nothing** — some locked-down machines block global key hooks;
  use `Ctrl+C` in the terminal, or run the terminal as the focused window.
- **Excel values shifted** — make sure you started on the intended cell and
  didn't touch the keyboard/mouse while it typed.
- **Accented characters wrong in VS Code** — ensure the file/editor encoding is
  UTF-8.

## Safety summary

Source files are read-only inputs, never overwritten or executed. The tool
never pastes, never forces focus repeatedly, releases held keys on stop, and
does not disguise that its keystrokes are software-generated.
