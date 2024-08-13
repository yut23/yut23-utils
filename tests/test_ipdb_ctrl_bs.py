from __future__ import annotations

from typing import TYPE_CHECKING

import IPython.terminal.debugger
import pytest

from yut23_utils._prompt_toolkit_ctrl_bs import _CTRL_BACKSPACE_SEQ, patch

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


def mock_esc_seqs(mocker: MockerFixture) -> MagicMock:
    # this is accessed by name in _get_reverse_ansi_sequences()
    ansi_seqs = mocker.patch.dict(
        "prompt_toolkit.input.ansi_escape_sequences.ANSI_SEQUENCES", clear=True
    )
    esc_seqs = mocker.patch(
        "yut23_utils._prompt_toolkit_ctrl_bs.esc_seqs",
        ANSI_SEQUENCES=ansi_seqs,
        REVERSE_ANSI_SEQUENCES={},
    )
    mocker.seal(esc_seqs)
    return esc_seqs


class TestIpdbCtrlBs:
    def test_no_keys_controlbackspace(self, mocker: MockerFixture) -> None:
        # Keys.ControlBackspace not present
        esc_seqs = mock_esc_seqs(mocker)

        Keys = mocker.patch("yut23_utils._prompt_toolkit_ctrl_bs.Keys")  # noqa: N806
        del Keys.ControlBackspace

        patch()

        assert _CTRL_BACKSPACE_SEQ in esc_seqs.ANSI_SEQUENCES
        key = esc_seqs.ANSI_SEQUENCES[_CTRL_BACKSPACE_SEQ]
        assert isinstance(key, tuple)
        assert not esc_seqs.REVERSE_ANSI_SEQUENCES

    def test_with_keys_controlbackspace(self, mocker: MockerFixture) -> None:
        # Keys.ControlBackspace present
        esc_seqs = mock_esc_seqs(mocker)

        Keys = mocker.patch("yut23_utils._prompt_toolkit_ctrl_bs.Keys")  # noqa: N806
        Keys.ControlBackspace = "c-backspace"

        with pytest.warns(
            UserWarning, match="Keys.ControlBackspace already present in prompt_toolkit"
        ):
            patch()

        assert _CTRL_BACKSPACE_SEQ in esc_seqs.ANSI_SEQUENCES
        key = esc_seqs.ANSI_SEQUENCES[_CTRL_BACKSPACE_SEQ]
        assert key == Keys.ControlBackspace
        assert esc_seqs.REVERSE_ANSI_SEQUENCES[key] == _CTRL_BACKSPACE_SEQ

    def test_unneeded(self, mocker: MockerFixture) -> None:
        esc_seqs = mock_esc_seqs(mocker)

        # add placeholder entry for _CTRL_BACKSPACE_SEQ
        esc_seqs.ANSI_SEQUENCES[_CTRL_BACKSPACE_SEQ] = mocker.sentinel.key

        with pytest.warns(UserWarning, match="fully supported in prompt_toolkit"):
            patch()

        # check that the module didn't make any changes
        assert len(esc_seqs.ANSI_SEQUENCES) == 1
        assert esc_seqs.ANSI_SEQUENCES[_CTRL_BACKSPACE_SEQ] is mocker.sentinel.key
        assert not esc_seqs.REVERSE_ANSI_SEQUENCES


def test_ipdb_ctrl_bs(mocker: MockerFixture) -> None:
    # mock out the patch function, as we've tested it above
    mock_patch = mocker.patch("yut23_utils._prompt_toolkit_ctrl_bs.patch")
    # undo imports when the test is finished
    mocker.patch.dict("sys.modules")

    # pylint: disable-next=import-outside-toplevel
    from yut23_utils.ipdb_ctrl_bs import TerminalPdb

    assert mock_patch.call_count == 1
    assert TerminalPdb is IPython.terminal.debugger.TerminalPdb
