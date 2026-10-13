"""TTS 机制已上收 vibe-tts：tts.py 只许再导出，不得再内联副本（RSI 不变量 16）。

两道防线：
  - 行为面：tts.X 的 `__module__` 必须落在 vibe_tts_*，不是本文件；
  - 结构面：AST 扫 tts.py 顶层，被上收的名字不得再以 def/class/赋值形态出现。
vibe-tts 缺位必须大声退出，不得静默降级到内联实现。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import tts

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

#: 上收到 vibe-tts 的函数/类（行为面按 __module__ 判）。
MOVED_CALLABLES = [
    "tts_text",
    "mp3_duration",
    "parse_emo_vector",
    "sampling_suffix",
    "digest_edge",
    "digest_indextts",
    "block_digest_suffix",
    "NonRetryableError",
    "_http_error_detail",
    "_deterministic_mps_oom",
    "http_json",
    "http_synthesize",
    "http_synthesize_block",
    "store_entry",
    "store_has",
    "store_deposit",
    "store_restore",
    "frame_db",
    "silence_runs",
    "plan_block_cuts",
    "split_block_pcm",
]
#: 上收的数据常量（结构面按 AST 判；无 __module__）。
MOVED_DATA = [
    "DEFAULT_VOICE",
    "DEFAULT_RATE",
    "EMO_KEYS",
    "STYLE_PRESETS",
    "SAMPLING_PASSTHROUGH_DEFAULTS",
    "SAMPLING_DEFAULTS",
    "SAMPLING_RANGES",
    "CONCURRENCY_INDEXTTS",
    "HTTP_TIMEOUT",
    "RETRIES",
]


@pytest.mark.parametrize("name", MOVED_CALLABLES)
def test_moved_callable_comes_from_vibe_tts(name):
    mod = getattr(tts, name).__module__
    assert mod.startswith("vibe_tts_"), (
        f"tts.{name} 来自 {mod}，应是 vibe-tts 的 vibe_tts_* 模块（不得内联副本）"
    )


def test_tts_py_defines_none_of_the_moved_names():
    tree = ast.parse((SCRIPTS / "tts.py").read_text(encoding="utf-8"))
    local: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            local.add(node.name)
        elif isinstance(node, ast.Assign):
            local.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            local.add(node.target.id)
    dup = sorted(local & (set(MOVED_CALLABLES) | set(MOVED_DATA)))
    assert not dup, f"tts.py 内联了已上收到 vibe-tts 的定义：{dup}"


def test_server_script_lives_in_vibe_tts_not_here():
    assert not (SCRIPTS / "tts_server.py").exists(), (
        "服务端已上收 vibe-tts，本仓不得再带副本"
    )
    assert tts.SERVER_SCRIPT.name == "vibe_tts_server.py"
    assert tts.SERVER_SCRIPT.is_file()
    assert SCRIPTS not in tts.SERVER_SCRIPT.parents, (
        "服务端脚本不应落在本仓 scripts/ 下"
    )


def test_vibe_tts_scripts_is_appended_not_prepended():
    """append 而非 insert(0)：本仓兄弟模块优先解析，vibe-tts 的同名模块不得遮蔽它们。"""
    vibe_tts_scripts = str(tts._VIBE_TTS_SCRIPTS)
    assert vibe_tts_scripts in sys.path
    here = str(SCRIPTS)
    if here in sys.path:
        assert sys.path.index(here) < sys.path.index(vibe_tts_scripts)


def test_missing_vibe_tts_exits_loudly(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))  # 屏蔽真实 ~/.claude/skills/vibe-tts
    monkeypatch.setenv("VIBE_TTS_HOME", str(tmp_path / "nope"))
    with pytest.raises(SystemExit) as e:
        tts._find_vibe_tts_scripts()
    msg = str(e.value)
    assert "找不到 vibe-tts skill" in msg and "ln -sfn" in msg, (
        "须列出已检查候选并给出安装命令"
    )
    assert str(tmp_path / "nope") in msg


def test_vibe_tts_home_wins_over_mounts(monkeypatch, tmp_path):
    fake = tmp_path / "vibe-tts"
    (fake / "scripts").mkdir(parents=True)
    (fake / "SKILL.md").write_text("x")
    (fake / "scripts" / "vibe_tts.py").write_text("x")
    monkeypatch.setenv("VIBE_TTS_HOME", str(fake))
    assert tts._find_vibe_tts_scripts() == (fake / "scripts").resolve()


def test_vibe_tts_dir_without_sentinels_is_rejected(monkeypatch, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("VIBE_TTS_HOME", str(empty))
    with pytest.raises(SystemExit):
        tts._find_vibe_tts_scripts()
