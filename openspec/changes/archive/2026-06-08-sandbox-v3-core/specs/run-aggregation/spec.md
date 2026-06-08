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
