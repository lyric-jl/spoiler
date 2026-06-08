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
