# Understand-Anything 工程能力融入 vibe-video：评估存证与方案比选

> **结论先行**：Understand-Anything（UA，MIT，钉版 `000fbf3`）的工程能力**可以融入，但只以薄形态**——真正的增量不是搬它的代码或 dashboard，而是补两处与工具无关的规格缺口：① B 型纯代码仓库信源缺「结构骨架与素材映射」节（② 色彩契约/分幕、⑥ Map-First 全景/走查链因此没有结构原料）；② ② 分幕表缺「前置概念」列（幕级「先释后用」无法审计，RSI-015 jev 集实证）。UA 本身只作**按集 opt-in 的骨架起草器与读码导航**，其 LLM 字段永远只是线索：不进证据、不进口播、不作 ④ 锚点、不上屏。不 vendor 任何代码、不加依赖、不开新阶段、不加证据等级。落位：[01「六、结构骨架与素材映射」](../../references/01-source-extraction.md)（含 UA opt-in 子节）、[02 分幕表前置概念列](../../references/02-planning.md)；协议：RSI-060（[台账](../.agents/issue.md)）。事实快照均为 2026-10-12 口径（两轮 Workflow 调研 15 子代理 + 3 份对抗核验，**本文全部采用核验修正后的结论**）。

## 一、事实快照（UA @ `000fbf3`，2026-10-12）

钉版：`000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe`（下文文件引用一律挂此永久链）。仓库与生态：MIT 许可（Copyright (c) 2026 Yuxiang Lin），2026-03-15 建仓，85,935★ / open issues 317（2026-10-12 实测），release v2.9.0 落后插件 2.9.7。

**安装面**：Claude Code 官方路径是 `/plugin marketplace add` + `/plugin install`，**整插件一起装**（[hooks/hooks.json](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/hooks/hooks.json) + 9 个 skills + 10 个 agents，目录结构实测），**没有官方「只装单 skill」的选项**；[plugin 清单](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/.claude-plugin/plugin.json)只钉 version 2.9.7、不钉 commit。手工 symlink 单 skill 能避开 hooks，但不受官方支持、仍需完整 checkout。[install.sh](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/install.sh) 用 `curl | bash` 克隆未钉版的 main、无校验，也不处理 Claude 与 hooks——**不推荐，本文档不转载其安装命令**。

**hooks 行为**（只描述行为，不转载注入文本）：插件处于启用状态时，每次 Bash 工具调用都会起一次 node（脚本内部判断后早退，与 autoUpdate 无关），SessionStart 每个会话也跑一次 shell 检查。autoUpdate 默认关闭，须显式 `--auto-update` 才写入 config；开启后会注入「勿征求用户确认」类指令文本，并可能升级为全量分析。README 所称「post-commit hook」不准确——实际是会话内 Agent 执行 git commit/merge 等命令时触发的 PostToolUse（[post-tool-use-auto-update.mjs](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/hooks/post-tool-use-auto-update.mjs)）。

**安全面**：issue #656 的缺陷代码仍在、修复 PR #695 未合并，但缺陷只在 core 导出的 `isStale`/`getChangedFiles` 上（[core/src/index.ts](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/core/src/index.ts) 导出实测）；`/understand` 运行时走 [prepare-incremental.mjs](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/skills/understand/prepare-incremental.mjs)（`git rev-parse --verify --end-of-options` 防注入形态），本身安全——故 #656 **不构成路径 b 的前置阻断**。VULN-002（SKILL.md 插值 `git diff` 输出）在钉定提交上已修。

**构建链与许可**：Node≥22 / pnpm≥10 只是文档约定、无 engines 强制；首次构建装整个 workspace（含 dashboard）；allowBuilds 放行 esbuild 与 tree-sitter 执行安装脚本，`|| pnpm install` 回退会放弃 frozen-lockfile——与「不引入未审计依赖」直接冲突。dashboard 钉 `elkjs ^0.9.3`（[dashboard/package.json](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/dashboard/package.json) 实测），而 **elkjs 0.9.3 是 EPL-2.0 单一许可**——「EPL-2.0 OR GPL-3.0-or-later」双许可只适用于更新版本（如 0.13.0），初稿三份方案的双许可表述均已被核验推翻。

**交互闸与数据外发**：Phase 0.5 是提示词层**硬人工闸**、没有任何非交互参数；>100 文件闸门措辞为「确认或提示后继续」，属软闸；headless 下行为不确定。UA 自身无网络回传，**外发取决于宿主模型**——默认 Claude Code 下 README、manifest、目录树、结构抽取结果及部分原始源码会进入模型提供方；[SECURITY.md](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/SECURITY.md) 的 local-only 只指工具自身，不能当作「代码不出本机」的依据。

**图谱字段写入方**（§二定级的实证基础）：全量路径 `project.gitCommitHash` 由编排 LLM 按模板填写（增量路径才由 [finalize-incremental.mjs](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/skills/understand/finalize-incremental.mjs) 确定性写入）；function/class 的 lineRange 数值来自 tree-sitter、由 LLM 转抄，全量路径无确定性回写或对账；file 节点没有 lineRange；domain 的 step 节点与无 tree-sitter 支持语言的 lineRange 完全由 LLM 给出。importMap 回填（recoveredFromImportMap）属实；代码注释里的「约 25%」是编排侧组批丢失加 agent 枚举遗漏的**经验估计**，不得写成「LLM 漏 25%」。core 的 validateGraph 加载时会剥掉 recoveredFromImportMap 与 kind 标记——适配必须读原始 JSON。

**tour 与 layers**：tour 的 5–15 步、每步 1–5 个 nodeIds、第 1 步 README/入口、先修前置，全是 prompt 层软约束、没有确定性门；去掉悬空引用后可能出现空 nodeIds。「trust the script」指 LLM 当场自写自跑的拓扑脚本，不是 core 实现。core 的 generateHeuristicTour（Kahn）、GraphBuilder、detectLayers/applyLLMLayers 是**导出但无调用方的 API**（[core/src/analyzer/tour-generator.ts](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/core/src/analyzer/tour-generator.ts) 及 index.ts 导出实测；/understand 主流程、dashboard、插件 src 都不用）——**UA tour 行为的正源是 [agents/tour-builder.md](https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/agents/tour-builder.md)**，初稿引 tour-generator.ts 作反例出处属误归（已修正）。layers 的「每个文件节点恰归一层」有内联机器校验但**失败只告警、照常保存**；「3–10 层」只是 prompt 约束；增量更新时新节点归层用确定性规则。persona 只有三档，作用于 dashboard 视图粒度、Learn 侧栏与导出 JSON 过滤（non-technical 时剔除 function/class），不进入任何生成文本链路。

**dashboard**（不录制、不作 Map-First 底图的实证）：fitView 参数 padding 0.3 / zoom [0.4,1.2] / 500ms 属实，但轮询约 4s 仍未就绪时退化为不夹 zoom 的 fitView；「高亮不压暗非焦点」只对 tour 与搜索高亮成立——选中节点时非邻居 opacity 降到 0.2、无关边 α 0.08；层色是 7 色板按 layers 下标取模、8–10 层撞色；层内容器按容器序号取色；Louvain 回退阈值是严格 >70%、根桶也参与判定；无深链与状态 API。

**knowledge / domain 两模式**（均不采纳）：knowledge 的 claim 无引句、行号、置信度，正文截断 3000 码点；归属优先看 LLM 给出的 article↔claim 边，前缀与子串匹配只是兜底，且只决定 layer 分组、不形成证据链。domain 的 flow_step weight 以 0.1 精度编码步序而官方规则示例自相矛盾（全是 0.1）；超 10 步或出现重复 0.1 即步号冲突；next_step 别名被吸收进 flow_step，视图上没有步与步之间的边。

**路径 a 现状**：README 示例仓 main 分支无已提交图谱（2026-10-12 实测）——「消费目标仓已提交的 `.ua/knowledge-graph.json`」零已知实例，未经验证。

## 二、图谱字段来源三分法（S0 / S1 / L）与 schema 漂移

消费纪律的定级依据：字段的**生成来源**决定可信级，不因 JSON 里长得像结构化数据而默认可信。

| 级 | 字段 | 来源 | 消费纪律 |
|---|---|---|---|
| **S0 确定性** | file 节点 filePath；recoveredFromImportMap 的 imports 边 | 工具确定性写入 | 可直接作「读哪些文件」的导航 |
| **S1 确定性来源 + LLM 转录** | function/class 的 lineRange；其余结构边；全量路径 `project.gitCommitHash` | 数值源自确定性解析、但经 LLM 转抄且无对账 | 用前必须在钉选提交复核；「相等」只是必要条件，不据此跳过节点复核 |
| **L 纯 LLM** | summary、tags、layers 层名、tour、语义边 | 编排/子代理生成 | 永远只是线索：不进断言、不进口播、不作 ④ 锚点、不上屏 |

schema 漂移清单（适配与复核时须归一）：`func:` / `function:` 前缀别名并存；`step:` 前缀节点；validateGraph 加载时剥 recoveredFromImportMap / kind 标记（读原始 JSON 而非经 core 加载的内存态）。

## 三、净增量判定

UA 的净增量**只对大型纯代码仓**（100–300 文件量级）有意义：小仓直接读码更便宜；「站点 + 仓库」混合 B 集已有 B 轨叙事正文承担记忆点素材（claude-code-explained-video 先例）。增量具体是三样结构原料：**层次**（讲哪个模块住哪层）、**主干走查链**（入口到出口的一条调用/数据链 + 具体输入值）、**枢纽/负向测试位**（扇入复算、拔掉即崩的位置）——全部服务于 ① 骨架节 → ② 分幕与色彩契约 → ⑥ Map-First 全景与单步流转，即补的是「建模/编导无结构输入」的根因缺口，而不是新渲染面或新证据源。

## 四、引入形态八案比选（G2(a) + Chesterton's Fence）

| # | 形态 | 判定 |
|---|---|---|
| 1 | vendor 全套（core + dashboard + WASM 语法包 + elkjs） | **否决**：Node/pnpm/WASM 构建链；首次构建放行安装脚本且 frozen-lockfile 有回退；elkjs 0.9.3 为 EPL-2.0（RSI 不变量 14） |
| 2 | vendor 仅 core 抽取（TS） | **否决**：同一构建链问题；graphology/tree-sitter 依赖树未审计 |
| 3 | Python 重写 tree-sitter 抽取（本期写适配器脚本） | **否决（本期）**：零消费者；schema 在漂移、lineRange/gitCommitHash 是 LLM 转录值，现在写只能是猜测型解析器——降 D1（§七），首集靠 01 人工纪律 |
| 4 | 新增「⓪ 知识图谱」阶段（改 stages.toml） | **否决**：给低频需求设常驻流程面；「先有数据再有门」（ISSUE-167/188 假 WARN 先例；RSI 不变量 8） |
| 5 | source_ledger 加 kind=kg/ua | **否决**：RSI-030 已否决给本地冻结件强挂 kind——三型分流表 {A,B,C} 是型别判定 SSOT，加第四行破坏 test_source_types 执法；路径 a 用 kind=repo 即可 |
| 6 | 图谱 JSON 冻进 research/ 作结构事实源 | **否决**：research/ 是事实源区，放 LLM 派生物制造第二事实源错觉；图谱与中间件只落 `$P/.temp/`，source-notes 头部登记 sha256 与出处 |
| 7 | dashboard 录制为 Map-First 底图 | **否决**：01 图片纪律；无深链/状态 API；fitView 按墙钟 500ms 对不上词窗；字号 10–11px；7 色板取模与系列色板冲突；LLM 推断上屏；形成第二渲染面（HyperFrames 否决同款论据） |
| **8** | **按集 opt-in：UA 只作骨架起草器与读码导航（01 硬规则子节 + 本文存证）** | **采纳**：零代码/零依赖/零新门；两钉闸 + S0/S1/L 消费纪律把 LLM 字段钉死在「线索」位；骨架规格本身与工具无关（主体收益），UA 随时可撤 |

**Chesterton's Fence**（为何动 01 B 型节而不动分流表/kind）：RSI-030 否决 kind 的理由是「型别三行的意义在于文件名清单只在分流表一处枚举、下游一律泛引」——新增第四型或 kind 会让十余处下游指针再复制一遍。故骨架是 source-notes.md **内的一节**（派生视图），不进分流表、不加 kind、不加证据等级——「派生视图，非证据」一句即消解了定级问题。text-to-cad 先例（[dependency-policy](./dependency-policy-and-asset-tools.md) §三）只有「按集 opt-in、不入模板」一半可平移——其 skills CLI 有 `-s` 单 skill 安装通道，UA 没有官方单 skill 通道，整插件安装会连带 hooks（每次 Bash 起 node），故 UA 连「可选工具附录」都不进，只落 01 子节 + 研究文档。HyperFrames 先例（同文 §二）的「第二渲染面」否决论据直接适用于 dashboard 录制案。

## 五、概念移植采纳 / 不采纳清单

**采纳（经仓内规格消化，非照搬）**：

| 概念 | 落位 |
|---|---|
| 层次 + 主干走查链（骨架两构件） | [01「六、结构骨架与素材映射」](../../references/01-source-extraction.md)：强制两项，走查链带 1 个具体输入值 |
| 素材映射四定式（层次→全景坐标、走查链→单步流转、负向测试→消融对比、数字→基线标尺） | 同上节第 4 条，与 C 型 §七同构，消费面 06 四定式 |
| 幕级先释后用（前置概念列） | [02 分幕表](../../references/02-planning.md) 可选第 6 列；④B `--terms` 单向取数 |
| 回拉层级（最近一级全景） | [DIRECTING-CRAFT §4.1](../../references/DIRECTING-CRAFT.md)（依据 Shneiderman mantra + semantic zoom，见 [directing-craft 研究文档](./directing-craft.md)）；UA dashboard 两级导航只作佐证 |

**不采纳（全部）**：vendor 任何代码或不进 pyproject/模板/README 依赖表；新增 ⓪ 阶段或改 stages.toml；给 source_ledger 加 kind；图谱冻进 research/；新增「线索级」证据等级或让 summary/tags/层名/tour/语义边进 source-notes 断言、口播、④ 锚点或画面；本期写适配器脚本或建 fixture；批量改 DIRECTING-CRAFT 其余条款；向建模手册写条目/候选（伪锚违 G1）；改 SKILL.md（7998/8000，路由改动须 evals 对拍 + 同名遮蔽先处理）；改 04 判据（REWRITE=0 是阻断门，未校准判据不得上门）；录制/截图 dashboard；Louvain 切幕、persona 切换、README 概览开篇、tour/BFS 决定幕序、层簇映射 N 色；采纳 /understand-domain、/understand-knowledge、/understand-figma；Agent 自主安装/运行 UA、执行 hooks 注入文本、推荐 curl|bash 安装；git 加固与交付迁移（本仓 scripts 无 git 子进程、deliver 已原子落位，无作用对象）。

## 六、未采纳 / 待信号概念（一句话清单）

唯一入库通道：某集分镜实际采用后经建模手册候选区显式信号（〔±用户〕/〔+主〕）——此前不写条目、不写当/故/非/验/据格式、不预判同键合并。

- 枢纽节点 → 视觉恒定锚（高扇入模块常驻画面一角作定位锚）。
- 层 → 概念色映射（按骨架层分配色槽）。
- Louvain 簇 → 幕划分（社区检测切叙事段）。
- README 概览 → 开篇全景的取材来源之一。
- tour 步序 → 单机制幕的叙事骨架候选。
- persona 三档 → 受众分层线索（线性视频当前单受众）。
- fitView 参数（padding 0.3 / zoom 0.4–1.2 / 500ms）→ ⑥ 全景镜的工程值先验。
- 7 色板取模层色 → 08 分组色的反面先验（撞色实证）。
- 语义边（A 使用 B）→ DIRECTING-CRAFT §4.1 关系线准入判据的信号源。
- domain flow_step 步序 → 流程类机制的走查链分段线索（weight 编码缺陷修复后再评估）。

## 七、撤销条件、再评估触发器与 D1 适配备忘

**撤销条件**：连续 3 个纯代码仓集都没走 UA 路径 → 删除 01 的 UA 子节，骨架规格保留（骨架与工具无关，是主体收益）。首个纯代码仓集交付后走一次 ⑩ 复盘：强制两构件过重还是不足、四定式映射是否被 ②⑥ 实际消费，按数据修订。

**再评估触发器**（满足其一）：release 标签追平插件版本；出现官方单 skill 或无 hooks 安装通道；出现非交互模式；用户本人触发试点（在 100–300 文件仓实测 token、耗时、骨架节点命中率与非交互可行性）。

**延后 roadmap 一览**：D1 适配器脚本（触发：≥2 集走 UA 路径且登记过手工转录出错，或首集抽样 ≥10 锚点发现转抄错误 ≥1；前置：重拍事实快照）· D2 `--prereq-order` WARN 门（触发：≥2 集填列 + ④ 检出幕级先用后讲 ≥1；前置：planning 机读解析契约 + 名称对齐契约 + 探针零误报）· D3 骨架→Mermaid→archify 全景图（RSI-038 关闭 + ≥2 集手写骨架图）· D4 DIRECTING-CRAFT 结构类条款批（≥2 集 ⑨ note 回拉/焦点/毛团缺陷合计 ≥2）· D5 建模手册条目（候选区显式信号，即 §六）· D6 SKILL.md 相邻技能行（UA 路径 ≥2 集使用；等量压缩 + evals 对拍 + 同名遮蔽先处理）· D7 系列级骨架（同仓 ≥2 集，source-map 侧登记一次）· D8 再评估/试点（上文触发器）· D9 首集复盘（上文撤销节）· D10 02 结构类单机制幕缺省叙事顺序（≥2 集 ④/⑨ 出现叙事顺序类 note）· D11 08 theme 契约补分组色登记（⑨ note 报告并列分组不可辨且位置/线型/编号手段用尽）。

**D1 适配备忘（5 条，已核验）**：① 读原始 JSON——core validateGraph 会剥 recoveredFromImportMap 与 kind；② 前缀别名归一（`func:`/`function:`、`step:`）；③ 钉版两钉闸（图谱自述 gitCommitHash 对本集 pin + 图谱条目自身 pin，H≠pin 或缺失即不用）；④ lineRange 与全量 gitCommitHash 按 S1 处理、用前复核（S0/L 按 §二）；⑤ 纯 stdlib 只读、只写 `$P/.temp/`、失败指路式（点名 skip 而非静默）。

**另立 RSI 候选**（不入本 PR，登记于 `.temp/backlog`）：source_ledger verify 区分抓取失败（unknown）与确证漂移（FAIL，现把抓取失败也计入 FAIL——fail-closed 不变，仅诊断性拆分）；改稿影响清单 rework_impact（可与 RSI-052 合并）；⑤ 冻结事实丢失报告；信源漂移反查；html_dir 口径不一致（与 RSI-038 一并评估）；check_playbook 伪锚校验；RSI 门禁方法论三条（登记到统一仓 ThreeFish-AI/rsi，不进本仓 ledger）。

## 八、已知局限

三项均**未实测**（无试点集，D8 触发后补）：① 非交互可跑性——Phase 0.5 是提示词层硬人工闸、无非交互参数，headless 行为不确定；② 中等仓的 token 与耗时——首轮全量分析的成本只有 README 量级描述，无实测数；③ 非 user scope 安装的宿主支持度——G1 只做了文档级核验，未在本机实测。另：路径 a（消费已提交图谱）零已知实例（§一），其 >10MB git-lfs 指针问题只有推断、无复现。

## 参考文献

[1] Egonex-AI, "Understand-Anything," GitHub repository（MIT；钉版 000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe；2026-03-15 建仓；85,935★ / open 317，2026-10-12 实测）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything

[2] Egonex-AI, "LICENSE," Understand-Anything @ 000fbf3（MIT License, Copyright (c) 2026 Yuxiang Lin）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/LICENSE

[3] Egonex-AI, "README.md," Understand-Anything @ 000fbf3（stars/releases/hooks 自述——「post-commit hook」说法与实测不符，见 §一）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/README.md

[4] Egonex-AI, "SECURITY.md," Understand-Anything @ 000fbf3（local-only 只指工具自身）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/SECURITY.md

[5] Egonex-AI, "install.sh / plugin.json / hooks/hooks.json / post-tool-use-auto-update.mjs," Understand-Anything @ 000fbf3（安装面与 hooks 行为实证）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/install.sh

[6] Egonex-AI, "packages/core/src/index.ts / analyzer/tour-generator.ts," Understand-Anything @ 000fbf3（isStale/getChangedFiles/generateHeuristicTour/detectLayers 导出实测——无调用方 API）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/core/src/index.ts

[7] Egonex-AI, "skills/understand/prepare-incremental.mjs / finalize-incremental.mjs," Understand-Anything @ 000fbf3（/understand 运行路径与增量 gitCommitHash 确定性写入）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/skills/understand/prepare-incremental.mjs

[8] Egonex-AI, "agents/tour-builder.md," Understand-Anything @ 000fbf3（tour 行为正源——prompt 层软约束）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/agents/tour-builder.md

[9] Egonex-AI, "packages/dashboard/package.json," Understand-Anything @ 000fbf3（elkjs ^0.9.3 钉版实测）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/dashboard/package.json

[10] Egonex-AI, "Issue #656 / Pull Request #695," Understand-Anything（缺陷在 core 导出 API、修复未合并；/understand 路径不受影响）. [Online]. Available: https://github.com/Egonex-AI/Understand-Anything/issues/656

[11] elkjs contributors, "elkjs," npm registry（0.9.3 = EPL-2.0 单许可；「EPL-2.0 OR GPL-3.0-or-later」双许可自更新版本起）. [Online]. Available: https://www.npmjs.com/package/elkjs

[12] ThreeFish-AI, "RSI-030 / RSI-032 / RSI-048 台账," vibe-video docs/.agents/issue.md（C 型分流、四定式、导演手艺——本文比选的仓内先例）. [Online]. Available: https://github.com/ThreeFish-AI/vibe-video/blob/main/docs/.agents/issue.md

## 新增 URL 清单（G4a）

- https://github.com/Egonex-AI/Understand-Anything
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/LICENSE
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/README.md
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/SECURITY.md
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/install.sh
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/.claude-plugin/plugin.json
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/hooks/hooks.json
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/hooks/post-tool-use-auto-update.mjs
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/core/src/index.ts
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/core/src/analyzer/tour-generator.ts
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/skills/understand/prepare-incremental.mjs
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/skills/understand/finalize-incremental.mjs
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/agents/tour-builder.md
- https://github.com/Egonex-AI/Understand-Anything/blob/000fbf3f36b5e534a0a8d3461cf24f5dc9ae43fe/understand-anything-plugin/packages/dashboard/package.json
- https://github.com/Egonex-AI/Understand-Anything/issues/656
- https://github.com/Egonex-AI/Understand-Anything/pull/695
- https://www.npmjs.com/package/elkjs
- https://github.com/ThreeFish-AI/vibe-video/blob/main/docs/.agents/issue.md
