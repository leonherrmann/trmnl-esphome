#!/usr/bin/env python3
"""Apply known ESPHome Designer export bugs to a YAML paste.

This is *not* a merger — it just runs textual find/replace fixes that the
designer would otherwise make you re-do by hand after every export.

Usage:
  python esphome/fix-paste.py -i esphome/packages/designer.yaml   # in place
  pbpaste | python esphome/fix-paste.py > esphome/packages/designer.yaml
  python esphome/fix-paste.py paste.yaml > esphome/packages/designer.yaml

Fixes applied:

  * markdown auto-link mangle (only present if you copied from a markdown view):
        [time.is](http://time.is)_valid()  ->  time.is_valid()
  * api_is_connected() — not a real ESPHome lambda function. HA time validity
    already implies the API is connected, so the call is dropped or replaced.
  * display id epaper -> epaper_display, so the designer's hard-coded
    `component.update: epaper_display` resolves. Skip this rename if you want
    to keep the original id; just delete that fix from FIXES below.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\[([\w.]+)\]\(http://\1\)"), r"\1"),
    (re.compile(r"\s*&&\s*api_is_connected\(\)"), ""),
    (re.compile(r"api_is_connected\(\)\s*&&\s*"), ""),
    (re.compile(r"\bapi_is_connected\(\)"), "id(ha_time).now().is_valid()"),
    (re.compile(r"\bepaper(?!\w)"), "epaper_display"),
    # `allow_other_uses: true` is only valid when a pin has multiple users.
    # Always-on mode has no deep_sleep, so the button pin only has one user
    # and ESPHome rejects the flag. Strip the whole line.
    (re.compile(r"^[ \t]*allow_other_uses:\s*true\s*\n", re.M), ""),
    # Partial refresh (7.50inv2p) requires a panel built after Sep 2023.
    # Tested on a current retail TRMNL OG and the panel silently ignored
    # the partial-refresh waveform. Leaving the rule disabled by default;
    # uncomment if you ever confirm a newer panel.
    # (re.compile(r"(model:\s+)7\.50inv2(?!\w)"), r"\g<1>7.50inv2p"),
    # The Waveshare 7.5"v2 panel in the retail TRMNL OG has inverted color
    # polarity vs. what ESPHome's 7.50inv2 driver assumes — feeding the
    # framebuffer conventional constants produces a black background with
    # white widgets. Force the lambda's COLOR_WHITE / COLOR_BLACK constants
    # to the inverse so the rendered output looks normal on the panel.
    # Idempotent: re-running the helper doesn't double-invert. If you ever
    # switch to a conventional panel, comment these two rules out.
    (re.compile(r"const auto COLOR_WHITE\s*=\s*Color\([^)]+\)[^\n]*"),
     "const auto COLOR_WHITE = Color(0, 0, 0); // inverted polarity for TRMNL OG panel"),
    (re.compile(r"const auto COLOR_BLACK\s*=\s*Color\([^)]+\)[^\n]*"),
     "const auto COLOR_BLACK = Color(255, 255, 255); // inverted polarity for TRMNL OG panel"),
    # Designer emits printf format strings with literal `%` at the end
    # ("%.0f%", "--%"), which is undefined behaviour. Escape it.
    (re.compile(r'(?<!%)%(?=")'), "%%"),
]


def fix(text: str) -> str:
    for pat, repl in FIXES:
        text = pat.sub(repl, text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", nargs="?", help="file to read (default: stdin)")
    ap.add_argument(
        "-i", "--in-place", action="store_true",
        help="rewrite the given file in place (requires file argument)",
    )
    args = ap.parse_args()

    if args.in_place and not args.file:
        ap.error("-i requires a file argument")

    raw = Path(args.file).read_text() if args.file else sys.stdin.read()
    fixed = fix(raw)

    if args.in_place:
        Path(args.file).write_text(fixed)
        sys.stderr.write(f"Patched {args.file}\n")
    else:
        sys.stdout.write(fixed)


if __name__ == "__main__":
    main()
