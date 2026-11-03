"""归档双档枚举与零归档 skip 的离线回归钉（I-091）。

tests/test_source_map.py 整文件 env-gate（真树集成模式，env 缺位全 skip）——
单档残留漂移（双档删回一档）在其门内不可见、machine_checks 计数无差。本文件
以 tmp_path 合成树钉住枚举形态：env 缺位照常执行，纯 pathlib、秒级（跨测试
模块导入先例：test_pron_gate.py 对 test_check_script）。
"""

from __future__ import annotations

import pytest

import test_source_map as tsm


def _mk_archive(ws, rel_ep: str) -> None:
    d = ws / rel_ep / "research" / "source-archive" / "abc1234"
    d.mkdir(parents=True)
    (d / "upstream.md.txt").write_text("archived bytes\n", encoding="utf-8")


def test_archive_dirs_enumerates_both_flat_and_nested(monkeypatch, tmp_path):
    """双档缺一即红：删第二档 → nested 失枚举；删第一档 → flat 失枚举。"""
    _mk_archive(tmp_path, "episodes/ep-flat")
    _mk_archive(tmp_path, "episodes/my-series/ep-nested")
    monkeypatch.setattr(tsm, "WORKSPACE", tmp_path)
    assert [str(d.relative_to(tmp_path)) for d in tsm.archive_dirs()] == [
        "episodes/ep-flat/research/source-archive",
        "episodes/my-series/ep-nested/research/source-archive",
    ]


def test_archives_or_skip_skips_on_empty(monkeypatch, tmp_path):
    """零归档 → pytest.skip（显式黄），不是空集静默通过。"""
    monkeypatch.setattr(tsm, "WORKSPACE", tmp_path)
    with pytest.raises(pytest.skip.Exception):
        tsm._archives_or_skip()
