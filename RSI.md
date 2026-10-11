# RSI：递归自改进回路（Skill 自身缺陷与改进的协议）

> RSI（Recursive Self-Improvement）是**元回路**：作用对象是本 Skill 仓自身（规格、脚本、模板、流程、制度），与阶段化视频流水线正交——视频内容的质量问题走 Stage ④/⑨ 既有 QA 回路，不进本协议；唯一的内容侧例外是**可跨集复用的建模经验**，走第十节「建模经验分支」沉淀进有界手册。回路的**通用协议**（触发白名单、旁路捕获、状态机、G0–G4 门禁、子代理派发与编排、确认与降级）已上收至统一仓库 [ThreeFish-AI/rsi](https://github.com/ThreeFish-AI/rsi) 的 [references/protocol.md](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md)；本文只保留本仓特有的触发分流、ledger 纪律、不变量清单与建模经验分支，旧四道门 G1–G4 与统一门禁的映射见统一协议[附录A](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#附录a-vibe-video-旧门禁映射)。仓内特殊节的子代理 prompt 底稿属性保留（同阶段规格先例），通用角色底稿（steward / verifier / context-reviewer）见统一仓库 references/；触发分流的一句话判据见 [SKILL.md](SKILL.md)「自改进回路（RSI）」节。

**目录**：一、触发与分流 · 二、登记 · 三、子代理协议 · 四、门禁（统一 G0–G4） · 五、两种处理模式 · 六、PR 规范 · 七、失败出路 · 八、降级路径 · 九、不变量保护清单 · 十、建模经验分支

## 一、触发与分流

发现者不限：Agent 在制片中自行撞见，或用户主动提出。先判归属再动手：

| 现象 | 归属 | 去处 |
|---|---|---|
| 断言与信源不符、黑帧、覆盖门 FAIL、字幕错位 | 视频内容问题 | 既有 QA 回路（[04](references/04-verification.md) 校验清零 / [09](references/09-render-qa.md) 修复回路），**不进 RSI** |
| 脚本崩溃/误报/漏报、文档命令复制即跑失败、契约不清致代理误用、模板与执法测试矛盾、规格与实现漂移 | Skill 自身缺陷 | RSI |
| 用户提出「这个流程/制度/方法可以更好」 | Skill 自身改进项 | RSI |
| 用户对某个**建模方法**（概念 → 画面/母题/构图/动效强度）明确认可或否决、或主 Agent 自评认可，且可跨集复用 | 建模经验 | RSI 建模经验分支（第十节）：追加手册候选区，攒批策展 |

**边界规则**：一次事故两层都有（内容写错 + 机制纵容了它）→ 内容当场修，机制的纵容登记为 RSI 改进项——RSI 不背内容的锅，内容不替机制挡枪。

## 二、登记（ledger 是回路的入口）

发现即登记 [docs/.agents/issue.md](docs/.agents/issue.md)（`$T` 非 git 仓时不落本地，登记改走第八节 GitHub Issue 草稿路径）；通用入账流程（入账硬条件、脱敏边界、条目状态机）见[统一协议 §3 旁路捕获](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#3-旁路捕获)。仓内 ledger 纪律：

- 编号 `RSI-001` 起三位递增；**刻意不用 `ISSUE-` 前缀**（上游 negentropy 的 ISSUE-xxx 已占用本仓正文外链，复用必混淆；引用上游教训一律写全 URL）。
- 新条目追加文件末尾，同一问题只维护一处；复发不新开编号，在原条目追加带日期的复盘点。
- 登记字段六段式：表因（可观测症状）/ 根因（技术归因，含文件路径）/ 定性（阻断性缺陷｜非阻断改进）/ 处理方式（PR + commit 链接）/ 后续防范（Negative Prompt 式禁令）/ 同类问题影响（可选）。
- 条目格式（与统一模板字段映射）：仓内沿用六段式——表因↔最小复现与来源、根因↔疑似根因、定性↔两种处理模式归属（阻断性缺陷｜非阻断改进）并可标注统一分级 T1–T3、处理方式↔结论（PR/commit 回填即 `submitted` 终态；「排队待议」「不成立 + 证据」即 `ready`/`rejected` 的仓内自然语言形态）、后续防范与同类问题影响为仓内特有（Negative Prompt 沉淀，统一模板无对应）；统一模板的状态六态住项目 `.temp` backlog（统一协议 §3），回填本 ledger 时不搬运。

## 三、子代理协议（fresh context）

通用派发与编排（Steward / Verifier / Context-Reviewer 三角色、隔离 clone、noreply 提交身份、限流背压）见[统一协议 §4 派发与编排](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#4-派发与编排)；仓内附加纪律：

- 主代理只做三件事：**登记 ledger → 另起子代理 → 不顺手改**（制作过程中 `$T` 机制文件对主代理只读，例外仅两处**仅追加**的登记面：本 ledger、[建模手册](references/MODELING-PLAYBOOK.md)「候选区」——机制热修与手册条目增删改都走子代理，不在制片上下文里顺手落笔）。
- 子代理只在 `$T` 的 git worktree 话题分支上工作（不占用户当前分支）；`$W`/`$P`/`$V` 一律只读——复现可读，绝不写；禁止 push 主分支、禁止 Rebase，commit 遵循仓库既有中文 conventional 风格。
- 输入契约仓内脱敏加强：用户内容**脱敏摘录**不整搬——**声音样本是生物特征**，样本路径与音频一律不进材料。
- 输入契约附改动面白名单：主代理派发时初步圈定允许触碰的文件，子代理可申请扩圈，但须在 PR 描述里说明理由——改动面裁量权锚在持制片上下文的主代理侧，不随 fresh context 子代理自定。
- 分级线（仿 Stage ④「互不污染视角」）：触碰第九节不变量清单、或横跨 ≥3 文件的改动：**实施与核验须两个独立子代理**（核验方只拿 diff + ledger 条目，不拿实施方的推理过程）；一行 typo / 死链级修复：允许单代理自查过门。

## 四、门禁（统一 G0–G4）

判据、回执格式与反刷分规则以[统一协议 §5 核验门禁](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#5-核验门禁)为准（G0 预检去重 / G1 属实与正确性 / G2 方案比选与收益 / G3 非回归与不变量勾验 / G4 安全隐私）；旧 G1–G4 的逐门映射见[附录A](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#附录a-vibe-video-旧门禁映射)。仓内附加执法资产：改动 SKILL.md 描述或路由时按 [evals/](evals/README.md) 做新旧对拍（统一协议无此仓内资产，触发条件住本节）。仓内机器执法命令（统一适配档案 `machine_checks` 引用同一份；与 pyproject.toml 顶部注释由 `test_machine_checks_pinned` 锚定一致）：

```bash
# 命令与 pyproject.toml 顶部注释（折行快照）由 test_machine_checks_pinned 锚定一致；依赖漂移在 pytest 收集阶段即大声报错
uv run --no-project --with pytest --with numpy --with pillow --with mutagen --with soundfile python -m pytest tests -q
```

## 五、两种处理模式

阻断性缺陷（立即快速通道、门禁一道不省）与非阻断改进（默认登记排队、收益证据门槛更高）的判据已上收[统一协议 §4](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#4-派发与编排)。

仓内解堵纪律：阻断性缺陷修复期间，主代理可临时采用子代理分支上的修复继续制片（修复 worktree 挂 `$T` 侧检出），PR 与回归核验照常走完——制片不等合并。

## 六、PR 规范

- 分支 `ThreeFish-AI/rsi-<NNN>-<topic>`；base = `main`（本仓惯例，无长期 feature 基线分支）；RSI 编号入 PR 标题。
- 门禁全过 → 按统一协议 §7 **一次确认后创建 PR** 并回报链接；PR 标题中文 conventional（`fix|docs|feat(rsi): …`），描述必含 **G0–G4 核验回执表**（[统一协议 §5](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#5-核验门禁) 格式：每门 ✅/❌ + 一句话证据）。
- CHANGELOG `[Unreleased]` 登记；ledger 条目回填 PR 与 commit 链接。通用确认与提交流程（一次授权、Draft 规则、硬禁令）见[统一协议 §7](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#7-确认与提交)。

## 七、失败出路（门未过怎么办）

分级出路（不成立闭环 / 触碰不变量无论证升级用户决策 / 收益不足降级待议 / 破坏项三条件齐备才放行 / 反复不过门丢弃分支记死因）已上收[统一协议 §9](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#9-失败出路)。

## 八、降级路径（`$T` 非 git 仓库）

拷贝式安装（无 `.git`）时**大声退出**（对齐仓内哨兵文化），绝不直接改无版本控制的副本——出路：GitHub 开 Issue（附 ledger 条目草稿），或 clone 正式仓迁移条目后走标准回路；通用降级矩阵（无网络 / 无 gh / 无子代理 / 背压）见[统一协议 §10](https://github.com/ThreeFish-AI/rsi/blob/main/references/protocol.md#10-降级矩阵)。

## 九、不变量保护清单（统一 G3 勾验面）

清单是**索引不是事实源**——每条一句话判由，正文 SSOT 各归其位（防第二事实源）：

1. 阶段序号与规格文件号一一对齐（第 N 阶段 ↔ `NN-*.md`；RSI-009 废除历史错位，RSI-013 插入 ⑤ 时整段顺移），严禁再引入错位；新增或删除阶段 = 规格整段改名 + 全仓入链同步（执法：`test_stage_numbers_align_spec_files`、`test_spec_references_resolve`）。
2. `narration.md` 唯一 SSOT；narration.json / manifest.json / chapters.json 是派生物，不得开「直改派生物」的口子。
3. frozen Remotion skeleton：改 frozen 文件 = 改模板 + 全集同步 + `verify_skeleton.py` 字节级过；不得只改某一集的复制件。
4. 运动层 `video/src/motion/` frozen 且不读 theme token。
5. `timing.json` 时序 SSOT（TS/Python 双语共读），不得在任何一侧内联时序常数。
6. 「复制不共享」边界：Python 实现只住 `$T/scripts/`，工作区 / 分集 scripts 只许薄包装。
7. config SCHEMA 是默认值唯一来源，toml 只写偏离；机器属性永不进 toml。
8. 全部阶段 gates 与 [stages.toml](references/stages.toml) 同源（SKILL.md 速查表门列逐字抄录，执法：`test_router_gates_match_stages`）；不新增阶段状态机。
9. `deliver` 刻意不串联 `render --final`、不入扇出白名单（完成行信号契约 + 破坏性命令显式执行）。
10. 命令四变量锚定：`$T` 命令不混工作区字面量；变量定义只在 [references/PIPELINE.md](references/PIPELINE.md)（执法：`test_docs_paths.py`）。
11. SKILL.md 路由壳纪律：只给路由、指针与不变量、速查表行数 = stages.toml 阶段数（一阶段一行）、不复制正文；frontmatter 只用 Agent Skills 规范六字段且须过官方校验器口径（执法：[test_skill_spec](tests/test_skill_spec.py)）。
12. 双锚点：skill 根自 `__file__` 找 SKILL.md、工作区根由哨兵搜索；静默猜根被禁止。
13. 声音样本生物特征纪律：不入库只存指纹；RSI 材料与示例不得引导样本路径进仓。
14. 许可与依赖纪律：pyproject 刻意无 `[project]`（依赖走 `--with`）；不引入未审计第三方依赖或新许可冲突。
15. 建模手册有界：预算与条目规则唯一实现于 [check_playbook.py](scripts/check_playbook.py)；超限只许按第十节压缩阶梯逐级压缩，禁整文件重写与「搬进规格正文腾预算」（执法：[test_modeling_playbook](tests/test_modeling_playbook.py)）。

## 十、建模经验分支（有界经验库的策展协议）

作用对象是 [references/MODELING-PLAYBOOK.md](references/MODELING-PLAYBOOK.md)：沉淀「画什么、怎么隐喻」的策略层经验，与 references/08「怎么动」的机制层正交。设计依据与证据见 [研究文档](docs/research/modeling-experience-distillation.md)。

**信号与角色**（Generator / Reflector / Curator 分权，防自评自改）：

- **Generator = 制片主 Agent**：②⑥ 设计前读手册；分镜采用条目时标注〔M-xxx〕；收到显式信号当场往候选区追加一行 `- 〔±号来源〕<集目录名>#<镜号>：…`（`〔+用户〕` 认可 / `〔-用户〕` 否决 / `〔+主〕` 主 Agent 自评认可；主 Agent 不单独否决），不改条目。
- **Reflector + Curator = 策展子代理**（fresh context）：默认在 ⑩ 交付后、候选区非空时启动一次（攒批），同一时刻至多一个策展 PR 在途；逐条给出处置 ADD / EDIT / VOTE±1 / MERGE / DISCARD，提交态候选区恒为空。删并既有条目 ≥3 条或触发压缩时，另起独立核验子代理（同第三节分级）。
- **交接**（每条信号只计一次）：候选行是 `$T` 主检出的未提交追加，建自 HEAD 的 worktree 看不到——主代理须把候选行**原文**随输入契约交给策展子代理；PR 合入前这些行留在主检出作在途记录（PR 被丢弃则顺延进下一批）；合入后 pull `$T` 前撤掉已交出的行（期间无新追加即 `git -C $T checkout -- references/MODELING-PLAYBOOK.md`；有则先摘出新行、同法还原、pull 后原样追加回）。否则 pull 被本地改动拦住，或同一 VOTE 在下一批重复计入。
- 信号强度：用户显式认可/否决为强信号；主 Agent 自评为弱信号，只能新增 w=1 的试行条目，不能单独推动晋升（存储的错误经验会被后续照抄放大）。

**权重生命周期**：新条目 w=2（用户认可）或 w=1（仅主 Agent）；复用后被认可 +1、被否决或返工 −1；w≤0 必须移出。**晋升定式**须 w ≥ `PROMOTE_W`、证覆盖 ≥ `PROMOTE_EPISODES` 集（门执法），且含 ≥1 次用户信号（门不可见，由核验子代理对照条目去向表核对）。

**门禁映射**（不新增门；编号为统一 G0–G4 语义，旧四道门对应见统一协议附录A）：G1 信号属实（显式信号 + 可复查锚点：候选须 `集目录名#镜号`，条目「证」可放宽为 `集目录名[#镜号]`——多镜综合的经验允许不点名单镜）/ G2 可迁移且不重复（抽象为「概念结构 → 视觉形式」，同键合并，不重述 08 机制与红线）/ G3 `check_playbook.py` 零 ERROR 零 WARN 且 pytest 全绿（越过 `HIGH` 须在同一 PR 内压到 `TARGET`）并附**条目去向表**（每个被删/并编号 → 去向 + 理由）/ G4 安全隐私按统一协议 §5。

**压缩阶梯**（字数 ≥ `HIGH` 触发，逐级执行、达 ≤ `TARGET` 即停；数值只在 check_playbook.py，失真由小到大）：

1. **淘汰**：w≤0 的条目移出（git 历史即冷档，commit 记编号与死因）；
2. **同键合并**：键 = 概念结构 × 视觉通道；保留较早编号，w 相加，证取最新 2 条；
3. **下沉执法**：已被机器门或模板组件吸收的条目删除（知识下沉到代码层才是真减熵）；
4. **归纳**：同族 ≥3 条 → 1 条参数化原则 + 最佳实例（Rule of Three）；
5. **冷退**：试行、w 最低、最久未更新且**非唯一覆盖**其概念类型者移出（保能力删除：先删被包含者，唯一覆盖者最后动）；
6. **措辞精简**：只压「非/据/证」等附属字段，「当/故/验」语义不得丢。

**禁令**：整文件或整节重写（ACE 实测整体重写致上下文坍缩、准确率跌破无适应基线）；为腾预算把条目搬进 references/08 等规格正文（转移熵而非减熵）；删唯一覆盖或高 w 条目凑数。

**回潮信号**（递归纠偏）：被淘汰或归纳掉的条目，其同键候选再次出现 ⇒ 判为过度压缩，恢复原条目（w 重置为 2）并在 PR 点名——压缩阶梯本身也受经验反馈约束。
