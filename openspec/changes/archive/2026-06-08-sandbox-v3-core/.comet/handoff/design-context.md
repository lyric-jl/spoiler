# Comet Design Handoff

- Change: sandbox-v3-core
- Phase: design
- Mode: compact
- Context hash: 49f86f788769b2c507ad690a8e5142af40c63c930ef3858aa334603f1f067976

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
- SHA256: ff172f6b207737072617813d3c2d9885dec67b63c38633c882404ec097d1c969

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
- [ ] 5.2 场景库扩充（手写补充 + 共创产出，目标量执行时与作者定）
- [ ] 5.3 P3 验收：新场景全链跑通 + 库管理（增/查/去重）可用

## 6. 收尾

- [ ] 6.1 全量回归：测试套件全绿 + live 标杆局
- [ ] 6.2 演示打磨：操作台一镜到底走一遍
- [ ] 6.3 交接文档：README/运行手册/已知边界（据实）
```

## openspec/changes/sandbox-v3-core/specs/console/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/console/spec.md
- Lines: 1-45
- SHA256: f4e18e430fe83604fc012e2e297d57cdc81e99c7ebe158faf9e154db335b617b

```md
# console — 操作台与三代前端

## ADDED Requirements

### Requirement: server 直播
操作台 SHALL 为本地 server（stdlib，零第三方依赖）：页面→服务→引擎→LLM 全链真跑；前端轮询事件流增量渲染；事件类型沿用蓝本协议（run_started/status/scene_open/beat_open/inner/decision/audit/settle/consequence/next_tp/done/saved/error）。

#### Scenario: 直播一局
- **WHEN** 选场景点开拍
- **THEN** 页面随事件流逐步呈现推演全程，跑中再点开拍被拒（409 语义）

### Requirement: 舞台呈现基线
舞台 SHALL 以蓝本拍定形态为基线：行动方金圈、中央选项卡（呈现序已洗牌标注）、换序三问表决条+选项得票点、选中项金线连线、理由黄框、候选人头像下一句话心理（点开全文）、状态灯表（变化标红）、幕回合历史（黄旗⚑）、简要判断流（含信息越权红标、心口缝金标）、收场卡（时间戳+在场知情者）。多人化时名单上的真 agent 均可为行动方并可点开内心。

#### Scenario: 表决可视化
- **WHEN** 任意回合决策完成
- **THEN** 表决条显示各问选择与判决（全票/多数票/摇摆），选项带得票点

### Requirement: 状态行如实等待
直播等待真实生成时 SHALL 如实显示当前环节文案；不得用假动画掩盖真实等待（直播≠成片）。

#### Scenario: 等待如实
- **WHEN** 引擎正在等待某次 LLM 返回
- **THEN** 状态行显示对应环节（如"X 正在换序三问中作答…"）

### Requirement: 聚合视图
操作台右下面板 SHALL 在状态灯下方呈现最新批次的 5-run 聚合视图（批次/承诺轨迹/灯众数分布/拉扯度/心口缝/脚注），无批次数据时如实提示。

#### Scenario: 读最新批次
- **WHEN** 存在至少一个批跑产物
- **THEN** 聚合视图显示最新批次数据并可手动刷新

### Requirement: 三代前端共存
档案页与回放器 SHALL 可基于任意 run 的 trace 生成（缺省取最新）；操作台落盘的 trace 对二者兼容。

#### Scenario: 旧件可渲染
- **WHEN** 操作台跑完一局
- **THEN** 档案页与回放器命令对该 trace 均能生成可打开页面

### Requirement: 诚实脚注与错误外露
页面 SHALL 字面包含诚实脚注（单 run 轨迹/人设合成或蒸馏/承诺非预测/一句话心理外显口径/审计员同为 AI/换序三问公示）；引擎错误必须以 error 事件亮到页面。

#### Scenario: 错误亮出
- **WHEN** 推演中途 LLM 持续失败
- **THEN** 页面出现明确错误条目，推演状态复位可重新开拍
```

## openspec/changes/sandbox-v3-core/specs/info-firewall/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/info-firewall/spec.md
- Lines: 1-35
- SHA256: fa375cac8eb89c69401aed1a36516900ada863b1bd7a0408399252cedb56187e

```md
# info-firewall — 信息防火墙

## ADDED Requirements

### Requirement: 台账在场者标注
每条台账条目 SHALL 携带 witnesses（知晓该事件的角色名单）：幕摘要的 witnesses 由收场报出的在场知情者构成，后果条目的 witnesses 逐条标注；越界人名拒收并落回本幕在场者名单。

#### Scenario: 私下事件的知晓面
- **WHEN** 某后果只发生在两名角色之间（如私聊）
- **THEN** 该台账条目的 witnesses 只含这两人，其余角色不知晓

### Requirement: agent 知情物理隔离
行动 agent 的情绪评价与决策提示词 SHALL 只包含其在场（witnesses 含其名）的台账条目——非亲历条目物理上不进入其提示词，不依赖模型自觉。

#### Scenario: 缺席者看不见
- **WHEN** 台账存在某 agent 不在 witnesses 中的条目
- **THEN** 该条目不出现在该 agent 的任何提示词中

### Requirement: SM 泄密硬约束
Scene Master 的搭景与推进提示词 SHALL 包含信息防火墙硬约束：任何角色的叙事、念头、选项不得引用其知情范围外的信息；他人人设中的私密设定不得以传闻、直觉、巧合等形式凭空泄入；私密信息进入他人认知必须有舞台上可观察的来源。转折点素材明确设定的公开信息 SHALL 放行。

#### Scenario: 对抗局零泄漏
- **WHEN** 以含一方私密信息的场景（如上级知情未公开的组织变动）跑完整局
- **THEN** 泄漏检查工具对另一方的内心/理由/选项/投票理由/叙事认知句式扫描，关键词命中为 0

#### Scenario: 剧本公开传闻放行
- **WHEN** 转折点素材本身设定了公开传闻（如"茶水间都在传"）
- **THEN** 该传闻可进入各角色认知，不算泄漏

### Requirement: 泄漏检查工具
仓库 SHALL 提供可重复执行的泄漏检查工具（tools/），对任意 trace 按角色侧扫描私密关键词并输出逐条命中或零泄漏结论。

#### Scenario: 工具可用
- **WHEN** 对一个含私密信息场景的 trace 运行泄漏检查
- **THEN** 输出每条命中的位置与文本，或"零泄漏"结论
```

## openspec/changes/sandbox-v3-core/specs/jd-context/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/jd-context/spec.md
- Lines: 1-24
- SHA256: 13b98d4a35009b7b7ffcacc0264da8c5bf9f725e92523669152e14c44a2bb036

```md
# jd-context — JD 进引擎

## ADDED Requirements

### Requirement: JD 进场景搭景
当用户提供 JD 时，场景搭景提示词 SHALL 携带 JD 作为岗位/团队背景参考；未提供时管线行为不变。

#### Scenario: 带 JD 开局
- **WHEN** 用户在操作台粘贴 JD 后开拍
- **THEN** SM 搭景提示词含 JD 块，场景设定与岗位语境一致

### Requirement: JD 进蒸馏上下文
蒸馏器 SHALL 接受可选 JD 输入，使行为手册的 if→then 条目向岗位相关情境侧重；JD 缺省时蒸馏照常工作。

#### Scenario: 带 JD 蒸馏
- **WHEN** 蒸馏时提供了 JD
- **THEN** 产出手册的情境词与岗位场景对齐（如后端岗出现联调/排期类情境）

### Requirement: JD 不做硬性评分
JD SHALL 只作语境参考：不得据 JD 对候选人打分、排序或生成"匹配度"数字；JD 原文随 run 入档。

#### Scenario: 无评分输出
- **WHEN** 任意带 JD 的推演完成
- **THEN** 产物中不存在"JD 匹配分"类数字字段
```

## openspec/changes/sandbox-v3-core/specs/multi-agent-cast/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/multi-agent-cast/spec.md
- Lines: 1-35
- SHA256: 9dd2ddd79e090af164e735c82e3f81243227866e37bd1de4b93f29e26480200f

```md
# multi-agent-cast — 名单制多人引擎

## ADDED Requirements

### Requirement: 名单制角色注册表
角色 SHALL 以有序名单（cast）管理，每人一张卡 `{name, role, persona, playbook, kind}`；kind ∈ {candidate, counterpart, colleague}，candidate（观察主体）有且仅有一个。引擎显式接收 cast 对象，不依赖模块级全局变量。

#### Scenario: N=2 特例等价
- **WHEN** 名单上只有 candidate 和 counterpart 两张卡
- **THEN** 推演行为与双人版蓝本机制一致（行动方在两人间选择、承诺围绕候选人×团队）

#### Scenario: 名单约束
- **WHEN** 导入的名单缺 candidate 或含两个 candidate
- **THEN** 导入被拒绝并明示原因

### Requirement: 行动方从名单选择
Scene Master SHALL 从名单（含同事）中挑选每个节骨眼的行动方；越界人名落回 candidate 并记警告；同事作为行动方时走与主角相同的完整管线（情绪评价→换序三问→审计）。

#### Scenario: 同事真决策
- **WHEN** SM 指定某同事为行动方
- **THEN** 该同事经历完整决策管线，其选择/理由/审计与主角同等入档

### Requirement: network 单灯加关系细目
盘面状态灯中 network SHALL 保持单灯（supportive/neutral/opposed/mixed）；收场 SHALL 另输出候选人×每位非候选人成员的态度细目（态度+一句话证据）入 trace 档案层（relations 字段），不进灯面、不进选幕启发式。

#### Scenario: 团队态度分化
- **WHEN** 一位同事排斥而上级支持候选人
- **THEN** network 灯判 mixed，relations 细目分别记录两人的态度与证据

### Requirement: 角色卡导入与推演锁定
系统 SHALL 支持导入整套名单（角色卡 JSON）；导入即全管线生效（提示词/舞台/trace 人名跟随）；推演进行中拒绝换名单。

#### Scenario: 推演中导入被拒
- **WHEN** 一局推演进行中收到导入请求
- **THEN** 返回明确拒绝（409 语义），名单不变
```

## openspec/changes/sandbox-v3-core/specs/persona-distill/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/persona-distill/spec.md
- Lines: 1-24
- SHA256: 6fd38311873bf95b68fabd45d58d522137a77504cdaa953849cb11cd8419331b

```md
# persona-distill — 蒸馏器

## ADDED Requirements

### Requirement: 两段式蒸馏管线
蒸馏器 SHALL 以两段式把材料包蒸成角色卡：第一段对每份材料独立产出证据链小结（只要具体行为，禁猜测）；第二段融合成 200-300 词第二人称人设＋5-7 条 if→then 行为手册。材料映射：简历→自述侧、测评→自评量表侧、面试官评价→他人视角侧、背调→第三方事实侧。

#### Scenario: 材料包到角色卡
- **WHEN** 输入一套合成材料包（简历+测评+面试官评价+背调）
- **THEN** 输出符合 cast 角色卡 schema 的 JSON（name/role/persona/playbook）

### Requirement: 三纪律
蒸馏提示词 SHALL 包含三纪律：①evidence or silence——证据不足的维度写"未知"，不许编；②保留视角分歧不调和——自述与他人视角矛盾时两面原样并存（如"你自述冷静，面试官记录你答压力题时语速明显加快"）；③标记矛盾不抹平。

#### Scenario: 视角分歧保留
- **WHEN** 简历自述与面试官评价对同一特质方向相反
- **THEN** 产出的人设同时呈现两个视角，不挑边、不平均

### Requirement: 蒸馏产物直接入名单
蒸馏产物 SHALL 与 cast 角色卡同 schema，可直接导入名单开局——"从材料到 agent 一键，引擎一行不改"。

#### Scenario: 蒸馏闭环
- **WHEN** 蒸出的角色卡导入名单并跑一局
- **THEN** 该 agent 的行为可辨认地顺着材料中的行为证据（live 人判验收）
```

## openspec/changes/sandbox-v3-core/specs/reason-audit/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/reason-audit/spec.md
- Lines: 1-28
- SHA256: 0103c791c700f8faf3fe97cd5fb87e3a712769731893276086975464b74a0877

```md
# reason-audit — 理由审计员

## ADDED Requirements

### Requirement: 独立四查对账
每个决策 SHALL 由独立 LLM 调用的理由审计员做结构对账，四查：①行为手册条款命中/冲突；②理由与内心想法的一致性（一致/部分一致/矛盾）；③理由引用线索的事实出处（场景/本幕回合/其知情范围内台账，查无出处记编造线索）；④信息越权（理由或内心引用只存在于其知情范围外的信息）。任何一项不一致判"黄旗"，全对得上判"通过"。审计员只标记不改判。

#### Scenario: 编造线索亮旗
- **WHEN** 行动者的理由引用了场景、回合与其知情台账中都不存在的"事实"
- **THEN** 该线索记入 fabricated_cues，verdict 判黄旗

#### Scenario: 信息越权亮旗
- **WHEN** 行动者的理由引用了只存在于其知情范围外的信息
- **THEN** info_overreach 记录越权说明，verdict 判黄旗

### Requirement: 心口缝只记录不判旗
审计员 SHALL 单独记录"心口缝"（行动者内心想法与最终外显行动之间的方向落差）；心口缝不参与判旗——它是关系信号不是毛病，落差只描述不打分。

#### Scenario: 心口分离但理由诚实
- **WHEN** 行动者内心想回避、行动却迎上，且其陈述理由与手册/事实对得上
- **THEN** inner_gap 记录落差描述，verdict 仍可判"通过"

### Requirement: 审计产物全量入档
verdict、手册命中/冲突、内心一致性、编造线索、信息越权、心口缝 SHALL 全量进入 trace 与台本，并经事件流送达前端；meta SHALL 含黄旗计数与按行动方分组的心口缝计数。

#### Scenario: 黄旗可追溯
- **WHEN** 任意回合被判黄旗
- **THEN** trace 中可读到完整审计明细，操作台判断流有对应黄旗行
```

## openspec/changes/sandbox-v3-core/specs/rollout-engine/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/rollout-engine/spec.md
- Lines: 1-64
- SHA256: 588f6918e0d128ae5a136b29e54adcef2530810e45c8744c4b8e2ac0d7261272

```md
# rollout-engine — 受控选项推演核心

## ADDED Requirements

### Requirement: 受控选项决策
推演的证据单元 SHALL 是受控选项决策：Scene Master 在每个节骨眼给出 3-4 个互斥、单行动者、可观察的候选行动，行动 agent 只能从中选择并给出理由，不得发明或修改选项。

#### Scenario: 正常选择
- **WHEN** 节骨眼回合中 agent 从呈现的选项中返回合法 action_id
- **THEN** 该选项成为本回合行动，action/reasoning/confidence 记入 trace

#### Scenario: 越界选择拒收
- **WHEN** agent 返回的 action_id 不在呈现选项集合内
- **THEN** 系统落到该问呈现序第一个选项，并将越界事实写入 warnings

### Requirement: 换序三问取多数票
每个节骨眼决策 SHALL 以 3 种互不相同的选项顺序并发提问 3 次（洗牌一次+轮转生成），按选项内容（原序 id）取多数票；官方决策的 action_id 映射回第 1 问呈现序。每一问的顺序、选中呈现位与理由 SHALL 全量记入 trace。

#### Scenario: 多数票
- **WHEN** 三问中两问选中同一内容
- **THEN** 该内容为官方选择，vote_summary.verdict 记"多数票"

#### Scenario: 三问全分裂（摇摆）
- **WHEN** 三问各选不同内容
- **THEN** 取第 1 问的选择继续推演，verdict 记"摇摆"并写入 warnings（摇摆是信号，入档不丢弃）

### Requirement: 差量式状态灯
收场 SHALL 采用差量制：只接收"本幕有直接可观察证据需要变化的灯"，其余沿用上一幕；拒收越界值与"已知状态退回 unknown"；单幕 ≥3 灯变化自动黄旗；无冲突时不得判 repaired/successful。

#### Scenario: 无变化幕
- **WHEN** 收场输出空的 state_changes
- **THEN** 八灯全部沿用上一幕原值，trace 中 evidence 为空

#### Scenario: 退回 unknown 拒收
- **WHEN** 收场试图把已知状态改回 unknown
- **THEN** 该差量被拒收，原值沿用，拒收事实写入 warnings

### Requirement: 台账时间线
每幕 SHALL 携带 sim_time（入职第X周·周几·时段格式），且不得早于上一幕；台账条目带时间前缀。

#### Scenario: 时间防倒流
- **WHEN** SM 生成新一幕场景
- **THEN** 其 sim_time 不早于上一幕（提示词携带上一幕时间与"只许向前"硬约束）

### Requirement: 回合制节骨眼
一幕 SHALL 由 1-3 个节骨眼回合组成；第 1 回合不得直接收幕；上级/同事侧关键决定必须由其本人作为行动方决策，不得由叙事代笔。

#### Scenario: 首回合禁收幕
- **WHEN** SM 在第 1 回合返回 scene_over=true
- **THEN** 该幕记入"第1回合即收幕"警告

### Requirement: 后果结算与台账唯一性
每幕收场后 SHALL 独立结算悬而未决事项的直接后果并写入台账；台账是后续幕唯一可引用的既往事实，SM 不得虚构台账外的过往互动。

#### Scenario: 后果入账
- **WHEN** 本幕存在未获回应的请求或悬置事项
- **THEN** 结算其保守、具体、与人设一致的直接后果，连同知晓者名单写入台账

### Requirement: live-only 运行时
产品代码 SHALL 不含任何 mock 分支；LLM 调用失败重试后大声抛错；引擎错误必须以 error 事件外露，不得静默吞掉。

#### Scenario: 无 API key
- **WHEN** 运行时缺少 DEEPSEEK_API_KEY
- **THEN** 立即抛错并明示原因，不回退到任何假数据
```

## openspec/changes/sandbox-v3-core/specs/run-aggregation/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/run-aggregation/spec.md
- Lines: 1-31
- SHA256: 9f6078cf0b90147b92a7556f1f460e698a92e9f3162b4083182e6314fe55263c

```md
# run-aggregation — 5-run 聚合

## ADDED Requirements

### Requirement: 并发批跑
系统 SHALL 支持同配置不同采样并发跑 N 局（默认 5），每局独立落 trace+台本，批次目录含聚合产物（aggregate.json+聚合报告）。

#### Scenario: 批跑产物齐全
- **WHEN** 以 N=5 跑一个批次
- **THEN** 产出 5 份独立 trace、1 份 aggregate.json、1 份人可读聚合报告

### Requirement: 倾向分布聚合
聚合 SHALL 至少包含：按幕号对齐的承诺轨迹（均值±极差）、状态灯终值众数+分布、拉扯度（全票/多数票/摇摆计数与摇摆率）、审计黄旗率、心口缝总数与按行动方分布、每幕选择并排。

#### Scenario: 话术可直接生成
- **WHEN** 聚合完成
- **THEN** "N 局里 M 局走到某状态"式话术可直接从聚合数据读出

### Requirement: 软对齐与分叉如实标注
跨局对齐 SHALL 按幕号+行动方软对齐；各局场景序分叉时 SHALL 如实标注（aligned 字段+分叉场景清单），不得假装可比。

#### Scenario: 场景分叉标注
- **WHEN** 五局在第 2 幕走向不同转折点
- **THEN** 聚合报告该幕标注"场景分叉"并列出各局场景

### Requirement: 聚合诚实脚注
聚合产物 SHALL 携带脚注：聚合为该人设在沙盘中的倾向分布，未经对账校准，不构成对真实结局的预测。

#### Scenario: 脚注随产物走
- **WHEN** 查看任意聚合产物（json/报告/操作台聚合视图）
- **THEN** 脚注字面在场
```

## openspec/changes/sandbox-v3-core/specs/scene-bank/spec.md

- Source: openspec/changes/sandbox-v3-core/specs/scene-bank/spec.md
- Lines: 1-24
- SHA256: 0ccb47dca7ad4c46be4f2ed0b9470a35a7f3e62d1fb022e2cb842cbfe7ecc8c6

```md
# scene-bank — 场景库

## ADDED Requirements

### Requirement: 预设库迁移
场景库 SHALL 迁移蓝本的 12 条预设转折点（六类×2：初来乍到/磨合建制/压力测试/冲突与修复/深化里程碑/现代职场），含 owner_hints（用"新人/上级"称谓不用人名）。

#### Scenario: 预设可用
- **WHEN** 列出场景库
- **THEN** 12 条预设按类别完整可选

### Requirement: 自定义场景持久化
用户自定义与共创结晶的场景 SHALL 落文件持久化，服务重启后不丢；与预设库同列可选。

#### Scenario: 重启不丢
- **WHEN** 共创入库一条自定义场景后重启服务
- **THEN** 该场景仍出现在场景下拉中且可开拍

### Requirement: 共创结晶入库
场景共创对话 SHALL 可结晶为标准转折点结构（title/category/sketch/owner_hints）入库；类别越界落"现代职场"；同名场景加后缀去重（从简，不上相似度算法）。

#### Scenario: 共创到开拍
- **WHEN** 用户与共创助手聊出场景并点存
- **THEN** 结晶场景入库、出现在下拉、可直接用它开拍
```

