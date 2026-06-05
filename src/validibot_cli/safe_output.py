"""Helpers for safely rendering server-controlled text to the terminal.

API responses — error details, finding messages, workflow names/versions, etc.
— are attacker-influenced: a malicious or compromised server can embed terminal
control sequences in any string field. Rich's ``escape()`` and ``markup=False``
both neutralize Rich's *own* ``[tags]`` markup, but NEITHER strips raw terminal
control bytes (ANSI/OSC escape sequences, carriage returns). Those are a
distinct layer, and left intact they let a hostile server move the cursor,
recolor output to spoof a "PASSED", rewrite the window title, smuggle an OSC-8
hyperlink, or overwrite a line with ``\\r``.

These helpers strip those bytes so server text is rendered as inert characters.
"""

from __future__ import annotations

import re

from rich.markup import escape

# Strip C0 control chars EXCEPT tab (\x09) and newline (\x0a), plus DEL (\x7f)
# and the C1 range (\x80-\x9f, which includes the 8-bit CSI \x9b). This removes
# ESC (\x1b) — the start of every ANSI/OSC sequence — and carriage return
# (\x0d), used for line-overwrite spoofing, while preserving legitimate
# newlines and tabs in multi-line messages.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def strip_control_chars(text: str) -> str:
    """Remove terminal control/escape bytes from (possibly server-sent) text.

    Use this for any string that originates from the API before printing it —
    including ``markup=False`` prints, which Rich does NOT strip control bytes
    from.
    """
    return _CONTROL_CHARS.sub("", str(text))


def safe_markup(text: str) -> str:
    """Make server text safe to interpolate into a Rich *markup* string.

    Strips terminal control bytes first, then ``escape()``-s Rich markup so
    ``[tags]`` render literally. Use this anywhere a value is placed inside an
    f-string that Rich will parse for markup (the default ``console.print``).
    """
    return escape(strip_control_chars(text))
