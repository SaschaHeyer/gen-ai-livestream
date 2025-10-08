from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any


def _load_automation_module() -> Any:
    """
    Dynamically load the automation script so we can call run_agent() directly.
    """
    module_dir = Path(__file__).resolve().parent
    module_path = module_dir / "automation-gemini-computer-use.py"
    if not module_path.exists():
        raise FileNotFoundError(f"automation script missing at {module_path}")

    spec = importlib.util.spec_from_file_location("automation_gemini", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_and_print(target_url: str, note_text: str | None = None, pdf_source: str | None = None) -> None:
    module = _load_automation_module()
    run_agent = getattr(module, "run_agent", None)
    if run_agent is None:
        raise AttributeError("automation module does not expose run_agent()")

    result = run_agent(target_url=target_url, note_text=note_text, pdf_source=pdf_source)
    if result:
        print(result)
