"""音频版本库（tts.py 内容寻址持久库）的纯函数契约。

背景：集内 audio/ 是 gitignored 本地产物，换 worktree 即丢——版本库按
（集 slug, 句 id, digest）三元组持久化合成成果，使「改稿只重配变更句」
跨工作区成立。此处钉死四条不变量：回收等价缓存命中、digest 失配必 miss、
历史版本并存不覆盖、禁用时全程直通。库根解析（env 覆盖、旧名兼容读、
旧默认目录迁移回退）同为机器属性契约，一并在此钉死。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import tts  # noqa: E402
from tts import (
    digest_indextts,
    store_deposit,
    store_has,
    store_restore,
    store_root,
)


def _mk(root: Path, name: str, size: int = 64) -> Path:
    """占位音频：store 只搬运字节不解析，内容无语义。"""
    p = root / name
    p.write_bytes(bytes(range(size % 251)))
    return p


def test_disabled_store_is_transparent(tmp_path):
    assert store_root(disabled=True) is None
    src = _mk(tmp_path, "x.mp3")
    store_deposit(src, "x", "c" * 40, None, "ep")  # no-op 不炸、不建目录
    assert not (tmp_path / "store").exists()
    assert not store_restore("x", "c" * 40, tmp_path, None, "ep")


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBE_VIDEO_TTS_STORE", str(tmp_path / "custom"))
    assert store_root(disabled=False) == tmp_path / "custom"


def test_empty_env_disables_store(monkeypatch):
    monkeypatch.setenv("VIBE_VIDEO_TTS_STORE", "")
    assert store_root(disabled=False) is None


def test_default_dir_used_when_env_unset(monkeypatch, tmp_path):
    """不设 env ⇒ 落到默认路径（目录允许尚不存在，deposit 时再建）。"""
    monkeypatch.delenv("VIBE_VIDEO_TTS_STORE", raising=False)
    monkeypatch.setattr(tts, "DEFAULT_STORE", str(tmp_path / "fresh-store"))
    assert store_root(disabled=False) == tmp_path / "fresh-store"


def test_local_cache_hit_backfills_empty_store(monkeypatch, tmp_path):
    audio, store = tmp_path / "audio", tmp_path / "store"
    audio.mkdir()
    item = {"id": "p4-01", "scene": "P4", "text": "本地缓存。"}
    digest = digest_indextts(
        "r" * 12,
        "neutral",
        None,
        1.0,
        1.0,
        "ZH",
        "indextts",
        item["text"],
    )
    _mk(audio, "p4-01.mp3")
    (audio / "p4-01.sha").write_text(digest, encoding="utf-8")
    monkeypatch.setattr(tts, "mp3_duration", lambda _path: 1.25)

    def unexpected_synthesis(*_args, **_kwargs):
        raise AssertionError("本地缓存命中时不应调用服务端")

    monkeypatch.setattr(tts, "http_synthesize", unexpected_synthesis)

    result = asyncio.run(
        tts.synth_indextts(
            asyncio.Semaphore(1),
            item,
            False,
            "",
            "r" * 12,
            "neutral",
            None,
            1.0,
            1.0,
            "ZH",
            "indextts",
            "http://unused",
            audio,
            store=store,
            slug="ep",
        )
    )

    assert result["durationSec"] == 1.25
    assert store_has(store, "ep", "p4-01", digest)


def test_rename_miss_and_migration_mv_or_symlink(tmp_path):
    """I-092：store 键＝集目录叶名——集目录改名后新键零命中（失败形态）；
    库内目录 mv 改键、或软链（链接名＝新键、目标＝旧键目录，兼容未拉取改名
    的旧 checkout）迁移后新旧键恢复命中。迁移指引见 references/07 改名迁移段。"""
    audio, store = tmp_path / "audio", tmp_path / "store"
    audio.mkdir()
    digest = "d" * 40
    src = _mk(audio, "p1-01.mp3")
    store_deposit(src, "p1-01", digest, store, "a-video")

    # 失败形态：集目录 a-video 改名 a 后，新叶名键下同 digest take 零命中
    assert store_has(store, "a-video", "p1-01", digest)
    assert not store_has(store, "a", "p1-01", digest)

    # 迁移①：mv 库内目录改键——新键恢复命中，字节等价
    (store / "a-video").rename(store / "a")
    out1 = tmp_path / "audio1"
    out1.mkdir()
    assert store_restore("p1-01", digest, out1, store, "a")
    assert (out1 / "p1-01.mp3").read_bytes() == src.read_bytes()

    # 迁移②（多 checkout 过渡）：软链链接名＝新键、目标＝旧键目录——新旧两键同时命中
    (store / "a").rename(store / "a-video")
    (store / "a").symlink_to("a-video")
    out2, out3 = tmp_path / "audio2", tmp_path / "audio3"
    out2.mkdir()
    out3.mkdir()
    assert store_restore("p1-01", digest, out2, store, "a")
    assert store_restore("p1-01", digest, out3, store, "a-video")
