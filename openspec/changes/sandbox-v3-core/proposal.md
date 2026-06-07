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
