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
