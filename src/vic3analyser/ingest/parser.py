"""A parser for the Clausewitz/Jomini text format used by Paradox files.

Handles the subset needed for Victoria 3 melted saves and ``common/`` game
definitions:

* ``key = value`` assignments, with values being scalars or ``{ ... }`` blocks
* duplicate keys (very common in saves) collapsed into a list of values
* arrays of bare scalars: ``key = { 1 2 3 }`` -> ``[1, 2, 3]``
* arrays of blocks: ``key = { {..} {..} }`` -> ``[{...}, {...}]``
* quoted strings, ``#`` comments, ``yes``/``no`` booleans, numbers, dates
* comparison operators (``<``, ``>``, ``<=`` ...) found in trigger blocks of
  game defs; these are captured but rarely needed by the analyser.

Script-value math (``@var``, ``@[ ... ]``) is preserved verbatim as strings; it
is the higher layers' job to interpret it when relevant.

The parsed document is a plain ``dict`` (insertion-ordered). Duplicate keys map
to a ``list``. Bare-scalar / block-only blocks become a Python ``list``. A mixed
block keeps its keyed entries plus a ``"__values__"`` list for the bare ones.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

__all__ = ["parse", "parse_file", "as_list", "coerce_scalar"]

_TOKEN_RE = re.compile(
    r"""
      [ \t\r\n]+              # whitespace
    | \#[^\n]*               # comment
    | "(?:[^"\\]|\\.)*"      # quoted string
    | [{}]                   # braces
    | (?:<=|>=|!=|==|<|>|=)  # operators
    | [^\s{}=<>#"]+          # bare token
    """,
    re.VERBOSE,
)

_OPERATORS = {"=", "<", ">", "<=", ">=", "==", "!="}
_BRACES = {"{", "}"}


def _tokenize(text: str) -> list[str]:
    """Return significant tokens (whitespace and comments stripped)."""
    tokens: list[str] = []
    append = tokens.append
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        first = tok[0]
        if first in " \t\r\n#":
            continue
        append(tok)
    return tokens


def coerce_scalar(tok: str) -> Any:
    """Convert a bare/quoted token to a native Python scalar."""
    if tok and tok[0] == '"':
        # unquote, handling simple backslash escapes
        return tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if tok == "yes":
        return True
    if tok == "no":
        return False
    # int
    try:
        return int(tok)
    except ValueError:
        pass
    # float (but not dates like 1836.1.1 which have two dots)
    if tok.count(".") == 1:
        try:
            return float(tok)
        except ValueError:
            pass
    return tok


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.toks = tokens
        self.i = 0
        self.n = len(tokens)

    def _peek(self, ahead: int = 0) -> str | None:
        j = self.i + ahead
        return self.toks[j] if j < self.n else None

    def parse_document(self) -> dict:
        result = self._parse_map(top_level=True)
        return result

    # A block's contents, already past the opening '{'. Decides array vs map.
    def _parse_block(self) -> Any:
        # Empty block
        if self._peek() == "}":
            self.i += 1
            return {}

        # Look at the first element to guess shape: `tok op` => map, else array.
        first = self._peek()
        second = self._peek(1)
        if first != "{" and second in _OPERATORS:
            return self._parse_map(top_level=False)
        # Could still be a map if it starts with a nested block key... but in the
        # PDX format a block key is always `name op {`, caught above. So treat as
        # an array of scalars and/or blocks.
        return self._parse_array()

    def _parse_array(self) -> list:
        items: list[Any] = []
        while True:
            tok = self._peek()
            if tok is None:
                break
            if tok == "}":
                self.i += 1
                break
            if tok == "{":
                self.i += 1
                items.append(self._parse_block())
            else:
                self.i += 1
                items.append(coerce_scalar(tok))
        return items

    def _parse_map(self, top_level: bool) -> dict:
        result: dict[str, Any] = {}
        bare_values: list[Any] = []

        def add(key: str, value: Any) -> None:
            if key in result:
                existing = result[key]
                if isinstance(existing, list) and getattr(existing, "_multi", False):
                    existing.append(value)
                else:
                    lst = _MultiList([existing, value])
                    result[key] = lst
            else:
                result[key] = value

        while True:
            tok = self._peek()
            if tok is None:
                break
            if tok == "}":
                if not top_level:
                    self.i += 1
                break

            op = self._peek(1)
            if op in _OPERATORS:
                key = coerce_key(tok)
                self.i += 2  # consume key and operator
                value = self._parse_value()
                add(key, value)
            else:
                # A bare value inside what we thought was a map (mixed block).
                self.i += 1
                if tok == "{":
                    bare_values.append(self._parse_block())
                else:
                    bare_values.append(coerce_scalar(tok))

        if bare_values:
            if not result:
                return bare_values  # type: ignore[return-value]
            result["__values__"] = bare_values
        return result

    def _parse_value(self) -> Any:
        tok = self._peek()
        if tok == "{":
            self.i += 1
            return self._parse_block()
        self.i += 1
        return coerce_scalar(tok)


class _MultiList(list):
    """A list produced by collapsing duplicate keys (vs an array literal)."""

    _multi = True


def coerce_key(tok: str) -> str:
    if tok and tok[0] == '"':
        return tok[1:-1]
    return tok


def parse(text: str) -> dict:
    """Parse Clausewitz text into a nested dict."""
    return _Parser(_tokenize(text)).parse_document()


def parse_file(path: str | Path, encoding: str = "utf-8-sig") -> dict:
    """Parse a Clausewitz text file. Falls back to latin-1 on decode errors."""
    p = Path(path)
    try:
        text = p.read_text(encoding=encoding)
    except UnicodeDecodeError:
        text = p.read_text(encoding="latin-1")
    return parse(text)


def as_list(value: Any) -> list:
    """Normalise a value that may be a single item or a list into a list.

    Useful for keys that appear once or many times in the source.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    # Empty braces `{}` parse to an empty dict; for "list of tokens" fields
    # (unlocking_technologies, production_methods, ...) that means "none".
    if isinstance(value, dict):
        return [] if not value else [value]
    return [value]
