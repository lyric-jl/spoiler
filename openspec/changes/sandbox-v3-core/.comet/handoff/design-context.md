# Comet Design Handoff

- Change: sandbox-v3-core
- Phase: design
- Mode: compact
- Context hash: c99b63fcfec25af5d882c817aaba43dacfbada2d7c35b9a6052bd54958a8e322

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/sandbox-v3-core/proposal.md

- Source: openspec/changes/sandbox-v3-core/proposal.md
- Lines: 1-40
- SHA256: 529df0ce6f0eafed02d6478546a2c15a00ae2df8ec2ee59e37246b1739e09509

```md
# Proposal: sandbox-v3-core

## Why

relate_mvp（`fitsandbox/relate_mvp`）已验证 RELATE-Sim 受控选项制职场迁移全链可行——受控选项决策、换序三问取多数票、差量状态灯、SM 信息防火墙、理由审计员（含心口缝）、5-run 聚合、操作台直播，全部 live 验收（作者 2026-06-07 过目"可行"）。但 MVP 是冲刺产物：零测试、单包平铺、双人引擎写死、人设手写、JD 只暂存不喂引擎、场景库 12 条手写。**作者拍定（2026-06-07）：v3＝比赛主体（截止 06-14），在新仓 `D:\aidasai\sandbox-v3` 做正式实现。**

## What Changes

- 八大机制从 relate_mvp **行为等价迁移**进模块化新仓（受控选项推演 / 换序三问 / 差量灯 / 防火墙 / 审计+心口缝 / 时间线台账 / 5-run 聚合 / 操作台三代前端）
- **工程化底座**：测试套件（MVP 现状零测试）、模块边界、配置化
- **引擎扩多人**：同事从 NPC 布景变真 agent（N-agent 注册表，network 灯按关系对拆分方向待设计）
- **蒸馏器**：智联材料包（简历/测评/面试官评价/背调）→ 两段式蒸馏 → 角色卡一键导入（数据可插拔闭环）
- **JD 喂引擎**：JD 从"只暂存"变为进入场景初始化与蒸馏上下文
- **场景库扩充**：12 条手写场景扩充 + 共创入库持久化（MVP 现状重启即丢）
- 诚实工程红线全部延续（见 design.md），**无 BREAKING**（新仓全新实现，不动 fitsandbox）

## Capabilities

### New Capabilities

- `rollout-engine`: 受控选项推演核心——SM 五件循环（搭景/推进出选项/收场/后果结算/挑下一幕）、回合制节骨眼、换序三问取多数票、差量式八状态灯、台账时间线
- `info-firewall`: 信息防火墙——台账在场者隔离、agent 只见亲历、SM 泄密硬约束（放行剧本设定的公开信息）
- `reason-audit`: 理由审计员——四查（手册/内心/事实/知情范围）+ 心口缝记录（只记录不判旗）
- `multi-agent-cast`: 多人引擎——N-agent 注册表、SM 从集合选行动方、同事真 agent 化
- `persona-distill`: 蒸馏器——材料包两段式蒸馏（证据链小结→融合人设+if→then 手册），三纪律（evidence or silence / 视角分歧不调和 / 矛盾标记不抹平）
- `jd-context`: JD 进引擎——场景初始化与蒸馏的岗位上下文
- `scene-bank`: 场景库——预设库、共创结晶、自定义持久化
- `run-aggregation`: 5-run 聚合——并发批跑、倾向分布聚合（承诺轨迹/灯众数/拉扯度/心口缝分布）、分叉如实标注
- `console`: 操作台——server 直播、放映厅舞台（选项连线/一句话心理/状态灯/聚合视图）、档案页与回放器

### Modified Capabilities

（无——新仓首个 change，无既有 spec）

## Impact

- 全新仓 `D:\aidasai\sandbox-v3`（独立 git 仓），不影响 `fitsandbox`（relate_mvp 保持原样作为已验证蓝本与回退底）
- 依赖：Python 3.x stdlib + DeepSeek API（`DEEPSEEK_API_KEY`），延续零第三方依赖
- 比赛计划书重写需对准 v3（属文档工作，不在本 change 内，另行处理）
- **进度风险（据实）**：距截止 7 天内完成 build＋验收＋演示打磨，风险高；tasks 按 P0→P3 分层，任何时点砍尾不砍头，P0 完成即有可演示底座
```

## openspec/changes/sandbox-v3-core/design.md

- Source: openspec/changes/sandbox-v3-core/design.md
- Lines: 1-47
- SHA256: 18480efb07b04926997a618dc628dd212bfcc3b3d891725de58bcac10841a268

```md
# Design: sandbox-v3-core（高层）

> 本文件是开启阶段的高层方向盘；逐项细化（含 delta spec 与技术 RFC）在深度设计阶段产出。

## Context

- 蓝本＝`fitsandbox/relate_mvp`（十轮提交、全链 live 验收）：单包平铺 13 个模块，行为已验证但工程形态是 MVP。
- v3＝比赛主体（截止 06-14），同时是正式产品底座——"机制已证明，现在把房子盖正"。
- 关键资产可直接搬运：prompt 全文（含整改与红线措辞）、12 条场景库、八状态枚举、验收方法（位置偏置体检 / 防火墙对抗局 / 泄漏检查脚本）。

## Goals / Non-Goals

**Goals:**
- 八大机制行为等价迁移，且每个机制有测试守门（MVP 零测试 → v3 测试套件）
- 多人引擎：同事真 agent 化（demo 至少三人局立住）
- 蒸馏器 + JD：数据可插拔闭环（"从简历到 agent 一键，引擎一行不改"）
- 场景库扩充与持久化
- 操作台直播体验不回退（MVP 已拍定的前端形态为基线）

**Non-Goals:**
- 旧轨对话式引擎不迁移（fitsandbox 主包是存货，不动）
- 不做部署/多租户/账号体系/移动端
- 计划书重写不在本 change（文档工作另行处理）
- 不追求论文评测闭环（论文 64.4% 那套对账实验不复刻）

## Decisions（高层拍定 + 待深度设计的问题）

**已定方向：**
1. **技术栈延续**：Python 3.x stdlib、DeepSeek API、零第三方依赖、操作台 stdlib http.server——MVP 全套验证过，不换。
2. **模块化分层**（对应 9 个 capability）：engine 核心与 firewall/audit/aggregation 拆开，console 与引擎经事件流（emit 回调）解耦——MVP 的 emit 协议已验证，保留为引擎-前端契约。
3. **多人引擎方向**（沿用已拍备忘）：PERSONAS 注册表化（N 个 agent）；SM 从集合选行动方；调用量随行动方数线性涨；先三人局验证机制再扩。
4. **蒸馏器配方**（照论文 §5.2 两段式）：材料映射＝简历→self、测评→ersi、面试官评价→rpd/ctss（他人视角）、背调→sfn；三纪律进 prompt。
5. **诚实工程红线全部延续**：live-only 运行时无 mock 回退、错误亮到页面不许吞；落差只描述不打分；承诺未经对账校准不构成预测（脚注不许丢）；审计员只标记不改判；心口缝只记录不判旗；选项洗牌+换序三问留全量对账账目。

**待深度设计的问题（brainstorming 议题）：**
- 测试与 live-only 的边界口径：运行时禁 mock 是红线，但测试需要确定性——拟走"依赖注入假 LLM 只进测试"，边界措辞要钉死（"测试 fake ≠ 运行时 mock 冒充"）
- network 灯多人化：拆按关系对（候选人×每同事）还是保留单灯+聚合，调用成本与盘面可读性的取舍
- 多人局的防火墙：知情范围在 N 人下的台账结构（witnesses 已有，N 人共谋/私聊场景怎么记）
- 蒸馏器输出与多人引擎角色卡 schema 的统一
- 场景库持久化格式与共创结晶的去重
- 八大机制"行为等价"的验收定义（拿 relate_mvp 同 seed 对照？trace schema 兼容到什么程度）

## Risks / Trade-offs

- **时间**：7 天内 build＋验收＋演示打磨。对策：tasks 按 P0（机制平移+工程化）→ P1（多人）→ P2（蒸馏器+JD）→ P3（场景库）分层，每层独立可演示，砍尾不砍头；relate_mvp 始终是可回退的参赛底。
- **重写回归**：已立住的验收（位置偏置 29%、防火墙 0 泄漏）在 v3 必须重做，不得引用旧仓数据冒充新仓验收。
- **范围膨胀**：四个扩展全选+7 天＝高压；深度设计阶段如发现单 change 装不下，按 comet 规矩拆新 change，不硬塞。
```

## openspec/changes/sandbox-v3-core/tasks.md

- Source: openspec/changes/sandbox-v3-core/tasks.md
- Lines: 1-52
- SHA256: 5643504386e95975c4ce51a5acc7525ce890366b202c2a0c5af4b8877417ee89

```md
# Tasks: sandbox-v3-core

> 分层纪律：P0 → P3 顺序执行，任何时点砍尾不砍头；每层收尾时该层验收过、可独立演示。
> 细化的实施计划（含代码级步骤）由 build 阶段按 Design Doc 产出，本清单是 WHAT 级账目。

## 1. P0 · 机制平移 + 工程化底座

- [ ] 1.1 新仓骨架：包结构、配置、README、.gitignore、UTF-8 纪律
- [ ] 1.2 LLM 客户端迁移（live-only、重试后大声抛错）+ 测试用假 LLM 注入边界（按深度设计拍的口径）
- [ ] 1.3 八状态灯 + 差量应用（apply_state_deltas 行为等价）+ 测试
- [ ] 1.4 推演引擎核心：SM 五件循环 + 回合制 + 换序三问取多数票 + 时间线台账 + 测试
- [ ] 1.5 信息防火墙：witnesses 隔离 + SM 硬约束 + 测试（含对抗局脚本化）
- [ ] 1.6 理由审计员：四查 + 心口缝（只记录不判旗）+ 测试
- [ ] 1.7 场景库基础：12 条预设迁移 + 持久化格式
- [ ] 1.8 trace 落盘 + 台本渲染 + 单跑入口（run 一局全链冒烟绿）
- [ ] 1.9 P0 验收：行为等价对照（同 seed 结构对照 relate_mvp）+ 位置偏置体检 + 防火墙泄漏检查在新仓重做

## 2. P0 · 操作台与聚合（演示底座）

- [ ] 2.1 事件流协议（emit 契约）迁移 + server 路由
- [ ] 2.2 操作台页面：舞台/选项连线/表决条/一句话心理/状态灯/判断流（以 MVP 拍定形态为基线）
- [ ] 2.3 5-run 聚合：并发批跑 + 聚合产物 + 操作台聚合视图
- [ ] 2.4 档案页 + 回放器迁移（三代前端共存）
- [ ] 2.5 P0 演示验收：live 全链直播一局 + 聚合面板出数 + 诚实脚注逐条在页

## 3. P1 · 多人引擎

- [ ] 3.1 PERSONAS 注册表化（N-agent），SM 从集合选行动方
- [ ] 3.2 network 灯多人口径落地（按深度设计拍的方案）
- [ ] 3.3 多人防火墙：N 人知情范围 + witnesses 扩展 + 对抗验证
- [ ] 3.4 操作台多人呈现：真 agent 头像/内心/行动方金圈（替换 NPC 布景占位）
- [ ] 3.5 P1 验收：三人局 live 立住（同事真 agent 做真决策，审计/灯/聚合全链兼容）

## 4. P2 · 蒸馏器 + JD

- [ ] 4.1 合成材料包测例（简历/测评/面试官评价/背调，作者过目）
- [ ] 4.2 两段式蒸馏管线（证据链小结→融合）+ 三纪律 prompt + 测试
- [ ] 4.3 角色卡 schema 统一（蒸馏产物=导入插口=多人注册表同一张卡）
- [ ] 4.4 JD 进引擎：场景初始化上下文 + 蒸馏上下文（告别"只暂存"）
- [ ] 4.5 P2 验收：材料包→蒸馏→导入→跑局，行为可辨认地顺材料证据；"一键、引擎一行不改"话术成立

## 5. P3 · 场景库扩充

- [ ] 5.1 场景共创入库持久化（重启不丢）
- [ ] 5.2 场景库扩充（手写补充 + 共创产出，目标量深度设计定）
- [ ] 5.3 P3 验收：新场景全链跑通 + 库管理（增/查/去重）可用

## 6. 收尾

- [ ] 6.1 全量回归：测试套件全绿 + live 标杆局
- [ ] 6.2 演示打磨：操作台一镜到底走一遍
- [ ] 6.3 交接文档：README/运行手册/已知边界（据实）
```

