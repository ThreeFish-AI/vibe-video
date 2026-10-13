"""check_archify 结构门：素材帧率口径与未知 slug 的失败形态。

夹具在 tmp_path 铺最小工程（manifest / views / 产物 / sidecar / scenes cue），
不给 audio manifest——rate 预演按设计跳过并 WARN，不影响受测判据。
CLI 门测试断言 (returncode, 输出子串)，同 test_check_archify_coverage 范式。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_archify.py"

CHAPTER = {
    "id": "ch1",
    "label": "首章",
    "file": "demo--ch1.mp4",
    "endStill": "demo--ch1-end.png",
    "beats": 1,
    "leadSec": 2.0,
    "storySec": 3.0,
    "beatNodes": ["n1"],
}


def _scene(slug: str) -> str:
    return (
        "export const P0X = () => (\n"
        f'  <ArchifyRecap slug="{slug}" caption="演示" variant="inset"\n'
        "    cues={[\n"
        "      {chapterId: 'ch1', at: at('p0-01') - bA.from, durationInFrames: dur('p0-01')},\n"
        "    ]}\n"
        "  />\n"
        ");\n"
    )


def build(tmp_path: Path, *, chapter_fps: dict, cue_slug: str = "demo") -> Path:
    root = tmp_path / "fixture-check-archify"
    arch = root / "video" / "public" / "archify"
    (arch / "views").mkdir(parents=True)
    (arch / "views" / "demo.json").write_text(json.dumps([{"id": "ch1"}]), "utf-8")
    for name in (CHAPTER["file"], CHAPTER["endStill"]):
        (arch / name).write_bytes(b"x")
    # 顶层 measured_fps 取 CDP 档的 CFR 输出值（恒 25），真实采集帧率只在逐章 capture_fps
    (arch / "demo.json").write_text(
        json.dumps(
            {
                "slug": "demo",
                "measured_fps": 25.0,
                "chapters": [{"id": "ch1", **chapter_fps}],
            }
        ),
        "utf-8",
    )
    src = root / "video" / "src"
    (src / "scenes").mkdir(parents=True)
    (src / "archify.manifest.ts").write_text(
        "export const ARCHIFY = "
        + json.dumps(
            {"demo": {"slug": "demo", "chapters": [CHAPTER]}}, ensure_ascii=False
        )
        + " as const satisfies Record<string, ArchifyDiagram>;\n",
        "utf-8",
    )
    (src / "scenes" / "P0X.tsx").write_text(_scene(cue_slug), "utf-8")
    return root


def run_archify_gate(root: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode, r.stdout + r.stderr


def test_low_capture_fps_warns_despite_cfr_measured_fps(tmp_path):
    """CDP 档 measured_fps 恒 25：门须按逐章 capture_fps 判，否则 min_fps 形同虚设。"""
    rc, out = run_archify_gate(
        build(tmp_path, chapter_fps={"measured_fps": 25.0, "capture_fps": 12.0})
    )
    assert rc == 0 and "录制帧率 12.0 < 18.0" in out, out

    rc, out = run_archify_gate(
        build(tmp_path / "ok", chapter_fps={"measured_fps": 25.0, "capture_fps": 24.0})
    )
    assert rc == 0 and "录制帧率" not in out, out


def test_legacy_sidecar_falls_back_to_measured_fps(tmp_path):
    """playwright 档无 capture_fps：回退逐章 measured_fps（VFR 实测值）。"""
    rc, out = run_archify_gate(build(tmp_path, chapter_fps={"measured_fps": 15.0}))
    assert "录制帧率 15.0 < 18.0" in out, out


def test_cue_with_unknown_slug_fails_not_crashes(tmp_path):
    """cue 引用 manifest 外的图 → 点名 FAIL，而非 KeyError traceback。"""
    rc, out = run_archify_gate(
        build(tmp_path, chapter_fps={"capture_fps": 25.0}, cue_slug="ghost")
    )
    assert rc == 1 and "ghost" in out and "不存在的图" in out, out
    assert "Traceback" not in out, out


# ---------------- fps 口径边界（topology C11 特征加固：钉现状，非收编） ----------------


def _sidecar(root: Path) -> Path:
    return root / "video" / "public" / "archify" / "demo.json"


def test_zero_capture_fps_treated_as_missing_by_or_chain(tmp_path):
    """capture_fps=0.0 是 falsy——现状 `capture_fps or measured_fps` 把它当缺失
    回退 measured_fps=25.0，门放行。录制器 encode_frames 已构造性排除 0.0，该
    形态只在手改/损坏输入可达；本用例钉住现状语义，收编口径时不得静默变更。"""
    rc, out = run_archify_gate(
        build(tmp_path, chapter_fps={"capture_fps": 0.0, "measured_fps": 25.0})
    )
    assert rc == 0 and "录制帧率" not in out, out


def test_chapter_without_id_still_enters_fps_min(tmp_path):
    """章 dict 缺 `id` 键照常参与 min 判定——fps 提取不读章 id（id 只在
    manifest×views 一致性面消费），缺 id 不会把该章静默滤出帧率门。"""
    root = build(tmp_path, chapter_fps={"capture_fps": 25.0})
    d = json.loads(_sidecar(root).read_text("utf-8"))
    d["chapters"] = [{"id": "ch1", "capture_fps": 25.0}, {"measured_fps": 15.0}]
    _sidecar(root).write_text(json.dumps(d), "utf-8")
    rc, out = run_archify_gate(root)
    assert rc == 0 and "录制帧率 15.0 < 18.0" in out, out


def test_top_level_measured_fps_fallback_without_chapters(tmp_path):
    """sidecar 无 `chapters` 键 → 逐章列表为空，回退顶层 measured_fps=9.0 判门。"""
    root = build(tmp_path, chapter_fps={"capture_fps": 25.0})
    d = json.loads(_sidecar(root).read_text("utf-8"))
    d.pop("chapters")
    d["measured_fps"] = 9.0
    _sidecar(root).write_text(json.dumps(d), "utf-8")
    rc, out = run_archify_gate(root)
    assert rc == 0 and "录制帧率 9.0 < 18.0" in out, out
