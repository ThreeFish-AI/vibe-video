#!/usr/bin/env python3
"""分镜表（storyboard.md）行解析唯一实现；消费者 check_script / check_archify_coverage /
qa_frames；不得写第二行文法。

两个消费者读同一个 storyboard.md，解析规则分叉即 split-brain：行集 = 镜号/
句区间/画面三列齐全的行（画面列在此一并取出——覆盖门的分镜声明对账要读它，
单独再写一个行正则就是第二解析器）。本模块纯函数、无 IO 之外的依赖（stdlib
re/pathlib），供各脚本以同目录 import 复用。
"""

from __future__ import annotations

import re
from pathlib import Path

#: 分镜表行：| 镜号 | 句区间 | 画面 | 动效 |。镜号形如 `0-A`/`2-B2`。
ROW_RE = re.compile(r"^\|\s*(\d+-[A-Z]\d*)[^|]*\|([^|]*)\|([^|]*)\|")
#: 句区间单元格：`p0-01..03`（右端可为裸编号，须补幕前缀）、`p6-06a..06d`、单句 `p6-07`。
SPAN_RE = re.compile(r"^\s*(p\d+-[0-9a-z-]+(?:\.\.[0-9a-z-]+)?)\s*([^|]*)$")
#: 幕名（P0/P1/…）从句 id 前缀还原
SCENE_OF_RE = re.compile(r"^(p\d+)-")


def _rows(path: Path) -> list[tuple[str, str, str]]:
    """→ [(镜号, 句区间单元格, 画面单元格)]。行集 = 镜号/句区间/画面三列齐全的行。

    画面列在此一并取出：覆盖门（check_archify_coverage）的分镜声明对账要读它，
    单独再写一个行正则就是第二解析器——分叉即 split-brain。"""
    out: list[tuple[str, str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if m := ROW_RE.match(raw):
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def parse_storyboard(path: Path) -> list[tuple[str, str, str, str]]:
    """返回 [(镜号, 起句id, 止句id, 区间单元格原文)]。单元格原文含「尾」= 刻意压尾标注。"""
    beats: list[tuple[str, str, str, str]] = []
    for beat_id, span_cell, _visual in _rows(path):
        sm = SPAN_RE.match(span_cell)
        if not sm:
            continue
        span, cell = sm.group(1), (sm.group(1) + sm.group(2))
        if ".." in span:
            left, _, right = span.partition("..")
            # 右端可为裸编号（p0-01..03）——须补幕前缀，否则永远匹配不到句子
            if not right.startswith("p"):
                scene = SCENE_OF_RE.match(left).group(1)  # type: ignore[union-attr]
                right = f"{scene}-{right}"
        else:
            left = right = span
        beats.append((beat_id, left, right, cell))
    return beats


def parse_storyboard_visual(path: Path) -> list[tuple[str, str]]:
    """→ [(镜号, 画面列原文)]。行集与 parse_storyboard 完全一致（同一 _rows + SPAN_RE
    过滤，索引按序对齐）——覆盖门从画面列抽 `·**archify …**` 声明。"""
    out: list[tuple[str, str]] = []
    for beat_id, span_cell, visual in _rows(path):
        if SPAN_RE.match(span_cell):
            out.append((beat_id, visual))
    return out
