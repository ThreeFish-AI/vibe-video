"""Stage ① 三型信源（A paper-notes / B source-notes / C gl-notes）的锚定执法（I-030）。

C 型（guided-learn 精读产物）落地后的纪律：**文件名清单只在 01 顶部分流表一处枚举**，
下游规格一律三型泛引（指针指向 01），防第四型出现时再复制十余处。本文件钉四个字符串
锚点（写法同 test_docs_paths 的文案锚定测试）；刻意不做「02–05 全文禁裸 paper-notes」
类脆断言——01 的 A 型正文与各规格对 A 型的具名使用（如「A 型即 paper-notes」括注）是
合法形态，一刀切禁词会把它们误判成漂移。

I-060 追加：B 型纯代码仓库「结构骨架与素材映射」节（骨架是派生视图非证据）与
Understand-Anything 按集 opt-in 子节的桥接锚，下游 02/03/04/05/06/09 同步指针——跨文件指针
按节名断言、不带节号（01 自身标题除外），防节号顺移再复制一份脆锚。
"""

from __future__ import annotations

import re

from helpers import lines_with, read_ref, read_skill_md


def _type_table_rows(text: str) -> dict[str, str]:
    """→ {型别字母: 该行全文}：01 顶部块引用分流表里的 A/B/C 数据行。"""
    out: dict[str, str] = {}
    for ln in text.splitlines():
        m = re.match(r">\s*\|\s*\*\*([ABC])\*\*\s*\|", ln)
        if m:
            out[m.group(1)] = ln
    return out


def test_source_type_table_lists_three_types():
    """01 顶部分流表须含 A/B/C 三行，C 行指向 research/gl-notes.md（型别判定 SSOT）。"""
    rows = _type_table_rows(read_ref("01-source-extraction.md"))
    assert set(rows) == {"A", "B", "C"}, (
        f"01 顶部分流表应含 A/B/C 三行，实际 {sorted(rows)}——"
        "新增信源形态先挂分流表，挂不进 = 规格缺口而非绕路理由"
    )
    assert "research/gl-notes.md" in rows["C"], (
        "C 行事实源文件应为 research/gl-notes.md"
    )
    assert "guided-learn" in rows["C"], "C 行信源形态应点名 guided-learn 精读产物"


def test_narration_fact_source_line_covers_three_types():
    """03 头部模板行的事实源指引覆盖三型文件名，或含指向 01 的判定指针。"""
    text = read_ref("03-narration.md")
    src_lines = [ln for ln in text.splitlines() if "事实源：" in ln]
    assert src_lines, "03 头部模板行丢了「事实源：」指引（检测器失效？）"
    line = src_lines[0]
    has_all_names = all(
        name in line for name in ("paper-notes", "source-notes", "gl-notes")
    )
    points_to_spec = "01" in line
    assert has_all_names or points_to_spec, (
        f"03 事实源指引未泛化到三型：{line.strip()!r}——文件名清单的 SSOT 在 01 顶部表，"
        "此处要么三型并列、要么指针指向 01"
    )


def test_verification_checklist_column_generalized():
    """04 核查表列名须为「事实源锚点」；旧「paper-notes 锚点」是 B/C 型失配形态（反控红面）。"""
    text = read_ref("04-verification.md")
    assert "事实源锚点" in text, "04 核查表列名应为「事实源锚点」（三型泛引）"
    assert "paper-notes 锚点" not in text, (
        "04 核查表列名仍写「paper-notes 锚点」——B/C 型集按此列名找不到锚点落法"
    )


def test_skill_router_has_c_type_entry():
    """SKILL.md 任务分流表须含 C 型入口（GL 精读产物成片）。"""
    text = read_skill_md()
    assert "GL 精读产物" in text, (
        "SKILL.md 任务表缺「GL 精读产物成片」入口——上游 guided-learn 产物无路由，"
        "Stage ① 会被迫重复精读（I-030 表因）"
    )


def test_guided_learn_process_concretization_bridges():
    """I-032：GL 伴生资产直通承接、五元过程具象化映射、被动收看双门、成文护栏与四大分镜/动效定式须在位。"""
    s01 = read_ref("01-source-extraction.md")
    s02 = read_ref("02-planning.md")
    s04 = read_ref("04-verification.md")
    s05 = read_ref("05-prose-refinement.md")
    s06 = read_ref("06-storyboard.md")
    s08 = read_ref("08-remotion-implementation.md")

    assert "GL 伴生资产直通承接" in s01 and "过程具象化" in s01
    assert "视觉母题全片统摄" in s02 and "Worked Example" in s02
    assert "No Rule Without Trace" in s04 and "Zero Backward-Lookup" in s04
    assert "No Rule Without Trace" in s05 and "Worked Example" in s05
    assert "过程具象化四大定式动效落地" in s08
    for pattern in (
        "全景坐标先行",
        "机制必演单步流转",
        "反例必演消融对比",
        "数字必带基线标尺",
    ):
        assert pattern in s06, f"06-storyboard.md 缺少过程具象化定式：{pattern}"
        assert pattern in s08, (
            f"08-remotion-implementation.md 缺少过程具象化动效映射：{pattern}"
        )


def test_b_type_structure_skeleton_bridge():
    """I-060：B 型纯代码仓库结构骨架节 + UA 按集 opt-in 纪律在位，下游六规格同步指针。

    跨文件断言一律按节名（「结构骨架与素材映射」）、不带节号——01 节号再顺移不破此门；
    01 自身的「六、结构骨架与素材映射」标题是唯一带节号锚（目录行 TOC 门另案执法）。
    """
    s01 = read_ref("01-source-extraction.md")
    assert "## 六、结构骨架与素材映射" in s01, "01 缺 B 型结构骨架节（I-060 主体收益）"
    for anchor in ("派生视图，非证据", "按集 opt-in", "不进口播", "gitCommitHash"):
        assert anchor in s01, f"01 结构骨架节缺锚点：{anchor}"

    s02 = read_ref("02-planning.md")
    assert "前置概念" in s02, (
        "02 分幕表缺可选「前置概念」列（幕级先释后用，I-015 承接）"
    )
    assert lines_with(s02, "60–90 秒", "结构骨架与素材映射"), (
        "02 记忆点括注缺 B 型骨架指针（01/02 双处同步；行级共现，防同名他处代偿）"
    )
    assert "**名称对齐**（单向派生）" in s02, (
        "02 前置概念列缺名称对齐规则（④B --terms 取名方向与回改责任，防两份概念名清单漂移）"
    )

    s03 = read_ref("03-narration.md")
    assert "结构骨架与素材映射" in s03, (
        "03 术语降落括注缺 B 型骨架指针（02/03 双处同步）"
    )

    s05 = read_ref("05-prose-refinement.md")
    assert "前置概念" in s05, "05 §五缺「前置概念列不改写」半句"
    assert "结构骨架" in s05, (
        "05 §六冻结清单缺结构骨架节三要素（层名/节点名/走查链输入值）"
    )

    s04 = read_ref("04-verification.md")
    assert "前置概念" in s04, (
        "04 缺 `--terms` 从「前置概念」列逐字取的指针（02 名称对齐单向派生）"
    )

    s06 = read_ref("06-storyboard.md")
    assert lines_with(s06, "四定式", "B 型", "结构骨架与素材映射"), (
        "06 四定式引导句未泛化到 B 型结构骨架（按节名指针，不带节号）"
    )

    s09 = read_ref("09-render-qa.md")
    assert "上屏结构回溯" in s09, (
        "09 缺上屏结构回溯目检指针（06/09 单指针，判据以 06 为准）"
    )
