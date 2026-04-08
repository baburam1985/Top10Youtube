"""Top 10 YouTube pipeline modules package."""

import importlib as _importlib
import sys as _sys

# Pre-load all submodules so that `modules.research`, `modules.script`, etc.
# are accessible as attributes (needed for `patch("modules.research.run")` style mocking).
for _name in [
    "modules.research",
    "modules.script",
    "modules.voice",
    "modules.visuals",
    "modules.captions",
    "modules.music",
    "modules.assembler",
    "modules.thumbnail",
    "modules.metadata",
]:
    try:
        _importlib.import_module(_name)
    except Exception:
        pass

# Expose submodules as package attributes
for _attr in [
    "research",
    "script",
    "voice",
    "visuals",
    "captions",
    "music",
    "assembler",
    "thumbnail",
    "metadata",
]:
    _full = f"modules.{_attr}"
    if _full in _sys.modules:
        globals()[_attr] = _sys.modules[_full]
