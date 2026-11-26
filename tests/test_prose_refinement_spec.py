"""成文规格依据分层与事实订正的回归锚（I-095）。

I-095 订正的是 Markdown 长行里的半句（一句依据分层与三处事实表述），纯文字
事实没有行为测试可执法，行锚是防回退的最低成本形态（写法同
test_directing_craft / test_voice_tiers 的文档级锚定执法）：
  1. 05 §八依据按来源性质分层；[18] 只是该文实验条件下的结论，不得回写成
     「清楚流畅的科普视频反而没有学习增益」的通则；
  2. story 档不是新集终声档默认（新集缺省引擎是 edge，story 档是克隆升档
     引擎的默认风格档，见 07 两档表），05 两处括注不得回退；
  3. DIRECTING-CRAFT 的 13 CPS 是屏幕阅读速度的估值、未校准，限定语须留在
     含该数值的同一行；
  4. 研究文档检查表覆盖面计数记为 Z1–Z14，旧计数 Z1–Z13 不得回退。
"""

from __future__ import annotations

from helpers import lines_with, read_ref
from paths import skill_root

RESEARCH = skill_root() / "docs" / "research" / "prose-refinement.md"


def test_evidence_tiering_and_fact_corrections():
    """I-095：05 依据分层与两处事实订正、13 CPS 未校准限定、研究文档 Z1–Z14 计数不回退。"""
    spec = read_ref("05-prose-refinement.md")
    assert "反而没有学习增益" not in spec, (
        "05 回写了「反而没有学习增益」：[18] 只支持其实验条件下的结论，"
        "不支持「清楚流畅的科普视频没有学习增益」的通则（I-095）"
    )
    assert "新集终声档默认" not in spec, (
        "05 回写了「新集终声档默认」：新集缺省引擎是 edge，story 档是克隆升档"
        "引擎的默认风格档，旧串与 07 两档表矛盾（I-095）"
    )
    assert "依据按来源性质分层" in spec, (
        "05 §八缺「依据按来源性质分层」：依据列混用作者文论、英文广播从业者"
        "文章、社区/厂商清单与英文语料研究，不分层则读者无从判断可迁移性"
    )

    craft = read_ref("DIRECTING-CRAFT.md")
    assert lines_with(craft, "13 CPS", "未校准"), (
        "DIRECTING-CRAFT 含「13 CPS」的行缺「未校准」：13 CPS 是屏幕阅读速度的"
        "估值、暂无核实来源，限定语须与数值同行（I-095）"
    )

    research = RESEARCH.read_text(encoding="utf-8")
    assert "Z1–Z13" not in research, (
        "研究文档回写了旧计数「Z1–Z13」：检查表覆盖面应记为 Z1–Z14"
    )
    assert "Z1–Z14" in research, (
        "研究文档缺「Z1–Z14」：检查表覆盖面计数须与 05 检查表一致"
    )
