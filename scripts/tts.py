#!/usr/bin/env python3
"""逐句合成配音并产出时长 manifest——公共管线版本（双引擎）。

- 输入：<工程>/script/narration.json（单一事实源派生）
- 输出：<工程>/video/public/audio/{id}.mp3 + <工程>/video/public/audio/manifest.json
- 引擎：
  - edge（默认）：edge-tts 预置音色，免密钥，行为与历史版本完全一致；
  - indextts：声音克隆（IndexTTS-2.5 本地服务），需先启动 tts_server.py，
    通过 --ref 提供参考音色样本、--style 选择风格（sunny 明快阳光为推荐位，
    sunny-steady 为其定稿档＝同参数 + 束宽 3；另有激情/轻快/自信/正能量）。
- 幂等：参数与文本未变则跳过（SHA1 摘要 sidecar 缓存）。
- 版本库（indextts）：合成成功的句子按 digest 存入机器级持久库（默认
  ~/Library/Application Support/vibe-video/tts-store，环境变量 VIBE_VIDEO_TTS_STORE
  覆盖，--no-store 禁用）；集内缓存未命中时先按 digest 回收——换 worktree / 清盘不再
  丢整集合成成果，改稿只重配变更句。历史版本按 digest 文件名并存，不互相覆盖。

用法：
  edge：    uv run --no-project --with edge-tts --with mutagen $T/scripts/tts.py \
                --project $P [--narration-lang zh] [--voice zh-CN-YunxiNeural] [--rate +4%] [--force]
  indextts：uv run --no-project --with mutagen $T/scripts/tts.py \
                --project $P --engine indextts --final-voice --ref <参考样本.wav> \
                [--style passionate] [--server http://127.0.0.1:8766] [--force]
                （--final-voice＝本人显式要求的具名授权，RSI-040：缺此 flag 的实跑硬失败）
  情感三来源（互斥）：--style/--emo-vector 向量注入 · --emo-ref <另一段录音> 语调迁移
                （更自然）· --emo-text "轻快爽朗、自信阳光" 自然语言（需服务端 --use-qwen-emo）
  （工程内薄包装等价于在工程目录下运行 scripts/tts.py）

声音克隆完整手册（部署/风格/排障/许可）见 references/VOICE-CLONING.md。
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import math
import os
import sys
from pathlib import Path


def _find_dub_scripts() -> Path:
    """定位 dub skill 的 scripts/（TTS 机制原语的 SSOT）。

    顺序：DUB_HOME → ~/.claude/skills/dub → ~/.agents/skills/dub；候选须同时含
    SKILL.md 与入口脚本 dub.py。找不到即大声退出——绝不静默降级到内联副本。
    本文件不 import 同目录兄弟模块（test_tts_lang_mirror 钉死），发现逻辑因此内联，
    与 dub 仓 dub_paths.find_dub_root 同构。
    """
    candidates = []
    if os.environ.get("DUB_HOME"):
        candidates.append(Path(os.environ["DUB_HOME"]).expanduser())
    candidates += [
        Path("~/.claude/skills/dub").expanduser(),
        Path("~/.agents/skills/dub").expanduser(),
    ]
    for c in candidates:
        if (c / "SKILL.md").is_file() and (c / "scripts" / "dub.py").is_file():
            return (c / "scripts").resolve()
    sys.exit(
        "找不到 dub skill（TTS 机制原语住在那里）。已检查：\n"
        + "\n".join(f"  - {c}" for c in candidates)
        + "\n安装：git clone https://github.com/ThreeFish-AI/dub ~/Documents/projects/aurelius/dub"
        " && ln -sfn ~/Documents/projects/aurelius/dub ~/.claude/skills/dub（或设 DUB_HOME）"
    )


_DUB_SCRIPTS = _find_dub_scripts()
# append 而非 insert(0)：dub 的库模块一律 dub_ 前缀，本仓兄弟模块优先解析，杜绝同名遮蔽
sys.path.append(str(_DUB_SCRIPTS))

# 机制原语（风格预设/摘要/HTTP 客户端/版本库/切分函数）全部来自 dub，在此再导出——
# 本文件内的编排代码、tts_sample.py 与测试经 `tts.X` 取用，命名空间保持不变。
from dub_audio import mp3_duration  # noqa: E402,F401
from dub_engine_edge import RETRIES, digest_edge  # noqa: E402,F401
from dub_engine_indextts import (  # noqa: E402,F401
    CONCURRENCY_INDEXTTS,
    HTTP_TIMEOUT,
    SAMPLING_DEFAULTS,
    SAMPLING_PASSTHROUGH_DEFAULTS,
    SAMPLING_RANGES,
    NonRetryableError,
    _deterministic_mps_oom,
    _http_error_detail,
    block_digest_suffix,
    digest_indextts,
    http_json,
    http_synthesize,
    http_synthesize_block,
    sampling_suffix,
    store_deposit,
    store_entry,
    store_has,
    store_restore,
)
from dub_profiles import (  # noqa: E402,F401
    DEFAULT_RATE,
    DEFAULT_VOICE,
    EMO_KEYS,
    STYLE_PRESETS,
    parse_emo_vector,
)
from dub_textprep import tts_text  # noqa: E402,F401
from dub_tts_blocks import (  # noqa: E402,F401
    frame_db,
    plan_block_cuts,
    silence_runs,
    split_block_pcm,
)

# edge_tts / mutagen 均惰性导入：克隆模式（indextts）无需 edge_tts；`--list-styles` 等本地操作零依赖。


#: 语言镜像表：narration-lang → (IndexTTS infer lang 码, edge 缺省音色)。
#: ⚠️ 内联而非 import langs——本文件会被拷进 ~/tools/index-tts 的 venv 单独运行
#: （paths.py「导入边界」），同目录依赖会断掉那条拷出路径；与 scripts/langs.py
#: 的 LANGS 注册表的一致性由 tests/test_tts_lang_mirror.py 钉住（timing.json
#: 「TS/Python 双语共读」的同构纪律）。路径后缀规则（zh 无后缀 / en 加 .en）
#: 同理内联，与 langs.narration_json / langs.audio_dir 同构。
LANG_MIRROR: dict[str, tuple[str, str]] = {
    "zh": ("ZH", DEFAULT_VOICE),
    "en": ("EN", "en-US-AndrewNeural"),
}
CONCURRENCY_EDGE = 6
MANUAL = str(
    Path(__file__).resolve().parents[1] / "references" / "VOICE-CLONING.md"
)  # skill 根 references/
SPEC_07 = str(
    Path(__file__).resolve().parents[1] / "references" / "07-tts-voice.md"
)  # 人为触发原则 SSOT（RSI-040）；与 MANUAL 同构派生，不 import 兄弟模块

# --plan 排期估算用的实测常数（MPS fp32，长跑折算口径：含降频、机器争用与逐句开销）。
# RTF_1BEAM 来自三集 596 句连续跑 8.5 小时 / 40.2 分钟纯语音；RTF_MULTIBEAM 由同句
# 1↔3 束 A/B 实测的约 3.2 倍推得（与早期 3 束直测的 RTF 40–58 区间一致）。
#
# ⚠️ 2026-08-20 实测偏差（EP1 v3 两遍法，187 句）：
#   A 遍 sunny(beams=1)：墙钟 ~1.9 h、纯语音 12.98 分 → 实测 RTF ≈ 8.8（常量 13 偏保守 1.5×）
#   B 遍 sunny-steady(beams=3)：墙钟 1.98 h、纯语音 12.89 分 → 实测 RTF ≈ 9.2（常量 45 偏保守 4.9×）
# 即机器空闲时 3 束的实际代价远低于「+241%」的旧口径（本次 B/A ≈ 1.04），旧数据应是
# 在机器被占用/热节流时测得。**常量刻意不下调**：--plan 的用途是排期决策，宁可高估
# 让人留出窗口，也不要低估导致长跑撞上其他任务；但看到估算与实测差 3–5 倍属正常。
RTF_1BEAM = 13.0
RTF_MULTIBEAM = 45.0
AVG_SEC_PER_LINE = 4.2  # 三集每句音频均值


def synth_source_text(item: dict) -> str:
    """取该句真正送去合成的文本：优先 `ttsText`（含发音标注），否则 `text`。

    `narration.json` 的 `text` 是**人读文本**，同时被字幕（captions.py）与字数预算
    （check_script.py）消费；发音标注只能进 `ttsText`，否则会泄漏到 SRT/VTT 并污染预算。
    未标注的句子没有 `ttsText` 字段 ⇒ 取值与历史完全一致 ⇒ 存量缓存不失效。
    """
    return item.get("ttsText") or item["text"]


# ---------------- 风格解析 ----------------


def resolve_style(
    args: argparse.Namespace,
) -> tuple[str, list[float] | None, float, float, int]:
    """返回 (风格名, 情感向量|None, emo_alpha, duration_factor, num_beams)。

    三个可覆盖参数（alpha / df / beams）一律「命令行显式给值优先，否则取预设」——
    故 --num-beams 的 argparse 默认值必须是 None 而非 1，否则无法区分「没给」与「给了 1」。
    """
    beams = args.num_beams if args.num_beams is not None else 1
    if args.emo_vector:
        vec = parse_emo_vector(args.emo_vector)
        alpha = args.emo_alpha if args.emo_alpha is not None else 0.6
        df = args.duration_factor if args.duration_factor is not None else 1.0
        return "raw", vec, alpha, df, beams
    preset = STYLE_PRESETS[args.style]
    alpha = args.emo_alpha if args.emo_alpha is not None else preset["alpha"]
    df = args.duration_factor if args.duration_factor is not None else preset["df"]
    if args.num_beams is None:  # 预设可自带束宽（如 sunny-steady=3），缺省为 1
        beams = preset.get("beams", 1)
    return args.style, preset["vec"], alpha, df, beams


#: 采样参数的 CLI 名 → 属性名（argparse 把连字符转下划线）。text_normalization / seed 单独处理。
SAMPLING_CLI = (
    "temperature",
    "top_p",
    "top_k",
    "length_penalty",
    "repetition_penalty",
    "max_mel_tokens",
    "interval_silence",
)


def resolve_sampling(args: argparse.Namespace) -> dict[str, float | int | bool]:
    """收集所有**被显式改动过**的采样参数；全默认时返回空 dict（摘要因此不变）。

    优先级同 alpha/df/beams：命令行显式给值 > 风格预设的 `sampling` 键 > 上游默认。
    预设自带采样参数是刻意留的扩展位——束宽已证明「属于风格的一部分」，length_penalty
    这类同样影响韵律的旋钮理应能随风格走；但**任何写进预设的值都会改摘要 ⇒ 整集重录**，
    故当前所有预设都不带 sampling，待 A/B 拿到证据后再定档。
    """
    preset: dict = STYLE_PRESETS.get(args.style, {}) if args.style else {}
    preset_sampling: dict = preset.get("sampling", {})
    out: dict[str, float | int | bool] = {}
    for key in SAMPLING_CLI:
        cli_val = getattr(args, key, None)
        val = cli_val if cli_val is not None else preset_sampling.get(key)
        if val is None:
            continue
        lo, hi = SAMPLING_RANGES[key]
        if not lo <= val <= hi:  # NaN 比较恒 False，一并被拦
            raise ValueError(f"--{key.replace('_', '-')} 必须在 [{lo:g}, {hi:g}]")
        if key == "top_k" and val == 1:
            raise ValueError(
                "--top-k 1 在束搜索下不安全（每束需保底 2 个候选）：用 0 关闭或 ≥2"
            )
        if val != SAMPLING_DEFAULTS[key]:
            out[key] = val
    if getattr(args, "no_text_normalization", False):
        out["text_normalization"] = False
    if getattr(args, "seed", None) is not None:
        # --seed-offset 是「换一条 take」的逃生口：固定种子会把某句锁死在一条可能不佳的
        # 采样结果上，偏移一位即可换一条而仍然可复现。
        out["seed"] = int(args.seed) + int(getattr(args, "seed_offset", 0) or 0)
    elif preset.get("seed") is not None:
        # 预设自带种子（story：定档 take 可复现）。CLI --seed 优先；--seed-offset 叠加（整集换 take）。
        # 经 |seed= 后缀进摘要（同 CLI 路径），故存量无种子口径零波及。
        out["seed"] = int(preset["seed"]) + int(getattr(args, "seed_offset", 0) or 0)
    return out


# ---------------- 混合档：整集低束宽 + 指定句高束宽 ----------------
#
# 动机（实测）：3 束把语调起伏收窄约 10–20%、听感更「稳/可信」，但短句 RTF 从 6–7 涨到
# 20–31（数字密集句可达 31.5），整集从 2.5–3.5 小时涨到 8–15 小时。而真正决定第一印象的
# 只是冷开场与各幕金句——把这几句单独升到 3 束即可。代价按句线性：189 句一集里每升 1 句
# 约 +2.2 分钟（+1.3%），升 5 句 2.9→3.1 小时、升 20 句 →3.6 小时，而整集升档要 9.9 小时。
# 缓存 sidecar 按句独立（摘要含 |beams=N），故同一集内混用两种束宽完全安全、可分批补跑。


def parse_steady_selector(spec: str) -> tuple[set[str], set[str], list[str]]:
    """`P0,p3-25b,p5-*` → (精确句 id, 幕名, 前缀)。

    判定规则（可预测、无歧义）：以 `*` 结尾→前缀通配；含 `-`→精确句 id；其余→幕名。
    全部大小写不敏感。
    """
    ids: set[str] = set()
    scenes: set[str] = set()
    prefixes: list[str] = []
    for raw in spec.split(","):
        tok = raw.strip().lower()
        if not tok:
            continue
        if tok.endswith("*"):
            prefixes.append(tok[:-1])
        elif "-" in tok:
            ids.add(tok)
        else:
            scenes.add(tok)
    if not (ids or scenes or prefixes):
        raise ValueError("--steady 不能为空")
    return ids, scenes, prefixes


def steady_match(
    item: dict, ids: set[str], scenes: set[str], prefixes: list[str]
) -> bool:
    sid = str(item["id"]).lower()
    if sid in ids or str(item.get("scene", "")).lower() in scenes:
        return True
    return any(sid.startswith(p) for p in prefixes)


# ---------------- 音色签名护栏（防整集静默改写） ----------------

#: 音频目录下的音色签名标记。逐句 `{id}.sha` 只能发现「这一句该重合成」，
#: 发现不了「整集正被换成另一种声音」——因为换音色时每一句的摘要都合法地变了。
#: 本标记补的正是这个缺口：它记录上次成功合成的引擎/音色/风格，
#: 与本次不一致时硬失败，要求显式 --allow-voice-switch。不参与逐句摘要，故零缓存影响。
ENGINE_MARKER = ".engine"

#: 服务端脚本住在 dub 仓（机制 SSOT）。启动命令此前有三份副本（本文件、tts_sample.py、
#: VOICE-CLONING.md），收敛为唯一生成处。
SERVER_SCRIPT = _DUB_SCRIPTS / "dub_tts_server.py"


def server_launch_hint(port: int = 8766) -> str:
    """返回可直接粘贴的 IndexTTS 服务启动命令（服务须运行在 index-tts 自己的环境里）。

    显式 flag 集对齐 VOICE-CLONING §2.3 权威命令（--indextts-version/--host 显式化，
    语义同服务端缺省）；可选的 --use-qwen-emo 以独立提示行呈现——tts_resume 的同名
    透传参数映射此 flag（RSI-035）。提示行用 POSIX `:` no-op 前缀而非 `#` 注释：
    macOS 缺省 zsh 交互态 interactivecomments 关闭，`#` 会连注释文本一起进入
    服务 argv、被 argparse 拒收（服务起不来）——`: ` 前缀在 bash/zsh/sh 粘贴
    均为无害空命令。
    """
    return (
        "  cd ~/tools/index-tts && uv run --frozen --with fastapi --with uvicorn \\\n"
        "      --with soundfile --with numpy --with lameenc \\\n"
        f"      python {SERVER_SCRIPT} --model-dir checkpoints --indextts-version 2.5 \\\n"
        f"      --host 127.0.0.1 --port {port} \n"
        "      : 可选：--use-qwen-emo（自然语言情感 --emo-text 需要，约 +1.5 GB 内存）"
    )


def check_voice_marker(out_dir: Path, signature: str, allow_switch: bool) -> None:
    """比对音色签名；不一致且未显式放行时硬失败。"""
    marker = out_dir / ENGINE_MARKER
    if not marker.exists():
        return
    previous = marker.read_text(encoding="utf-8").strip()
    if previous == signature or allow_switch:
        return
    sys.exit(
        f"音色签名与上次合成不一致，将整集改写（{len(list(out_dir.glob('*.mp3')))} 个 mp3 单槽位覆盖）：\n"
        f"  上次: {previous}\n"
        f"  本次: {signature}\n"
        f"若确为有意重录，请显式加 --allow-voice-switch；否则请检查 --engine/--ref/--style 是否写错。\n"
        f"详见 {MANUAL} §六"
    )


def write_voice_marker(out_dir: Path, signature: str) -> None:
    (out_dir / ENGINE_MARKER).write_text(signature + "\n", encoding="utf-8")


def enforce_final_voice_gate(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """人为触发原则主闸（RSI-040）：IndexTTS 声音克隆只在本人显式点名时启用。

    --final-voice 是具名授权声明——每次非 --plan 的 indextts 实跑都必须在命令行
    在场（zh/en 每语言各算一次独立要求），缺席即拒。刻意先于工程文件读取调用
    （先于 narration 存在性、ref 校验、.engine 比对、健康检查与连服）：.engine
    护栏拦不住本闸针对的两种形态（首次启用无标记放行、同签名重跑放行），授权
    证据只能来自命令行本身。--plan 是纯本地预演（不连服不合成），免闸；纯缓存
    命中的幂等重跑同样要 flag（防「缓存命中掩护下的签名外改写」灰区）。
    与 clone_only 族同用 parser.error；缺 flag 形态在 tts_resume 入口预检即拦，
    不会进入冷重启循环（循环内自愈语义保持 RSI-022 原样）。
    """
    if args.engine == "indextts" and not args.plan and not args.final_voice:
        parser.error(
            "IndexTTS 声音克隆须本人显式点名才可启用，本次命令缺 --final-voice 授权。\n"
            "  · 缺省配音一律 edge 草声：省略 --engine 即秒级直跑；\n"
            "  · 若本人确已要求本次用 Index TTS（中英每语言各算一次独立要求），"
            "请显式加 --final-voice；\n"
            "  · 只排期不实跑用 --plan，无需授权。\n"
            f"纪律与触发话术见 {SPEC_07}"
        )


# ---------------- 引擎一：edge-tts（历史路径，保持字节级一致） ----------------


async def synth_edge(
    sem: asyncio.Semaphore,
    item: dict,
    force: bool,
    voice: str,
    rate: str,
    out_dir: Path,
    lang: str = "ZH",
) -> dict:
    import edge_tts  # 惰性导入：仅 edge 引擎需要

    sid, text = item["id"], item["text"]
    mp3 = out_dir / f"{sid}.mp3"
    meta = out_dir / f"{sid}.sha"
    digest = digest_edge(voice, rate, text)

    if (
        not force
        and mp3.exists()
        and mp3.stat().st_size > 0
        and meta.exists()
        and meta.read_text() == digest
    ):
        pass
    else:
        async with sem:
            last_err: Exception | None = None
            for attempt in range(RETRIES):
                try:
                    communicate = edge_tts.Communicate(
                        tts_text(text, lang), voice, rate=rate
                    )
                    await communicate.save(str(mp3))
                    if mp3.stat().st_size == 0:
                        raise RuntimeError("空音频文件")
                    meta.write_text(digest)
                    break
                except Exception as e:  # noqa: BLE001 - 网络服务需要整体重试
                    last_err = e
                    await asyncio.sleep(1.5 * (attempt + 1))
            else:
                raise RuntimeError(f"{sid} 合成失败: {last_err}")

    duration = mp3_duration(mp3)
    return {**item, "durationSec": round(duration, 3)}


# ---------------- 音频版本库（内容寻址持久库，仅 indextts） ----------------
#
# 集内 audio/ 是 gitignored 本地产物 ⇒ 换 worktree / 清盘即丢整集合成成果
# （Claude Code 系列的 mp3 曾在任何工作区都不剩一份，实测教训）。版本库按
# 「句 id + digest 前 12 位」命名放在机器级持久目录，与任何 worktree 解耦：
#   - 合成成功 → store_deposit 入库（同 digest 刷新为最新音频；不同 digest 并存=保留历史版本）；
#   - 集内缓存未命中 → store_restore 按 digest 回收，命中即等价集内缓存命中；
#   - 改稿/换风格 ⇒ 新 digest 自然 miss 重配，旧版本文件保留可回退。
# 路径是机器属性：默认值在此 + VIBE_VIDEO_TTS_STORE 环境变量覆盖，永不写进
# 受版本控制的 toml（与
# config.py 对 tts.server 的立场一致；tts.py 不 import paths.py 的边界也不变
# ——默认值是纯字面量）。仅接 indextts：edge 预置音色免密钥秒级重合成，
# 无 2 小时级资产可丢。
#
# 条目按内容寻址（<slug>/<sid>.<digest12>.mp3），库根整体搬迁零失效（mv 即迁移）。
#
# ⚠️ 继承是中性的：坏 take 同样按 digest 逐代继承（187/187 句恢复零重合成 =
# 缺陷一并回来；换 worktree 重建继续继承，ISSUE-192）。撤销发音标注会使 digest
# 回退旧值、静默复活历史坏 take——死 digest 下的已知坏 take 一律改名隔离
# （<sid>.<digest12>.mp3 → *.bad-<tag>，.sha 邻档同步），留档不删，恢复后抽检。

DEFAULT_STORE = "~/Library/Application Support/vibe-video/tts-store"


def store_root(disabled: bool) -> Path | None:
    """版本库根目录；--no-store 或 env 置空串时返回 None（全程直通不落盘）。

    解析顺序：VIBE_VIDEO_TTS_STORE → 默认目录（不存在则原样返回，首存即建）。"""
    if disabled:
        return None
    env = os.environ.get("VIBE_VIDEO_TTS_STORE")
    if env == "":
        return None
    if env:
        return Path(env).expanduser()
    return Path(DEFAULT_STORE).expanduser()


async def synth_indextts(
    sem: asyncio.Semaphore,
    item: dict,
    force: bool,
    ref: str,
    ref_sha1: str,
    style: str,
    vec: list[float] | None,
    alpha: float,
    df: float,
    lang: str,
    engine_tag: str,
    server: str,
    out_dir: Path,
    num_beams: int = 1,
    emo_ref: str | None = None,
    emo_ref_sha1: str | None = None,
    emo_text: str | None = None,
    sampling: dict | None = None,
    store: Path | None = None,
    slug: str = "",
) -> dict:
    sid, text = item["id"], synth_source_text(item)
    mp3 = out_dir / f"{sid}.mp3"
    meta = out_dir / f"{sid}.sha"
    digest = digest_indextts(
        ref_sha1,
        style,
        vec,
        alpha,
        df,
        lang,
        engine_tag,
        text,
        num_beams,
        emo_ref_sha1,
        emo_text,
        sampling,
    )

    local_hit = (
        not force
        and mp3.exists()
        and mp3.stat().st_size > 0
        and meta.exists()
        and meta.read_text() == digest
    )
    if local_hit:
        pass
    elif not force and store_restore(sid, digest, out_dir, store, slug):
        pass  # 版本库回收命中：mp3 + .sha 已落位，等价集内缓存命中（--force 不走库）
    else:
        async with sem:
            last_err: Exception | None = None
            for attempt in range(RETRIES):
                try:
                    audio, fmt = await asyncio.to_thread(
                        http_synthesize,
                        server,
                        tts_text(text, lang),
                        ref,
                        vec,
                        alpha,
                        df,
                        lang,
                        num_beams,
                        emo_ref,
                        emo_text,
                        None,  # headers_out：管线主路径不需要回填响应头
                        sampling,
                    )
                    if fmt != "mp3":
                        raise NonRetryableError(
                            f"服务端编码器不可用（X-Audio-Format={fmt}）—— 按 {MANUAL} §七 检查 soundfile/lameenc"
                        )
                    if not audio:
                        raise RuntimeError("空音频响应")
                    mp3.write_bytes(audio)
                    if mp3.stat().st_size == 0:
                        raise RuntimeError("空音频文件")
                    meta.write_text(digest)
                    store_deposit(mp3, sid, digest, store, slug)
                    break
                except NonRetryableError as e:
                    # 与重试耗尽分支同款包装：确定性失败（4xx / MPS 上限 OOM）也带句 id，
                    # remedy 的「拆短该句」才有定位锚点
                    raise NonRetryableError(f"{sid} 合成失败: {e}") from e
                except Exception as e:  # noqa: BLE001 - 推理服务需要整体重试
                    last_err = e
                    await asyncio.sleep(1.5 * (attempt + 1))
            else:
                raise RuntimeError(f"{sid} 合成失败: {last_err}")

    duration = mp3_duration(mp3)
    if local_hit and not store_has(store, slug, sid, digest):
        store_deposit(mp3, sid, digest, store, slug)
    return {**item, "durationSec": round(duration, 3)}


# ---------------- 段落演绎（story 档）：块请求与块合成 ----------------


def resolve_block_vec(
    block_items: list[dict], preset_vec: list[float], preset_alpha: float
) -> tuple[list[float], float, str | None]:
    """块情感：台本 cue（块首句 item["cue"]）优先，否则预设向量。

    cue 方向归一到 Σ=1、强度取 cue.alpha 或预设 α——与 #07 的「名义 Σ0.35×α0.8」
    在上游 4 位截断后逐位等价（0.35×0.8 = 1×0.28），故可复现定档 take。
    返回 (vec, alpha, 出错的句 id|None)；α>0.8（方向已归一，有效和即 α）时返回错误 id 由调用方报错。
    """
    cue = block_items[0].get("cue")
    if not cue:
        return list(preset_vec), preset_alpha, None
    vec = parse_emo_vector(cue["emo"])
    total = sum(vec)
    if total <= 0:
        return list(preset_vec), preset_alpha, block_items[0]["id"]
    vec = [x / total for x in vec]
    alpha = float(cue.get("alpha", preset_alpha))
    if alpha > 0.8:
        return vec, alpha, block_items[0]["id"]
    # 归一后 Σ 浮点可能是 1.0000000000000002：α=0.8 时 Σ×α 以 1 ulp 之差撞本地与服务端的
    # ≤0.8 护栏（build 已放行同一台本）。仅此情形把最大分量逐 ulp 下调（≤2 步），上游 4 位
    # 截断下无可听差异；未超界的块向量与摘要逐位不变
    top = max(range(len(vec)), key=vec.__getitem__)
    while sum(vec) * alpha > 0.8:
        vec[top] = math.nextafter(vec[top], 0.0)
    return vec, alpha, None


def block_sampling(block_items: list[dict], sampling: dict) -> dict:
    """块采样口径：台本 `[take]`（成员句 item["take"]）把该块种子 +N，其余块原样。

    块模式的重掷单位是块：--seed-offset 作用于全局种子 ⇒ 全部块换摘要、整集重录；
    take 只改本块 |seed= 后缀 ⇒ 只重录这一块，定稿值留在台本即可复现。
    同块多句带 take 时歧义（加和还是择一），报错由调用方收口。
    """
    takes = [(i["id"], i["take"]) for i in block_items if i.get("take")]
    if not takes:
        return sampling
    if len(takes) > 1:
        raise ValueError(
            f"台本 [take] 在同一块内出现多次（{'、'.join(s for s, _ in takes)}）："
            "块是重掷单位，只保留一条"
        )
    if "seed" not in sampling:
        raise ValueError(f"台本 [take] 需要种子口径（{takes[0][0]}）")
    return {**sampling, "seed": sampling["seed"] + takes[0][1]}


def blocks_unsupported_hint(health: dict) -> str:
    """/health 报告不支持块合成时的可操作诊断：三种成因处置不同，不能一律「重启」。

    IndexTTS-2 与 low_vram（上游按 CUDA 显存 <10 GB 自动开启）是服务端的固有形态，
    重启不会变——只能换 v2.5 服务/换机器，或本集改逐句档；仅字段缺失才是代码过旧。
    """
    fallback = '；或本集改用逐句档（pipeline.toml [tts] style = "sunny"，直调 tts.py 用 --style sunny）'
    if "supports_blocks" not in health:
        return (
            "当前服务不支持块合成（story 档需要）：服务端代码过旧，请用本 skill"
            f" 当前 tts_server.py 重启服务，见 {MANUAL} §二"
        )
    if health.get("version") == "2":
        return (
            "当前服务为 IndexTTS-2：块合成（story 档）仅在 v2.5 上验证开放"
            f"——改用 v2.5 服务（见 {MANUAL} §二）{fallback}"
        )
    if health.get("low_vram"):
        return (
            "当前服务运行在上游 low_vram 路径（CUDA 显存 <10 GB 自动开启，重启不会变）："
            "长文本按 40 字分段、段间定长静音会污染句界，块合成（story 档）不可用"
            f"——换显存 ≥10 GB 的设备{fallback}"
        )
    return (
        "当前服务报告不支持块合成（supports_blocks=false，未回报原因）"
        f"——请用本 skill 当前 tts_server.py 重启服务（见 {MANUAL} §二）{fallback}"
    )


async def synth_block_indextts(
    sem: asyncio.Semaphore,
    block_items: list[dict],
    force: bool,
    ref: str,
    ref_sha1: str,
    style: str,
    preset_vec: list[float],
    preset_alpha: float,
    df: float,
    lang: str,
    engine_tag: str,
    server: str,
    out_dir: Path,
    num_beams: int = 1,
    sampling: dict | None = None,
    store: Path | None = None,
    slug: str = "",
    discard_sec: float = 0.32,
    tail_pad_sec: float = 0.18,
    perform_punct: bool = False,
) -> list[dict]:
    """一个故事块 → N 句 mp3（块=缓存单位；切分失败逐句兜底，仍按块成员摘要落盘）。"""
    vec, alpha, bad_id = resolve_block_vec(block_items, preset_vec, preset_alpha)
    if bad_id is not None:
        raise NonRetryableError(
            f"{bad_id} 的台本情绪有效和 Σvec×alpha 超过 0.8 上限（见 {MANUAL} §4.2）"
        )
    try:
        sampling = block_sampling(block_items, sampling or {})
    except ValueError as e:
        raise NonRetryableError(str(e)) from e
    member_texts = [synth_source_text(i) for i in block_items]
    block_text = block_synth_text(block_items)
    suffix = block_digest_suffix(member_texts, discard_sec, tail_pad_sec)
    n = len(block_items)
    digests = [
        digest_indextts(
            ref_sha1,
            style,
            vec,
            alpha,
            df,
            lang,
            engine_tag,
            member_texts[k],
            num_beams,
            None,
            None,
            sampling,
            suffix,
            f"{k + 1}/{n}",
        )
        for k in range(n)
    ]
    weights = [sentence_weight(i["text"]) for i in block_items]

    # 块=缓存单位：全部成员命中（集内或版本库回收）才跳过合成，否则整块重录
    all_hit = True
    if not force:
        for k, item in enumerate(block_items):
            mp3 = out_dir / f"{item['id']}.mp3"
            meta = out_dir / f"{item['id']}.sha"
            if not (
                mp3.exists()
                and mp3.stat().st_size > 0
                and meta.exists()
                and meta.read_text() == digests[k]
            ):
                if not store_restore(item["id"], digests[k], out_dir, store, slug):
                    all_hit = False
    else:
        all_hit = False

    async def request(text: str, w: list[float], label: str, pad: float) -> dict:
        # 锁只罩单次请求（含重试）：兜底要再发请求，锁内递归会与 Semaphore(1) 自锁
        last_err: Exception | None = None
        async with sem:
            for attempt in range(RETRIES):
                try:
                    return await asyncio.to_thread(
                        http_synthesize_block,
                        server,
                        tts_text(text, lang, perform=perform_punct),
                        ref,
                        vec,
                        alpha,
                        df,
                        lang,
                        num_beams,
                        w,
                        discard_sec,
                        pad,
                        sampling,
                    )
                except NonRetryableError as e:
                    # 同逐句路径：确定性失败也带块 label，供「拆短该块」定位
                    raise NonRetryableError(f"块合成失败（{label}）: {e}") from e
                except Exception as e:  # noqa: BLE001 - 推理服务需要整体重试
                    last_err = e
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"块合成失败（{label}）: {last_err}")

    split_note: str | None = None
    if not all_hit:
        resp = await request(
            block_text, weights, f"{block_items[0]['id']}…{n} 句", tail_pad_sec
        )
        clips = resp.get("clips") if resp.get("split") == "ok" else None
        if clips:
            if resp.get("seams"):
                print(
                    f"WARN 块内出现上游分段缝 {resp['seams']}（>118 token 被迫分段，段间为"
                    f" 200ms 定长静音）——请缩短该块：{block_items[0]['id']}",
                    file=sys.stderr,
                )
            if len(clips) != n:
                raise NonRetryableError(
                    f"块切分数 {len(clips)} != 句数 {n}（{block_items[0]['id']}）"
                )
        else:
            # 切分失败：逐句兜底（单句块无句界，服务端必 split ok），同块情绪。产物仍按块
            # 成员摘要落盘——同输入+定种子下切分失败可复现，复跑直接命中而非每次重试整块。
            # 尾垫只给末句（同块合成口径）：服务端单句路径无条件补垫，非末句须传 0
            print(
                f"WARN 块切分失败（{resp.get('reason', '未知')}），退回逐句合成："
                f"{block_items[0]['id']}…共 {n} 句",
                file=sys.stderr,
            )
            split_note = "fallback"
            clips = []
            for k, item in enumerate(block_items):
                one = await request(
                    block_synth_text([item]),
                    [weights[k]],
                    item["id"],
                    tail_pad_sec if k == n - 1 else 0.0,
                )
                got = one.get("clips") if one.get("split") == "ok" else None
                if not got or len(got) != 1:
                    raise NonRetryableError(
                        f"逐句兜底仍切分失败（{item['id']}）: {one.get('reason', '未知')}"
                    )
                clips.append(got[0])
        fmts = {c.get("format") for c in clips}
        if fmts != {"mp3"}:  # 同逐句路径的编码器守卫：WAV 字节不得落成 .mp3
            raise NonRetryableError(
                f"服务端编码器不可用（format={','.join(sorted(map(str, fmts)))}）"
                f"—— 按 {MANUAL} §七 检查 soundfile/lameenc，或用当前 tts_server.py 重启服务"
            )
        for k, clip in enumerate(clips):
            item = block_items[k]
            mp3 = out_dir / f"{item['id']}.mp3"
            meta = out_dir / f"{item['id']}.sha"
            audio = base64.b64decode(clip["audio"])
            if not audio:
                raise RuntimeError(f"空音频响应（{item['id']}）")
            mp3.write_bytes(audio)
            meta.write_text(digests[k])
            store_deposit(mp3, item["id"], digests[k], store, slug)
    else:
        # 同逐句路径：整块命中但库中缺档（曾 --no-store 或入库失败）⇒ 回填
        for k, item in enumerate(block_items):
            if not store_has(store, slug, item["id"], digests[k]):
                store_deposit(
                    out_dir / f"{item['id']}.mp3", item["id"], digests[k], store, slug
                )

    results = []
    for item in block_items:
        # 合成与命中同口径实测 mp3 时长（同逐句路径）：否则复跑时 manifest 随缓存状态漂移
        dur = mp3_duration(out_dir / f"{item['id']}.mp3")
        r = {**item, "durationSec": round(dur, 3)}
        if split_note:
            r["blockSplit"] = split_note
        results.append(r)
    return results


# ---------------- 段落演绎（story 档）：故事块划分 + 块音频切分 ----------------
#
# 机制：同幕连续句拼成一次 /synthesize（块文本 ≤118 token 时上游单段连续生成，
# 句间是模型自带的自然停顿）；响应在服务端按句界切回 N 个 mp3。切分/划块的本体
# 是 dub 仓 dub_tts_blocks 里的纯函数——numpy 惰性 import，唯一执行者是 dub 的服务端
# dub_tts_server.py（它持有 mp3 编码前的 float32 PCM）；本文件只负责「划块」（plan_blocks）
# 与请求编排，不触碰切分函数。
#
# 实测定档依据（2026-09-25，dream-rsi P0）：
# - 句界自然停顿 0.31–0.55 s 与句内逗号停顿 0.14–0.42 s 区间重叠 ⇒ 不能「取最长
#   N−1 个静音」，按字符占比期望位置就近选（DP），4/4 块选对且最近错误候选 ≥0.5 s；
# - 停顿保留在音频内：句界静音正中丢弃恰好 sentenceGapSec，时间轴又加回同值
#   ⇒ 听感＝自然停顿原值，frozen 模板与 14 集零波及。


def sentence_weight(text: str) -> float:
    """句「发音量」权重：期望切点按各句权重占比内插。

    口径：CJK/数字=1、拉丁字母=0.35（约 1 个音节）、句中标点=1.5（拖停顿），
    其余字符（空格/引号）不计。够粗——DP 容差 ±max(1.0, 0.15T) 秒吸收估计误差。
    """
    import unicodedata

    w = 0.0
    for ch in text:
        if ch in "，、；：？！…—":
            w += 1.5
            continue
        cat = unicodedata.category(ch)
        if ch.isdigit() or cat.startswith("Lo"):  # 中日韩表意文字按 1
            w += 1.0
        elif ch.isalpha():  # 拉丁字母按 0.35
            w += 0.35
    return w


def plan_blocks(items: list[dict], cfg: dict) -> list[list[dict]]:
    """narration items → 故事块（同幕连续句的列表的列表）。

    硬边界：幕界 + 台本 blockStart（item 里的 cue 台本由 build_narration 落成
    blockStart:true）。无台本段自动划分：先按位置切成 2×max_sentences 句的定长窗
    （1 句尾窗并入前窗），窗内块数取 ≥max(⌈n/3⌉,⌈ΣL/90⌉) 的首个可行值，DP 最小化
    块长方差，块 ≤max_sentences 句、≤max_chars 字（合成文本口径，超限单句自成一块）。
    台本段超限被拆开时，后续子块继承段首 cue（块首句浅拷贝注入，不改原件）。
    """
    ms, mc = cfg.get("max_sentences", 3), cfg.get("max_chars", 90)

    def synth_len(i: dict) -> int:
        return len(synth_source_text(i))

    blocks: list[list[dict]] = []
    run: list[dict] = []

    def window_cuts(seg: list[dict]) -> list[int]:
        n = len(seg)
        total = sum(synth_len(i) for i in seg)
        k_min = min(n, max(1, -(-n // ms), -(-total // mc)))
        # DP：best[end][j]＝前 end 句切成 j 块（块句数 ≤ms、多句块长 ≤mc）的最小块长方差。
        # k_min 只是下界：装箱约束下恰好 k_min 块常切不出，逐层放宽到首个可行块数
        # （j=n 即逐句，必可行）——否则整窗会整体退化为逐句
        INF = float("inf")
        best: list[list[tuple[float, int]]] = [
            [(INF, -1)] * (n + 1) for _ in range(n + 1)
        ]
        best[0][0] = (0.0, -1)
        lens = [0]
        for i in seg:
            lens.append(lens[-1] + synth_len(i))
        k = n
        for j in range(1, n + 1):
            for end in range(1, n + 1):
                for start in range(max(0, end - ms), end):
                    seglen = lens[end] - lens[start]
                    if seglen > mc and start + 1 < end:
                        continue  # 多句块不许超字数；单句超长只能自成一块放行
                    prev = best[start][j - 1][0]
                    if prev == INF:
                        continue
                    # 方差代理：Σlen²（固定块数与总量下最小化它＝最小化方差）
                    cand = prev + seglen * seglen
                    if cand < best[end][j][0]:
                        best[end][j] = (cand, start)
            if j >= k_min and best[n][j][0] < INF:
                k = j
                break
        cuts, end = [], n
        for j in range(k, 0, -1):
            cuts.append(end)
            end = best[end][j][1]
        cuts.append(0)
        cuts.reverse()
        return cuts

    def flush_auto(seg: list[dict]) -> None:
        # 定长窗：块界只依赖窗内句长 ⇒ 改一句至多重排所在窗（≤2×ms+1 句）。整段全局 DP
        # 下块界依赖段内全部句长，改一个字即可整段平移、整幕重录（14 集对拍：改字爆炸
        # 半径 max 34→7 句，块数 +2.6%）。窗界按位置而非内容，插/删句仍重排同段其后各窗
        starts = list(range(0, len(seg), 2 * ms))
        if len(starts) > 1 and len(seg) - starts[-1] == 1:
            starts.pop()  # 1 句尾窗并入前窗：幕末收束句不孤立成逐句合成
        cuts = [0]
        for a, b in zip(starts, [*starts[1:], len(seg)]):
            cuts += [a + c for c in window_cuts(seg[a:b])[1:]]
        cue = seg[0].get("cue")
        for a, b in zip(cuts, cuts[1:]):
            blk = seg[a:b]
            if a and cue:  # 台本段被上限拆开：子块沿用段首情绪，不在段中途换档
                blk = [{**blk[0], "cue": cue}, *blk[1:]]
            blocks.append(blk)

    for i in items:
        hard = i.get("blockStart") or (run and run[-1]["scene"] != i["scene"])
        if hard and run:
            flush_auto(run)
            run = []
        run.append(i)
    if run:
        flush_auto(run)
    return blocks


def block_synth_text(items: list[dict]) -> str:
    """块的合成文本＝成员句拼接；句末无停顿标点者补 `。`（上游按标点断句合并段）。

    `，：、——` 结尾是原稿有意的续接（本身即停顿、可作切点候选），原样保留——追加 `。`
    会拼出 `，。`（上游映射为 `,.` 双标点）并把续接改成句末降调。收引号/括号不算末字：
    `不可能！”` 按 `！` 判定，否则会拼出 `！”。` 同类双标点。
    """
    PAUSE = "。！？…；，：、—"
    CLOSERS = "”’」』）)》】\"'"
    parts = []
    for i in items:
        t = synth_source_text(i).strip()
        body = t.rstrip(CLOSERS)
        if body and body[-1] not in PAUSE:
            t += "。"
        parts.append(t)
    return "".join(parts)


# ---------------- 主流程 ----------------


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="逐句 TTS 合成 + 时长 manifest（双引擎）"
    )
    parser.add_argument(
        "--engine",
        choices=["edge", "indextts"],
        default="edge",
        help="edge=预置音色（默认）；indextts=声音克隆（需本地服务）",
    )
    parser.add_argument(
        "--project", default=".", help="视频工程根目录（含 script/ 与 video/）"
    )
    parser.add_argument(
        "--narration-lang",
        default="zh",
        choices=list(LANG_MIRROR),
        help="逐字稿语言：选输入 json（zh=script/narration.json、en=script/narration.en.json）"
        "与输出目录（zh=video/public/audio/、en=…/audio/en/，含独立 manifest 与 .engine 签名）",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="[edge] 语音（缺省按 --narration-lang 解析：zh→zh-CN-YunxiNeural、"
        "en→en-US-AndrewNeural）",
    )
    parser.add_argument("--rate", default=DEFAULT_RATE, help="[edge] 语速（默认 +4%%）")
    parser.add_argument("--force", action="store_true", help="忽略缓存强制重合成")
    parser.add_argument(
        "--no-store",
        action="store_true",
        help="[indextts] 禁用音频版本库（默认启用；库根目录可用环境变量 VIBE_VIDEO_TTS_STORE 覆盖）",
    )
    parser.add_argument(
        "--allow-voice-switch",
        action="store_true",
        help="放行音色签名变更（引擎/音色/风格换档＝整集重录，须显式确认）",
    )
    parser.add_argument("--list-styles", action="store_true", help="列出风格预设并退出")

    idx = parser.add_argument_group("indextts 声音克隆")
    idx.add_argument(
        "--ref",
        default=None,
        help="[indextts] 参考音色样本路径（建议 10–14s 干净人声；硬上限 15s，上游超出即静默前截）",
    )
    idx.add_argument(
        "--expect-ref-sha1",
        default=None,
        metavar="12HEX",
        help="[indextts] 期望的参考样本 sha1 前 12 位，不符即硬失败——pipeline.py 从"
        "各集 pipeline.toml 自动带上，防「换样本静默重录整集」（指纹清单见 voices/refs.toml）",
    )
    idx.add_argument(
        "--server", default="http://127.0.0.1:8766", help="[indextts] 服务地址"
    )
    idx.add_argument(
        "--style",
        default="neutral",
        choices=list(STYLE_PRESETS),
        help="[indextts] 风格预设（默认 neutral）",
    )
    idx.add_argument(
        "--emo-vector",
        default=None,
        help="[indextts] 原始情感向量，如 happy:0.6,calm:0.2（与 --style 非默认值互斥）",
    )
    idx.add_argument(
        "--emo-ref",
        default=None,
        help="[indextts] 情感参考音频：音色仍取 --ref，语调/情绪迁移自这段录音（比向量注入更自然；"
        "与 --style 非默认值/--emo-vector/--emo-text 互斥）",
    )
    idx.add_argument(
        "--emo-text",
        default=None,
        help="[indextts] 自然语言情感描述，如「轻快爽朗、自信阳光」（需服务端 --use-qwen-emo；"
        "与 --style 非默认值/--emo-vector/--emo-ref 互斥）",
    )
    idx.add_argument(
        "--emo-alpha",
        default=None,
        type=float,
        help="[indextts] 情感强度 0–1（默认随风格）",
    )
    idx.add_argument(
        "--duration-factor",
        default=None,
        type=float,
        help="[indextts] 语速 0.5–2.0（默认随风格）",
    )
    idx.add_argument(
        "--lang",
        default=None,
        help="[indextts] 语言（缺省按 --narration-lang 解析：zh→ZH、en→EN；"
        "显式给值须与之一致，冲突即报错退出）",
    )
    idx.add_argument(
        "--num-beams",
        default=None,
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="[indextts] GPT 束搜索宽度（缺省随风格，多数预设为 1、sunny-steady 为 3；"
        "束宽越大韵律越稳但 GPT 段耗时约按束宽线性放大——长篇批量跑 1，定稿可试 3）",
    )
    idx.add_argument(
        "--steady",
        default=None,
        metavar="P0,p3-25b,p5-*",
        help="[indextts] 混合档：仅这些句子改用高束宽（默认 3），其余仍按风格的束宽。"
        "支持幕名（P0）/精确句 id（p3-25b）/前缀通配（p5-*），逗号分隔、大小写不敏感。"
        "用于把冷开场与金句升到更稳的档而不拖长整集耗时",
    )
    idx.add_argument(
        "--steady-beams",
        default=3,
        type=int,
        choices=[2, 3, 4, 5],
        help="[indextts] --steady 命中句所用束宽（默认 3）",
    )
    idx.add_argument(
        "--plan",
        action="store_true",
        help="[indextts] 只打印合成计划（各束宽句数、缓存命中/待合成、耗时估算）并退出，不连服务",
    )
    idx.add_argument(
        "--final-voice",
        action="store_true",
        help="[indextts] 终稿配音具名授权（RSI-040 人为触发原则）：本人显式要求本次用"
        " Index TTS 才可带上——每次非 --plan 合成、zh/en 每语言各算一次独立要求；"
        "缺省 edge 草声，缺此 flag 的 indextts 实跑直接硬失败（见 references/07-tts-voice.md）。"
        "与 --allow-voice-switch 分工：本 flag＝使用授权（每次实跑都要）；"
        "彼 flag＝音色签名变化的防误闸（换引擎/风格/样本时才需要）",
    )
    idx.add_argument(
        "--engine-tag",
        default="indextts",
        help="[indextts] 缓存标记；模型升级后自定义以失效旧缓存",
    )

    # 采样参数族：上游经 **generation_kwargs 透传给 HF generate，此前全部隐式继承上游默认，
    # 任何调优都得改服务源码。显式化后它们会**进缓存摘要**（仅在 ≠ 上游默认时），故改参必然
    # 重合成，不会出现「改了参数却命中旧缓存 ⇒ 误判无效果」这类假验证。
    # 缺省一律 None = 取风格预设的 sampling，再退到上游默认（见 resolve_sampling）。
    smp = parser.add_argument_group(
        "indextts 采样参数（专家级，缺省即上游默认；改任一项都会失效该句缓存）"
    )
    smp.add_argument(
        "--temperature",
        default=None,
        type=float,
        help="[indextts] 采样温度 0.1–2.0（上游默认 0.8）。收紧可降低长视频的句间韵律漂移，"
        "过紧会滑向单调播报",
    )
    smp.add_argument(
        "--top-p",
        default=None,
        type=float,
        help="[indextts] 核采样 0–1（上游默认 0.8）",
    )
    smp.add_argument(
        "--top-k",
        default=None,
        type=int,
        help="[indextts] top-k 0–100（上游默认 30；0=关闭，1 在束搜索下不安全故禁用）",
    )
    smp.add_argument(
        "--length-penalty",
        default=None,
        type=float,
        help="[indextts] 束打分长度惩罚 -2–2（上游默认 0.0）。**0.0 不是中性**：打分不做长度"
        "归一化而对数概率恒负，故系统性偏好更短假设，是 --num-beams>1 时吞尾/漏字的机制来源。"
        "抬到 0.3–1.0 可缓解；仅束搜索打分时生效，--num-beams 1 下改它无效",
    )
    smp.add_argument(
        "--repetition-penalty",
        default=None,
        type=float,
        help="[indextts] 重复惩罚 0.1–20（上游默认 10.0，自 v1 沿用且无测试支撑）。"
        "作用在语义码头上、是对 logit 的符号相关缩放；有效强度依赖 logit 绝对尺度，"
        "故**与音色/情感向量耦合**，跨音色不可迁移调参结论",
    )
    smp.add_argument(
        "--max-mel-tokens",
        default=None,
        type=int,
        help="[indextts] 生成上限 50–1815（上游默认 1500 ≈30 s；1815 为架构上限 ≈36.2 s）。"
        "溢出后果不是音频被裁短，而是文本尾部根本没被念出。本管线单句远未触顶，通常不需要动",
    )
    smp.add_argument(
        "--interval-silence",
        default=None,
        type=int,
        help="[indextts] 单请求内**分段之间**的静音毫秒（上游默认 200）。本管线逐句合成、"
        "单句远低于分段预算，故默认不生效；句间停顿由 video/src/timing.json 的 sentenceGapSec 决定",
    )
    smp.add_argument(
        "--no-text-normalization",
        action="store_true",
        help="[indextts] 关闭上游中文文本归一化（v2.5 专属）。**通常不要用**：实测 %% / 小数 /"
        "量词 / 月日 / 章节的读法本来就正确，关掉等于把全部读法责任推给逐字稿；"
        "发音标注 <字|读音> 本身免疫归一化，不需要为保标记而关它",
    )
    smp.add_argument(
        "--seed",
        default=None,
        type=int,
        help="[indextts] 随机种子。上游 do_sample 恒 True 且全链路无种子，同句每次合成都是"
        "不同的 take；给定种子后逐句可复现——这是任何参数 A/B 可信的前提",
    )
    smp.add_argument(
        "--seed-offset",
        default=0,
        type=int,
        help="[indextts] 与 --seed 相加（默认 0）。固定种子会把某句锁死在一条可能不佳的"
        "采样结果上，偏移一位即可换一条 take 而仍然可复现",
    )
    args = parser.parse_args()
    args.server = args.server.rstrip(
        "/"
    )  # 尾斜杠归一：health/synthesize 两处拼 URL 前收口

    # 语言解析：--lang/--voice 未显式给出时按 --narration-lang 从镜像表取缺省——
    # `--narration-lang en` 下绝不能静默回落 ZH/中文音色（digest 与音色都会错槽位）。
    want_lang, want_voice = LANG_MIRROR[args.narration_lang]
    # 显式 --lang 与镜像解析值冲突即拦（两引擎统一）：错语言 take 的 digest 自洽，
    # 后续会当缓存命中，事后只能靠听发现。
    if args.lang is not None and args.lang != want_lang:
        parser.error(
            f"--lang {args.lang} 与 --narration-lang {args.narration_lang}"
            f"（应为 {want_lang}）冲突——省略 --lang 即按逐字稿语言自动解析"
        )
    tts_lang = want_lang  # 冲突已拦：显式值若给出必与镜像解析值相等
    voice = args.voice if args.voice is not None else want_voice

    if args.list_styles:
        print(
            "风格            说明      情感向量（happy,angry,sad,afraid,disgusted,melancholic,surprised,calm）"
            "  alpha  有效注入  语速  束宽"
        )
        for name, p in STYLE_PRESETS.items():
            vec = (
                ",".join(f"{x:g}" for x in p["vec"]) if p["vec"] else "—（不注入情感）"
            )
            eff = (sum(p["vec"]) * p["alpha"]) if p["vec"] else 0.0
            smp_note = (
                ""
                if not p.get("sampling")
                else "  采样 "
                + ",".join(f"{k}={v!r}" for k, v in sorted(p["sampling"].items()))
            )
            # 预设自带种子/块合成同样改合成口径（进摘要），不能只在表外隐身
            if p.get("seed") is not None:
                smp_note += f"  seed={p['seed']}"
            if blk := p.get("block"):
                smp_note += (
                    f"  块合成（≤{blk['max_sentences']} 句/≤{blk['max_chars']} 字）"
                )
            print(
                f"{name:<14}  {p['label']:<6}  {vec:<62}  {p['alpha']:<5}  "
                f"{eff:<8.3g}  {p['df']:<4}  {p.get('beams', 1)}{smp_note}"
            )
        print(
            "\n采样参数（temperature/top_p/top_k/length_penalty/repetition_penalty/"
            "max_mel_tokens/interval_silence）未在任何预设中覆盖，"
            "均取上游默认："
            + ", ".join(f"{k}={v!r}" for k, v in SAMPLING_DEFAULTS.items())
            + "；行尾标 seed= 的预设自带种子（覆盖 seed=None），标「块合成」的按故事块合成"
            f"（{MANUAL} §4.5）"
        )
        return

    if args.engine == "edge":
        # --plan 语义是「只看不跑」，而 edge 无束宽/无估时口径。若沿用「提示后照跑」的处理，
        # 漏写 --engine indextts 时会静默全量合成，把整集克隆音频改写成 edge 预置音色
        # （两引擎摘要必然不同，且 {id}.mp3 单槽位），故此处硬失败而非忽略。
        if args.plan:
            parser.error(
                "--plan 仅对 --engine indextts 生效（edge 草声秒级无需排期；"
                "克隆若漏写 --engine indextts 请补上）"
            )
        # 克隆专属参数分两类处置。**带值参数硬失败**：漏写 --engine indextts 的典型手型
        # 就是「照抄文档打了 --ref/--style 却丢了 --engine」，而 {id}.mp3 是单槽位、
        # 两引擎摘要必然不同 ⇒ 照跑就会把整集克隆音频静默改写成 edge 预置音色。
        # 上面 --plan 已按此论证硬化，合成路径同理（否则只硬化了「看」、没硬化「跑」）。
        clone_only = [
            flag
            for flag, val in {
                "--ref": args.ref,
                "--emo-vector": args.emo_vector,
                "--emo-ref": args.emo_ref,
                "--emo-text": args.emo_text,
                "--emo-alpha": args.emo_alpha is not None,
                "--duration-factor": args.duration_factor is not None,
                "--num-beams": args.num_beams is not None,
                "--steady": args.steady,
                "--style": args.style != "neutral",
                # 采样参数族同属克隆专属：edge 不认这些旋钮，且两引擎摘要必然不同，
                # 照跑同样会把整集克隆音频改写成 edge 预置音色 ⇒ 与上面同口径硬失败。
                "--temperature": args.temperature is not None,
                "--top-p": args.top_p is not None,
                "--top-k": args.top_k is not None,
                "--length-penalty": args.length_penalty is not None,
                "--repetition-penalty": args.repetition_penalty is not None,
                "--max-mel-tokens": args.max_mel_tokens is not None,
                "--interval-silence": args.interval_silence is not None,
                "--no-text-normalization": args.no_text_normalization,
                "--seed": args.seed is not None,
                # RSI-040：授权 flag 同属克隆专属——edge 下给了授权却没给 --engine，
                # 照跑会把「本人要的终稿声音」静默降级成 edge 草声，且留下假授权痕迹。
                "--final-voice": args.final_voice,
            }.items()
            if val
        ]
        if clone_only:
            parser.error(
                f"以下参数仅对 --engine indextts 生效: {' '.join(clone_only)}"
                "（是否漏写 --engine indextts？若确实要用 edge 预置音色，请去掉这些参数）"
            )
        # 无副作用的旁路参数：给不到默认值也不会改变输出，只提示不失败
        benign = [
            flag
            for flag, val in {
                "--steady-beams": args.steady_beams != 3,
                "--server": args.server != "http://127.0.0.1:8766",
                "--engine-tag": args.engine_tag != "indextts",
                # --seed-offset 单独给值而没给 --seed 时无任何效果（见 resolve_sampling）
                "--seed-offset": args.seed_offset != 0 and args.seed is None,
            }.items()
            if val
        ]
        if benign:
            print(
                f"提示：以下参数仅对 --engine indextts 生效，已忽略: {' '.join(benign)}",
                file=sys.stderr,
            )

    # ── 人为触发原则（RSI-040）：先于一切工程文件读取 ──────────────────
    # 缺 --final-voice 的 indextts 实跑在此硬失败（见上方函数 docstring）。
    enforce_final_voice_gate(parser, args)

    root = Path(args.project).resolve()
    # 后缀规则内联（与 langs.narration_json / langs.audio_dir 同构，见 LANG_MIRROR 注）：
    # 主语言 zh 路径逐字节等于旧版，非主语言加 .<lang> 后缀 / 子目录。
    sfx = "" if args.narration_lang == "zh" else f".{args.narration_lang}"
    src = root / "script" / f"narration{sfx}.json"
    if not src.is_file():
        sys.exit(
            f"narration{sfx}.json 不存在: {src}"
            f" —— 先运行 build_narration.py --lang {args.narration_lang} 生成"
        )
    audio_base = root / "video" / "public" / "audio"
    out_dir = (
        audio_base if args.narration_lang == "zh" else audio_base / args.narration_lang
    )
    items = json.loads(src.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    store = store_root(args.no_store)
    slug = root.name

    if args.engine == "edge":
        signature = f"edge|{voice}|{args.rate}"
        check_voice_marker(out_dir, signature, args.allow_voice_switch)
        sem = asyncio.Semaphore(CONCURRENCY_EDGE)
        results = await asyncio.gather(
            *(
                synth_edge(sem, i, args.force, voice, args.rate, out_dir, tts_lang)
                for i in items
            )
        )
    else:
        # 情感三来源互斥：显式向量 / 情感参考音频 / 自然语言描述（服务端亦校验，此处提前失败）
        emo_sources = [
            f
            for f, v in (
                ("--emo-vector", args.emo_vector),
                ("--emo-ref", args.emo_ref),
                ("--emo-text", args.emo_text),
            )
            if v
        ]
        if len(emo_sources) > 1:
            parser.error(f"情感来源互斥，只能给一个：{' '.join(emo_sources)}")
        if args.style != "neutral" and emo_sources:
            parser.error(f"--style 非默认值与 {emo_sources[0]} 互斥")
        if args.emo_ref or args.emo_text:
            # 音频/文本驱动情感时不注入向量；alpha 默认 1.0（完全采用该情感来源）
            style_name = "emoref" if args.emo_ref else "emotext"
            vec = None
            alpha = args.emo_alpha if args.emo_alpha is not None else 1.0
            df = args.duration_factor if args.duration_factor is not None else 1.0
            beams = args.num_beams if args.num_beams is not None else 1
        else:
            try:
                style_name, vec, alpha, df, beams = resolve_style(args)
            except ValueError as e:
                parser.error(str(e))
        try:
            sampling = resolve_sampling(args)
        except ValueError as e:
            parser.error(str(e))
        if not args.ref:
            parser.error(
                "--engine indextts 需要 --ref 参考音色样本（见 " + MANUAL + " §三）"
            )
        ref_path = Path(args.ref).expanduser().resolve()
        if not ref_path.is_file():
            parser.error(f"参考样本不存在: {ref_path}")
        if args.emo_alpha is not None and not 0.0 <= args.emo_alpha <= 1.0:
            parser.error("--emo-alpha 必须在 [0, 1]")
        if (
            vec is not None and sum(vec) * alpha > 0.8
        ):  # infer 内部以 alpha 缩放，校验有效和
            parser.error(
                f"情感向量有效和 {sum(vec) * alpha:.3f}（Σvec×alpha）超过 0.8 上限"
            )
        if args.duration_factor is not None and not 0.5 <= args.duration_factor <= 2.0:
            parser.error("--duration-factor 必须在 [0.5, 2.0]")

        emo_ref_path = emo_ref_sha1 = None
        if args.emo_ref:
            p = Path(args.emo_ref).expanduser().resolve()
            if not p.is_file():
                parser.error(f"情感参考音频不存在: {p}")
            emo_ref_path = str(p)
            # 情感样本按内容入摘要：换情感录音必须失效缓存（与 ref 同口径）
            emo_ref_sha1 = hashlib.sha1(p.read_bytes()).hexdigest()[:12]
        ref_sha1 = hashlib.sha1(ref_path.read_bytes()).hexdigest()[:12]
        # 指纹硬校验：样本即音色。换样本 = 整集换音色，必须在长跑开始前失败
        if args.expect_ref_sha1 and args.expect_ref_sha1 != ref_sha1:
            parser.error(
                f"参考样本指纹不符：期望 {args.expect_ref_sha1}，实得 {ref_sha1}"
                f"（{ref_path}）——源录音或裁剪参数已变。"
                f"勿在未核验音色上跑长合成；指纹清单见 $V/refs.toml（$W/voices/）"
            )

        # 混合档：解析选择器并逐句定束宽（此处即失败，避免典型的「id 拼错→静默全按低束宽跑完」）
        beams_of: dict[str, int] = dict.fromkeys((i["id"] for i in items), beams)
        if args.steady:
            if args.steady_beams <= beams:
                parser.error(
                    f"--steady-beams {args.steady_beams} 不高于基础束宽 {beams}，混合档无意义"
                )
            try:
                sids, scenes, prefixes = parse_steady_selector(args.steady)
            except ValueError as e:
                parser.error(str(e))
            for tok in sorted(sids | scenes) + [p + "*" for p in prefixes]:
                one_id, one_scene, one_pre = parse_steady_selector(tok)
                if not any(steady_match(i, one_id, one_scene, one_pre) for i in items):
                    parser.error(
                        f"--steady 的 {tok!r} 未命中任何句子（幕名/句 id 拼错？）"
                    )
            for i in items:
                if steady_match(i, sids, scenes, prefixes):
                    beams_of[i["id"]] = args.steady_beams

        signature = f"indextts|{args.engine_tag}|{style_name}|{ref_sha1}"
        # 在 --plan 之前检查：排期正是发现「这次长跑将整集换音色」的最佳时机
        check_voice_marker(out_dir, signature, args.allow_voice_switch)

        # ── 段落演绎（story 档）：块模式解析 ─────────────────────────────
        # 块=同幕连续句一次合成（句间自然停顿），服务端切回逐句 mp3。仅预设声明 block
        # 时启用；EN 未验证（07-tts-voice 跨语种须试听）回退逐句；--steady 的逐句升束
        # 与「块=一个请求」冲突，硬拒。
        block_cfg = (STYLE_PRESETS.get(style_name) or {}).get("block")
        if block_cfg and tts_lang != "ZH":
            print(
                "提示：story 档块合成未在 EN 验证（跨语种须试听，见 references/07-tts-voice.md），"
                "EN 本次回退逐句合成",
                file=sys.stderr,
            )
            block_cfg = None
        # 须排在 EN 回退之后：回退逐句的 EN 版与 --steady 并不冲突
        if block_cfg and args.steady:
            parser.error("--steady 的逐句升束与块合成（story 档）冲突：整块同一束宽")
        perform_punct = bool(block_cfg and block_cfg.get("perform_punct"))
        # 句界丢弃量＝时间轴句距（时间轴随后加回 ⇒ 听感＝自然停顿原值）。
        # 直读 timing.json（不 import 兄弟模块），缺文件/缺键回退机制常数 0.32。
        discard_sec = 0.32
        if block_cfg:
            timing_json = root / "video" / "src" / "timing.json"
            if timing_json.is_file():
                try:
                    discard_sec = float(
                        json.loads(timing_json.read_text(encoding="utf-8"))[
                            "sentenceGapSec"
                        ]
                    )
                except (ValueError, KeyError, TypeError):
                    pass
        blocks: list[list[dict]] = plan_blocks(items, block_cfg) if block_cfg else []
        # 台本护栏提前到 --plan：长跑前发现 Σvec×alpha 超界、同块多条 [take]
        if block_cfg:
            for b in blocks:
                _, _, bad_id = resolve_block_vec(b, vec, alpha)
                if bad_id is not None:
                    parser.error(
                        f"{bad_id} 的台本情绪有效和超过 0.8 上限（见 {MANUAL} §4.2）"
                    )
                try:
                    block_sampling(b, sampling)
                except ValueError as e:
                    parser.error(str(e))

        if args.plan:  # 计划模式：纯本地计算，不连服务
            print(
                f">> 计划：{root.name} · 风格 {style_name} · alpha {alpha:g} · 语速 {df:g}"
                + (
                    ""
                    if not sampling
                    else " · 采样 "
                    + ",".join(f"{k}={sampling[k]!r}" for k in sorted(sampling))
                )
            )
            todo = {b: 0 for b in sorted(set(beams_of.values()))}
            cached = dict(todo)
            store_hits = dict(todo)
            if block_cfg:
                # 块=缓存单位：整块成员全部命中才算命中；改一句 ⇒ 整块重录
                cached_blocks = recoverable_blocks = todo_blocks = todo_members = 0
                recoverable_members = 0
                for b in blocks:
                    b_vec, b_alpha, _ = resolve_block_vec(b, vec, alpha)
                    b_sampling = block_sampling(b, sampling)
                    suffix = block_digest_suffix(
                        [synth_source_text(i) for i in b],
                        discard_sec,
                        block_cfg.get("tail_pad_sec", 0.18),
                    )
                    n = len(b)
                    all_local, all_recoverable = True, True
                    for k, i in enumerate(b):
                        d = digest_indextts(
                            ref_sha1,
                            style_name,
                            b_vec,
                            b_alpha,
                            df,
                            tts_lang,
                            args.engine_tag,
                            synth_source_text(i),
                            beams,
                            None,
                            None,
                            b_sampling,
                            suffix,
                            f"{k + 1}/{n}",
                        )
                        meta, mp3 = (
                            out_dir / f"{i['id']}.sha",
                            out_dir / f"{i['id']}.mp3",
                        )
                        local_ok = (
                            not args.force
                            and mp3.exists()
                            and mp3.stat().st_size > 0
                            and meta.exists()
                            and meta.read_text() == d
                        )
                        if not local_ok:
                            all_local = False
                            if args.force or not store_has(store, slug, i["id"], d):
                                all_recoverable = False
                    if all_local:
                        cached_blocks += 1
                    elif all_recoverable:
                        recoverable_blocks += 1
                        recoverable_members += n
                        todo_blocks += 1
                        todo_members += n
                    else:
                        todo_blocks += 1
                        todo_members += n
                # 同逐句口径：版本库整块直收不占合成时间，不进估时
                est = (
                    (todo_members - recoverable_members)
                    * AVG_SEC_PER_LINE
                    * (RTF_1BEAM if beams == 1 else RTF_MULTIBEAM)
                )
                print(
                    f"   块模式：{len(blocks)} 块 · 待合成 {todo_blocks} 块 / {todo_members} 句"
                    f" · 已整块缓存 {cached_blocks} 块"
                    + (
                        f" · 版本库可整块回收 {recoverable_blocks} 块"
                        if recoverable_blocks
                        else ""
                    )
                    + "（块=缓存单位，改一句重录整块）"
                )
                print(
                    f">> 待合成合计 {todo_members} 句（块口径）"
                    + (
                        f"（其中 {recoverable_blocks} 块 / {recoverable_members} 句由版本库整块直收，"
                        "不占合成时间）"
                        if recoverable_members
                        else ""
                    )
                    + f"，估算墙钟约 {est / 3600:.1f} 小时"
                    f"（长跑折算口径 RTF 1 束≈{RTF_1BEAM:g} / 高束宽≈{RTF_MULTIBEAM:g}，"
                    f"机器负载会显著影响，仅作排期参考）"
                )
                return
            for i in items:
                b = beams_of[i["id"]]
                d = digest_indextts(
                    ref_sha1,
                    style_name,
                    vec,
                    alpha,
                    df,
                    tts_lang,
                    args.engine_tag,
                    synth_source_text(i),
                    b,
                    emo_ref_sha1,
                    args.emo_text,
                    sampling,
                )
                meta, mp3 = out_dir / f"{i['id']}.sha", out_dir / f"{i['id']}.mp3"
                hit = (
                    not args.force
                    and mp3.exists()
                    and mp3.stat().st_size > 0
                    and meta.exists()
                    and meta.read_text() == d
                )
                (cached if hit else todo)[b] += 1
                if not hit and not args.force and store_has(store, slug, i["id"], d):
                    store_hits[b] += 1
            # 估时用**整集长跑折算口径**（含降频、机器争用与逐句开销），不是单句空闲口径：
            # 1 束 RTF≈13（三集 596 句实测 8.5 h 折算）、≥2 束≈45（短句 A/B 实测约 3.2 倍）；
            # 每句音频按 4.2s（三集均值）。单句空闲时可快到 RTF 6–7，故本估算偏保守。
            est = sum(
                (n - store_hits[b])
                * AVG_SEC_PER_LINE
                * (RTF_1BEAM if b == 1 else RTF_MULTIBEAM)
                for b, n in todo.items()
            )
            for b in sorted(todo):
                print(
                    f"   束宽 {b}：待合成 {todo[b]:>3} 句 · 已缓存 {cached[b]:>3} 句"
                    + (
                        f" · 版本库可回收 {store_hits[b]:>3} 句"
                        if store_hits[b]
                        else ""
                    )
                    + ("" if b == 1 else "（高束宽档）")
                )
            print(
                f">> 待合成合计 {sum(todo.values())} 句"
                + (
                    f"（其中 {sum(store_hits.values())} 句由版本库直收，不占合成时间）"
                    if sum(store_hits.values())
                    else ""
                )
                + f"，估算墙钟约 {est / 3600:.1f} 小时"
                f"（长跑折算口径 RTF 1 束≈{RTF_1BEAM:g} / 高束宽≈{RTF_MULTIBEAM:g}，"
                f"机器负载会显著影响，仅作排期参考）"
            )
            return

        try:
            health = await asyncio.to_thread(
                http_json, "GET", f"{args.server}/health", None, 10
            )
            if not health.get("ok"):
                raise RuntimeError(f"health.ok=false: {health}")
        except Exception as e:  # noqa: BLE001 - 服务未启动给出可操作指引
            print(
                f"IndexTTS 服务不可用（{e}）。请先启动：\n{server_launch_hint()}\n详见 {MANUAL} §二",
                file=sys.stderr,
            )
            sys.exit(1)
        if df != 1.0 and not health.get("supports_duration_factor"):
            parser.error(
                "当前服务为 IndexTTS-2（无语速控制）：去掉 --duration-factor，或风格选 neutral，见 "
                + MANUAL
            )
        if args.emo_text and not health.get("supports_emo_text"):
            parser.error(
                "当前服务未加载 QwenEmotion：重启服务加 --use-qwen-emo，或改用 --emo-vector/--emo-ref，见 "
                + MANUAL
            )
        # 采样参数/种子对旧服务是**静默丢弃**（Pydantic 默认忽略未声明字段），而摘要这边已经
        # 按新参数变了 ⇒ 会产出「摘要说改过、音频其实没改」的假验证。故显式硬失败。
        sampling_only = {k: v for k, v in sampling.items() if k != "seed"}
        if sampling_only and not health.get("supports_sampling_params"):
            parser.error(
                f"当前服务不支持采样参数（{','.join(sorted(sampling_only))}）：服务端代码过旧，"
                f"请用本 skill 当前 tts_server.py 重启服务，见 {MANUAL} §二"
            )
        if "seed" in sampling and not health.get("supports_seed"):
            parser.error(
                f"当前服务不支持 --seed：服务端代码过旧，请用本 skill 当前 tts_server.py 重启服务，见 {MANUAL} §二"
            )
        if sampling.get("text_normalization") is False and not health.get(
            "supports_text_normalization"
        ):
            parser.error(
                "当前服务为 IndexTTS-2（infer() 无 text_normalization 形参）："
                "去掉 --no-text-normalization，或改用 v2.5 服务"
            )
        if block_cfg and not health.get("supports_blocks"):
            parser.error(blocks_unsupported_hint(health))

        sem = asyncio.Semaphore(CONCURRENCY_INDEXTTS)
        if block_cfg:
            # 段落演绎：块=合成与缓存单位；逐块并发=1（服务端串行锁），结果按原顺序展平
            block_results = await asyncio.gather(
                *(
                    synth_block_indextts(
                        sem,
                        b,
                        args.force,
                        str(ref_path),
                        ref_sha1,
                        style_name,
                        vec,
                        alpha,
                        df,
                        tts_lang,
                        args.engine_tag,
                        args.server,
                        out_dir,
                        num_beams=beams,
                        sampling=sampling,
                        store=store,
                        slug=slug,
                        discard_sec=discard_sec,
                        tail_pad_sec=block_cfg.get("tail_pad_sec", 0.18),
                        perform_punct=perform_punct,
                    )
                    for b in blocks
                )
            )
            results = [r for br in block_results for r in br]
        else:
            results = await asyncio.gather(
                *(
                    synth_indextts(
                        sem,
                        i,
                        args.force,
                        str(ref_path),
                        ref_sha1,
                        style_name,
                        vec,
                        alpha,
                        df,
                        tts_lang,
                        args.engine_tag,
                        args.server,
                        out_dir,
                        # 逐句束宽：基础值来自「命令行优先、否则取预设」，--steady 命中句再提高
                        num_beams=beams_of[i["id"]],
                        emo_ref=emo_ref_path,
                        emo_ref_sha1=emo_ref_sha1,
                        emo_text=args.emo_text,
                        sampling=sampling,
                        store=store,
                        slug=slug,
                    )
                    for i in items
                )
            )

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    write_voice_marker(out_dir, signature)  # 成功收尾才落签名，中途失败不改变基线
    total = sum(r["durationSec"] for r in results)
    print(f"合成 {len(results)} 句，纯语音总时长 {total / 60:.2f} 分钟")
    if args.engine == "indextts" and args.steady:  # 混合档：回执两档各多少句，便于对账
        hi = sum(1 for i in items if beams_of[i["id"]] != beams)
        print(
            f"混合档：{len(items) - hi} 句按束宽 {beams}（{style_name}）+ "
            f"{hi} 句按束宽 {args.steady_beams}（--steady {args.steady}）"
        )
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
