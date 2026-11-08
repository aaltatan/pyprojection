import runpy
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.py"))


class TestExamples:
    def test_there_are_examples(self):
        assert EXAMPLES

    @pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
    def test_example_runs_and_its_asserts_hold(self, path, capsys):
        runpy.run_path(str(path), run_name="__main__")
        assert capsys.readouterr().out
