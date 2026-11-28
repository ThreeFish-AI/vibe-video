"""时序常数不得内联：RSI.md 第九节第 5 条的扫描测试。

钉的判由：`timing.json` 时序 SSOT（TS/Python 双语共读），不得在任何一侧内联时序
常数。Python 侧的合法入口是 `timeline.load_constants`；这里用 AST 扫时间轴相关脚本
里的 float 字面量，数值等于模板 timing.json 任一键的默认值、又不在容许清单里的
即红。

现存例外 2 处，都登记在容许清单 ALLOWED 里、处数钉死：scripts/tts.py 的
`discard_sec: float = 0.32`（函数默认参数，scripts/ 内唯一调用点显式传值，生产路径
不可达）与块模式（story 档）的 `discard_sec = 0.32`（timing.json 缺失、缺键或
损坏时静默沿用的回退值）。两处由 PR #17（I-011）引入；tts.py 受 paths.py 导入边界约束
不得 import timeline，回退行为是否改成大声退出属行为语义改动，不在本测试的改动面内。

只扫 float 字面量，不扫 int：按衍生值（帧数、毫秒数）扫会多出 10 处巧合命中
（秒转分钟的 60、sha 截断的 12 等），噪声压过信号；fps 的 30 是模板唯一的 int 默认值。

漏报面：注释、docstring 与字符串里的数值；以表达式给出的数值（如 `32 / 100`）；
TS 侧；分集场景代码；扫描名单之外的脚本（新增的时间轴相关脚本须手动加进
SCANNED_SCRIPTS）。
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import timeline

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TEMPLATE_DIR = ROOT / "assets" / "video-skeleton" / "video" / "src"
TEMPLATE_TIMING = TEMPLATE_DIR / "timing.json"
TEMPLATE_TIMING_TS = TEMPLATE_DIR / "timing.ts"
FIXTURE_TIMING = Path(__file__).resolve().parent / "fixtures" / "timing.json"

#: 读 timing.json 的时间轴相关脚本；名单外的脚本不扫。
SCANNED_SCRIPTS = (
    "timeline.py",
    "captions.py",
    "qa_frames.py",
    "check_script.py",
    "check_archify.py",
    "check_archify_coverage.py",
    "pipeline.py",
    "tts.py",
)

#: 容许清单：(脚本名, 数值, 允许处数, 镜像的 timing.json 键, 理由)。键为 None 表示与时序
#: 无关的数值巧合。清单只收「与时序无关的巧合」与「已在案的现存回退值」，不得借清单
#: 放行新增的镜像常量：新增时序常数一律经 `timeline.load_constants` 读取。坑位：模板
#: 默认值改成某个脚本里已有的数值时（如一位小数的权重），那个字面量会成为新命中，
#: 核实确属巧合后登记进清单。
ALLOWED = (
    (
        "tts.py",
        0.32,
        2,
        "sentenceGapSec",
        "现存回退值：synth_block_indextts 的 discard_sec 默认参数（scripts/ 内唯一"
        "调用点显式传值，生产路径不可达；tests/test_tts_blocks.py 的调用用到"
        "默认值），与块模式在 timing.json 缺失、缺键或损坏时沿用的回退值；"
        "PR #17（I-011）引入，tts.py 受 paths.py 导入边界约束不得 import timeline",
    ),
    ("tts.py", 0.6, 1, None, "与时序无关的巧合：情绪强度 emo_alpha 的缺省值"),
    ("tts.py", 2.0, 1, None, "与时序无关的巧合：语速校准 --duration-factor 取值域上界"),
)


def _template_defaults() -> dict:
    return json.loads(TEMPLATE_TIMING.read_text(encoding="utf-8"))


def _keys_by_value(defaults: dict) -> dict[float, list[str]]:
    """默认值 → 键名列表（模板里两个键同值时都要点名）。"""
    by_value: dict[float, list[str]] = {}
    for key, value in defaults.items():
        by_value.setdefault(float(value), []).append(key)
    return by_value


def _float_literals(tree: ast.AST):
    """产出 (行号, 数值)：AST 里的 float 数值常量。bool 是 int 的子类，天然不在内。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and type(node.value) is float:
            yield node.lineno, node.value


def test_no_inline_timing_constants_in_timeline_scripts():
    """时间轴相关脚本不得内联等于 timing.json 默认值的 float 字面量。

    默认值从模板现读（不写死），模板改值后扫描目标自动跟随。清单外的命中、
    清单内处数的增减都红。
    """
    keys_by_value = _keys_by_value(_template_defaults())
    expected = {(name, float(value)): count for name, value, count, _k, _r in ALLOWED}
    hits: dict[tuple[str, float], list[int]] = {}
    for name in SCANNED_SCRIPTS:
        path = SCRIPTS / name
        assert path.is_file(), (
            f"扫描名单里的脚本不存在：{name}（改名请同步 SCANNED_SCRIPTS）"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno, value in _float_literals(tree):
            if value in keys_by_value:
                hits.setdefault((name, value), []).append(lineno)

    extra = [
        f"{'、'.join(f'{name}:{n}' for n in sorted(where))}："
        f"{value!r} 等于 timing.json 的 "
        f"{'/'.join(keys_by_value[value])}"
        f"（容许 {expected.get((name, value), 0)} 处，实际 {len(where)} 处）"
        for (name, value), where in sorted(hits.items())
        if len(where) > expected.get((name, value), 0)
    ]
    assert not extra, (
        "时间轴相关脚本内联了时序常数：\n  "
        + "\n  ".join(extra)
        + "\n修法：时序常数改经 timeline.load_constants 读取（tts.py 受导入边界"
        "约束，只能由调用方经入参传入）；或确属与时序无关的巧合时登记进容许"
        "清单 ALLOWED 并写明理由"
    )

    stale = [
        f"{name} 的 {value!r}：容许 {count} 处，实际 {len(hits.get((name, value), []))} 处"
        for (name, value), count in expected.items()
        if len(hits.get((name, value), [])) < count
    ]
    assert not stale, (
        "容许清单已过期（命中数少于登记数）：\n  "
        + "\n  ".join(stale)
        + "\n修法：删掉该条目或把处数改对；模板默认值变了而回退值没跟的情况见 "
        "test_tts_block_fallback_matches_template"
    )


def test_timing_template_wiring_is_consistent():
    """三处键集逐字相等，夹具与模板逐字节相同。

    load_constants 只认 REQUIRED_KEYS，timing.ts 只认自己消费的键：键集不等意味
    着某一侧会对模板里的键视而不见。
    """
    template_keys = set(_template_defaults())
    ts_keys = set(
        re.findall(
            r"\bconstants\.([A-Za-z_][A-Za-z0-9_]*)",
            TEMPLATE_TIMING_TS.read_text(encoding="utf-8"),
        )
    )
    mismatches = []
    for label, keys in (
        ("timing.ts 消费的键", ts_keys),
        ("timeline.REQUIRED_KEYS", set(timeline.REQUIRED_KEYS)),
    ):
        if keys != template_keys:
            mismatches.append(
                f"{label}：仅模板有 {sorted(template_keys - keys)}，"
                f"仅该处有 {sorted(keys - template_keys)}"
            )
    assert not mismatches, "键集与模板 timing.json 不等：\n  " + "\n  ".join(mismatches)

    assert FIXTURE_TIMING.read_bytes() == TEMPLATE_TIMING.read_bytes(), (
        "tests/fixtures/timing.json 与模板 timing.json 不再逐字节相同："
        "模板默认值改了，夹具要跟着改"
    )


def test_tts_block_fallback_matches_template():
    """容许清单里登记为镜像的数值必须等于模板当前的默认值。

    tts.py 的回退值与模板在运行时并无绑定，相等只是约定；模板默认值改了而
    回退值没跟，这里先红。
    """
    defaults = _template_defaults()
    drifted = []
    for name, value, _count, key, _reason in ALLOWED:
        if key is None:
            continue
        if key not in defaults:
            drifted.append(f"{name} 的 {value!r}：模板 timing.json 已无键 {key}")
        elif float(value) != float(defaults[key]):
            drifted.append(f"{name} 的 {value!r} ≠ 模板 {key}={defaults[key]!r}")
    assert not drifted, (
        "镜像常量与模板 timing.json 漂移：\n  "
        + "\n  ".join(drifted)
        + "\n修法：模板默认值改了，就同步 scripts/tts.py 的回退值与 ALLOWED 的数值"
    )
