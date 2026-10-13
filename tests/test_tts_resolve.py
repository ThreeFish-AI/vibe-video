"""resolve_sampling 与 synth_source_text：本仓 CLI 层的采样参数解析与送合成文本选取。

这两者是视频流水线的编排逻辑（argparse Namespace → 采样字典；narration 条目 → 送合成文本），
留在 vibe-video。摘要格式、后缀规则与预设不变量属 dub 机制，其黄金值与不变量测试住 dub 仓。
"""

from __future__ import annotations

import argparse

import pytest

from tts import SAMPLING_DEFAULTS, resolve_sampling, synth_source_text


#: resolve_sampling 期望的 Namespace 形状（全 None = 全取上游默认）
_NS_BASE = {
    "style": "neutral",
    "temperature": None,
    "top_p": None,
    "top_k": None,
    "length_penalty": None,
    "repetition_penalty": None,
    "max_mel_tokens": None,
    "interval_silence": None,
    "no_text_normalization": False,
    "seed": None,
    "seed_offset": 0,
}


def _ns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**{**_NS_BASE, **kw})


def test_resolve_sampling_drops_upstream_defaults():
    """显式传入与上游默认相同的值不得进摘要——否则「照抄 --list-styles 输出」会整集重录。"""
    ns = _ns(
        temperature=SAMPLING_DEFAULTS["temperature"],
        length_penalty=SAMPLING_DEFAULTS["length_penalty"],
    )
    assert resolve_sampling(ns) == {}
    ns.length_penalty = 0.8
    assert resolve_sampling(ns) == {"length_penalty": 0.8}


def test_resolve_sampling_validates_ranges():
    for kw, frag in (
        ({"temperature": 0.05}, "temperature"),
        ({"top_p": 1.5}, "top-p"),
        ({"top_k": 1}, "束搜索下不安全"),
        ({"length_penalty": 3.0}, "length-penalty"),
        ({"repetition_penalty": 25.0}, "repetition-penalty"),
        ({"max_mel_tokens": 1816}, "max-mel-tokens"),
        ({"interval_silence": 3000}, "interval-silence"),
    ):
        with pytest.raises(ValueError, match=frag):
            resolve_sampling(_ns(**kw))
    # top_k=0 是「关闭 TopK」的合法值，不能被上面的 1 规则误伤
    assert resolve_sampling(_ns(top_k=0)) == {"top_k": 0}


def test_resolve_sampling_seed_offset():
    """--seed-offset 是「换一条 take」的逃生口；单独给 offset 而无 seed 时不生效。"""
    assert resolve_sampling(_ns(seed=1000, seed_offset=0)) == {"seed": 1000}
    assert resolve_sampling(_ns(seed=1000, seed_offset=3)) == {"seed": 1003}
    assert resolve_sampling(_ns(seed=None, seed_offset=3)) == {}


def test_synth_source_text_prefers_tts_text():
    """发音标注走 ttsText，字幕用的 text 不受影响；无标注句取值与历史完全一致。"""
    assert (
        synth_source_text({"id": "p0-01", "text": "他在银行里走。"}) == "他在银行里走。"
    )
    assert (
        synth_source_text(
            {
                "id": "p0-01",
                "text": "他在银行里走。",
                "ttsText": "他在银<行|HANG2>里走。",
            }
        )
        == "他在银<行|HANG2>里走。"
    )
    # 空字符串 ttsText 视为未提供（防 build_narration 写出空字段导致合成空文本）
    assert synth_source_text({"id": "x", "text": "正文", "ttsText": ""}) == "正文"
