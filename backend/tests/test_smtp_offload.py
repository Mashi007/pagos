# -*- coding: utf-8 -*-
import threading

from app.core.smtp_offload import run_in_smtp_thread


def test_run_in_smtp_thread_uses_other_thread():
    caller = threading.get_ident()
    seen = {}

    def _fn():
        seen["tid"] = threading.get_ident()
        seen["name"] = threading.current_thread().name
        return 7

    assert run_in_smtp_thread(_fn) == 7
    assert seen["tid"] != caller
    assert seen["name"].startswith("smtp-io")


def test_nested_run_in_smtp_thread_does_not_deadlock():
    def inner():
        return "ok"

    def outer():
        return run_in_smtp_thread(inner)

    assert run_in_smtp_thread(outer) == "ok"
