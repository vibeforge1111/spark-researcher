from __future__ import annotations

from unittest.mock import patch

from spark_researcher.ruvector import run_search


def test_run_search_uses_double_dash_before_query() -> None:
    """Queries starting with dashes must not be parsed as CLI flags."""
    fake_result = type(
        "FakeResult",
        (),
        {"returncode": 0, "stdout": '{"results": []}', "stderr": ""},
    )

    with patch("spark_researcher.ruvector.subprocess.run", return_value=fake_result()) as mock_run, \
         patch("spark_researcher.ruvector.shutil.which", return_value="/usr/bin/ruvector"), \
         patch("spark_researcher.ruvector._has_pi_identity", return_value=True):
        run_search("--output /etc/passwd")

    args_list = mock_run.call_args[0][0]
    dash_dash_index = args_list.index("--")
    query_index = dash_dash_index + 1
    assert args_list[query_index] == "--output /etc/passwd"
    assert "--json" in args_list


def test_run_search_double_dash_for_normal_query() -> None:
    """Normal queries also get the -- separator."""
    fake_result = type(
        "FakeResult",
        (),
        {"returncode": 0, "stdout": '{"results": []}', "stderr": ""},
    )

    with patch("spark_researcher.ruvector.subprocess.run", return_value=fake_result()) as mock_run, \
         patch("spark_researcher.ruvector.shutil.which", return_value="/usr/bin/ruvector"), \
         patch("spark_researcher.ruvector._has_pi_identity", return_value=True):
        run_search("machine learning basics")

    args_list = mock_run.call_args[0][0]
    assert "--" in args_list
    query_idx = args_list.index("--") + 1
    assert args_list[query_idx] == "machine learning basics"
