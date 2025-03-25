# SPDX-FileCopyrightText: 2025-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

# pylint: disable=redefined-outer-name
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from yut23_utils.imports import import_from_path

MODULE_CONTENTS = """
CONSTANT = 42

def frobnicate(x: int) -> float:
    return x / 2
"""


@pytest.fixture
def example_path(tmp_path):
    p = tmp_path / "example.py"
    p.write_text(MODULE_CONTENTS, encoding="utf-8")
    return p


def test_import_from_path(example_path: Path) -> None:
    # shield other tests from changes to sys.modules
    with patch.dict(sys.modules):
        assert "example" not in sys.modules
        example = import_from_path("example", example_path)
        assert example.__name__ == "example"
        assert example.__file__ == str(example_path)
        assert example.CONSTANT == 42
        assert example.frobnicate(2) == 1
        assert example is sys.modules["example"]


def test_invalid_import(example_path: Path) -> None:
    with patch.dict(sys.modules):
        assert "example" not in sys.modules
        with pytest.raises(FileNotFoundError):
            import_from_path("example", example_path.with_suffix(".not-existing.py"))
        assert "example" not in sys.modules


def test_invalid_suffix(example_path: Path) -> None:
    with patch.dict(sys.modules):
        assert "example" not in sys.modules
        with pytest.raises(ImportError, match="returned an invalid module spec"):
            import_from_path("example", example_path.with_suffix(".invalid-suffix"))
        assert "example" not in sys.modules
