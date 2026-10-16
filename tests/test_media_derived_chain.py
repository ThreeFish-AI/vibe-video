"""媒体面派生链与改稿再生纪律的锚定执法（I-074）。

路由与规格是本纪律的行为面：SKILL.md 图示资产句与逐字稿不变量行承载「candidate
真源 / durationSec 指纹清单」的路由可见性，PIPELINE §五承载 sidecar 与 candidate
的辨析细则——任一回退，改稿后都会重新出现「手改 manifest / 把录制 sidecar 当
candidate 改」的静默漂移（I-074 运行时证据）。钉字符串锚点（写法同
test_voice_tiers / test_source_types 的文案锚定，存在性断言、不做内容快照）。
"""

from __future__ import annotations

from paths import skill_root

REFERENCES = skill_root() / "references"


def test_skill_routes_carry_derived_chain_anchors():
    """SKILL.md 须含 durationSec 与 docs/diagrams/ 锚串：派生链真源与指纹清单
    纪律在路由壳可见（改稿/改图入口第一步就能撞上，不必进 PIPELINE 才发现）。"""
    text = (skill_root() / "SKILL.md").read_text(encoding="utf-8")
    assert "durationSec" in text, (
        "SKILL.md 缺 durationSec 锚——manifest 每句实测时长的指纹清单纪律不在"
        "路由壳可见，改稿后手改 manifest 文本无门可拦（I-074 表因）"
    )
    assert "docs/diagrams/" in text, (
        "SKILL.md 缺 docs/diagrams/ 锚——candidate 图源真源位置不在路由壳可见，"
        "录制清单会被误当改图入口（I-074 表因）"
    )


def test_pipeline_has_sidecar_candidate_distinction():
    """PIPELINE §五须含派生链小节标题与「录制 sidecar」/candidate 辨析锚：
    「谁派生谁、改哪里重跑什么」的细则住处不被误删。"""
    text = (REFERENCES / "PIPELINE.md").read_text(encoding="utf-8")
    assert "媒体面派生链与改稿再生" in text, (
        "PIPELINE 缺「媒体面派生链与改稿再生」节——图示链与配音链的再生纪律"
        "无细则住处（I-074）"
    )
    assert "录制 sidecar" in text, (
        "PIPELINE 缺「录制 sidecar」辨析锚——video/public/archify/*.json 的"
        "身份（录制清单非 candidate）失明，重录链第一步即误读（I-074）"
    )
    assert "candidate" in text, (
        "PIPELINE 缺 candidate 图源真源锚——docs/diagrams candidate 与本地产"
        "产物的派生关系失明（I-074）"
    )
