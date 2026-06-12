# 契合沙盘 · FitSandbox（sandbox-v3）

用 multi-agent 沙盘做"录用契合 · 未来演化"推演的系统（投智联首届全国 AI 创新大赛 · 赛道 ③ AI+创意）。

候选人 agent 在场景导演（Scene Master）给出的 **3-4 个互斥受控选项**里做选择——不是自由对话，是受控选项决策。一局推演下来，**状态灯 / 留任-契合承诺 / 理由审计**全程可见、全量入 trace，可在操作台直播看，也可导出自包含 HTML 档案页/回放厅。

架构迁移自 RELATE-Sim（arXiv 2510.00414）的受控选项决策范式，把"恋爱关系推演"迁到"职场试用期推演"。

---

## 快速开始

### 环境

- **Python 3.x，stdlib 零第三方依赖**（HTTP 客户端、服务器、JSON 全用标准库；`requirements.txt` 都没有）。
- **必需三把 API Key**（2026-06-12 起多模型分工，见 `config.ROLES`）：`DEEPSEEK_API_KEY`（导演=deepseek-v4-pro）、`MOONSHOT_API_KEY`（编剧=kimi-k2.6：出题/蒸馏/搭团队/场景/答卷）、`SILICONFLOW_API_KEY`（演员=Qwen3.6-35B-A3B + 审计=GLM-5.1，一把 key 两个工种）。本系统 **live-only，无 mock 回退**——缺 key 直接报错，不会用假数据顶替。
- **工种分工的设计思想**：编剧要文笔（中文创意第一档）、导演要推理深度、演员要快且人设稳（海量调用+直播）、审计要指令遵循且**与演员/编剧不同源**（异构独立审计，不让模型自己批改自己的作业）；答卷模型也刻意与沙盘演员不同源，免得"自陈 vs 行为"的落差变成同一模型自说自话。沿用 RELATE-Sim 双模型分工思路（GPT-OSS-120b 蒸馏 + Qwen3-32B 跑模拟）并细化到四工种。
- Windows 终端先设 UTF-8（本机 stdout 默认 gbk）：

  ```powershell
  $env:PYTHONUTF8=1; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8
  ```

### 主命令

> ⚠ 除 `--help` 和测试外，下列命令都会真调大模型（花钱，按 `config.ROLES` 分工走三家）。

- **操作台（主秀，直播看推演）**：
  ```
  python -m sandbox3.server [--port 8781]
  ```
  起在 http://127.0.0.1:8781/（端口故意避开蓝本 relate_mvp 的 8780，两台可同时跑）。

- **单跑一局**（产物落 `output/run_<时间戳>/`，含 `trace.json` + `台本.md`）：
  ```
  python -m sandbox3.run [--scenes 4] [--start C1-01] [--seed S] [--cast path.json]
  ```
  `--cast` 缺省用 `data/cast_default.json`（双人局：候选人周默 + 上级沈雯）；`data/cast_three.json` 是三人局（多一个同事）。

- **5-run 聚合**（同配置并发跑 N 局，聚合倾向分布；产物落 `output/batch_<时间戳>/`，含各 run + `aggregate.json` + `聚合报告.md`）：
  ```
  python -m sandbox3.aggregate [--runs 5] [--scenes 4] [--start C1-01] [--seed 42]
  ```
  seed 为基值，逐局 +1（洗牌可复现）；各局场景序可能分叉，按"幕号+行动方"软对齐，分叉如实标注。操作台聚合视图读最新一批。

- **蒸馏器**（材料包目录 → 角色卡 JSON，直接可入名单）：
  ```
  python -m sandbox3.distill <material_dir> [--jd jd.txt] [--out card.json] [--name 周默]
  ```
  示例材料包：`data/materials_zhou/`（*.md）。`--name` 是候选人真名——姓名是确定性事实（PII），由调用方显式指定，不靠 LLM 蒸馏。

### 导出页（不调 API，读已有 run 目录）

- 档案页（单文件 HTML，`file://` 直开）：`python -m sandbox3.pages.archive [--run output/run_xxx]`
- 回放厅（可交互回放，点头像看内心）：`python -m sandbox3.pages.replay [--run output/run_xxx]`

两者缺省都取 `output/` 下最新 run。

### 测试

```
python -m unittest discover -s tests
```

当前 **129 个测试全绿**（约 0.8s）。测试注入 `FakeLLM`（不调 API、不花钱），测的是机制账本（表决计票 / 差量应用 / 防火墙过滤 / 审计字段流转 / 台账时序 / 名单制行动方选择 / 坏 JSON 重试），不测模型演技。

---

## 架构（文件全景）

包名 `sandbox3`。一局生命周期：搭景 →〔推进 → 情绪评价 → 换序三问表决 → 理由审计〕×回合（≤3）→ 差量收场 → 后果结算 → 挑下一幕。

```
sandbox3/
├── config.py          全局常量：ENDPOINTS/ROLES 多模型分工表、端口 8781、换序三问轮数 3、每幕回合上限 3、名单上限 6
├── llm.py             多模型客户端 LLMClient(role)（live-only，重试 2 次后大声抛 LLMError，无 mock 分支；含各家特例：kimi 锁温、qwen 关思考、glm/v4-pro 抬 token 地板）
├── states.py          八状态灯（职场版）+ 枚举校验 + 差量应用 + 下一幕类别启发式
├── cast.py            名单制角色注册表（Cast/Card）；候选人有且仅有 1 个，2-6 人
├── ledger.py          滚动台账：时间戳 + 在场者 witnesses + 知情过滤（防火墙数据层）
├── scenes.py          场景库 SceneBank：预设 + 自定义持久化（同名加后缀去重）
├── engine.py          推演主循环（依赖注入 cast/llm/bank，emit 事件流回调）
├── audit.py           理由审计员（独立调用，只标记不改判；verdict 越界保守落黄旗）
├── trace.py           trace → Markdown 台本渲染 + save_run（落 trace.json/台本.md）
├── aggregate.py       5-run 并发聚合 + 聚合报告渲染
├── distill.py         蒸馏器：材料包 → 两段式 → cast 角色卡 JSON
├── run.py             CLI 单跑入口
├── server.py          操作台本地服务（stdlib HTTP，零依赖；REST + 事件轮询）
├── prompts/           提示词层
│   ├── sm.py          Scene Master 五件（搭景/推进/收场/后果/挑下一幕）+ 共创两件
│   ├── agent.py       agent 情绪评价 / 受控选项决策 + 理由审计员
│   └── distill.py     蒸馏器两段式（证据链小结 → 融合人设+行为手册）
├── pages/             前端
│   ├── theater.py     操作台单页（PAGE 字符串，由 server.py 提供，数据走 /api/*）
│   ├── archive.py     档案页生成器（自包含 HTML）
│   └── replay.py      回放厅生成器（自包含 HTML，可交互）
└── tools/             体检工具（CLI，读 trace.json，不调 API）
    ├── checkup.py     位置偏置体检（官方选择第1问呈现位 A 占比是否落 [20%,47%]）
    └── leakcheck.py   防火墙泄漏检查（子串匹配、高召回、供人工复核）
```

设计要点：

- **名单制 Cast**（多人原生底座，双人 = N=2 是特例）：引擎显式接收 Cast 对象，无模块全局名单变量；候选人=观察主体，有且仅有一个。
- **依赖注入 LLM**：运行时唯一路径是 live（四工种按 `config.ROLES` 各配各家）；测试以 `FakeLLM` 注入（`tests/`，引擎的 `actor_llm`/`audit_llm` 缺省回落 `llm`，单替身即可），不开运行时分支。
- **引擎-前端经 emit 事件流解耦**：事件类型 `run_started/status/scene_open/beat_open/inner/decision/audit/settle/consequence/next_tp/done/saved/error`，操作台轮询 `/api/events?since=N` 消费。
- **八状态灯（职场版）**：冲突 / 修复结果 / 角色清晰度 / 投入绑定 / 外部机会 / 变动 / 团队接纳 / 离职信号，差量制（只接收本幕有证据要变的灯，其余沿用上一幕）。

---

## 诚实工程红线（逐条，照设计文档）

1. **live-only，无 mock 回退**：产品代码无任何 mock 分支；测试替身只住 `tests/`。LLM 调用失败重试后大声抛错——要么是真的，要么明着失败，错误必须亮到页面不许吞。
2. **落差只描述不打分**：心口缝（内心 vs 行为的落差）只记录、不判旗。落差小（心口一致）同样是好信号——不惩罚老实人、不奖励会演的人。
3. **承诺与状态灯未经对账校准，不构成对真实结局的预测**：留任-契合承诺、状态灯都是推演机制的内部部件，**不能当预测用**；这条脚注随每一帧产物走，不许丢。
4. **理由审计员只标记不改判**：它也是 AI，做的是结构对账（条款命中 / 内心自洽 / 线索查证 / 信息越权四查），供人复核，不是语义终审；越界保守落黄旗。
5. **信息防火墙：物理隔离，不靠模型自觉**：agent 只见自己亲历的台账条目（`ledger.visible` 按 witnesses 过滤），知情过滤在数据层做掉。
6. **换序三问取多数票，防位置偏置**：每个决策把选项洗牌 + 逐问轮转坑位问 3 次，按内容（orig_id）取多数；原序与各问呈现序全量对账入 trace。
7. **模型层偏好分布如实公示**：表决全票/多数票/摇摆、各呈现位被选分布、审计黄旗、心口缝处数都进 trace 与报告。

---

## 已知边界（据实，不回避）

- **承诺 / 状态灯不能当预测用**：它们是机制部件、未经真实结局对账校准。这是定位红线，不是缺陷掩饰——本 demo 的目标是把机制跑通给人看，不是做成生产级预测系统。
- **leakcheck 是子串高召回工具，需人工复核**：它做关键词子串匹配，会误报（如关键词"HC"命中候选人引用上级当面亲口说的合法公开信息）。**不作自动判定**——P0 验收里它报"防火墙击穿"，人工复核确认是合法引用、防火墙实际守住（证据见 `evidence/p0/`）。
- **双人局跑"资深同事"类场景会兜底**：如 C4-03（被一句话否掉的方案，owner_hints 写"资深同事"），双人 cast 里没这个角色，SM 会提到名单外角色、引擎正确兜底落候选人（非 bug，会出一条良性 warn）。**三人局（含 colleague）跑这类场景更完整。**
- **JD 影响场景叙事的 live 验证留标杆局**：JD 进引擎的代码路径已通（蒸馏 `stage1/stage2_user`、`scene_init_user`、server `STATE["jd"]` 都接了 jd 形参），但 JD 实际如何影响场景叙事的 live 验证留在收尾标杆局；操作台当前把 JD 只入档 `jd.txt`、不喂引擎驱动（作者 2026-06-07 拍：先只做输入框）。
- **操作台浏览器形态 / 台本叙事质量是人判项**，未自动化验收——需起 server 在浏览器看、读 `output/run_*/台本.md` 评。
- **场景库 15 条预设**（六类分布 2/2/3/3/2/3），demo 量级、非穷尽。

### RELATE-Sim 引用红线（防误用，写进 README）

迁移自 **RELATE-Sim（arXiv 2510.00414）** 的受控选项决策架构。引用其数字时：

- 64.4% 只能论证 **"动态推演 > 静态画像"**，**不能说成"对话模拟有效"**——该论文明文禁止对话模拟。
- 引用 64.4% 必带分母 **101** + 置信区间 **[+2.3, +29.3]pp**。
- **"80% 情侣预测"是幻觉数字，禁用。**
- 别说"它没有内心层"——正确说法是：它的内心是脚手架、不外显；本系统把内心外显并做心口落差对照（落差只描述不打分）。

---

## 合规姿态

- 输出**只进 HR 侧、不流向候选人**。
- 对候选人保留最低告知："本流程使用 AI 辅助评估，可要求人工复核。"
- 落差只描述不打分（重申）：心口一致同样是好信号，杜绝"惩罚老实人、奖励会演的人"。

---

*架构参照 RELATE-Sim（arXiv 2510.00414）。relate_mvp 为本系统的搬运蓝本与可回退参赛底。*
