"""Shim to support CSI-u ctrl-backspace in ipdb under pytest.

Monkey-patches prompt_toolkit to handle the escape sequence upon import.

Usage: pytest --pdb --pdbcls=yut23_utils.ipdb_ctrl_bs:TerminalPdb
"""

from IPython.terminal.debugger import TerminalPdb

from yut23_utils._prompt_toolkit_ctrl_bs import patch

__all__ = ["TerminalPdb"]

patch()
