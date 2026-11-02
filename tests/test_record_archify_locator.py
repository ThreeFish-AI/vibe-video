"""find_remotion 双档定位（I-082 表因①）：嵌套工作区不再误报「未找到任何集的 node_modules」。

record_archify 模块顶部 import playwright，但 find_remotion 是纯文件系统探测、
零 playwright 消费——用最小 stub 满足模块导入即可在无 playwright 环境真跑
（machine_checks 不装 playwright；importorskip 先例会让本回归在门禁环境静默
跳过、钉不住失败形态）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"

_DRIVER = (
    "import record_archify; "
    "hit = record_archify.find_remotion(); "
    "print('None' if hit is None else f'{hit[0]}|{hit[1]}')"
)


def _stub_playwright(tmp_path: Path) -> None:
    """最小 playwright stub：只满足模块级 import，被测路径不触它。"""
    pkg = tmp_path / "stubs" / "playwright"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "sync_api.py").write_text(
        "def sync_playwright():\n    raise NotImplementedError('stub')\n",
        encoding="utf-8",
    )


def _ws_with_episode(tmp_path: Path, rel: str) -> Path:
    """工作区哨兵 + 一集「已装好」的 remotion CLI（假可执行文件，is_file 即命中）。"""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".vibe-video-root").write_text("", encoding="utf-8")
    exe = ws / "episodes" / rel / "video" / "node_modules" / ".bin" / "remotion"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    return ws


def _find(ws: Path, tmp_path: Path) -> str:
    """子进程驱动（cwd 刻意不在工作区内：锚不得依赖调用现场）。"""
    _stub_playwright(tmp_path)
    r = subprocess.run(
        [sys.executable, "-c", _DRIVER],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        env={
            **os.environ,
            "VIBE_VIDEO_WORKSPACE": str(ws),
            "PYTHONPATH": os.pathsep.join([str(tmp_path / "stubs"), str(SCRIPTS)]),
        },
    )
    assert r.stderr == "", r.stderr
    return r.stdout.strip()


def test_locates_nested_episode(tmp_path):
    """嵌套集 node_modules 装好仍找不到 = 改前形态（cdp 预检误报 FAIL 的根）。"""
    ws = _ws_with_episode(tmp_path, "demo-group/ep-n1")
    out = _find(ws, tmp_path)
    assert out != "None", "嵌套集 remotion CLI 漏定位——I-082 表因①回归"
    exe, proj = out.split("|")
    assert exe.endswith("episodes/demo-group/ep-n1/video/node_modules/.bin/remotion")
    assert proj.endswith("episodes/demo-group/ep-n1/video")


def test_flat_episode_still_located(tmp_path):
    """平面布局照常命中（双档第一档，向后兼容）。"""
    ws = _ws_with_episode(tmp_path, "ep-f1")
    out = _find(ws, tmp_path)
    assert out.endswith("episodes/ep-f1/video"), out


def test_multi_level_nesting_is_non_goal(tmp_path):
    """多级嵌套刻意不认——`**` 会给非目标形态隐性支持面（比选见 I-081）。"""
    ws = _ws_with_episode(tmp_path, "g1/g2/ep-deep")
    out = _find(ws, tmp_path)
    assert out == "None", out
