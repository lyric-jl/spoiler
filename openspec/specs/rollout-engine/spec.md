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
