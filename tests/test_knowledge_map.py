"""knowledge-map 反向完备性（整仓 preening 第二轮补的执法面）。

knowledge-map.md 自称「全仓文档的唯一索引」——既有执法只查出链可达，
没有「每篇文档都在索引里」的反向门：索引静默腐化（新增文档漏登记）
时无任何信号。本文件补反向门：受索引管辖面（根文档 / references /
docs/.agents / docs/research / evals）的每个 .md 必须以相对链接形态
出现在 knowledge-map.md 中。assets/** 是模板与产物（voices/README、
skeleton README.tmpl 等内容模板件），不属「知识文档」，刻意不在管辖面。
"""

from __future__ import annotations

import os
import subprocess

from paths import skill_root  # noqa: E402

KM_REL = os.path.join("docs", ".agents", "knowledge-map.md")
GOVERNED_PREFIXES = (
    "references/",
    "docs/.agents/",
    "docs/research/",
    "evals/",
)
GOVERNED_ROOTS = ("SKILL.md", "README.md", "CHANGELOG.md", "RSI.md")


def _tracked_md_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], capture_output=True, text=True, check=True
    )
    files = []
    for f in out.stdout.splitlines():
        if f.startswith("assets/"):
            continue  # 模板/产物面，见模块 docstring
        if f.startswith(GOVERNED_PREFIXES) or f in GOVERNED_ROOTS:
            files.append(f)
    return sorted(files)


def test_every_governed_doc_is_indexed():
    """管辖面每个 .md 都能以相对链接形态在 knowledge-map.md 中找到。"""
    km = (skill_root() / KM_REL).read_text(encoding="utf-8")
    km_dir = (skill_root() / KM_REL).parent
    missing = []
    for f in _tracked_md_files():
        if f == KM_REL:
            continue  # 索引不自链；其入口由 test_knowledge_map_self_indexed 执法
        rel = os.path.relpath(skill_root() / f, km_dir)
        if not any(f"({p}{rel}{s})" in km for p in ("", "./") for s in ("", "#")):
            missing.append(f"{f}（缺链接 ({rel}) 或 ({'./' + rel})）")
    assert not missing, (
        "knowledge-map 反向完备性失守——以下文档未入索引（新增文档须同批登记，"
        "「全量索引」的承诺才有执法面）：\n  " + "\n  ".join(missing)
    )


def test_knowledge_map_self_indexed():
    """索引文件自身也可从管辖面链接抵达（README 文档地图 → knowledge-map）。"""
    km_path = skill_root() / KM_REL
    rel_from_readme = os.path.relpath(km_path, skill_root())
    readme = (skill_root() / "README.md").read_text(encoding="utf-8")
    assert f"({rel_from_readme})" in readme, (
        f"README 文档地图缺 knowledge-map 链接 ({rel_from_readme})——索引无入口即孤岛"
    )
