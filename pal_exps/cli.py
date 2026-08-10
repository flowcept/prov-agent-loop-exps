from __future__ import annotations

from .analysis import build_metrics_main, query_suite_main
from .codex_capture import main as start_adapter_main
from .export_import import export_main, import_main
from .validation import validate_main


def start_adapter() -> None:
    start_adapter_main()


def query_suite() -> None:
    query_suite_main()


def build_metrics() -> None:
    build_metrics_main()


def export_run() -> None:
    export_main()


def import_run() -> None:
    import_main()


def validate_run() -> None:
    validate_main()
