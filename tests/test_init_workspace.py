"""scaffold --init-workspace 的落盘契约：全工件、幂等、--force、旧哨兵共存。

init 是「新工作区的第一脚」，自己必须在**还不存在工作区**的目录里可跑
（paths 的惰性求值正是为它开的口子）。按真实调用形态（cwd=目标目录 +
脚本绝对路径）以子进程驱动，钉住：

  1. _WS_ARTIFACTS 映射与期望集一致——清单缩水（悄悄少掉哨兵或某个包装器）
     会产出「看起来正常但门全失效」的工作区，必须红在这里由人显式决策；
  2. 幂等 = 逐工件 skip-if-exists（二跑字节零变更），--force 才覆盖；
  4. 落盘的机读默认值可解析且为空——init 只做机械落盘，内容决策留给人。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import scaffold  # conftest 已把 scripts/ 注入 sys.path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = SKILL_ROOT / "scripts" / "scaffold.py"
WS_TEMPLATE = SKILL_ROOT / "assets" / "workspace"

#: _WS_ARTIFACTS 的契约钉（模板名 → 落盘名）：映射键集是被文档承诺的工作区
#: 骨架面，缩水即静默缺失的哨兵/包装器/指纹清单，须红在这里走人工决策。
EXPECTED_ARTIFACTS = {
    "vibe-video-root.tmpl": ".vibe-video-root",
    "series.json.tmpl": "series.json",
    "series.md.tmpl": "series.md",
    "vibe-video.toml.tmpl": "vibe-video.toml",
    "gitignore.tmpl": ".gitignore",
    "README.md.tmpl": "README.md",
    "scripts/pipeline.py.tmpl": "scripts/pipeline.py",
    "scripts/check_series.py.tmpl": "scripts/check_series.py",
    "voices/README.md": "voices/README.md",
    "voices/refs.toml": "voices/refs.toml",
}


def init(ws: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """按真实调用形态驱动：cwd=目标目录（--init-workspace 缺省 const="."
    依赖子进程 CWD 解析为该目录）+ 脚本绝对路径。

    env 剥掉 VIBE_VIDEO_WORKSPACE：init 路径本不消费它，剥掉是防外层
    （集成模式）env 在未来机制漂移时改变解析走向。"""
    r = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--init-workspace", *extra],
        cwd=ws,
        env={k: v for k, v in os.environ.items() if k != "VIBE_VIDEO_WORKSPACE"},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def tree_snapshot(root: Path) -> dict[str, bytes]:
    """→ {相对路径: 字节}。幂等判据用字节而非 mtime：skip-if-exists 语义下
    内容不许变；`.gitkeep` 的 touch 只动 mtime，天然不在比对面内。"""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_ws_artifacts_mapping_is_pinned():
    assert dict(scaffold._WS_ARTIFACTS) == EXPECTED_ARTIFACTS


def test_init_lays_down_every_artifact(tmp_path: Path):
    r = init(tmp_path)
    for src_name, dst_name in EXPECTED_ARTIFACTS.items():
        dst = tmp_path / dst_name
        assert dst.is_file(), f"init 未落盘 {dst_name}"
        # 逐工件字节等于模板：init 是纯机械复制不渲染——README 的
        # {{WORKSPACE_TITLE}} 刻意留给使用者按实态改写（人工步骤 4）
        assert dst.read_bytes() == (WS_TEMPLATE / src_name).read_bytes(), dst_name
    assert (tmp_path / ".vibe-video-root").is_file()
    for d in ("episodes", "source-map"):
        assert (tmp_path / d / ".gitkeep").is_file(), f"{d}/.gitkeep 缺失"
    assert f"新建 {len(EXPECTED_ARTIFACTS)} 件" in r.stdout


def test_second_run_is_byte_idempotent(tmp_path: Path):
    init(tmp_path)
    before = tree_snapshot(tmp_path)
    r = init(tmp_path)
    assert tree_snapshot(tmp_path) == before
    assert "新建 0 件" in r.stdout
    assert f"保留既有 {len(EXPECTED_ARTIFACTS)} 件" in r.stdout
    assert "--force" in r.stdout  # 发生保留时必须同时广告逃生口


def test_force_restores_tampered_artifacts(tmp_path: Path):
    init(tmp_path)
    (tmp_path / ".gitignore").write_text("# 本地私改\n", encoding="utf-8")
    (tmp_path / "series.json").write_text(
        '{"seriesList": [{"id": "mine"}]}\n', encoding="utf-8"
    )
    r = init(tmp_path, "--force")
    assert (tmp_path / ".gitignore").read_bytes() == (
        WS_TEMPLATE / "gitignore.tmpl"
    ).read_bytes()
    assert (tmp_path / "series.json").read_bytes() == (
        WS_TEMPLATE / "series.json.tmpl"
    ).read_bytes()
    assert f"新建 {len(EXPECTED_ARTIFACTS)} 件" in r.stdout
    assert "保留既有 0 件" in r.stdout


def test_machine_readable_defaults_parse_empty(tmp_path: Path):
    init(tmp_path)
    cfg = tomllib.loads((tmp_path / "vibe-video.toml").read_text(encoding="utf-8"))
    assert cfg == {
        "check_series": {
            "project_globs": [],
            "course_series_ids": [],
            "next_card_series_ids": [],
        }
    }
    assert json.loads((tmp_path / "series.json").read_text(encoding="utf-8")) == {
        "seriesList": []
    }


# ── 分发模板的布局口径（I-082 表因②③ + I-083 随带）─────────────────────────
# gitignore 单星 episodes/*/ 行只盖平面布局：全量嵌套工作区的 audio/ 与 archify
# 派生物不被 ignore，git status 整屏污染；README 的 <slug>-video 示范会让新工作区
# 复写已废除的命名约定（I-083）。


def test_gitignore_template_covers_nested_episode_artifacts(tmp_path: Path):
    """嵌套集与平面集的大件派生物同被 .gitignore 覆盖（真 git 语义，非文本形态）。"""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".gitignore").write_bytes((WS_TEMPLATE / "gitignore.tmpl").read_bytes())
    # GIT_CONFIG_*=/dev/null 隔离全局/系统 excludesFile，只验模板自身的规则
    subprocess.run(
        ["git", "init", "-q"],
        cwd=ws,
        capture_output=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
        check=True,
    )
    rels = [
        # audio/ 以目录本身判定（目录内 mp3 会被 **/*.mp3 兜底、测不出单星缺陷）
        "demo-group/ep-n1/video/public/audio",
        "demo-group/ep-n1/video/public/archify/d1.webm",
        "demo-group/ep-n1/video/public/archify/d1.mp4",
        "demo-group/ep-n1/video/public/archify/d1-end.png",
        "demo-group/ep-n1/video/public/out/draft.mp4",
        "ep-f1/video/public/audio",  # 平面布局同盖（** 匹配零层）
    ]
    for rel in rels:
        p = ws / "episodes" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix:
            p.write_bytes(b"x")
        else:
            p.mkdir(exist_ok=True)
    r = subprocess.run(
        ["git", "check-ignore", *[f"episodes/{rel}" for rel in rels]],
        cwd=ws,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
        check=False,
    )
    ignored = set(r.stdout.split())
    missing = [rel for rel in rels if f"episodes/{rel}" not in ignored]
    assert not missing, f"以下派生物未被 .gitignore 覆盖：{missing}"


def test_workspace_readme_template_is_layout_neutral():
    """工作区 README 模板不再示范 <slug>-video 与单层 episodes 假设（I-082/I-083）。"""
    text = (WS_TEMPLATE / "README.md.tmpl").read_text(encoding="utf-8")
    assert "<slug>-video" not in text, "已废除的 -video 命名不得再被模板示范"
    # 嵌套口径从句在位（$P 定义行指向 series.json `path`）
    assert "$P = $W/episodes/<slug>" in text
    assert "`path`" in text
