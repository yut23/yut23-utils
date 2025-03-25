import contextlib
import importlib.util
import os
import sys
from types import ModuleType


def import_from_path(module_name: str, file_path: os.PathLike[str]) -> ModuleType:
    """https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        msg = "importlib.util.spec_from_file_location() returned an invalid module spec"
        raise ImportError(msg, name=module_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        # clear out sys.modules if there was an error
        with contextlib.suppress(KeyError):
            del sys.modules[module_name]
        raise
    return module
