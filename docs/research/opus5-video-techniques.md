# Opus 5.5 视频生态五仓评估：学习/借鉴/引入存证

> **结论先行**：微信文章《用 Claude Opus 5.5 做视频堪称一绝》[1] 提及的五个开源仓全部核实存在并已钉版取证。**架构层面零引入必要**——文章主推的「单 HTML/Canvas + 截帧 + FFmpeg」临时路线在本仓已有 Remotion 确定性流水线面前全面处于劣势（[HyperFrames 否决同款论据](./dependency-policy-and-asset-tools.md)：第二渲染面）。**概念层借鉴分两轮落位**：首轮存证后经用户复核校正归引——[DIRECTING-CRAFT](../../references/DIRECTING-CRAFT.md) 反模式表的既有准入是「业界已验证原理」（RSI-048 先例：Murch/Disney/Mayer 来源），不适用建模手册的成片锚点伪锚禁令，故业界原理级**四项落规格**（反模式表 A-29 metronome 等长镜头 / A-30 硬交换冒充承接、08 帧驱动条款 CSS transition/animation 禁令、08 Motion Blur 启用时机——180° 快门法则）；cue 路线为**存证另列**：opuscar 的 CC0 音源 + 程序化配乐/事件驱动音效是 02「留空轨」cue 系统后续 RSI 的技术路线参照（§五，三轮补证 Austerlitz「画面推导音效 + 空间音频属性」并入）。**待信号七项**住 §四，核心两项：carry score 元素级连续性 oracle（QA 语义盲区的自动化候选——实现路径未验证、误报面未知，09 判据上架纪律硬约束）与风格库 11 节骨架（零消费者，首例风格化需求时按 §2.2 形态起库）。事实快照均为 2026-10-13 钉版口径（三路并行子代理只读取证，raw @ 钉版 sha，未 clone、未执行外部代码）。协议：RSI-068（[台账](../.agents/issue.md)）。

## 一、事实快照（五仓钉版 + Austerlitz 案例补证，2026-10-13）

| 仓 | 钉版 | 许可 | ★ | 定位 |
|---|---|---|---|---|
| [feitangyuan/onetake](https://github.com/feitangyuan/onetake) | `4157581` | **PolyForm NC 1.0.0** [4] | 2259 | 一镜到底产品片 Skill：节拍表 + carry score 量化验收 + 动作库 |
| [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | `fdc46d7` | MIT | 2129 | 43 种影片风格库 + Skill（每风格 = 样片 + STYLE.md，无 copy-paste prompt） |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | `7ba4dcf` | **无 LICENSE** | 5108 | Remotion 官方 Agent Skills（12 个：best-practices/markup/render/captions/maps/…） |
| [joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts) | `7977c80` | **无 LICENSE** | 306 | 18 个结构化 prompt + 54 案例索引 |
| [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) | `e6c7eee` | MIT | 4755 | 853 个视频 prompt 索引（纯语料，无方法论） |
| [WinterArc21/Battle-of-Austerlitz-Film](https://github.com/WinterArc21/Battle-of-Austerlitz-Film) | `86dae32`（单 commit 仓） | **无 LICENSE** | 24 | 5 分钟奥斯特里茨战役片：WebGL 程序化渲染 + 真实 SRTM 地形 + 画面推导音效（三轮补证） |

**许可硬边界** [4]：onetake 原文「onetake is free for noncommercial use only」——禁商用，代码级复用被排除；两个无 LICENSE 仓按版权默认法保留所有权利，**其文本（prompt/skill 正文）不得转载进本仓文档**，本评估只提炼归纳性规则要点（子代理取证已按此纪律执行）。opuscar 的 MIT 只覆盖其代码与指南文本，风格样片为 Opus 5.5 调优产物，本仓 Claude 模型栈下可复现性存疑。

## 二、逐仓净增量判定

### 2.1 onetake：carry score 与 16 条硬规则

**carry score 算法**（[scripts/probe.py](https://raw.githubusercontent.com/feitangyuan/onetake/415758128aa45cc54340df40d8109363447f582e/scripts/probe.py) `continuity()`）[2]：输入不是视频像素，而是对确定性时间函数 `__seek(t)` 的**元素级采样序列**（每元素：id/key/x/y/w/h/op/vis）。核心：① 相邻采样做**加权 Jaccard**（`weight = vis·op/area`，key 匹配取 min/max 作交集/并集）；② Jaccard < 0.3 且两侧有内容 → 硬切；③ 切点滞后 0.4s 后 Jaccard < 0.2 → 边界事件；④ 事件按共同存活元素分级：位移 ≥ 0.02 对角线或缩放 ≥ 0.1 → **carried**（1.0）、同 key 共同面积 ≥ 0.03 → **anchored**（0.5）、皆无 → **bare**（0.0）；⑤ 豁免 burst、片尾 1.2s、声明剪切点；⑥ `score = Σ分级 / considered`。

**与本仓 QA 的对照**：[qa_frames.py](../../scripts/qa_frames.py) 的冻帧检测是像素级 16×16 指纹，无法区分「转场交换」与「物体位移」——语义级连续性目前全靠人工门（导演级四维）。carry score 把「交接处什么活下来」变成了可计算判据，且其「确定性时间函数 + 元素采样」前提与本仓帧驱动渲染架构同构。**实现路径未验证**（Remotion 无「在屏元素清单」直接暴露，headless DOM 采样或像素差分退化方案的误报面未知），按 09 判据上架纪律（已知干净帧零误报）本期不动。

**16 条硬规则** [3] 与 [DIRECTING-CRAFT](../../references/DIRECTING-CRAFT.md) 对照，三条本仓无等价物：「禁 metronome 剪辑」（等长镜头 = 幻灯片——A-10 只管静态 > 5s，不管节奏均匀）、「Never replace a beat — carry it」（display:none 交换 = 幻灯片——比 Morph Continuity 更锋利的同源表述）、「> 80px/帧必须 shutter motion blur」（本仓 Motion Blur opt-in 缺量化触发条件）。**三条均已二轮落地**：前两条落反模式表 A-29/A-30（业界原理级准入），第三条落 08 Motion Blur 启用时机；镜头抖动等其余禁项证据单薄（单仓禁令、无原理级支撑），维持待信号。另有一项**组织形态借鉴**：[cases/](https://github.com/feitangyuan/onetake/tree/415758128aa45cc54340df40d8109363447f582e/cases) 案例 README 以节拍表为骨、附验收数字（如 `continuity 1.00 over N boundaries`），部分案例留**被否版本及否决理由**（如 `domino-25s` 四次配乐试听全被否的逐版记录；`knockon-15s` 等首稿即通过的案例则没有）；carry 分的档案另住顶层 README 分数表（同一部片 v1 被否 0.00 → v2 0.40 → v3 通过 0.75，发布片 0.83）——本仓 RSI 台账记机制缺陷、建模手册记手法，唯独没有每集交付复盘的量化档案形态，入待信号（§四）。

### 2.2 lemo-opuscar：风格条目骨架与原创配乐路线

**STYLE.md 11 节固定骨架**（[ink-wash](https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/fdc46d7f0e20cc953a71d56241a92d1b4cb7298e/styles/ink-wash/STYLE.md)、[lowpoly-island](https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/fdc46d7f0e20cc953a71d56241a92d1b4cb7298e/styles/lowpoly-island/STYLE.md) 实证骨架一致）[5]：① Essence 正/负定义 → ② Materials & rendering（纸色 hex、五墨阶表、笔刷参数 / 六边形坐标公式、`flatShading` + 后处理管线）→ ③ Colour logic → ④ Type & subtitles（字幕驻留 `max(1.8s, speech + 0.6s)`）→ ⑤ Motion quality（人物 on twos 12fps、过冲曲线公式）→ ⑥ Camera grammar（`Move | Expresses | Can serve` 三列表）→ ⑦ Sound palette（乐器白名单 + mix −14 LUFS）→ ⑧ Native moves（媒介专属技法各带适用句式）→ ⑨ Pitfalls（bug/对策对）→ ⑩ Engine 清单 → ⑪ Variation space。**这不是 prompt 模板而是生产约束文档**，头部「References (grammar only)」禁抄声明与本仓「概念移植经规格消化，非照搬」同构。43 风格 [7] 中与科普图解片契合的子集：whiteboard / blueprint / iso-infographic / dataviz / swiss-motion / pictogram-motion。

**配乐全原创生成**（[TECHNIQUE.md](https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/fdc46d7f0e20cc953a71d56241a92d1b4cb7298e/TECHNIQUE.md)）[6]：免费/CC0 音源采样（VSCO 2 CE、VCSL、FreePats、Karoryfer、Salamander）+ Karplus–Strong 物理建模拨弦 + numpy 合成 chip tune/drone；音效 `click/whoosh/thump` 程序化合成、**由页面事件（`window.EV`）驱动**；混音两遍 loudnorm −14 LUFS、voice 高于 music 约 10dB。`window.EV 事件驱动`与本仓「句 id / 词窗 / beat 事件」SSOT 天然对接——这是 02 留白 cue 系统的完整技术参照（详见 §五）。配音侧 Kokoro（英，本地）/ edge-tts（中）+ faster-whisper ASR 词级时间戳校验，与本仓 edge 草声档 + ASR diff 候选门同族，无增量。

### 2.3 remotion-dev/skills：官方实践对读

12 个 skill 对读（[remotion-markup](https://raw.githubusercontent.com/remotion-dev/skills/7ba4dcf8ebe1626b00baa41e1f2478113719b60b/skills/remotion-markup/SKILL.md)）[8]，与本仓 [08 规格](../../references/08-remotion-implementation.md)三栏差异：

| 官方有 · 本仓无 | 判定 |
|---|---|
| 禁 CSS transition/animation 显式条款 | **已二轮落地**：08 帧驱动条款 +CSS 禁令（规格条款非机器门，不违不变量 8） |
| `scale/translate/rotate` 独立 CSS 属性 | 可选回填，非红线级 |
| blanket `premountFor={fps}` | 不回填——与本仓按镜显式控制相悖 |
| Google Fonts / local fonts 加载 | **有意偏离**：08 钉 macOS 系统字体栈，内嵌子集字体已在 Remotion 5.0 触发器闭环 |
| composition 注册元数据条款 | 不回填——skeleton frozen 工程配置已承载，重复即熵增 |
| Studio 优先 / 按需渲染 | **冲突**，不回填——08 是无头确定性流水线，官方该条面向交互式创作 |
| `@remotion/media` AnimatedImage | 暂不回填——本仓无 GIF 素材路径 |

反向确认：本仓七条渲染红线、frozen 运动层铁律（弹簧只喂局部帧、effects 永不吃弹簧）、确定性渲染纪律（禁随机/同帧 PNG 逐字节门）、TTS manifest 绝对时间轴均为官方 skill 未覆盖的**本仓独有资产**。

### 2.4 opus-video-prompts：结构范式与反模式对读

XML 分段范式（`inputs/direction/structure/build/gotchas/start`）[9] 与本仓 [storyboard 四列 + Visual Lock](../../references/06-storyboard.md)、②钩子矩阵同构（规格先行、节拍表先行、禁项前置）——**验证了本仓范式与业界最佳实践的收敛，无增量**。禁用项清单（RGB 分离/镜头光晕/粒子爆发/弹跳缓动/镜头抖动/网格地面）与本仓 30 条反模式对读：**差异是哲学性的**——外部按审美一律禁，本仓 A-11 按「教学职能」条件禁（科普片定位下更优，Motion candy 有教学职能时合法）。真正未覆盖的候选中，等长镜头已落 A-29；镜头抖动显式禁、背景噪声动画证据单薄，并入 §2.1 待信号清单。正向吸收候选四条：音效按实测峰值对齐事件、contact sheet 逐拍预检、**循环末帧 = 首帧逐像素一致**（本仓 `--loop` 抽帧已是同族判据，可升级为逐像素口径，待信号）、响度归一口径。

### 2.5 awesome-opus5-5-videos：纯语料不引入

853 条 prompt 逐条挂原帖 + 技术标签（Motion graphics 58 / Explainers 16 / 3D 14 / Games 12）[10]，How-to 仅三步复制粘贴。**无方法论、无锚点，不引入**；唯一用途是未来建模经验/风格库建库时的检索语料源（按需单条取证，不批量 vendor）。

## 三、引入形态比选

| # | 形态 | 判定 |
|---|---|---|
| 1 | vendor 任一仓代码/资产/文本 | **否决**：onetake NC 禁商用；两无许可仓文本受版权保护；opuscar 风格资产为 Opus 调优、跨模型可复现性存疑 |
| 2 | 新增风格库（STYLE-PLAYBOOK 类，11 节骨架） | **否决（本期）**：零消费者零成片锚点，违「先有数据再有门」（不变量 8，ISSUE-167/188 先例）；骨架形态存证待信号，首个真实风格化需求出现时按 §2.2 骨架起库 |
| 3 | qa_frames 加 carry score 类判据 | **否决（本期）**：实现路径未验证（Remotion 元素清单暴露方式）、误报面未知，违 09 判据上架纪律；登记待信号，首集出现「转场 vs 位移」人工误判时立项 |
| 4 | 08 回填「禁 CSS transition/animation」 | **采纳（二轮落地）**：规格条款非机器门，不违不变量 8；一行堵 Studio 生成物与外部代码携带路径（08 帧驱动条款） |
| 5 | DIRECTING-CRAFT 反模式表加条目（等长镜头/硬交换/镜头抖动/背景噪声） | **部分采纳（二轮落地）**：A-29 metronome、A-30 硬交换落表——DIRECTING-CRAFT 准入是业界已验证原理（RSI-048 先例），伪锚禁令只约束建模手册；镜头抖动/背景噪声证据单薄维持待信号 |
| 6 | cue 系统 RSI 吸收 CC0 音源 + 程序化合成 + 事件驱动音效路线 | **存证采纳**（路线图输入，非本期实现，见 §五） |
| 7 | 本评估落研究文档 + ledger 登记 + 索引 | **采纳**（即本 PR 全部改动面） |

## 四、采纳 / 不采纳 / 待信号清单

**采纳（已落地）**：研究文档存证（本文）+ RSI-068 ledger 登记 + [knowledge-map](../.agents/knowledge-map.md) 索引 + CHANGELOG；二轮规格落地四项——[DIRECTING-CRAFT](../../references/DIRECTING-CRAFT.md) 反模式表 A-29/A-30、[08](../../references/08-remotion-implementation.md) 帧驱动条款 CSS 禁令、08 Motion Blur 启用时机；三轮补证 Austerlitz 画面推导音效入 §五（存证）。**零 vendor、零依赖。**

**待信号（登记后按触发条件立项；候选条目正文不入规格/手册，规格层仅许一行指针指向本清单，指针不是候选区）**：

| 概念 | 触发条件 | 落位候选 |
|---|---|---|
| carry score 类语义连续性判据 | 首集出现「转场交换 vs 物体位移」人工误判 | qa_frames `--check` 新判据（先零误报验证） |
| 风格库（11 节骨架形态） | 首个真实风格化分集需求 | 独立 bounded 手册（对齐 MODELING-PLAYBOOK 治理） |
| 反模式两条：镜头抖动 / 背景噪声动画 | 任一集成片出现对应病灶 | DIRECTING-CRAFT 反模式表（候选区先行） |
| 循环判据升级为末帧 = 首帧逐像素 | loop 型内容出现指纹误放行 | qa_frames `--loop` 口径 |
| contact sheet 逐拍预检（每拍一帧拼图，全量渲染前抽查） | 首集出现 beat 级预检需求（分幕复检粒度不足时） | qa_frames 抽帧模式扩展 |
| 渲染断点续跑（分块可恢复渲染，Austerlitz README 级线索） | 终渲因片长增长或中断而重跑成本显现时 | render/pipeline 的 chunk 化（先读其实现再设计，当前仅 README 自述） |
| 案例拆解档案形态（节拍表 + 验收数字 + 被否版本及理由，onetake cases/ 实证；carry 分档案在顶层 README） | 首集交付复盘时人工档案成本显现、或相邻集复用节拍结构时 | deliver 归档旁约定 breakdown.md（节拍表照抄 + 否决记录） |

**不采纳（全部，含理由）**：vendor 代码/资产/文本（许可 + 可复现性）；单 HTML 渲染路线（第二渲染面，[HyperFrames 先例](./dependency-policy-and-asset-tools.md)）；853 prompt 合集批量引入（无语料纪律）；图生视频/参考图扩展（超科普图解定位）；blanket premountFor / Studio 优先渲染 / composition 注册条款（见 §2.3 逐条判定）。

## 五、cue 系统路线图输入（02 留白的技术参照存证）

02 阶段明确「BGM 留空轨」边界（[02-planning.md](../../references/02-planning.md)），[DIRECTING-CRAFT](../../references/DIRECTING-CRAFT.md) 原则表注明「cue 系统属后续 RSI」。本次取证给出该后续 RSI 的**已验证技术路线**（opuscar [6] + onetake [3] + Austerlitz [11] 三源实证）：

- **音源**：CC0/免费采样库（VSCO 2 CE、VCSL、FreePats、Karoryfer、Salamander）——零许可风险；
- **合成**：Karplus–Strong 物理建模拨弦 + numpy 波形合成（chip tune/drone）+ 程序化音效（click/whoosh/thump）——确定性可复现，与本仓帧驱动哲学同构；
- **驱动**：页面事件（`window.EV`）触发音效 → 本仓对应「句 id / 实测词窗 / beat 事件 → cue」，可复用 TTS manifest 词级时间戳；onetake 侧印证「音效按实测峰值对齐事件、剪点落重拍」；
- **画面推导音效与空间属性**（Austerlitz [11]，三轮补证）：`events.js` 从画面事件派生音效 cue（每声炮、齐射、马蹄），并携带距离衰减、声像 pan 与 343 m/s 声速延迟——音效不仅按事件时间轴摆放，还能从「画面上发生了什么」推导，且带空间物理属性；作为 cue 粒度与属性设计的上限参照。其「阵型与粒子是 time 的纯函数、任意帧可独立渲染」与本仓确定性渲染哲学同构（验证收敛）；真实地形数据管线（SRTM 高程 → WebGL）与 [text-to-cad](./dependency-policy-and-asset-tools.md) 同属「数据驱动外部资产」先例，按集 opt-in 模式可平移；**分块可恢复渲染**（README 级线索：`tools/render.mjs` 自述 resumable chunks，未读实现，无断点机制细节）对照本仓：TTS 有 `tts_resume` 自愈续跑、渲染无断点续跑——当前分钟级渲染成本下可接受，入待信号（§四）；
- **混音**：loudnorm 归一 + voice 高于 music 约 10dB；响度口径两仓不同（opuscar −14 LUFS ≈ YouTube 标准、onetake −16 LUFS ≈ 播客标准），立项时按分发平台定档。

## 引用

[1] 逛逛GitHub.「用 Claude Opus 5.5 做视频堪称一绝，外网已经玩疯了」. 微信公众号, 2026-10-01. <https://mp.weixin.qq.com/s/vxkIjpJ4uAiiwTIQ-9Isaw>
[2] feitangyuan. onetake `scripts/probe.py` @ `4157581`. <https://raw.githubusercontent.com/feitangyuan/onetake/415758128aa45cc54340df40d8109363447f582e/scripts/probe.py>
[3] feitangyuan. onetake `SKILL.md` @ `4157581`. <https://github.com/feitangyuan/onetake/blob/415758128aa45cc54340df40d8109363447f582e/SKILL.md>
[4] feitangyuan. onetake `LICENSE`（PolyForm Noncommercial 1.0.0）@ `4157581`. <https://github.com/feitangyuan/onetake/blob/415758128aa45cc54340df40d8109363447f582e/LICENSE>
[5] Lemomo. lemo-opuscar `styles/ink-wash/STYLE.md` @ `fdc46d7`. <https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/fdc46d7f0e20cc953a71d56241a92d1b4cb7298e/styles/ink-wash/STYLE.md>
[6] Lemomo. lemo-opuscar `TECHNIQUE.md` @ `fdc46d7`. <https://raw.githubusercontent.com/lemomo-ai/lemo-opuscar/fdc46d7f0e20cc953a71d56241a92d1b4cb7298e/TECHNIQUE.md>
[7] Lemomo. lemo-opuscar `styles/`（43 风格全量清单）@ `fdc46d7`. <https://github.com/lemomo-ai/lemo-opuscar/tree/fdc46d7f0e20cc953a71d56241a92d1b4cb7298e/styles>
[8] Remotion. skills `skills/remotion-markup/SKILL.md` @ `7ba4dcf`. <https://raw.githubusercontent.com/remotion-dev/skills/7ba4dcf8ebe1626b00baa41e1f2478113719b60b/skills/remotion-markup/SKILL.md>
[9] joeseesun. opus-video-prompts `prompts/15-ui-morph-loop.md` 等 @ `7977c80`. <https://github.com/joeseesun/opus-video-prompts/tree/7977c807781d4ba7c235247b8899a72575a30d00/prompts>
[10] yihui-dev. awesome-opus5-5-videos `README.md` @ `e6c7eee`. <https://github.com/yihui-dev/awesome-opus5-5-videos/blob/e6c7eee870cbd6d40825d6348a0c5782b3721fe9/README.md>
[11] WinterArc21. Battle-of-Austerlitz-Film `README.md`（无 LICENSE，2026-10-13 检证）. <https://github.com/WinterArc21/Battle-of-Austerlitz-Film/tree/86dae32d20f0a0f2395e7dc8938846fd51e355a6>
