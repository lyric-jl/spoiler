# 验证报告 · sandbox-v3-core

- **Change**：sandbox-v3-core（契合沙盘 v3 完整实现）
- **日期**：2026-06-08
- **验证模式**：full（规模：30 任务 / 9 capability / 77 文件，远超轻量阈值）
- **结论**：**通过，可归档（无 CRITICAL）**

## 检查项（1-7 全 PASS）

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 1 | tasks.md 全勾 | PASS | 30/30 `[x]`，每项带 live 证据路径 |
| 2 | 实现符合 design.md 高层决策 | PASS | 名单制 cast / 依赖注入 LLM / emit 解耦 / 红线全落地 |
| 3 | 实现符合 Design Doc | PASS | 受控选项决策 / 换序三问 / 差量灯 / 防火墙 / 审计 / 蒸馏两段式 / JD 接通逐条对应 |
| 4 | 能力规格场景全通过 | PASS | 9/9 capability 核心 scenario 抽查到代码+测试 |
| 5 | proposal.md 目标满足 | PASS | MVP 四痛点（零测试/双人写死/JD 只暂存/场景重启丢）全消解 |
| 6 | delta spec 与 design doc 无矛盾 | PASS（见下方处理） | 五处授权偏差均合红线、tasks.md 有账；无需返工 |
| 7 | 设计文档可定位 | PASS | Design Doc 存在，front-matter 匹配本 change |

## 测试 / 红线 / 密钥

- **单元测试**：`python -X utf8 -m unittest discover -s tests` → **129 全绿**（约 0.8s，两次独立运行一致）
- **live 客观验收**：P0（A 占比 29.2% 防偏置 / 防火墙守住）/ P1（三人局陈磊 2 个完整决策回合）/ P2（蒸馏视角分歧两面进人设）/ 收尾（aggregate 5/5 出报告）。证据 `evidence/`
- **mock 红线**：产品代码零 mock 分支（"mock/fake" 只在 docstring/注释/tests/）PASS
- **硬编码密钥**：DEEPSEEK_API_KEY 走环境变量，无写死 key，PASS

## 第 6 项处理（verify 阶段文档完善，非返工）

build 期五处授权偏差（>4 选项守卫 raise / 蒸馏 name 由 --name 指定 / complete_json 坏 JSON 重试 / aggregate 单局容错 / 场景库扩至 15 条）均未与诚实工程红线冲突，**未发现需返工的 spec 漂移**。verify 阶段已补登：

- **WARNING 1 已修**：`scene-bank/spec.md` "12 条"→"≥12（当前 15）"，避免主 spec 落库带错
- **WARNING 2 已修**：Design Doc 追加 "Implementation Divergence" 节，记五处偏差使技术设计与实现对账闭环
- **SUGGESTION 3 已修**：`scenes.py` docstring "12 条"陈旧注释更正

## 已知缺口（据实，非阻塞归档）

- **SUGGESTION 4**：偏差 #1（>4 选项守卫）与偏差 #4（aggregate.main 单局容错分支）无专属单元测试——均为简单防御性 guard，aggregate 纯函数 `aggregate()` 有 24 测覆盖；列为可补项。
- **行为等价对照（1.9）/ JD-live 深验（4.4）**：作者放行时暂缓 / 作为已知边界（README 已列），收尾标杆局可覆盖。
