from __future__ import annotations

from contextlib import redirect_stdout
import io
import json

from spark_researcher.cli import print_json


class _Output(io.StringIO):
    def __init__(self, *, terminal: bool) -> None:
        super().__init__()
        self._terminal = terminal

    def isatty(self) -> bool:
        return self._terminal


def _render(payload: object, *, terminal: bool) -> str:
    output = _Output(terminal=terminal)
    with redirect_stdout(output):
        print_json(payload)
    return output.getvalue()


def test_print_json_is_pretty_and_sorted_for_terminal() -> None:
    rendered = _render({"z": 2, "a": 1}, terminal=True)

    assert rendered == '{\n  "a": 1,\n  "z": 2\n}\n'


def test_print_json_is_compact_and_sorted_for_pipeline() -> None:
    rendered = _render({"z": 2, "a": 1}, terminal=False)

    assert rendered == '{"a":1,"z":2}\n'
    assert json.loads(rendered) == {"a": 1, "z": 2}
