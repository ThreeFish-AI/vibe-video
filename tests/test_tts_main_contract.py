"""tts.py main 的进程内接线契约（C8 文件内拆分的护栏，先于拆分在 HEAD 采集）。

方法：monkeypatch sys.argv（argv[0] 固定 "tts.py"）+ asyncio.run(tts.main())，
patch 引擎合成与 HTTP/存储边界（synth_edge / synth_indextts / synth_block_indextts /
http_json / store_has / mp3_duration），把每次调用的 (args, kwargs) JSON 化后
断言序列。只依赖「调用时按全局名查找」的模块级符号，不假设 main 内部结构
（拆分前后逐字一致 ⇒ 行为等价的直接证据）。

pytestmark 把 RuntimeWarning 升级为错误：漏 await 的协程（如能力闸被静默跳过）
在这里当场红，而不是靠 subprocess 用例间接暴露。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import pytest

import tts  # noqa: E402 - tests/conftest.py 已把 scripts/ 注入 sys.path

pytestmark = pytest.mark.filterwarnings("error::RuntimeWarning")

FAKE_DIGEST = "0123456789abcdef0123456789abcdef01234567"
DEFAULT_SERVER = "http://127.0.0.1:8766"


def _sha1_12(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def _j(x):
    """调用参数 JSON 化：Path→str、Semaphore→占位串，其余原样（dict/list/tuple 递归）。"""
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, asyncio.Semaphore):
        return "<sem>"
    if isinstance(x, dict):
        return {k: _j(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_j(v) for v in x]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


def _project(
    tmp_path: Path, items: list[dict], timing_gap: float | None = None
) -> Path:
    """最小工程骨架：narration.json（+ 可选 timing.json）。"""
    root = tmp_path / "proj"
    (root / "script").mkdir(parents=True)
    (root / "video" / "public" / "audio").mkdir(parents=True)
    (root / "script" / "narration.json").write_text(
        json.dumps(items, ensure_ascii=False), encoding="utf-8"
    )
    if timing_gap is not None:
        src = root / "video" / "src"
        src.mkdir(parents=True)
        (src / "timing.json").write_text(
            json.dumps({"sentenceGapSec": timing_gap}), encoding="utf-8"
        )
    return root


def _ref_wav(tmp_path: Path) -> Path:
    ref = tmp_path / "me.wav"
    ref.write_bytes(b"RIFFfake-pcm-bytes")
    return ref


def _recorder(name: str, ret=None):
    """纯记录器：只记调用并返回固定值。"""
    calls: list = []

    def fake(*args, **kwargs):
        calls.append(
            {
                "func": name,
                "args": [_j(v) for v in args],
                "kwargs": {k: _j(v) for k, v in kwargs.items()},
            }
        )
        return ret

    return fake, calls


def _synth_fake(name: str, digest: str = FAKE_DIGEST, duration: float = 2.5):
    """合成函数替身：记录调用 + 写确定性 mp3/.sha + 返回 manifest 行
    （block 档返回成员列表，main 原样展平）。"""
    calls: list = []

    async def fake(*args, **kwargs):
        calls.append(
            {
                "func": name,
                "args": [_j(v) for v in args],
                "kwargs": {k: _j(v) for k, v in kwargs.items()},
            }
        )
        if name == "synth_block_indextts":
            members, out_dir = args[1], next(a for a in args if isinstance(a, Path))
            for item in members:
                (out_dir / f"{item['id']}.mp3").write_bytes(
                    b"ID3" + name.encode() + item["id"].encode()
                )
                (out_dir / f"{item['id']}.sha").write_text(digest, encoding="utf-8")
            return [{**item, "durationSec": duration} for item in members]
        item = next(a for a in args if isinstance(a, dict))
        out_dir = next(a for a in args if isinstance(a, Path))
        (out_dir / f"{item['id']}.mp3").write_bytes(
            b"ID3" + name.encode() + item["id"].encode()
        )
        (out_dir / f"{item['id']}.sha").write_text(digest, encoding="utf-8")
        return {**item, "durationSec": duration}

    return fake, calls


def _read(out_dir: Path, name: str) -> str:
    return (out_dir / name).read_text(encoding="utf-8")


# ---------------- edge 成功路径 ----------------


def test_edge_success_writes_manifest_engine_sha(monkeypatch, tmp_path, capsys):
    """假 synth_edge 逐句写确定性 mp3/.sha ⇒ manifest.json / .engine / stdout 回执
    全部接线正确；调用序列（顺序+参数）JSON 化逐字段断言。"""
    items = [
        {"id": "p0-01", "scene": "P0", "text": "第一句"},
        {"id": "p0-02", "scene": "P0", "text": "第二句"},
    ]
    root = _project(tmp_path, items)
    fake, synth_calls = _synth_fake("synth_edge")
    mp3dur, mp3dur_calls = _recorder("mp3_duration", ret=2.5)
    monkeypatch.setattr(tts, "synth_edge", fake)
    monkeypatch.setattr(tts, "mp3_duration", mp3dur)
    monkeypatch.setattr(sys, "argv", ["tts.py", "--project", str(root)])

    asyncio.run(tts.main())

    out_dir = root / "video" / "public" / "audio"
    assert json.loads(_read(out_dir, "manifest.json")) == [
        {"id": "p0-01", "scene": "P0", "text": "第一句", "durationSec": 2.5},
        {"id": "p0-02", "scene": "P0", "text": "第二句", "durationSec": 2.5},
    ]
    assert _read(out_dir, ".engine") == "edge|zh-CN-YunxiNeural|+4%\n"
    assert _read(out_dir, "p0-01.sha") == FAKE_DIGEST
    assert _read(out_dir, "p0-02.sha") == FAKE_DIGEST
    out = capsys.readouterr().out
    assert "合成 2 句，纯语音总时长 0.08 分钟" in out
    assert f"manifest: {out_dir / 'manifest.json'}" in out
    # 接线：edge 引擎按 items 原序、缺省音色/语速/ZH、不强制重合成
    assert synth_calls == [
        {
            "func": "synth_edge",
            "args": [
                "<sem>",
                {"id": "p0-01", "scene": "P0", "text": "第一句"},
                False,
                "zh-CN-YunxiNeural",
                "+4%",
                str(out_dir),
                "ZH",
            ],
            "kwargs": {},
        },
        {
            "func": "synth_edge",
            "args": [
                "<sem>",
                {"id": "p0-02", "scene": "P0", "text": "第二句"},
                False,
                "zh-CN-YunxiNeural",
                "+4%",
                str(out_dir),
                "ZH",
            ],
            "kwargs": {},
        },
    ]
    # 时长来自合成边界返回值，main 不二次实测
    assert mp3dur_calls == []


# ---------------- --list-styles 早退 ----------------


def test_list_styles_prints_table_and_exits_zero(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["tts.py", "--list-styles"])
    asyncio.run(tts.main())
    out = capsys.readouterr().out
    assert out.startswith("风格")
    assert "sunny-steady" in out
    assert "seed=4242" in out  # story 档自带种子须在表尾标出


# ---------------- indextts --plan（不落盘、不连服） ----------------


def test_indextts_plan_prints_plan_and_writes_nothing(monkeypatch, tmp_path, capsys):
    """--plan 纯本地预演：打印排期，不落 manifest/.engine、不连服务。"""
    items = [
        {"id": "p0-01", "scene": "P0", "text": "第一句"},
        {"id": "p0-02", "scene": "P0", "text": "第二句"},
    ]
    root = _project(tmp_path, items)
    ref = _ref_wav(tmp_path)
    store_has, store_calls = _recorder("store_has", ret=False)
    never, never_calls = _synth_fake("synth_indextts")
    monkeypatch.setattr(tts, "store_has", store_has)
    monkeypatch.setattr(tts, "synth_indextts", never)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tts.py",
            "--project",
            str(root),
            "--engine",
            "indextts",
            "--plan",
            "--no-store",
            "--style",
            "sunny",
            "--ref",
            str(ref),
        ],
    )

    asyncio.run(tts.main())

    out_dir = root / "video" / "public" / "audio"
    assert not (out_dir / "manifest.json").exists()
    assert not (out_dir / ".engine").exists()
    out = capsys.readouterr().out
    assert ">> 计划：proj · 风格 sunny · alpha 0.35 · 语速 0.95" in out
    assert "束宽 1：待合成   2 句 · 已缓存   0 句" in out
    assert "估算墙钟约" in out
    # 逐句查库计划；不合成
    assert [c["args"][2] for c in store_calls] == ["p0-01", "p0-02"]
    assert never_calls == []


# ---------------- indextts 成功路径（/health 能力闸全过） ----------------

#: 全能力位健康回包（六个 supports_* 全 True）——成功路径与能力闸负例共用基线。
HEALTH_OK = {
    "ok": True,
    "version": "2.5",
    "supports_duration_factor": True,
    "supports_emo_text": True,
    "supports_sampling_params": True,
    "supports_seed": True,
    "supports_text_normalization": True,
    "supports_blocks": True,
}


def test_indextts_success_sentence_mode(monkeypatch, tmp_path, capsys):
    """逐句档：http_json 只做一次 /health；synth_indextts 逐句接线
    （束宽/情感/采样/库槽位），.engine 指纹、manifest、回执全部落位。"""
    items = [
        {"id": "p0-01", "scene": "P0", "text": "第一句"},
        {"id": "p0-02", "scene": "P0", "text": "第二句"},
    ]
    root = _project(tmp_path, items)
    ref = _ref_wav(tmp_path)
    ref_sha1 = _sha1_12(b"RIFFfake-pcm-bytes")
    fake, synth_calls = _synth_fake("synth_indextts")
    http, http_calls = _recorder("http_json", ret=dict(HEALTH_OK))
    mp3dur, mp3dur_calls = _recorder("mp3_duration", ret=2.5)
    monkeypatch.setattr(tts, "synth_indextts", fake)
    monkeypatch.setattr(tts, "http_json", http)
    monkeypatch.setattr(tts, "mp3_duration", mp3dur)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tts.py",
            "--project",
            str(root),
            "--engine",
            "indextts",
            "--final-voice",
            "--style",
            "sunny",
            "--no-store",
            "--ref",
            str(ref),
        ],
    )

    asyncio.run(tts.main())

    out_dir = root / "video" / "public" / "audio"
    assert http_calls == [
        {
            "func": "http_json",
            "args": ["GET", f"{DEFAULT_SERVER}/health", None, 10],
            "kwargs": {},
        }
    ]
    assert _read(out_dir, ".engine") == f"indextts|indextts|sunny|{ref_sha1}\n"
    assert json.loads(_read(out_dir, "manifest.json")) == [
        {"id": "p0-01", "scene": "P0", "text": "第一句", "durationSec": 2.5},
        {"id": "p0-02", "scene": "P0", "text": "第二句", "durationSec": 2.5},
    ]
    out = capsys.readouterr().out
    assert "合成 2 句，纯语音总时长 0.08 分钟" in out
    # 接线：位置参数（sem/item/force/ref/ref_sha1/风格/向量/α/df/语言/tag/服务/out_dir）
    # + 关键字槽位（束宽/情感参考/采样/库）。story 之外的逐句档束宽 1、采样空 dict。
    expected_args = [
        "<sem>",
        {"id": "p0-01", "scene": "P0", "text": "第一句"},
        False,
        str(Path(str(ref)).expanduser().resolve()),
        ref_sha1,
        "sunny",
        tts.STYLE_PRESETS["sunny"]["vec"],
        0.35,
        0.95,
        "ZH",
        "indextts",
        DEFAULT_SERVER,
        str(out_dir),
    ]
    tail_kwargs = {
        "num_beams": 1,
        "emo_ref": None,
        "emo_ref_sha1": None,
        "emo_text": None,
        "sampling": {},
        "store": None,
        "slug": "proj",
    }
    assert synth_calls == [
        {
            "func": "synth_indextts",
            "args": expected_args,
            "kwargs": tail_kwargs,
        },
        {
            "func": "synth_indextts",
            "args": [
                "<sem>",
                {"id": "p0-02", "scene": "P0", "text": "第二句"},
                *expected_args[2:],
            ],
            "kwargs": tail_kwargs,
        },
    ]
    assert mp3dur_calls == []


def test_indextts_success_block_mode(monkeypatch, tmp_path, capsys):
    """story 档（块模式）：块=一次请求单位，discard_sec 取 timing.json 的
    sentenceGapSec，块参数（尾垫/表演标点）与预设种子进 sampling。"""
    items = [
        {"id": "p0-01", "scene": "P0", "text": "第一句"},
        {"id": "p0-02", "scene": "P0", "text": "第二句"},
    ]
    root = _project(tmp_path, items, timing_gap=0.25)
    ref = _ref_wav(tmp_path)
    ref_sha1 = _sha1_12(b"RIFFfake-pcm-bytes")
    fake, block_calls = _synth_fake("synth_block_indextts")
    http, _ = _recorder("http_json", ret=dict(HEALTH_OK))
    monkeypatch.setattr(tts, "synth_block_indextts", fake)
    monkeypatch.setattr(tts, "http_json", http)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tts.py",
            "--project",
            str(root),
            "--engine",
            "indextts",
            "--final-voice",
            "--style",
            "story",
            "--no-store",
            "--ref",
            str(ref),
        ],
    )

    asyncio.run(tts.main())

    out_dir = root / "video" / "public" / "audio"
    assert json.loads(_read(out_dir, "manifest.json")) == [
        {"id": "p0-01", "scene": "P0", "text": "第一句", "durationSec": 2.5},
        {"id": "p0-02", "scene": "P0", "text": "第二句", "durationSec": 2.5},
    ]
    assert _read(out_dir, ".engine") == f"indextts|indextts|story|{ref_sha1}\n"
    assert block_calls == [
        {
            "func": "synth_block_indextts",
            "args": [
                "<sem>",
                [
                    {"id": "p0-01", "scene": "P0", "text": "第一句"},
                    {"id": "p0-02", "scene": "P0", "text": "第二句"},
                ],
                False,
                str(Path(str(ref)).expanduser().resolve()),
                ref_sha1,
                "story",
                tts.STYLE_PRESETS["story"]["vec"],
                0.28,
                1.0,
                "ZH",
                "indextts",
                DEFAULT_SERVER,
                str(out_dir),
            ],
            "kwargs": {
                "num_beams": 1,  # story 预设 beams=1
                "sampling": {"seed": 4242},  # story 预设自带种子（进采样摘要）
                "store": None,
                "slug": "proj",
                "discard_sec": 0.25,  # 来自 timing.json 的 sentenceGapSec
                "tail_pad_sec": 0.18,
                "perform_punct": True,
            },
        }
    ]


# ---------------- /health 能力闸（6 能力组合 × parser.error rc=2） ----------------

#: 各能力闸负例：能力位缺席 + 触发该闸的最小 argv + stderr 片段。
#: supports_seed 在 story 档先于 blocks 闸命中（预设种子），故 blocks 负例须带
#: supports_seed=True；supports_sampling_params 同理先于 text_normalization 闸。
HEALTH_GATE_CASES = [
    pytest.param(
        [],
        {"ok": True},
        ["--duration-factor", "1.5"],
        "无语速控制",
        id="duration-factor",
    ),
    pytest.param(
        [],
        {"ok": True, "supports_duration_factor": True},
        ["--emo-text", "轻快爽朗"],
        "QwenEmotion",
        id="emo-text",
    ),
    pytest.param(
        [],
        {"ok": True},
        ["--temperature", "0.9"],
        "不支持采样参数",
        id="sampling-params",
    ),
    pytest.param(
        [],
        {"ok": True, "supports_sampling_params": True},
        ["--no-text-normalization"],
        "无 text_normalization 形参",
        id="text-normalization",
    ),
    pytest.param(
        [],
        {"ok": True},
        ["--seed", "4242"],
        "不支持 --seed",
        id="seed",
    ),
    pytest.param(
        [],
        {"ok": True, "supports_seed": True},
        ["--style", "story"],
        "不支持块合成",
        id="blocks",
    ),
]


@pytest.mark.parametrize("_,health,extra_argv,frag", HEALTH_GATE_CASES)
def test_health_capability_gate_errors(
    monkeypatch, tmp_path, capsys, _, health, extra_argv, frag
):
    """/health 能力闸六组合：缺对应能力位 + 触发参数 ⇒ parser.error（SystemExit rc=2），
    且绝不进入合成阶段。"""
    items = [{"id": "p0-01", "scene": "P0", "text": "第一句"}]
    root = _project(tmp_path, items)
    ref = _ref_wav(tmp_path)
    never, never_calls = _synth_fake("synth_indextts")
    http, _ = _recorder("http_json", ret=dict(health))
    monkeypatch.setattr(tts, "synth_indextts", never)
    monkeypatch.setattr(tts, "http_json", http)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tts.py",
            "--project",
            str(root),
            "--engine",
            "indextts",
            "--final-voice",
            "--no-store",
            "--ref",
            str(ref),
            *extra_argv,
        ],
    )

    with pytest.raises(SystemExit) as ei:
        asyncio.run(tts.main())
    assert ei.value.code == 2
    assert frag in capsys.readouterr().err
    assert never_calls == []  # 能力闸先于一切合成


@pytest.mark.parametrize(
    "health_ret",
    [
        pytest.param({"ok": False, "version": "2.5"}, id="ok-false"),
        pytest.param(RuntimeError("连接失败: refusing"), id="conn-fail"),
    ],
)
def test_health_unreachable_exits_rc1(monkeypatch, tmp_path, capsys, health_ret):
    """ok=false 与连接失败 ⇒ 提示启动命令并 sys.exit(1)（与 parser.error 的 rc2 区分）。"""
    root = _project(tmp_path, [{"id": "p0-01", "scene": "P0", "text": "第一句"}])
    ref = _ref_wav(tmp_path)
    if isinstance(health_ret, Exception):

        def bad_http(*a, **k):
            raise health_ret
    else:

        def bad_http(*a, **k):
            return dict(health_ret)

    never, never_calls = _synth_fake("synth_indextts")
    monkeypatch.setattr(tts, "synth_indextts", never)
    monkeypatch.setattr(tts, "http_json", bad_http)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tts.py",
            "--project",
            str(root),
            "--engine",
            "indextts",
            "--final-voice",
            "--no-store",
            "--ref",
            str(ref),
        ],
    )

    with pytest.raises(SystemExit) as ei:
        asyncio.run(tts.main())
    assert ei.value.code == 1
    assert "IndexTTS 服务不可用" in capsys.readouterr().err
    assert never_calls == []
