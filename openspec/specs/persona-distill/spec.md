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
