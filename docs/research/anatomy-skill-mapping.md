# Anatomy ↔ vibe-video 机制映射报告

> 声明：只分析不改码；锚点均经实际代码核验（`grep -n` 实测，钉版仓库 [anatomy-skill 精读](./anatomy-skill.md) §参考 [1]，本仓为当前工作分支）。评估协议循 [I-068 先例](./opus5-video-techniques.md)：钉版取证（`bc943e4`，2026-10-15）→ 许可核实（MIT，文本可带署名引用）→ 净增量判定 → 引入形态比选。

## 结论先行

**两仓在「单一事实源 + 机器门执法 + 失败驱动沉淀」三层高度同构，10 条映射中 7 条已对齐（多数形态不同、强度不输）**；唯一干净的净增量——**规模/成本门控行为学**——**已在本分支落进 02 规格与 ② gate**（草集/正集/大集三档 + 大集拒启给替代 + 超时上报）；其余 2 条（M7/M8）弱增量并入既有实践、4 条暂缓项登记在 [ledger I-071](../.agents/issue.md) 暂缓跟踪表（Skill 工程文件只放已落地规格）。Anatomy 的真正强项（等距几何审计的射线深度证明、墨量单调验收）依赖其「形状可登记、投影可解析」的技术前提，对 Remotion 像素级渲染管线**不构成可迁移机制**，其精神（判据数值化、归零放行）本仓已在 `--check` 系判据与对比度门中实践。学习方法论层面的收获已沉淀进[精读笔记](./anatomy-skill.md)。

## 映射总表

| # | 材料机制（出处） | 本仓对应 | 锚点 | 判定 |
| :--- | :--- | :--- | :--- | :--- |
| M1 | 单句核心锚 + 失败模式↔治愈对（SKILL.md「The object is the explanation」+ too abstract/too flat） | 16 条不变量清单 + 30 条反模式表（忌/因/验三字段） | [RSI.md](../../RSI.md) §九（16 条）；[DIRECTING-CRAFT.md:195](../../references/DIRECTING-CRAFT.md) | ✅已对齐（形态不同：清单锚 vs 单句锚） |
| M2 | 规模三档 + Epic 拒启给替代 + 首小时可用页 + 每步 date 遥测超两倍上报（SKILL.md 工作流第 1 步） | 原：无规模档位（评估时 `grep 规模\|档位 SKILL.md 02-planning.md` 零命中）→ **本分支已落地**：② 新增「成本档位与开工门」节（草集/正集/大集 + 大集拒启给替代 + 超时上报） | [02-planning.md](../../references/02-planning.md) 成本档位节；[stages.toml:43](../../references/stages.toml) gate；SKILL.md 速查表 ② 行 | ✅已落地（本分支） |
| M3 | 构造性同源：纯函数模型喂全部输出；audit 与页面同读一份弹簧数据；`needleAt.toString()` 同函数喂静态/动态（kit.md §12、craft.md「Count what you draw」） | 逐字稿单一事实源；`timing.json` 双语言镜像「结构性不存在漂移」；storyboard SSOT | [03-narration.md:3](../../references/03-narration.md)；[PIPELINE.md:216](../../references/PIPELINE.md) | ✅已对齐（timing.json 即本仓的 rig.ts） |
| M4 | 渲染前置 audit-to-zero：11 类具名几何失败线全零放行；修几何不修键偏置（kit/audit.mjs） | 前置静态检查已有：`check --check-scenes` 分镜↔代码互比、`tsc --noEmit` + 七条渲染红线；事后 `qa --check` 数值门 + 目检 | [stages.toml:81,101,110](../../references/stages.toml)；[09-render-qa.md:58](../../references/09-render-qa.md) | ✅已对齐（判据数值化同族，残余增量见暂缓 ①） |
| M5 | 验证工具箱：4× 裁切每接点、双主题、contact sheet、逐 PNG 阅读、墨量单调实测（verify.md / webgl.md §8） | 多抽样器抽帧 QA、A/B 对拍回归、`--check-theme` 对比度门、人工目检清单、分幕音画复检 | [09-render-qa.md:5,119](../../references/09-render-qa.md) | ✅已对齐 |
| M6 | 范例即规格：八个完整范例随 skill 发行、开工先开最近范例、CI 强制重建 byte-identical | golden-episode 黄金集回归 + frozen skeleton 指纹钉住（I1/I2 双不变量）；规格文档（references/NN）承担锚定职能 | [verify_skeleton.py:16](../../scripts/verify_skeleton.py)；`tests/fixtures/golden-episode/` | ✅已对齐（规格锚 vs 范例锚；本仓确定性渲染纪律同族且更严） |
| M7 | skill 自带 evals：5 题，expected_output 含过程证据（audit passed、4× crop 已读） | output + trigger 双评测集，expected_output 全程门禁化（REWRITE=0、check 零 FAIL、独立子代理评审、增量缓存断言） | [evals/evals.json:7,24](../../evals/evals.json)；`evals/trigger-evals.json` | ✅已对齐且更厚 |
| M8 | 检查器自检：每条审计线配植入故障件自证（3d.md §13 plants） | 合成坏帧/冻帧负例测试 + 真实事故固化测试（I-041 豁免边界负例、I-020 纯黑段跨帧判据） | [test_qa_checks.py:73,131,200,409](../../tests/test_qa_checks.py) | ✅已对齐（突变测试同族） |
| M9 | 工艺审美数字化：倒角 0.4–1.6、填充 55–65%、390px 可读、管线 1.5 半径净空（craft.md） | 字幕单行宽度门（I-024）、术语密度预算机器面、时长预算窗、对比度门、手册水位滞回（HIGH=2700/CAP=3000） | [04-verification.md:28](../../references/04-verification.md)；[check_playbook.py:36](../../scripts/check_playbook.py) | ✅已对齐 |
| M10 | 发布伦理与零依赖：publish 仅用户点名、绝不代推；kit 仅 Node 内建（publish.md） | 永不推 main/不 merge/不 force-push 硬禁令；TTS 跨仓委托门（禁内联副本）；依赖策略专节 | [RSI.md](../../RSI.md) §六（硬禁令正文住统一协议 §7）；[PIPELINE.md](../../references/PIPELINE.md) 依赖策略节 | ✅已对齐 |

## 逐条说明（差异与建议，仅展开有实质差异者）

### M2 规模/成本门控行为学（唯一净增量，已落地）

**材料怎么做**：三档在动笔前声明——Figure（40–80 部件）免问直做且不报时间（实测常快于预估，1.1.0 版据此删掉该档报价）；Hero（80–150）先报「2–4 小时」再做；Epic（6 小时起）**拒绝启动**：给估价、提出保留核心的 Hero 替代、列明完整版增量，用户显式选择才做。执行中每步 `date` 记时，超两倍份额上报；任意档首小时必有可用页。

**本仓现状**：集子规模由 scaffold 时的 `pipeline.toml` 时长预算窗承载（[evals/evals.json](../../evals/evals.json) id1 断言「预算窗约 3 分钟」），但**没有档位语义与拒启行为**——双语版、IndexTTS 终声、复杂多系统动画这类「Epic 组合」开工时用户得不到成本预告与替代方案；唯一成本门在 TTS 侧（IndexTTS 显式授权 + ETA 排期，[stages.toml:90](../../references/stages.toml)、[issue.md:626](../.agents/issue.md) I-040/047）。时间遥测无全流程机制（IndexTTS 的 ETA 排期是孤例）。

**差异本质**：Anatomy 把「成本档位」当作第一道工序的门，本仓把它当作配置参数。对一次性成本数十分钟到数小时、且含 TTS/渲染重阶段的视频流水线，拒启行为学的价值不亚于图解场景。

**落地（本分支已完成）**：[02-planning.md](../../references/02-planning.md) 新增「成本档位与开工门（planning.md 头部声明）」节——planning.md 第一行声明档位（六节结构不动）；草集免问不报时、正集开工报成本量级、大集（两项及以上高成本要素：双语渲染/多系统复杂动画/整季首发/超长预算窗）不启动给替代；IndexTTS 不入档位判据（与 I-040 授权硬闸正交）。配套：[stages.toml](../../references/stages.toml) ② gate 与 SKILL.md 速查表同步增「档位声明」（test_stages 同源执法自动覆盖）、scaffold 提示语同步、「超两倍上报」纪律条款入 02、walking-skeleton 等价（内容层文档先行）显式化。

### M4/M5/M8 的残余差异（合并说明）

Anatomy 的 11 类失败线是一套**完备枚举的几何不变量**（穿透/端点/悬空/折返/自交/挤压/替身/支撑/抖动/鞍座/深度），本仓 `--check` 判据是逐 Issue 生长的清单（黑帧/早渐黑/字幕带侵入/纯底色/冻帧/对比度）。两者同族但生长方向相反：枚举式 vs 验尸式。本仓验尸式已有 I-041 型负例加固，枚举式的收益（系统性查缺）暂无实例支撑——列为暂缓 ①。墨量单调验收（审美判据数值化）本仓同族实践是 `--check-theme` 对比度门与水位滞回，无缺口。

### M3 的对照细节（无增量，记录对照价值）

Anatomy 防漂移的三个具体形态值得对照自检：① audit 与页面共享同一份弹簧常量数据（「审计回放的就是观众看到的」）；② 静态图与动态页共用同一函数字面量（`toString()` 内联）；③ 读数取实况不取目标。本仓对应物：`timing.json` 双语言同读（[PIPELINE.md:216](../../references/PIPELINE.md)）覆盖 ①② 精神；③ 的对应陷阱（相位词与数值取自不同瞬间）在 TTS→字幕→beat 帧位链路上由 manifest 绝对时间轴承载——链路完备，无缺口。

## 落地建议汇总

- **做**（✅ 已完成，本分支）：规模档位声明与 Epic 拒启行为学已落 [02-planning.md](../../references/02-planning.md)「成本档位与开工门」节 + [stages.toml](../../references/stages.toml) ② gate「档位声明」+ SKILL.md 速查表同步 + scaffold 提示语同步；与「时长预算窗」正交（预算窗管内容长度、档位管制作成本；档位仅以窗长为成本信号，不改写窗口设定）。暂缓项不进 Skill 工程文件，统一住 [ledger I-071](../.agents/issue.md) 暂缓跟踪表。
- **写**（一句话成本级）：无——原拟的「evals 预期输出补过程证据」经核验本仓已具备（[evals/evals.json:7](../../evals/evals.json)），撤销。
- **暂缓**（各带触发条件；跟踪唯一处为 [ledger I-071](../.agents/issue.md) 暂缓跟踪表 W1–W4）：
  1. **失败类目完备枚举**（qa 判据从验尸式补枚举式清单）——触发：`--check` 判据再次漏抓新缺陷类别（届时按漏抓类别补具名判据 + 负例测试，与 I-020/041 同法）；
  2. **单句核心锚**——触发：SKILL.md 下次结构性改版时顺手评估（16 条不变量清单当前已承担同等职能）；
  3. **全流程时间遥测**（每阶段 `date`/超限上报）——触发：出现一次长阶段失控实例（IndexTTS ETA 已覆盖最贵单段）；
  4. **Anatomy 产页作视觉素材源**（等距机器图解页 → 录屏进片）——触发：用户点名要做等距机器图解类集子；属内容源扩展非机制引入，届时另走信源取证协议。

## 交叉引用

- [Anatomy Skill 精读与通俗拆解](./anatomy-skill.md)（机制详解、实测数字与动手实验室）
- [opus5-video-techniques.md](./opus5-video-techniques.md)（I-068 五仓评估——外部借鉴四步协议先例与待信号清单范式）
- [RSI.md](../../RSI.md)（G0–G4 门禁；评估类条目登记与派发协议）
