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
