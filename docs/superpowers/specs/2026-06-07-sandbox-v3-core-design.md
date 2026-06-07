---
comet_change: sandbox-v3-core
role: technical-design
canonical_spec: openspec
---

# sandbox-v3-core 技术设计

> 需求事实源＝`openspec/changes/sandbox-v3-core/`（proposal + 9 个 capability 的 delta spec）。
> 本文只管 HOW：架构、关键技术决策、测试策略、风险。蓝本＝`D:\aidasai\fitsandbox\relate_mvp`（八大机制已 live 验收）。

## 作者已拍决策（2026-06-07，brainstorming 全程确认）

1. **v3＝比赛主体**（截止 06-14）；范围＝机制平移＋工程化＋多人引擎＋蒸馏器/JD＋场景库（P0→P3 砍尾不砍头）。
2. **架构＝多人原生底座（B 方案）**：名单制角色注册表，双人＝N=2 特例；不走"先双人后砸墙"。
3. **验收＝v3 自立**：不与 relate_mvp 输出逐字对照；在新仓重做全套验收动作（位置偏置体检/防火墙对抗局/live 冒烟）＋trace 账目完整性检查。
4. **network 灯＝单灯保留＋关系细目入档**：盘面不变，候选人×每同事的态度细目进档案层。
5. 包名 `sandbox3`；场景去重从简（同名加后缀）。

## 架构

### 包结构（职责分模块，对应 9 个 capability）

```
sandbox3/
├── config.py          配置：模型/端口/路径/名单上限
├── llm.py             DeepSeek 客户端（live-only，重试后大声抛错）
├── cast.py            名单制角色注册表 + 角色卡 schema（蒸馏产物=同一张卡）
├── states.py          八状态枚举 + 差量应用
├── ledger.py          台账：时间戳 + witnesses + 知情过滤（防火墙数据层）
├── scenes.py          场景库：预设迁移 + 文件持久化 + 共创入库
├── prompts/           按角色拆：sm.py / agent.py / audit.py / distill.py / cocreate.py
├── engine.py          SM 循环 + 回合制 + 换序三问表决（核心编排）
├── audit.py           理由审计员（四查 + 心口缝）
├── distill.py         蒸馏器两段式
├── aggregate.py       5-run 聚合（并发批跑 + 聚合产物）
├── trace.py           trace 落盘 + 台本渲染
├── server.py          操作台 server（事件流路由）
├── pages/             操作台页面 / 档案页 / 回放器（三代共存）
└── tools/             体检工具：位置偏置体检 / 防火墙泄漏检查（从临时脚本转正）
tests/
├── fakes.py           FakeLLM（脚本化 JSON 应答）——只住在 tests/
└── test_*.py          每机制一个测试文件
```

### 名单制核心（cast）

- 注册表＝有序名单，每人一张卡 `{name, role, persona, playbook, kind}`；`kind ∈ {candidate, counterpart, colleague}`，candidate（观察主体）唯一。
- SM 从名单挑行动方；prompt 人物格子按名单循环生成；承诺估计围绕"候选人×团队"。
- **去全局变量**：引擎显式接收 cast 对象（MVP 用模块全局 NEWCOMER/COUNTERPART，v3 改依赖注入——换名单不重启、测试不串档）。
- 行动方规矩措辞按 kind 泛化（上级侧关键决定→上级本人行动；同事侧→同事本人）。

### 数据流与兼容契约

一局生命周期照搬 MVP（已验证）：搭景 → [推进→情绪评价→换序三问表决→审计]×回合（≤3）→ 差量收场 → 后果结算 → 挑下一幕。

- **emit 事件流协议沿用** MVP 事件类型清单（run_started/status/scene_open/beat_open/inner/decision/audit/settle/consequence/next_tp/done/saved/error）——操作台契约不变。
- **trace 字段名沿用** MVP（votes/vote_summary/options_original/chosen_orig_id/witnesses/sim_time/inner_gap 等）；多人化只**附加**字段（present 在场名单、relations 关系细目），不破坏旧字段。

### 防火墙多人化

witnesses 本就是名单，N 人天然支持；agent 只见亲历的台账条目（物理隔离）；审计第四查（info_overreach）不变。私聊/小圈子＝witnesses 记在场子集。SM 约束措辞按"每个角色"泛化；"转折点素材明确设定的公开信息"放行条款保留。

### 蒸馏器 + JD

- 两段式（论文 §5.2）：每份材料→证据链小结→融合 200-300 词第二人称人设＋5-7 条 if→then；材料映射＝简历→self、测评→ersi、面试官评价→rpd/ctss（他人视角）、背调→sfn；三纪律进 prompt（evidence or silence／视角分歧不调和／矛盾标记不抹平）。
- 产物＝cast 同一张角色卡，蒸完直接入名单（"引擎一行不改"话术）。
- JD 两个进口：场景搭景上下文＋蒸馏上下文；**JD 不做硬性评分**（合规姿态）。
- 测例＝合成材料包（实现者起草、作者过目）。

## 测试策略（红线措辞，钉死）

> **测试替身只住在 tests/，产品代码无任何 mock 分支；运行时唯一的 LLM 路径是 DeepSeek live。**

- 引擎收 llm 客户端为依赖；测试注入 FakeLLM（按脚本吐 JSON），确定性地测**机制账本**：表决计票（多数/全票/摇摆/越界票拒收）、差量应用（拒收退 unknown/越界值）、防火墙过滤（agent 提示词不含未亲历条目）、审计字段流转、台账时序、名单制行动方选择。测的是账本，不是模型演技。
- live 验收四件套（CLI 工具）：全链冒烟／位置偏置体检（官方选择呈现位≈1/3）／防火墙对抗局 0 泄漏／三人局立住（P1）＋蒸馏闭环（P2）。凡"立住"判定必须 live 证据。

## 诚实工程红线（全部延续，逐条进实现）

落差只描述不打分；承诺未经对账校准不构成预测（脚注随帧走）；审计员只标记不改判；心口缝只记录不判旗；live-only 运行时无 mock 回退、错误亮到页面不许吞；选项洗牌+换序三问全量对账入 trace；模型层偏好分布如实公示。

## 风险 / 取舍

- **时间（7 天）**：P0 引擎+测试 ≈2 天 → P0 操作台+聚合 ≈1.5 天（到此可演示）→ P1 多人 ≈1.5 天 → P2 蒸馏+JD ≈1 天 → P3 场景库 ≈0.5 天 → 缓冲 0.5 天。relate_mvp 始终是可回退参赛底。
- **prompt 搬运纪律**：逐字搬＋格子泛化，措辞改动最小化——prompt 是已验证资产，乱动＝回归风险。
- **重写回归**：v3 验收全部重做，不引用旧仓数据冒充。
- **范围膨胀**：发现单 change 装不下时按 comet 规矩拆新 change，不硬塞。
