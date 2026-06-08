---
change: sandbox-v3-core
design-doc: docs/superpowers/specs/2026-06-07-sandbox-v3-core-design.md
base-ref: 8f35887bc48ca61045d11e1fb8fcdf75d07b5af0
archived-with: 2026-06-08-sandbox-v3-core
---

# 契合沙盘 sandbox-v3-core 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `D:\aidasai\sandbox-v3` 新仓实现契合沙盘 v3——以已验证的 relate_mvp 为蓝本、多人原生底座（名单制）、带测试套件的正式实现（比赛主体，截止 06-14）。

**Architecture:** 名单制 cast（双人=N=2 特例）+ 依赖注入 LLM 客户端（运行时 live-only、测试注入 FakeLLM）；引擎-前端经 emit 事件流解耦；trace 字段名沿用蓝本、多人字段只附加。

**Tech Stack:** Python 3.x stdlib（零第三方依赖）、DeepSeek API（chat completions）、stdlib http.server、unittest。

archived-with: 2026-06-08-sandbox-v3-core
---

## 全局约定（每个任务开工前读一遍）

- **路径记号**：`B:` = 蓝本 `D:\aidasai\fitsandbox\relate_mvp`；`R:` = 本仓 `D:\aidasai\sandbox-v3`。所有新代码在 `R:\sandbox3\`，测试在 `R:\tests\`。
- **终端纪律**（Windows，stdout 默认 gbk）：每开终端先 `$env:PYTHONUTF8=1; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8`。
- **源码一律用 Write 工具落 UTF-8**，禁 PowerShell `Set-Content` 写 `.py`/`.json`。
- **跑测试**：`cd D:\aidasai\sandbox-v3; python -m unittest discover -s tests -v`。
- **live 冒烟**需 `DEEPSEEK_API_KEY`（作者机器已设）；live 调用花真钱、走真网络，**只在标注 [LIVE] 的步骤跑**。
- **搬运纪律**：prompt 文本是已验证资产，**逐字搬**；只允许做"格子泛化"（人名→cast 循环）这一类计划里明确列出的改动。乱改措辞=回归风险。
- **红线（写代码时随时对照）**：产品代码无任何 mock 分支（测试替身只住 tests/）；落差只描述不打分；心口缝只记录不判旗；审计员只标记不改判；错误大声抛、不许吞；承诺脚注不许丢。
- **提交纪律**：每个 Task 至少一个 commit，message 前缀 `feat:`/`test:`/`port:`/`chore:`；勾掉 `openspec/changes/sandbox-v3-core/tasks.md` 对应项（映射见各 Task 标注）。

## 文件全景图

```
sandbox3/
├── __init__.py        （空）
├── config.py          常量：模型/URL/端口/输出目录/VOTE_ROUNDS/MAX_BEATS
├── llm.py             DeepSeekClient（live-only）
├── states.py          八状态枚举 + apply_state_deltas
├── cast.py            Cast 名单制注册表 + 角色卡校验 + persona_block
├── ledger.py          台账条目：格式化 + 按角色知情过滤
├── scenes.py          场景库：12 预设 + 自定义持久化 + 同名去重
├── prompts/
│   ├── __init__.py    re-export
│   ├── sm.py          Scene Master 五件（搭景/推进/收场/后果/选幕）+ 共创
│   └── agent.py       情绪评价 + 决策 + 审计
├── engine.py          run_simulation（名单制 + 换序三问 + 差量灯 + 防火墙接线）
├── audit.py           审计调用组装 + verdict 校验
├── trace.py           台本渲染 + run 落盘
├── aggregate.py       N 局并发批跑 + 聚合（含 __main__）
├── distill.py         蒸馏器两段式（P2）
├── run.py             单跑 CLI（含 __main__）
├── server.py          操作台 server（含 __main__）
├── pages/
│   ├── __init__.py
│   ├── theater.py     操作台单页 PAGE（自 B:\theater_page.py 移植）
│   ├── archive.py     档案页生成（自 B:\build_page.py 移植）
│   └── replay.py      回放器生成（自 B:\build_theater.py 移植）
└── tools/
    ├── __init__.py
    ├── checkup.py     位置偏置体检（读 trace 出呈现位分布）
    └── leakcheck.py   防火墙泄漏检查（参数化关键词+角色）
tests/
├── fakes.py           FakeLLM（脚本化 JSON 应答队列）
├── fixtures.py        测试用 cast 卡、场景、settle 应答等共享素材
└── test_{states,cast,ledger,scenes,prompts,engine_vote,engine_run,audit,trace,aggregate,scenes_persist,distill,tools}.py
data/
├── scene_bank.json    12 条预设（自 B:\bank.py 数据部分导出）
├── custom_scenes.json 自定义场景（运行时生成，gitignore）
└── cast_default.json  默认名单（周默+沈雯卡，自 B:\personas.py 导出）
```

执行顺序 = Task 编号。P0=Task 1-14，P1=Task 15，P2=Task 16，P3=Task 17，收尾=Task 18。

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 1: 仓库骨架 + config + llm + FakeLLM

对应 tasks.md 1.1/1.2。

**Files:**
- Create: `sandbox3/__init__.py`（空文件）、`sandbox3/config.py`、`sandbox3/llm.py`
- Create: `tests/__init__.py`（空）、`tests/fakes.py`、`tests/test_llm.py`
- Create: `.gitignore`、`data/`（目录）

- [ ] **Step 1: .gitignore 与骨架**

`.gitignore` 内容：

```
__pycache__/
*.pyc
output/
data/custom_scenes.json
.playwright-mcp/
```

建空文件 `sandbox3/__init__.py`、`tests/__init__.py`。

- [ ] **Step 2: 写 config.py**

```python
# sandbox3/config.py
"""全局常量。改这里不改散落各处。"""
from __future__ import annotations
import pathlib

MODEL = "deepseek-chat"
API_URL = "https://api.deepseek.com/chat/completions"
SERVER_PORT = 8781                      # 故意避开 relate_mvp 的 8780，两台可同时起
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
VOTE_ROUNDS = 3                         # 换序三问
MAX_BEATS = 3                           # 每幕节骨眼上限
MAX_CAST = 6                            # 名单上限（含候选人）
```

- [ ] **Step 3: 写失败测试 tests/test_llm.py**

```python
# tests/test_llm.py
import unittest

from sandbox3.llm import DeepSeekClient, LLMError, _strip_fences


class TestStripFences(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_strip_fences('{"a": 1}'), '{"a": 1}')

    def test_fenced(self):
        self.assertEqual(_strip_fences('```json\n{"a": 1}\n```'), '{"a": 1}')


class TestClientGuards(unittest.TestCase):
    def test_no_key_raises_loudly(self):
        c = DeepSeekClient(api_key="")
        with self.assertRaises(LLMError):
            c.complete("s", "u")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 跑测试确认失败**

Run: `python -m unittest tests.test_llm -v`
Expected: FAIL（ModuleNotFoundError: sandbox3.llm）

- [ ] **Step 5: 写 llm.py**

以 `B:\llm.py` 为底改成类（依赖注入用）。完整代码：

```python
# sandbox3/llm.py
"""DeepSeek 客户端（live-only）。红线：无 mock 回退——失败重试后大声抛错，
绝不静默用假数据冒充推演结果。测试替身在 tests/fakes.py，产品代码无任何 mock 分支。"""
from __future__ import annotations
import json, os, sys, time, urllib.error, urllib.request

from .config import API_URL, MODEL


class LLMError(RuntimeError):
    pass


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        nl = s.find("\n")
        s = s[nl + 1:] if nl != -1 else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


class DeepSeekClient:
    """引擎以依赖收下本对象；换实现=换对象，不开运行时分支。"""

    def __init__(self, api_key: str | None = None):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "") if api_key is None else api_key

    def complete(self, system: str, user: str, *, json_mode: bool = True,
                 temperature: float = 0.7, max_tokens: int = 1200, retries: int = 2) -> str:
        if not self.api_key:
            raise LLMError("DEEPSEEK_API_KEY 未设置——v3 只跑 live，不提供 mock。")
        payload = {"model": MODEL,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}],
                   "temperature": temperature, "max_tokens": max_tokens}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(API_URL, data=body, method="POST",
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.api_key}"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                    OSError, KeyError, IndexError) as e:
                last = e
                print(f"[sandbox3.llm] 第{attempt + 1}次调用失败：{e}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        raise LLMError(f"DeepSeek 调用在 {retries + 1} 次尝试后仍失败：{last}")

    def complete_json(self, system: str, user: str, **kw) -> dict:
        raw = self.complete(system, user, json_mode=True, **kw)
        out = json.loads(_strip_fences(raw))
        if not isinstance(out, dict):
            raise LLMError(f"模型未返回 JSON 对象，得到 {type(out).__name__}")
        return out
```

- [ ] **Step 6: 写 tests/fakes.py**

```python
# tests/fakes.py
"""FakeLLM：按脚本吐 JSON 的测试替身。只住在 tests/——产品代码不知道它存在。
用法：FakeLLM([dict1, dict2, ...]) 按队列出；或传 router 函数按 prompt 内容路由。"""
from __future__ import annotations
import json


class FakeLLM:
    def __init__(self, script: list[dict] | None = None, router=None):
        self.script = list(script or [])
        self.router = router
        self.calls: list[tuple[str, str]] = []     # (system, user) 留账供断言

    def complete_json(self, system: str, user: str, **kw) -> dict:
        self.calls.append((system, user))
        if self.router is not None:
            out = self.router(system, user)
            if out is not None:
                return out
        if not self.script:
            raise AssertionError(f"FakeLLM 脚本耗尽（第 {len(self.calls)} 次调用）\nsystem={system[:80]}")
        return self.script.pop(0)

    def complete(self, system: str, user: str, **kw) -> str:
        return json.dumps(self.complete_json(system, user, **kw), ensure_ascii=False)
```

- [ ] **Step 7: 跑测试确认过**

Run: `python -m unittest tests.test_llm -v`
Expected: 3 个测试 PASS

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: 仓库骨架 + config + live-only LLM 客户端 + FakeLLM 测试替身"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 2: states.py（八状态 + 差量应用）

对应 tasks.md 1.3。**蓝本已验证算法，逐字搬。**

**Files:**
- Create: `sandbox3/states.py`、`tests/test_states.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_states.py
import unittest

from sandbox3.states import STATE_ENUMS, initial_state, apply_state_deltas, plausible_categories


class TestApplyDeltas(unittest.TestCase):
    def setUp(self):
        self.prev = initial_state()

    def test_empty_delta_keeps_all(self):
        out, ev, warns = apply_state_deltas({}, self.prev)
        self.assertEqual(out, self.prev)
        self.assertEqual(ev, {})
        self.assertEqual(warns, [])

    def test_valid_change_applies_with_evidence(self):
        out, ev, warns = apply_state_deltas(
            {"conflict": {"new": "brewing", "evidence": "当众顶撞"}}, self.prev)
        self.assertEqual(out["conflict"], "brewing")
        self.assertEqual(ev["conflict"], "当众顶撞")
        self.assertEqual(warns, [])

    def test_unknown_light_rejected(self):
        out, ev, warns = apply_state_deltas({"mood": {"new": "bad"}}, self.prev)
        self.assertEqual(out, self.prev)
        self.assertEqual(len(warns), 1)

    def test_out_of_enum_rejected(self):
        out, ev, warns = apply_state_deltas({"conflict": {"new": "爆炸"}}, self.prev)
        self.assertEqual(out["conflict"], self.prev["conflict"])
        self.assertEqual(len(warns), 1)

    def test_downgrade_to_unknown_rejected(self):
        prev = dict(self.prev, conflict="brewing")
        out, ev, warns = apply_state_deltas({"conflict": {"new": "unknown"}}, prev)
        self.assertEqual(out["conflict"], "brewing")
        self.assertEqual(len(warns), 1)

    def test_noop_same_value_silently_skipped(self):
        out, ev, warns = apply_state_deltas({"conflict": {"new": "none"}}, self.prev)
        self.assertEqual(out, self.prev)
        self.assertEqual(ev, {})
        self.assertEqual(warns, [])


class TestHeuristic(unittest.TestCase):
    def test_initial_first_scene(self):
        # role_clarity=unclear → 必含 磨合建制
        self.assertIn("磨合建制", plausible_categories(initial_state(), 1))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_states -v` → FAIL（ModuleNotFoundError）

- [ ] **Step 3: 搬运实现**

把 `B:\states.py` **整文件逐字拷贝**为 `sandbox3/states.py`（该文件已含 STATE_ENUMS / STATE_LABELS / STATE_DESCRIPTIONS / initial_state / apply_state_deltas / plausible_categories，无需任何改动——它没有双人耦合）。

- [ ] **Step 4: 跑测试确认过**

Run: `python -m unittest tests.test_states -v` → 7 PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "port: states.py 八状态+差量应用（蓝本逐字搬）+ 测试守门"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 3: cast.py（名单制角色注册表）

对应 tasks.md 1.1（cast 部分）/ 3.1 的地基。**全新代码。**

**Files:**
- Create: `sandbox3/cast.py`、`tests/test_cast.py`、`data/cast_default.json`、`tests/fixtures.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_cast.py
import unittest

from sandbox3.cast import Cast, CastError
from tests.fixtures import card_zhou, card_shen, card_colleague


class TestCastValidation(unittest.TestCase):
    def test_two_person_cast_ok(self):
        c = Cast.from_cards([card_zhou(), card_shen()])
        self.assertEqual(c.candidate().name, "周默")
        self.assertEqual([m.name for m in c.members()], ["周默", "沈雯"])

    def test_three_person_cast_ok(self):
        c = Cast.from_cards([card_zhou(), card_shen(), card_colleague()])
        self.assertEqual(len(c.members()), 3)
        self.assertEqual([m.name for m in c.others()], ["沈雯", "陈磊"])

    def test_no_candidate_rejected(self):
        with self.assertRaises(CastError):
            Cast.from_cards([card_shen()])

    def test_two_candidates_rejected(self):
        z2 = card_zhou(); z2["name"] = "李四"
        with self.assertRaises(CastError):
            Cast.from_cards([card_zhou(), z2, card_shen()])

    def test_bad_playbook_rejected(self):
        z = card_zhou(); z["playbook"] = ["只有一条"]
        with self.assertRaises(CastError):
            Cast.from_cards([z, card_shen()])

    def test_duplicate_name_rejected(self):
        with self.assertRaises(CastError):
            Cast.from_cards([card_zhou(), card_zhou()])

    def test_persona_block_contains_playbook(self):
        c = Cast.from_cards([card_zhou(), card_shen()])
        block = c.persona_block("周默")
        self.assertIn("行为手册", block)
        self.assertIn("周默", block)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 写 tests/fixtures.py（共享测试素材）**

卡片文本从 `B:\personas.py` 的 PERSONAS 字典**逐字拷贝**（persona/playbook 原文），包装成函数：

```python
# tests/fixtures.py
"""共享测试素材。卡片文本逐字取自蓝本 personas.py（已验证人设资产）。"""


def card_zhou() -> dict:
    return {"name": "周默", "kind": "candidate",
            "role": "新人·后端开发工程师（入职第 1 周，试用期 6 个月）",
            "persona": "<逐字拷贝 B:\\personas.py 中 周默 的 persona 全文>",
            "playbook": ["<逐字拷贝 周默 playbook 7 条>"]}


def card_shen() -> dict:
    return {"name": "沈雯", "kind": "counterpart",
            "role": "直属上级·后端组组长（带 6 人，周默的汇报对象）",
            "persona": "<逐字拷贝 B:\\personas.py 中 沈雯 的 persona 全文>",
            "playbook": ["<逐字拷贝 沈雯 playbook 6 条>"]}


def card_colleague() -> dict:
    return {"name": "陈磊", "kind": "colleague",
            "role": "同事·后端组资深工程师（负责订单模块，坐周默斜对面）",
            "persona": ("你是陈磊，30 岁，后端组资深工程师，进公司四年，负责订单模块。"
                        "你技术好、说话直，看不惯绕弯子；新人问到点子上你会倾囊相授，"
                        "问得敷衍你就丢一句'文档里有'。你最反感别人动你模块的代码不打招呼。"
                        "你跟沈雯共事三年，配合默契但偶尔顶嘴。你不掺和办公室政治，"
                        "评价人只看代码和担当。"),
            "playbook": [
                "如果新人带着自己的尝试来问 → 指出关键点，顺手给文档链接。",
                "如果新人没做功课就问 → 回'文档里有'，观察他下一步。",
                "如果有人未打招呼改你模块 → 当场指出，要求走评审流程。",
                "如果会上意见和沈雯相左 → 直说理由，对事不对人。",
                "如果看到新人扛住了脏活 → 私下跟沈雯提一句他的好。"]}
```

> ⚠ 执行注意：`<逐字拷贝…>` 占位必须在执行时用 Read 工具读 `B:\personas.py` 后替换为原文，**禁止凭记忆默写**。陈磊卡是新写的（蓝本没有），上面就是全文，照抄即可。

- [ ] **Step 3: 跑测试确认失败** → FAIL（ModuleNotFoundError: sandbox3.cast）

- [ ] **Step 4: 写 cast.py 实现**

```python
# sandbox3/cast.py
"""名单制角色注册表（多人原生底座：双人=N=2 特例）。
设计要点：引擎显式接收 Cast 对象（无模块全局变量）；candidate（观察主体）有且仅有一个。"""
from __future__ import annotations
import json
import pathlib
from dataclasses import dataclass

from .config import DATA_DIR, MAX_CAST

KINDS = ("candidate", "counterpart", "colleague")


class CastError(ValueError):
    pass


@dataclass(frozen=True)
class Card:
    name: str
    kind: str
    role: str
    persona: str
    playbook: tuple[str, ...]


class Cast:
    def __init__(self, cards: list[Card]):
        self._cards = cards

    # ---- 构造与校验 ----
    @classmethod
    def from_cards(cls, raw_cards: list[dict]) -> "Cast":
        if not 2 <= len(raw_cards) <= MAX_CAST:
            raise CastError(f"名单需 2-{MAX_CAST} 人，得到 {len(raw_cards)}")
        cards, names = [], set()
        for rc in raw_cards:
            for k in ("name", "kind", "role", "persona", "playbook"):
                if not rc.get(k):
                    raise CastError(f"角色卡缺字段 {k}：{rc.get('name', '?')}")
            if rc["kind"] not in KINDS:
                raise CastError(f"kind 越界（{rc['kind']!r}），须为 {KINDS}")
            if not isinstance(rc["playbook"], list) or not 3 <= len(rc["playbook"]) <= 9:
                raise CastError(f"{rc['name']} 的 playbook 需为 3-9 条列表")
            if rc["name"] in names:
                raise CastError(f"人名重复：{rc['name']}")
            names.add(rc["name"])
            cards.append(Card(str(rc["name"]), rc["kind"], str(rc["role"]),
                              str(rc["persona"]), tuple(str(r) for r in rc["playbook"])))
        cands = [c for c in cards if c.kind == "candidate"]
        if len(cands) != 1:
            raise CastError(f"candidate（观察主体）须有且仅有 1 个，得到 {len(cands)}")
        return cls(cards)

    @classmethod
    def load_default(cls) -> "Cast":
        p = DATA_DIR / "cast_default.json"
        return cls.from_cards(json.loads(p.read_text(encoding="utf-8")))

    # ---- 查询 ----
    def members(self) -> list[Card]:
        return list(self._cards)

    def candidate(self) -> Card:
        return next(c for c in self._cards if c.kind == "candidate")

    def others(self) -> list[Card]:
        return [c for c in self._cards if c.kind != "candidate"]

    def names(self) -> list[str]:
        return [c.name for c in self._cards]

    def get(self, name: str) -> Card:
        try:
            return next(c for c in self._cards if c.name == name)
        except StopIteration:
            raise CastError(f"名单上没有 {name!r}") from None

    def persona_block(self, name: str) -> str:
        c = self.get(name)
        rules = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(c.playbook))
        return f"【身份】{c.role}\n【人设】{c.persona}\n【行为手册（如果…就…）】\n{rules}"
```

- [ ] **Step 5: 导出 data/cast_default.json**

把 `B:\personas.py` 的周默/沈雯两张卡导出为 JSON 数组（字段 name/kind/role/persona/playbook；周默 kind=candidate、沈雯 kind=counterpart），persona/playbook **逐字**。用 Write 工具落 UTF-8。

- [ ] **Step 6: 跑测试确认过** → 7 PASS

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: 名单制 Cast 注册表（candidate 唯一/kind 三类/3-9 条手册校验）+ 默认名单"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 4: ledger.py（台账：时间+在场者+知情过滤）

对应 tasks.md 1.5 的数据层。**自蓝本 engine/_visible + prompts/_ledger_text 提炼。**

**Files:**
- Create: `sandbox3/ledger.py`、`tests/test_ledger.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_ledger.py
import unittest

from sandbox3.ledger import entry, visible, ledger_text


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.led = [
            entry("入职第1周·周三", "第1幕[接活]：摘要A", ["周默", "沈雯"]),
            entry("入职第1周·周五", "第1幕后果结算：私聊 → 结果", ["沈雯", "陈磊"]),
        ]

    def test_visible_filters_by_witness(self):
        self.assertEqual(len(visible(self.led, "周默")), 1)
        self.assertEqual(len(visible(self.led, "沈雯")), 2)
        self.assertEqual(len(visible(self.led, "路人")), 0)

    def test_text_with_time_prefix(self):
        t = ledger_text(self.led)
        self.assertIn("[入职第1周·周三]", t)
        self.assertNotIn("在场", t)

    def test_text_with_witnesses(self):
        t = ledger_text(self.led, show_witnesses=True)
        self.assertIn("（在场：沈雯、陈磊）", t)

    def test_empty_message(self):
        self.assertEqual(ledger_text([]), "（尚无可引用的既往事件）")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败** → FAIL

- [ ] **Step 3: 实现**

```python
# sandbox3/ledger.py
"""滚动台账=唯一可引用的既往事实。条目带时间戳+在场者；
知情过滤是信息防火墙的数据层：agent 只见亲历条目（物理隔离，不靠模型自觉）。"""
from __future__ import annotations


def entry(time: str, text: str, witnesses: list[str]) -> dict:
    return {"time": time, "text": text, "witnesses": list(witnesses)}


def visible(ledger: list[dict], actor: str) -> list[dict]:
    """角色只记得标注他在场的台账事件。"""
    return [e for e in ledger if actor in (e.get("witnesses") or [])]


def ledger_text(ledger: list[dict], show_witnesses: bool = False) -> str:
    if not ledger:
        return "（尚无可引用的既往事件）"
    lines = []
    for e in ledger:
        w = f"（在场：{'、'.join(e['witnesses'])}）" if show_witnesses and e.get("witnesses") else ""
        lines.append(f"- [{e.get('time', '?')}] {e['text']}{w}")
    return "\n".join(lines)
```

- [ ] **Step 4: 跑测试确认过** → 4 PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: ledger 台账（时间戳+在场者+知情过滤）"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 5: scenes.py（场景库：预设迁移 + 持久化 + 去重）

对应 tasks.md 1.7 / 5.1。

**Files:**
- Create: `sandbox3/scenes.py`、`data/scene_bank.json`、`tests/test_scenes.py`

- [ ] **Step 1: 导出预设数据**

读 `B:\bank.py`，把其中 BANK 列表的 **12 条场景逐字**导出为 `data/scene_bank.json`（JSON 数组，字段 id/category/title/sketch/owner_hints 原样）。CATEGORIES 常量见 Step 3 代码。

- [ ] **Step 2: 写失败测试**

```python
# tests/test_scenes.py
import tempfile, pathlib, unittest

from sandbox3 import scenes as S


class TestSceneBank(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.bank = S.SceneBank(custom_path=self.tmp / "custom.json")

    def test_presets_loaded(self):
        self.assertEqual(len(self.bank.all()), 12)
        self.assertEqual(len({t["id"] for t in self.bank.all()}), 12)

    def test_by_id(self):
        self.assertEqual(self.bank.by_id("C1-01")["category"], "初来乍到")

    def test_add_custom_persists(self):
        sc = self.bank.add_custom({"title": "新场景", "category": "现代职场",
                                   "sketch": "素描", "owner_hints": "提示"})
        self.assertTrue(sc["id"].startswith("X-"))
        bank2 = S.SceneBank(custom_path=self.tmp / "custom.json")
        self.assertIn(sc["id"], {t["id"] for t in bank2.all()})

    def test_duplicate_title_suffixed(self):
        self.bank.add_custom({"title": "撞名", "category": "现代职场", "sketch": "a", "owner_hints": ""})
        sc2 = self.bank.add_custom({"title": "撞名", "category": "现代职场", "sketch": "b", "owner_hints": ""})
        self.assertNotEqual(sc2["title"], "撞名")

    def test_bad_category_falls_back(self):
        sc = self.bank.add_custom({"title": "x", "category": "不存在", "sketch": "s", "owner_hints": ""})
        self.assertEqual(sc["category"], "现代职场")

    def test_candidates_excludes_used(self):
        cands = self.bank.candidates(["初来乍到"], used={"C1-01"})
        self.assertNotIn("C1-01", {c["id"] for c in cands})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 实现 scenes.py**

```python
# sandbox3/scenes.py
"""场景库：12 条预设（data/scene_bank.json，蓝本逐字迁移）+ 自定义持久化。
去重从简：同名加后缀（作者拍，不上相似度算法）。"""
from __future__ import annotations
import json
import pathlib

from .config import DATA_DIR

CATEGORIES = ("初来乍到", "磨合建制", "压力测试", "冲突与修复", "深化里程碑", "现代职场")
_PRESET_PATH = DATA_DIR / "scene_bank.json"


class SceneBank:
    def __init__(self, custom_path: pathlib.Path | None = None):
        self.custom_path = custom_path or (DATA_DIR / "custom_scenes.json")
        self._presets = json.loads(_PRESET_PATH.read_text(encoding="utf-8"))
        self._custom: list[dict] = []
        if self.custom_path.exists():
            self._custom = json.loads(self.custom_path.read_text(encoding="utf-8"))

    def all(self) -> list[dict]:
        return self._presets + self._custom

    def by_id(self, sid: str) -> dict:
        for t in self.all():
            if t["id"] == sid:
                return t
        raise KeyError(f"场景 {sid!r} 不存在")

    def candidates(self, categories: list[str], used: set[str]) -> list[dict]:
        return [t for t in self.all() if t["category"] in categories and t["id"] not in used] \
            or [t for t in self.all() if t["id"] not in used]

    def add_custom(self, raw: dict) -> dict:
        title = str(raw.get("title") or "自定义场景")
        existing = {t["title"] for t in self.all()}
        n, t2 = 2, title
        while t2 in existing:
            t2 = f"{title}·{n}"
            n += 1
        scene = {"id": f"X-{len(self._custom) + 1:02d}", "title": t2,
                 "category": raw.get("category") if raw.get("category") in CATEGORIES else "现代职场",
                 "sketch": str(raw.get("sketch") or ""),
                 "owner_hints": str(raw.get("owner_hints") or "")}
        self._custom.append(scene)
        self.custom_path.parent.mkdir(parents=True, exist_ok=True)
        self.custom_path.write_text(json.dumps(self._custom, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
        return scene
```

- [ ] **Step 4: 跑测试确认过** → 6 PASS（先跑失败再实现的节奏同前，此处合并表述）

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: 场景库（12 预设迁移+自定义持久化+同名去重）"
```

### Task 6: prompts/（搬运 + 格子泛化）

对应 tasks.md 1.4/1.5/1.6 的提示词层。**纪律：逐字搬，只做下面明确列出的泛化改动。**

**Files:**
- Create: `sandbox3/prompts/__init__.py`、`sandbox3/prompts/sm.py`、`sandbox3/prompts/agent.py`
- Create: `tests/test_prompts.py`

**搬运总表**（源=`B:\prompts.py`，全部先 Read 原文再搬，禁默写）：

| 蓝本对象 | 去向 | 改动 |
|---|---|---|
| `SCENE_INIT_SYSTEM` | sm.py | 逐字（含防火墙硬约束段） |
| `scene_init_user` | sm.py | **泛化①**：人物块按 cast 循环；goal 字段改 goals 字典（见下） |
| `advance_system` | sm.py | **泛化②**：行动方规矩按 kind 措辞（见下） |
| `advance_user` | sm.py | 泛化①：两位角色块 → 名单循环 |
| `SETTLE_SYSTEM` / `settle_user` | sm.py | **泛化③**：schema 增 relations（关系细目，作者拍"单灯+细目入档"） |
| `CONSEQUENCE_*` / `NEXT_TP_*` / `COCREATE_*` / `CRYSTALLIZE_*` | sm.py | 逐字 |
| `appraisal_system/user`、`decision_system/user` | agent.py | 逐字（persona_block 改从 cast 取） |
| `AUDIT_SYSTEM` / `audit_user` | agent.py | 逐字（含四查+心口缝段；手册从 cast 卡取） |
| `_ledger_text` | 删 | 已在 ledger.py |
| `_state_text` / `_beats_text` / `EMOTION_KEYS` | sm.py（agent.py import） | 逐字 |

**泛化①（人物块循环）**——`scene_init_user` 人物段与 goals 改为：

```python
def scene_init_user(tp: dict, ledger: list[dict], state: dict, cast, jd: str = "",
                    prev_time: str = "") -> str:
    jd_block = f"【岗位/团队背景（JD，供设定参考）】\n{jd}\n\n" if jd else ""
    time_block = (f"【时间线】上一幕时间：{prev_time}；本幕时间必须在其之后，只许向前推进、不得倒流。\n\n"
                  if prev_time else "【时间线】这是第一幕，从'入职第1周'附近起算。\n\n")
    people = "\n\n".join(f"【{c.name}（{c.role}）】\n{cast.persona_block(c.name)}"
                         for c in cast.members())
    goals_json = ", ".join(f'"{c.name}": "{c.name}在本幕想要什么"' for c in cast.members())
    return (
        f"【本幕转折点】[{tp['category']}] {tp['title']}：{tp['sketch']}\n"
        f"【双方天然节骨眼提示】{tp.get('owner_hints', '')}\n\n"
        f"{time_block}{jd_block}{people}\n\n"
        f"【既往事件台账（唯一可引用的过往事实）】\n{ledger_text(ledger, show_witnesses=True)}\n\n"
        f"【当前关系状态灯】\n{_state_text(state)}\n\n"
        "输出 JSON（字段全部用中文内容填写）：\n"
        "{\n"
        '  "theme": "本幕主题一句话",\n'
        '  "sim_time": "本幕时间（格式：入职第X周·周几·时段，如：入职第2周·周四下午）",\n'
        '  "setting": "时间地点与情境",\n'
        '  "npc": ["卷入的第三方人物，可为空数组"],\n'
        '  "current_scene": "场景开场的具体描述（3-5句，含利害与张力）",\n'
        f'  "goals": {{{goals_json}}},\n'
        '  "scene_conflict": "本幕的核心冲突一句话"\n'
        "}"
    )
```

> 其余 user 函数照同样手法：凡蓝本里出现 `P.NEWCOMER`/`P.COUNTERPART` 的人物块，改为按 `cast.members()` 循环；凡取 persona/playbook 的，改为 `cast.persona_block(name)`/`cast.get(name).playbook`。措辞一个字不动。

**泛化②（行动方规矩按 kind）**——`advance_system` 中蓝本的两人规矩段替换为：

```python
def advance_system(cast) -> str:
    cand = cast.candidate().name
    others = "、".join(c.name for c in cast.others())
    return (
        "你是职场关系推演的场景主持人（Scene Master）。一幕由 1-3 个'节骨眼回合'组成。"
        "你的任务：接着本幕已发生的回合，把场景自然推进到下一个'必须有人行动'的节骨眼；"
        "若核心冲突已走到自然段落（双方都已亮明行动、或事件告一段落），则宣布收幕。\n"
        "推进纪律：只描述客观可见的事件与对话氛围，不替任何角色做出节骨眼上的关键决定；"
        "只准引用台账中已结算的既往事实，不得虚构过往互动细节。\n"
        "【信息防火墙（硬约束）】任何角色的叙事、念头、选项不得引用其知情范围外的信息"
        "（知情范围=自己人设+台账中标注他在场的事件+本幕他亲历的回合）；"
        "他人的私密设定不得以传闻、直觉、巧合、'脑子里闪过'等形式凭空泄入——"
        "私密信息进入他人认知必须有舞台上可观察的来源。\n"
        f"【行动方规矩（硬约束）】凡上级或同事侧的关键决定——派活方式、收不收活、给不给机会、"
        f"反馈方式、挡不挡刀、透不透信息——节骨眼必须交给该角色本人（{others}）行动，"
        f"不得在叙事中代笔拍板；同理，新人侧的关键决定必须交给{cand}本人。"
        "一幕内冲突自然涉及多方时，应让相关各方先后各自面对节骨眼。\n"
        "选项硬约束：互斥（不能同时做）；单行动者（只涉及行动者本人的行为）；"
        "可观察（外显行为，不是心理活动）；各自通向明显不同的关系后果；"
        "都在该角色人设的可能范围内，但要覆盖从稳妥到冒险的方向差异。\n"
        "只输出 JSON。"
    )
```

`advance_user` 的 `acting_agent` 示例值改为 `"名单中任一人名（{', '.join(cast.names())}）"`。

**泛化③（收场加关系细目）**——`SETTLE_SYSTEM` 在差量判读规则后追加一句：
`"另外为候选人与每位其他成员的关系给出态度细目（supportive/neutral/opposed + 一句话证据）——细目只入档案，不是状态灯。"`
`settle_user` 输出 schema 增加：

```
'  "relations": {"<其他成员名>": {"attitude": "supportive/neutral/opposed", "evidence": "一句话证据"}},\n'
```

（成员名循环 `cast.others()` 生成。）其余差量 schema（state_changes/witnesses/commitment）逐字保留。

- [ ] **Step 1: 写失败测试 tests/test_prompts.py**

```python
# tests/test_prompts.py
import unittest

from sandbox3.cast import Cast
from sandbox3.prompts import sm, agent
from sandbox3.states import initial_state
from tests.fixtures import card_zhou, card_shen, card_colleague


class TestPromptGeneralization(unittest.TestCase):
    def setUp(self):
        self.cast2 = Cast.from_cards([card_zhou(), card_shen()])
        self.cast3 = Cast.from_cards([card_zhou(), card_shen(), card_colleague()])

    def test_scene_init_contains_all_members(self):
        tp = {"category": "初来乍到", "title": "t", "sketch": "s", "owner_hints": ""}
        u = sm.scene_init_user(tp, [], initial_state(), self.cast3)
        for name in ("周默", "沈雯", "陈磊"):
            self.assertIn(name, u)
        self.assertIn('"sim_time"', u)

    def test_advance_system_names_others(self):
        s = sm.advance_system(self.cast3)
        self.assertIn("沈雯、陈磊", s)
        self.assertIn("信息防火墙", s)

    def test_settle_has_relations_for_others(self):
        u = sm.settle_user({"theme": "x"}, [], initial_state(), self.cast3)
        self.assertIn('"relations"', u)
        self.assertIn("陈磊", u)
        self.assertIn('"state_changes"', u)   # 差量制保留

    def test_audit_has_four_checks_and_gap(self):
        self.assertIn("信息越权", agent.AUDIT_SYSTEM)
        self.assertIn("心口缝", agent.AUDIT_SYSTEM)
        self.assertIn("只记录", agent.AUDIT_SYSTEM)

    def test_decision_schema_unchanged(self):
        u = agent.decision_user("想法", {"current_scene": ""}, [], "n", "j", [],
                                [{"id": "A", "text": "a"}], )
        self.assertIn('"action_id"', u)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑失败 → 按搬运总表实现 sm.py / agent.py → 跑过**

Run: `python -m unittest tests.test_prompts -v` → 5 PASS

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "port: prompts 逐字搬+三处格子泛化（人物循环/行动方按kind/收场加relations）"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 7: audit.py（审计调用组装）

对应 tasks.md 1.6。

**Files:**
- Create: `sandbox3/audit.py`、`tests/test_audit.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_audit.py
import unittest

from sandbox3.audit import run_audit
from sandbox3.cast import Cast
from tests.fakes import FakeLLM
from tests.fixtures import card_zhou, card_shen

GOOD = {"playbook_match": ["第1条"], "playbook_conflict": "无",
        "thought_consistency": "一致", "thought_note": "ok", "fabricated_cues": [],
        "info_overreach": "无", "inner_gap": "无", "verdict": "通过", "note": "ok"}


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.cast = Cast.from_cards([card_zhou(), card_shen()])
        self.kw = dict(actor="周默", internal_thoughts="t", scene={"current_scene": ""},
                       transcript=[], narration="n", juncture="j",
                       visible_ledger=[], hidden_ledger=[],
                       options=[{"id": "A", "text": "x"}],
                       decision={"action_id": "A", "action": "x", "reasoning": "r"})

    def test_passthrough(self):
        a, warns = run_audit(FakeLLM([GOOD]), self.cast, **self.kw)
        self.assertEqual(a["verdict"], "通过")
        self.assertEqual(warns, [])

    def test_bad_verdict_coerced_to_flag(self):
        bad = dict(GOOD, verdict="大概通过")
        a, warns = run_audit(FakeLLM([bad]), self.cast, **self.kw)
        self.assertEqual(a["verdict"], "黄旗")
        self.assertEqual(len(warns), 1)

    def test_hidden_ledger_in_prompt(self):
        fake = FakeLLM([GOOD])
        kw = dict(self.kw, hidden_ledger=[{"time": "t", "text": "秘密事件", "witnesses": ["沈雯"]}])
        run_audit(fake, self.cast, **kw)
        self.assertIn("秘密事件", fake.calls[0][1])     # 范围外块给审计员看（仅供越权对账）


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 实现**

```python
# sandbox3/audit.py
"""理由审计员（独立调用，只标记不改判）。verdict 越界保守落黄旗。"""
from __future__ import annotations

from .prompts import agent as A

VERDICTS = ("通过", "黄旗")


def run_audit(llm, cast, *, actor: str, internal_thoughts: str, scene: dict,
              transcript: list[str], narration: str, juncture: str,
              visible_ledger: list[dict], hidden_ledger: list[dict],
              options: list[dict], decision: dict) -> tuple[dict, list[str]]:
    audit = llm.complete_json(
        A.AUDIT_SYSTEM,
        A.audit_user(cast, actor, internal_thoughts, scene, transcript, narration,
                     juncture, visible_ledger, hidden_ledger, options, decision))
    warns = []
    if audit.get("verdict") not in VERDICTS:
        warns.append(f"审计 verdict 越界（{audit.get('verdict')!r}），保守记黄旗")
        audit["verdict"] = "黄旗"
    return audit, warns
```

（`agent.audit_user` 签名在 Task 6 中接收 cast 取手册，其余逐字蓝本。）

- [ ] **Step 3: 跑过 + Commit**

```bash
git add -A && git commit -m "feat: 审计调用组装（verdict 越界保守落黄旗）"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 8: engine.py 之一——表决与呈现序（纯函数）

对应 tasks.md 1.4 的换序三问。**蓝本已验证算法逐字搬，只换类型签名。**

**Files:**
- Create: `sandbox3/engine.py`（本 Task 先落纯函数部分）、`tests/test_engine_vote.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_engine_vote.py
import random
import unittest

from sandbox3.engine import _build_presentations, _tally_votes

OPTS = [{"id": "A", "text": "甲"}, {"id": "B", "text": "乙"}, {"id": "C", "text": "丙"}]


class TestPresentations(unittest.TestCase):
    def test_three_distinct_rotations(self):
        rounds = _build_presentations(OPTS, random.Random(42))
        self.assertEqual(len(rounds), 3)
        orders = [tuple(o["orig_id"] for o in r) for r in rounds]
        self.assertEqual(len(set(orders)), 3)            # 三问顺序互不相同
        for r in rounds:
            self.assertEqual([o["id"] for o in r], ["A", "B", "C"])  # 呈现位重发 ABC

    def test_each_option_leads_once(self):
        rounds = _build_presentations(OPTS, random.Random(7))
        firsts = {r[0]["orig_id"] for r in rounds}
        self.assertEqual(len(firsts), 3)                 # 每个选项各坐一次头排


class TestTally(unittest.TestCase):
    def _vote(self, rnd, orig):
        return {"round": rnd, "orig_id": orig, "position": "A", "reasoning": "", "confidence": 80}

    def test_majority(self):
        votes = [self._vote(1, "B"), self._vote(2, "A"), self._vote(3, "B")]
        s = _tally_votes(votes)
        self.assertEqual((s["verdict"], s["winner_orig_id"], s["winner_round"]), ("多数票", "B", 1))

    def test_unanimous(self):
        votes = [self._vote(i, "C") for i in (1, 2, 3)]
        self.assertEqual(_tally_votes(votes)["verdict"], "全票")

    def test_sway_takes_round1(self):
        votes = [self._vote(1, "A"), self._vote(2, "B"), self._vote(3, "C")]
        s = _tally_votes(votes)
        self.assertEqual((s["verdict"], s["winner_orig_id"]), ("摇摆", "A"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 实现（engine.py 顶部）**

```python
# sandbox3/engine.py
"""推演循环（名单制多人原生底座；蓝本=relate_mvp engine.py，机制行为等价迁移）。
机制清单：受控选项决策 / 换序三问取多数票 / 差量状态灯 / 防火墙（知情过滤）/
理由审计（独立调用）/ 台账时间线 / 后果结算 / ≥3灯黄旗。
依赖注入：run_simulation(cast=名单, llm=客户端, bank=场景库)——测试喂 FakeLLM，运行时唯一路径=DeepSeek live。"""
from __future__ import annotations
import random
import sys

from . import audit as AU
from .cast import Cast
from .config import MAX_BEATS, VOTE_ROUNDS
from .ledger import entry, ledger_text, visible
from .prompts import agent as PA
from .prompts import sm as PS
from .states import initial_state, apply_state_deltas, plausible_categories


def _log(msg: str) -> None:
    print(msg, flush=True)


def _coerce_options(raw) -> list[dict]:
    opts = []
    if isinstance(raw, list):
        for i, o in enumerate(raw):
            if isinstance(o, dict) and o.get("text"):
                opts.append({"id": str(o.get("id") or "ABCD"[i % 4]), "text": str(o["text"])})
    return opts


def _build_presentations(options: list[dict], rng: random.Random) -> list[list[dict]]:
    """洗牌一次得第1问呈现序，再逐问轮转——三问顺序互不相同、每个选项换坑位。
    每问按呈现位次重发 A/B/C/D，保留 orig_id 供对账。"""
    base = options[:]
    rng.shuffle(base)
    rounds = []
    for r in range(VOTE_ROUNDS):
        k = r % len(base)
        rot = base[k:] + base[:k]
        rounds.append([{"id": "ABCD"[i], "text": o["text"], "orig_id": o["id"]}
                       for i, o in enumerate(rot)])
    return rounds


def _tally_votes(votes: list[dict]) -> dict:
    """按内容（orig_id）计票：全票/多数票/摇摆（摇摆取第1问，入档是信号不是噪声）。"""
    tally: dict[str, int] = {}
    for v in votes:
        tally[v["orig_id"]] = tally.get(v["orig_id"], 0) + 1
    top = max(tally.values())
    verdict = "全票" if top == len(votes) else ("多数票" if top >= 2 else "摇摆")
    winner = next(v for v in votes if tally[v["orig_id"]] == top)
    return {"rounds": len(votes), "tally": tally, "verdict": verdict,
            "winner_orig_id": winner["orig_id"], "winner_round": winner["round"]}
```

- [ ] **Step 3: 跑过 + Commit**

```bash
git add -A && git commit -m "feat: 引擎纯函数——轮转呈现序+按内容计票（蓝本算法等价+测试守门）"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 9: engine.py 之二——run_simulation 全量

对应 tasks.md 1.4/1.5/1.6/1.8 接线。**核心编排，全文如下（接在 Task 8 代码之后）。**

**Files:**
- Modify: `sandbox3/engine.py`（追加）
- Create: `tests/test_engine_run.py`

- [ ] **Step 1: 实现 run_simulation（完整代码）**

```python
AUDIT_VERDICTS = ("通过", "黄旗")


def _vote_decision(*, llm, cast: Cast, actor: str, internal_thoughts: str, scene: dict,
                   transcript: list[str], narration: str, juncture: str,
                   vis_ledger: list[dict], presentations: list[list[dict]],
                   warnings: list[str]) -> tuple[dict, list[dict], dict]:
    """换序三问：并发问 VOTE_ROUNDS 次（线程池），按内容取多数。
    官方决策 action_id 映射回第1问呈现序（页面展示序）。"""
    from concurrent.futures import ThreadPoolExecutor

    def ask(presented):
        return llm.complete_json(
            PA.decision_system(cast, actor),
            PA.decision_user(internal_thoughts, scene, transcript, narration,
                             juncture, vis_ledger, presented))
    with ThreadPoolExecutor(max_workers=len(presentations)) as ex:
        raw = list(ex.map(ask, presentations))
    votes, decs = [], []
    for rnd, (presented, dec) in enumerate(zip(presentations, raw), 1):
        if dec.get("action_id") not in {o["id"] for o in presented}:
            warnings.append(f"第{rnd}问 action_id 越界（{dec.get('action_id')!r}），落该问呈现序第一个")
            dec["action_id"] = presented[0]["id"]
        chosen = next(o for o in presented if o["id"] == dec["action_id"])
        votes.append({"round": rnd, "order": [o["orig_id"] for o in presented],
                      "position": dec["action_id"], "orig_id": chosen["orig_id"],
                      "reasoning": dec.get("reasoning", ""), "confidence": dec.get("confidence")})
        decs.append(dec)
    summary = _tally_votes(votes)
    if summary["verdict"] == "摇摆":
        warnings.append("换序三问答案各不相同（摇摆），取第1问的选择继续；摇摆已入档")
    dec = decs[summary["winner_round"] - 1]
    dec["action_id"] = next(o["id"] for o in presentations[0]
                            if o["orig_id"] == summary["winner_orig_id"])
    dec["chosen_orig_id"] = summary["winner_orig_id"]
    return dec, votes, summary


def _run_beat(*, llm, cast: Cast, beat_no: int, scene_idx: int, scene: dict, tp: dict,
              ledger: list[dict], state: dict, transcript: list[str],
              rng: random.Random, counters: dict, emit) -> dict | None:
    emit({"type": "status", "text": "场景导演正在把剧情推进到节骨眼…"})
    adv = llm.complete_json(PS.advance_system(cast),
                            PS.advance_user(scene, tp, ledger, state, transcript,
                                            beat_no, MAX_BEATS, cast))
    counters["calls"] += 1
    narration = str(adv.get("narration", ""))
    if adv.get("scene_over"):
        if beat_no == 1:
            counters["warnings"].append("第1回合即收幕（违反推进规矩），本幕无任何行动")
        if narration:
            transcript.append(f"（收幕）{narration}")
        return None

    beat: dict = {"beat": beat_no, "narration": narration,
                  "juncture": str(adv.get("juncture", "")), "warnings": []}
    actor = adv.get("acting_agent", "")
    if actor not in cast.names():
        beat["warnings"].append(f"acting_agent 越界（{actor!r}），落候选人")
        actor = cast.candidate().name
    beat["acting_agent"] = actor

    options = _coerce_options(adv.get("options"))
    if not options:
        raise RuntimeError(f"回合 {beat_no} 没有产出任何可用选项，中止")
    if not 3 <= len(options) <= 4:
        beat["warnings"].append(f"选项数异常（{len(options)} 个），照常继续")
    rounds = _build_presentations(options, rng)
    presented = rounds[0]
    beat["options_original"] = options
    beat["options"] = presented
    emit({"type": "beat_open", "scene": scene_idx, "beat": beat_no, "narration": narration,
          "juncture": beat["juncture"], "actor": actor, "options": presented})

    vis_ledger = visible(ledger, actor)
    hid_ledger = [e for e in ledger if e not in vis_ledger]
    emit({"type": "status", "text": f"{actor} 心里正在过这件事…"})
    appr = llm.complete_json(PA.appraisal_system(cast, actor),
                             PA.appraisal_user(scene, transcript, narration,
                                               beat["juncture"], vis_ledger))
    counters["calls"] += 1
    beat["appraisal"] = appr
    emit({"type": "inner", "scene": scene_idx, "beat": beat_no, "actor": actor,
          "emotions": appr.get("emotions", {}),
          "internal_thoughts": appr.get("internal_thoughts", "")})

    emit({"type": "status", "text": f"{actor} 正在换序三问中作答（防位置偏置，取多数票）…"})
    dec, votes, vote_summary = _vote_decision(
        llm=llm, cast=cast, actor=actor,
        internal_thoughts=appr.get("internal_thoughts", ""), scene=scene,
        transcript=transcript, narration=narration, juncture=beat["juncture"],
        vis_ledger=vis_ledger, presentations=rounds, warnings=beat["warnings"])
    counters["calls"] += len(rounds)
    beat["votes"] = votes
    beat["vote_summary"] = vote_summary
    beat["decision"] = dec
    emit({"type": "decision", "scene": scene_idx, "beat": beat_no, "actor": actor,
          "action_id": dec["action_id"], "action": dec.get("action", ""),
          "reasoning": dec.get("reasoning", ""), "confidence": dec.get("confidence"),
          "emotion_tags": dec.get("emotion_tags") or [],
          "vote_verdict": vote_summary["verdict"], "vote_tally": vote_summary["tally"],
          "votes": [{"round": v["round"], "orig_id": v["orig_id"],
                     "position": v["position"], "confidence": v["confidence"]} for v in votes]})

    emit({"type": "status", "text": "理由审计员正在对账…"})
    audit, awarns = AU.run_audit(llm, cast, actor=actor,
                                 internal_thoughts=appr.get("internal_thoughts", ""),
                                 scene=scene, transcript=transcript, narration=narration,
                                 juncture=beat["juncture"], visible_ledger=vis_ledger,
                                 hidden_ledger=hid_ledger, options=presented, decision=dec)
    counters["calls"] += 1
    beat["warnings"].extend(awarns)
    beat["audit"] = audit
    emit({"type": "audit", "scene": scene_idx, "beat": beat_no, **{
        k: audit.get(k) for k in ("verdict", "playbook_match", "playbook_conflict",
                                  "thought_consistency", "thought_note", "fabricated_cues",
                                  "info_overreach", "inner_gap", "note")}})

    transcript.append(
        f"{narration}\n节骨眼：{beat['juncture']}\n"
        f"{actor} 选择：[{dec['action_id']}] {dec.get('action', '')}（理由：{dec.get('reasoning', '')}）")
    _log(f"   回合{beat_no} [{actor}] 三问 {'/'.join(v['orig_id'] for v in votes)}"
         f" → 取原序{vote_summary['winner_orig_id']}（{vote_summary['verdict']}）　审计：{audit['verdict']}")
    return beat


def run_simulation(*, cast: Cast, llm, bank, n_scenes: int = 4, start_tp: str = "C1-01",
                   seed: int | None = None, jd: str = "", emit=None) -> dict:
    """跑一条推演轨迹。emit(event_dict)=直播回调（None 则静默）。"""
    emit = emit or (lambda e: None)
    rng = random.Random(seed)
    state = initial_state()
    ledger: list[dict] = []
    sim_time = ""
    used: set[str] = set()
    tp = bank.by_id(start_tp)
    scenes: list[dict] = []
    counters = {"calls": 0, "warnings": []}
    emit({"type": "run_started", "n_scenes": n_scenes, "start_tp": start_tp, "seed": seed,
          "cast": [{"name": c.name, "kind": c.kind, "role": c.role} for c in cast.members()],
          "candidate": cast.candidate().name})

    for idx in range(n_scenes):
        _log(f"—— 第 {idx + 1}/{n_scenes} 幕 [{tp['category']}] {tp['title']} ——")
        rec: dict = {"index": idx + 1, "turning_point": tp, "warnings": []}

        emit({"type": "status", "text": "场景导演正在搭景…"})
        scene = llm.complete_json(PS.SCENE_INIT_SYSTEM,
                                  PS.scene_init_user(tp, ledger, state, cast,
                                                     jd=jd, prev_time=sim_time))
        counters["calls"] += 1
        rec["scene"] = scene
        if scene.get("sim_time"):
            sim_time = str(scene["sim_time"])
        else:
            rec["warnings"].append("SM 未报 sim_time，本幕沿用上一幕时间标注")
            sim_time = sim_time or f"入职初期（第{idx + 1}幕，SM 未报时间）"
        rec["sim_time"] = sim_time
        _log(f"   场景：[{sim_time}] {scene.get('setting', '?')}")
        emit({"type": "scene_open", "scene": idx + 1, "tp": tp, "sim_time": sim_time,
              "setting": scene.get("setting", ""), "current_scene": scene.get("current_scene", ""),
              "scene_conflict": scene.get("scene_conflict", ""), "npc": scene.get("npc") or []})

        transcript: list[str] = []
        beats: list[dict] = []
        for b in range(1, MAX_BEATS + 1):
            beat = _run_beat(llm=llm, cast=cast, beat_no=b, scene_idx=idx + 1, scene=scene,
                             tp=tp, ledger=ledger, state=state, transcript=transcript,
                             rng=rng, counters=counters, emit=emit)
            if beat is None:
                break
            beats.append(beat)
            rec["warnings"].extend(beat["warnings"])
        rec["beats"] = beats
        if not beats:
            raise RuntimeError(f"第{idx + 1}幕没有任何行动回合，中止")

        emit({"type": "status", "text": "记录者正在收场：判状态灯、估承诺…"})
        settle = llm.complete_json(PS.SETTLE_SYSTEM,
                                   PS.settle_user(scene, transcript, state, cast))
        counters["calls"] += 1
        new_state, evidence, warns = apply_state_deltas(settle.get("state_changes"), state)
        rec["warnings"].extend(warns)
        changed = {k: (state[k], new_state[k]) for k in state if state[k] != new_state[k]}
        if len(changed) >= 3:
            rec["warnings"].append(f"单幕 {len(changed)} 盏灯变化（≥3），判读偏宽嫌疑，需人工复核")
        try:
            commitment = max(0.0, min(5.0, float(settle.get("commitment"))))
        except (TypeError, ValueError):
            rec["warnings"].append(f"commitment 非数（{settle.get('commitment')!r}），记 None")
            commitment = None
        valid_names = set(cast.names()) | {str(n) for n in (scene.get("npc") or [])}
        wit = [str(w) for w in (settle.get("witnesses") or []) if str(w) in valid_names]
        if not wit:
            rec["warnings"].append(f"witnesses 缺失/越界（{settle.get('witnesses')!r}），落全名单")
            wit = cast.names()
        relations = {}
        for name, rel in (settle.get("relations") or {}).items():
            if name in cast.names() and name != cast.candidate().name and isinstance(rel, dict) \
                    and rel.get("attitude") in ("supportive", "neutral", "opposed"):
                relations[name] = {"attitude": rel["attitude"], "evidence": str(rel.get("evidence", ""))}
        rec.update({"states": new_state, "evidence": evidence, "state_changes": changed,
                    "witnesses": wit, "relations": relations, "commitment": commitment,
                    "commitment_rationale": settle.get("commitment_rationale", ""),
                    "scene_summary": settle.get("scene_summary", "")})
        state = new_state
        _log(f"   状态变化：{ {k: f'{a}->{b}' for k, (a, b) in changed.items()} or '无'}；承诺：{commitment}")
        emit({"type": "settle", "scene": idx + 1, "states": new_state,
              "changes": {k: list(v) for k, v in changed.items()},
              "evidence": evidence, "commitment": commitment,
              "rationale": rec["commitment_rationale"], "summary": rec["scene_summary"],
              "witnesses": wit, "sim_time": sim_time, "relations": relations,
              "warnings": rec["warnings"]})

        emit({"type": "status", "text": "记录者正在结算悬而未决的后果…"})
        conseq = llm.complete_json(PS.CONSEQUENCE_SYSTEM,
                                   PS.consequence_user(scene, transcript, rec["scene_summary"]))
        counters["calls"] += 1
        cons = [c for c in (conseq.get("consequences") or [])
                if isinstance(c, dict) and c.get("matter") and c.get("outcome")]
        rec["consequences"] = cons
        ledger.append(entry(sim_time, f"第{idx + 1}幕[{tp['title']}]：{rec['scene_summary']}", wit))
        for c in cons:
            cw = [str(w) for w in (c.get("witnesses") or []) if str(w) in valid_names]
            c["witnesses"] = cw or wit
            ledger.append(entry(sim_time, f"第{idx + 1}幕后果结算：{c['matter']} → {c['outcome']}",
                                c["witnesses"]))
        used.add(tp["id"])
        if cons:
            emit({"type": "consequence", "scene": idx + 1, "consequences": cons})

        if idx + 1 < n_scenes:
            cats = plausible_categories(state, idx + 1)
            cands = bank.candidates(cats, used)
            if not cands:
                rec["warnings"].append("转折点库耗尽，提前收束")
                scenes.append(rec)
                break
            pick = llm.complete_json(PS.NEXT_TP_SYSTEM, PS.next_tp_user(cands, ledger, state))
            counters["calls"] += 1
            cid = pick.get("choice_id")
            if cid not in {c["id"] for c in cands}:
                rec["warnings"].append(f"choice_id 越界（{cid!r}），落候选第一个")
                cid = cands[0]["id"]
            rec["next_tp"] = {"heuristic_categories": cats, "candidates": [c["id"] for c in cands],
                              "choice": cid, "why": pick.get("why", "")}
            emit({"type": "next_tp", "scene": idx + 1, "choice": cid,
                  "why": pick.get("why", ""), "categories": cats})
            tp = bank.by_id(cid)
        scenes.append(rec)
        for w in rec["warnings"]:
            print(f"   [警告] {w}", file=sys.stderr)
        counters["warnings"].extend(rec["warnings"])

    actor_counts: dict[str, int] = {}
    flags = 0
    gaps: dict[str, int] = {}
    vote_stats = {"全票": 0, "多数票": 0, "摇摆": 0}
    pos_counts: dict[str, int] = {}
    for sc in scenes:
        for bt in sc["beats"]:
            actor_counts[bt["acting_agent"]] = actor_counts.get(bt["acting_agent"], 0) + 1
            if bt["audit"].get("verdict") == "黄旗":
                flags += 1
            if (bt["audit"].get("inner_gap") or "无") not in ("无", ""):
                gaps[bt["acting_agent"]] = gaps.get(bt["acting_agent"], 0) + 1
            vote_stats[bt["vote_summary"]["verdict"]] += 1
            for v in bt["votes"]:
                pos_counts[v["position"]] = pos_counts.get(v["position"], 0) + 1
    trace = {"meta": {"model": "deepseek-chat", "n_scenes": len(scenes),
                      "n_llm_calls": counters["calls"], "seed": seed, "max_beats": MAX_BEATS,
                      "cast": [{"name": c.name, "kind": c.kind} for c in cast.members()],
                      "candidate": cast.candidate().name,
                      "vote_rounds": VOTE_ROUNDS, "vote_stats": vote_stats,
                      "vote_position_counts": pos_counts,
                      "actor_counts": actor_counts, "audit_flags": flags, "inner_gaps": gaps,
                      "warnings_total": len(counters["warnings"])},
             "final_state": state, "ledger": ledger, "scenes": scenes}
    emit({"type": "done", "meta": trace["meta"]})
    return trace
```

- [ ] **Step 2: 写集成测试 tests/test_engine_run.py（FakeLLM 全脚本一幕局）**

脚本化一幕（1 回合即收幕收不了——脚本给 2 回合后 scene_over）。用 router 按 system 关键词路由：

```python
# tests/test_engine_run.py
import unittest

from sandbox3.cast import Cast
from sandbox3.engine import run_simulation
from sandbox3.scenes import SceneBank
from tests.fakes import FakeLLM
from tests.fixtures import card_zhou, card_shen

SCENE = {"theme": "t", "sim_time": "入职第1周·周三·上午", "setting": "工位",
         "npc": [], "current_scene": "开场", "goals": {}, "scene_conflict": "冲突"}
ADV1 = {"narration": "推进1", "scene_over": False, "juncture": "节骨眼1", "acting_agent": "周默",
        "options": [{"id": "A", "text": "甲"}, {"id": "B", "text": "乙"}, {"id": "C", "text": "丙"}]}
ADV_OVER = {"narration": "收幕", "scene_over": True}
APPR = {"emotions": {"焦虑": 70}, "internal_thoughts": "心里想着乙"}
DEC_B = {"action_id": "?", "action": "做乙", "reasoning": "符合人设", "confidence": 80,
         "emotion_tags": ["谨慎"]}
AUDIT_OK = {"playbook_match": ["第1条"], "playbook_conflict": "无", "thought_consistency": "一致",
            "thought_note": "", "fabricated_cues": [], "info_overreach": "无",
            "inner_gap": "无", "verdict": "通过", "note": ""}
SETTLE = {"state_changes": {}, "scene_summary": "摘要", "witnesses": ["周默", "沈雯"],
          "relations": {"沈雯": {"attitude": "neutral", "evidence": "证据"}},
          "commitment": 3.0, "commitment_rationale": "理由"}
CONSEQ = {"consequences": []}


def router_factory():
    """按 system 提示词关键词路由 + 决策按'呈现的乙在哪个位置'返回该位（内容恒选乙）。"""
    state = {"adv": 0}
    def router(system, user):
        if "场景主持人" in system and "扩写" in system:
            return dict(SCENE)
        if "节骨眼回合" in system:
            state["adv"] += 1
            return dict(ADV1) if state["adv"] == 1 else dict(ADV_OVER)
        if "情绪评价" in system or "内部情绪" in system:
            return dict(APPR)
        if "面临一个决定" in system:
            # 找到"乙"在本问呈现序中的字母——内容稳定选乙，位置随轮转变
            for line in user.splitlines():
                for label in ("A", "B", "C", "D"):
                    if line.strip().startswith(f"{label}.") and "乙" in line:
                        return dict(DEC_B, action_id=label)
            raise AssertionError("呈现序里找不到乙")
        if "审计员" in system:
            return dict(AUDIT_OK)
        if "收场" in system:
            return dict(SETTLE)
        if "结算" in system:
            return dict(CONSEQ)
        raise AssertionError(f"未知调用：{system[:50]}")
    return router


class TestRunSimulation(unittest.TestCase):
    def setUp(self):
        self.cast = Cast.from_cards([card_zhou(), card_shen()])
        self.bank = SceneBank()
        self.events = []
        self.trace = run_simulation(cast=self.cast, llm=FakeLLM(router=router_factory()),
                                    bank=self.bank, n_scenes=1, seed=42,
                                    emit=self.events.append)

    def test_call_accounting(self):
        # 搭景1 + 回合(推进1+情绪1+三问3+审计1=6) + 收幕推进1 + 收场1 + 结算1 = 10
        self.assertEqual(self.trace["meta"]["n_llm_calls"], 10)

    def test_unanimous_content_vote_across_orders(self):
        bt = self.trace["scenes"][0]["beats"][0]
        self.assertEqual(bt["vote_summary"]["verdict"], "全票")     # 内容稳定→换序仍全票
        self.assertEqual(bt["decision"]["chosen_orig_id"], "B")
        orders = {tuple(v["order"]) for v in bt["votes"]}
        self.assertEqual(len(orders), 3)                            # 三问顺序确实不同

    def test_ledger_has_time_and_witnesses(self):
        e = self.trace["ledger"][0]
        self.assertEqual(e["time"], "入职第1周·周三·上午")
        self.assertEqual(e["witnesses"], ["周默", "沈雯"])

    def test_relations_validated(self):
        self.assertIn("沈雯", self.trace["scenes"][0]["relations"])

    def test_delta_states_empty_keeps_initial(self):
        self.assertEqual(self.trace["scenes"][0]["state_changes"], {})

    def test_event_stream_types(self):
        types = [e["type"] for e in self.events]
        for t in ("run_started", "scene_open", "beat_open", "inner", "decision",
                  "audit", "settle", "done"):
            self.assertIn(t, types)


class TestFirewallIsolation(unittest.TestCase):
    def test_agent_prompt_excludes_unwitnessed(self):
        """防火墙物理隔离：周默的提示词不得含他不在场的台账条目。"""
        cast = Cast.from_cards([card_zhou(), card_shen()])
        fake = FakeLLM(router=router_factory())
        # 预置台账走不进 run_simulation——改为两幕局：第1幕 witnesses 只有沈雯，第2幕查周默提示词
        settle_private = dict(SETTLE, witnesses=["沈雯"], scene_summary="沈雯单独知道的事")
        state = {"n": 0}
        base = router_factory()
        def router(system, user):
            if "收场" in system:
                state["n"] += 1
                return dict(settle_private) if state["n"] == 1 else dict(SETTLE)
            return base(system, user)
        # 路由的 adv 计数要支持两幕：每幕第1次推进给节骨眼、第2次收幕
        # （base 闭包只数到2，重建一个支持 4 次的：奇数次=ADV1，偶数次=ADV_OVER）
        adv = {"n": 0}
        def router2(system, user):
            if "节骨眼回合" in system:
                adv["n"] += 1
                return dict(ADV1) if adv["n"] % 2 == 1 else dict(ADV_OVER)
            return router(system, user)
        fake = FakeLLM(router=router2)
        run_simulation(cast=cast, llm=fake, bank=SceneBank(), n_scenes=2, seed=1)
        # 第2幕周默侧调用（情绪/决策）的 user 不得出现第1幕私密摘要
        zhou_calls = [u for s, u in fake.calls if "情绪" in s or "面临一个决定" in s]
        second_scene_calls = zhou_calls[1:]          # 第1幕的1次情绪+3次决策之后
        for u in second_scene_calls[4:]:
            self.assertNotIn("沈雯单独知道的事", u)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 跑全套测试**

Run: `python -m unittest discover -s tests -v`
Expected: 全绿（此时约 30+ 测试）

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: run_simulation 全量（名单制+防火墙接线+差量收场+relations 细目）+ 集成测试"
```

### Task 10: trace.py（台本渲染 + 落盘）

对应 tasks.md 1.8。**自 `B:\report.py` + `B:\run_mvp.py` 落盘段移植。**

**Files:**
- Create: `sandbox3/trace.py`、`tests/test_trace.py`

- [ ] **Step 1: 移植 render**

把 `B:\report.py` 的 `_beat_md`/`render` 整体搬入 `sandbox3/trace.py`，改动仅限：
1. 头部"观察主体"行改为从 `meta["candidate"]` 与 `meta["cast"]` 生成（列名单+kind）；
2. 增加每幕 `**时间**/**在场**` 行与 `relations` 细目渲染（幕末加一段：`**关系细目**（候选人×成员，只入档不进灯）：` 逐行 `- 沈雯：neutral——证据`）；
3. MVP 脚注行整句保留，再追加"人设可为蒸馏产物"半句。

新增落盘函数：

```python
def save_run(trace: dict, out_root: pathlib.Path | None = None, jd: str = "") -> pathlib.Path:
    import json, time
    from .config import OUTPUT_DIR
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = (out_root or OUTPUT_DIR) / f"run_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    (out_dir / "台本.md").write_text(render(trace), encoding="utf-8")
    if jd:
        (out_dir / "jd.txt").write_text(jd, encoding="utf-8")
    return out_dir
```

- [ ] **Step 2: 测试**

```python
# tests/test_trace.py（核心断言；trace 来源=test_engine_run 的 router 跑一局复用）
# 断言 render(trace) 包含："换序三问表决"、"心口缝（只记录不打分）"、"**时间**"、
# "关系细目"、"不构成对真实结局的预测"；save_run 产出 trace.json+台本.md 两件。
```

（测试代码按上述断言自拟，复用 test_engine_run.router_factory 生成 trace——把 router_factory 挪进 tests/fixtures.py 供两处共用。）

- [ ] **Step 3: 跑过 + Commit**

```bash
git add -A && git commit -m "port: 台本渲染（+时间/在场/关系细目）+ run 落盘"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 11: tools/（体检工具转正）

对应 tasks.md 1.9 的工具件。

**Files:**
- Create: `sandbox3/tools/__init__.py`、`sandbox3/tools/checkup.py`、`sandbox3/tools/leakcheck.py`、`tests/test_tools.py`

- [ ] **Step 1: checkup.py（位置偏置体检）**

输入：一个或多个 run 目录（含 trace.json）。输出：每问选中呈现位分布、官方选择呈现位分布、表决结果计数、官方选择呈现位 A 占比；判语（≈1/3 上下为过）。核心聚合逻辑同 `B:\output\_checkup.py`（本仓 relate_mvp 临时脚本——已验证），改为函数 `checkup(run_dirs: list[Path]) -> dict` + `__main__` 打印。

- [ ] **Step 2: leakcheck.py（防火墙泄漏检查）**

函数 `leakcheck(trace: dict, actor: str, keywords: list[str]) -> dict`：扫描该 actor 的内心/选择理由/行动/各问投票理由/给他的选项/叙事认知句式（`{actor}[^。]{{0,30}}(脑子|心想|心里|念头|想起|闪过)`），返回 hits 列表与 ok_mentions（其他角色内心合法提及）；`__main__` 接 run 目录+actor+逗号分隔关键词。逻辑同 `B:\output\_leakcheck.py`（已验证），参数化人名与关键词。

- [ ] **Step 3: 测试**

用手工构造的最小 trace dict（两个 beat：一个干净、一个在周默 reasoning 里埋"编制"）断言：命中数=1、位置标注正确；checkup 对构造 votes 的呈现位计数正确。

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: 体检工具转正（位置偏置 checkup + 防火墙 leakcheck）+ 测试"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 12: run.py（单跑 CLI）+ [LIVE] 首冒烟

对应 tasks.md 1.8。

**Files:**
- Create: `sandbox3/run.py`

- [ ] **Step 1: 实现**

```python
# sandbox3/run.py
"""入口：python -m sandbox3.run [--scenes 4] [--start C1-01] [--seed S] [--cast path.json]"""
from __future__ import annotations
import argparse, json, pathlib, time

from .cast import Cast
from .engine import run_simulation
from .llm import DeepSeekClient
from .scenes import SceneBank
from .trace import save_run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, default=4)
    ap.add_argument("--start", default="C1-01")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--cast", default=None, help="名单 JSON 路径（缺省用 data/cast_default.json）")
    args = ap.parse_args()
    cast = Cast.from_cards(json.loads(pathlib.Path(args.cast).read_text(encoding="utf-8"))) \
        if args.cast else Cast.load_default()
    t0 = time.time()
    trace = run_simulation(cast=cast, llm=DeepSeekClient(), bank=SceneBank(),
                           n_scenes=args.scenes, start_tp=args.start, seed=args.seed)
    trace["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = save_run(trace)
    print(f"\n完成：{trace['meta']['n_scenes']} 幕，{trace['meta']['n_llm_calls']} 次调用，"
          f"{trace['meta']['elapsed_s']}s，警告 {trace['meta']['warnings_total']} 条\n输出：{out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: [LIVE] 首冒烟**

Run: `python -m sandbox3.run --scenes 1 --seed 42`
Expected: 1 幕跑通、台本含三问/审计/时间戳、0 未处理异常。**看台本全文**确认叙事正常。

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: 单跑 CLI + live 首冒烟通过"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 13: aggregate.py（5-run 聚合）

对应 tasks.md 2.3。**自 `B:\run_batch.py` 移植。**

**Files:**
- Create: `sandbox3/aggregate.py`、`tests/test_aggregate.py`

- [ ] **Step 1: 移植**

`aggregate(traces)->dict` 与 `render_aggregate(agg,cfg)->str` 自 `B:\run_batch.py` **逐字搬**（它们是纯函数，无双人耦合——`inner_gap_by_actor` 等已按名字泛化）；`main()` 改用 `Cast.load_default()`/`DeepSeekClient()`/`SceneBank()` 组装，批跑线程池逻辑照搬，产物落 `output/batch_<stamp>/`。

- [ ] **Step 2: 测试**

用 fixtures 的 router 跑两局 FakeLLM trace（seed 不同），断言 `aggregate`：n_runs=2、承诺轨迹按幕对齐、`choices[0]["aligned"]` 为 True（同 start）、vote_stats 累加正确、脚注含"不构成对真实结局的预测"。

- [ ] **Step 3: 跑过 + Commit**

```bash
git add -A && git commit -m "port: 5-run 聚合（并发批跑+倾向分布+分叉标注）+ 测试"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 14: server.py + pages/（操作台移植）+ P0 验收闸门

对应 tasks.md 2.1/2.2/2.4/2.5/1.9。**最大搬运面，照清单做，别即兴。**

**Files:**
- Create: `sandbox3/server.py`、`sandbox3/pages/__init__.py`、`sandbox3/pages/theater.py`、`sandbox3/pages/archive.py`、`sandbox3/pages/replay.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: 移植 server.py**

以 `B:\server.py` 为底，改动清单：
1. import 与组装：`SceneBank()` 实例化共享、`DeepSeekClient()` 模块级 `LLM = DeepSeekClient()`（测试可替换）、`CAST = Cast.load_default()` 可变全局（import 锁定推演中不可换）；
2. `/api/run`：`run_simulation(cast=CAST, llm=LLM, bank=BANK, ...)`，落盘用 `trace.save_run(trace, jd=STATE["jd"])`；
3. `/api/import_persona` 改 **`/api/import_cast`**：请求体 `{"cast": [card, ...]}` → `Cast.from_cards` 校验通过才替换（CastError 转 400；推演中 409）；
4. `/api/state` 返回 `{"running", "n_events", "cast": [{name,kind,role}...], "candidate", "scenes", "jd_len"}`；
5. `/api/batch_latest` 照 `B:\server.py` 同名路由逐字；`/api/chat`、`/api/crystallize`（结晶改走 `BANK.add_custom`，自动持久化）、`/api/jd` 逐字；
6. 端口取 `config.SERVER_PORT`（8781）。

- [ ] **Step 2: 移植 pages/theater.py**

以 `B:\theater_page.py` 的 PAGE 为底（**整体复制后做以下适配**，CSS/布局/表决条/心口缝金标/聚合视图全保留）：
1. `loadState()`：从 `s.cast` 渲染——候选人（kind=candidate）居左，其余成员按 kind 排右列（counterpart 在前），**全部真 agent 头像**（金圈可行动、点开内心）；场景 npc 仍灰头像布景、点不开；
2. `names` 字典改 `cast` 数组驱动；COLORS 按序取色板 `['#4a6d8c','#8c4a5e','#6d8c4a','#8c7a4a','#4a8c7e','#7e4a8c']`；
3. `run_started` 事件读 `e.cast`/`e.candidate`；
4. 导入面板文案与 payload 改整套名单 JSON（`{"cast":[...]}`，调 `/api/import_cast`）；
5. 收场卡渲染 `relations` 细目（每行 `成员：attitude——证据`，放"本幕在场知情"行后）；
6. 诚实脚注块整段保留＋追加"名单制多人：同事亦为真 agent；关系细目只入档不进灯"。

`pages/archive.py`、`pages/replay.py`：自 `B:\build_page.py`/`B:\build_theater.py` 移植，读 trace 的字段名全部沿用故改动极小——只把"观察主体"读法换成 `meta.candidate`，并给 beat 渲染加 votes 表决行（照 `B:\report.py` 的表决明细句式）。

- [ ] **Step 3: 集成测试（FakeLLM 注入 server）**

```python
# tests/test_server.py 核心场景（http.client 实连本地起的服务线程）：
# 1) GET /api/state → cast 含两人、candidate=周默
# 2) POST /api/import_cast 非法卡（缺 candidate）→ 400
# 3) sandbox3.server.LLM = FakeLLM(router=...) 后 POST /api/run {scenes:1}
#    轮询 /api/events 至 done → 事件类型集合含 run_started/.../saved
# 4) 跑中再 POST /api/run → 409
```

- [ ] **Step 4: [LIVE] P0 验收闸门（全部记录证据到 evidence/p0/）**

1. `python -m sandbox3.run --scenes 1 --seed 42` 冒烟绿；
2. `python -m sandbox3.run --scenes 4 --seed 42` ＋ `--seed 7` 两局 → `python -m sandbox3.tools.checkup output/run_*` → **官方选择呈现位 A 占比 ≈1/3**；
3. `python -m sandbox3.run --scenes 2 --start C5-02 --seed 7` → `python -m sandbox3.tools.leakcheck <run_dir> 周默 编制,合并,缩编,裁员,HC` → **0 泄漏**；
4. 起 `python -m sandbox3.server`，浏览器全链直播一局：表决条/得票点/一句话心理/状态灯红变化/收场卡时间+在场者/判断流（含心口缝金标）逐项截图；
5. `python -m sandbox3.pages.archive` 与 `python -m sandbox3.pages.replay` 对最新 trace 生成可打开页面；
6. 诚实脚注逐条字面在页（对照 console delta spec 的脚注清单）。

**此处停下来等作者过目 P0 证据再继续 P1**（操作台形态、台本叙事质量是人判项）。

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "port: 操作台 server+三代前端（名单制适配）+ P0 live 验收证据"
```

### Task 15: P1 三人局（同事真 agent）

对应 tasks.md 3.1-3.5。**底座已多人原生，本 Task 主要是数据+验证。**

**Files:**
- Create: `data/cast_three.json`
- Modify: `tests/test_engine_run.py`（追加三人局集成测试）

- [ ] **Step 1: 三人名单**

`data/cast_three.json` = cast_default 两卡 + 陈磊卡（全文在 tests/fixtures.py 的 `card_colleague()`，kind=colleague，照抄）。

- [ ] **Step 2: 三人局集成测试（FakeLLM）**

在 test_engine_run.py 追加：router 的 ADV 改为轮流指定 `acting_agent` 为 周默→陈磊→沈雯（三回合后收幕），断言：
- `meta["actor_counts"]` 三人各 1；
- 陈磊作为行动方走了完整管线（其 beat 有 appraisal/votes/audit）；
- settle 的 relations 含 沈雯+陈磊 两条（router 的 SETTLE 相应加 relations 两键）；
- 防火墙：构造只有 沈雯+陈磊 在场的台账条目，断言周默后续提示词不含其文本。

- [ ] **Step 3: [LIVE] 三人局验收**

`python -m sandbox3.run --scenes 3 --seed 42 --cast data/cast_three.json`
人判清单：陈磊有真决策回合（非布景）；SM 行动方分布合理；台本关系细目两行；操作台直播三头像、陈磊可点开内心。证据存 `evidence/p1/`。**停下等作者过目。**

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: P1 三人局（同事真 agent）+ live 验收证据"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 16: P2 蒸馏器 + JD 接通

对应 tasks.md 4.1-4.5。

**Files:**
- Create: `sandbox3/distill.py`、`sandbox3/prompts/distill.py`、`data/materials_zhou/`（合成材料包）、`tests/test_distill.py`

- [ ] **Step 1: 合成材料包（先给作者过目再编码）**

`data/materials_zhou/` 下四个 UTF-8 文本文件，以周默人设反推（执行时起草，要点）：
- `resume.md`：简历（自述侧——上家小公司独立扛服务、技术栈、自评"抗压、自驱"）；
- `assessment.md`：测评报告（自评量表侧——尽责性高、宜人性中、外向性低、压力应对"先自行解决"）；
- `interview.md`：两条面试官评价（**他人视角**——"答压力题时语速明显加快，与自述'冷静'不符"这类视角分歧故意埋一条）；
- `backcheck.md`：背调（第三方事实——上家在职时长、离职原因中性表述）。

**把四件贴给作者过目后再进 Step 2。**

- [ ] **Step 2: 蒸馏 prompt（prompts/distill.py）**

两段式两个 prompt，三纪律逐字进 SYSTEM：

```python
# sandbox3/prompts/distill.py
"""蒸馏器两段式（论文 §5.2 配方）。三纪律：evidence or silence／保留视角分歧不调和／标记矛盾不抹平。"""

STAGE1_SYSTEM = (
    "你是人才材料的证据提取员。任务：从给定的单份材料中提取关于此人行为方式的证据链小结。"
    "纪律（硬约束）：①只要具体行为与事实，禁猜测、禁演绎人格标签；"
    "②证据不足的方面直接略过，不许编造（evidence or silence）；"
    "③注明每条证据的出处材料。输出 JSON：{\"source\": \"材料名\", "
    "\"evidence\": [\"行为证据句…\"], \"perspective\": \"self/other/third-party\"}"
)

STAGE2_SYSTEM = (
    "你是人设合成器。任务：把多份证据链小结融合成一张可推演的角色卡。"
    "纪律（硬约束）：①200-300 词第二人称人设 + 5-7 条 if→then 行为手册；"
    "②保留视角分歧不调和——自述与他人视角矛盾时两面原样并存"
    "（如'你自述冷静，面试官记录你答压力题时语速明显加快'），不挑边不平均；"
    "③矛盾处显式标记；④证据不足的维度写'未知'，不许编。"
    "输出 JSON：{\"name\": \"…\", \"kind\": \"candidate\", \"role\": \"…\", "
    "\"persona\": \"第二人称人设\", \"playbook\": [\"如果…→…\"]}"
)


def stage1_user(material_name: str, text: str, jd: str = "") -> str:
    jd_block = f"【目标岗位 JD（供相关性参考）】\n{jd}\n\n" if jd else ""
    return f"{jd_block}【材料：{material_name}】\n{text}\n\n提取证据链小结，只输出 JSON。"


def stage2_user(summaries: list[dict], jd: str = "") -> str:
    import json
    jd_block = f"【目标岗位 JD（行为手册的情境往岗位场景侧重）】\n{jd}\n\n" if jd else ""
    return (f"{jd_block}【各材料证据链小结】\n"
            f"{json.dumps(summaries, ensure_ascii=False, indent=1)}\n\n融合成角色卡，只输出 JSON。")
```

- [ ] **Step 3: distill.py 管线**

```python
# sandbox3/distill.py
"""蒸馏器：材料包目录 → 两段式 → cast 角色卡 JSON（直接可入名单）。
用法：python -m sandbox3.distill data/materials_zhou [--jd jd.txt] [--out card.json]"""
from __future__ import annotations
import argparse, json, pathlib

from .cast import Cast
from .llm import DeepSeekClient
from .prompts import distill as DP


def distill(llm, material_dir: pathlib.Path, jd: str = "") -> dict:
    files = sorted(material_dir.glob("*.md"))
    if not files:
        raise ValueError(f"{material_dir} 下没有材料（*.md）")
    summaries = [llm.complete_json(DP.STAGE1_SYSTEM,
                                   DP.stage1_user(f.stem, f.read_text(encoding="utf-8"), jd))
                 for f in files]
    card = llm.complete_json(DP.STAGE2_SYSTEM, DP.stage2_user(summaries, jd))
    card.setdefault("kind", "candidate")
    Cast.from_cards([card, {"name": "_占位上级", "kind": "counterpart", "role": "占位",
                            "persona": "占位", "playbook": ["a", "b", "c"]}])   # 借校验器验卡
    return card


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("material_dir")
    ap.add_argument("--jd", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    jd = pathlib.Path(args.jd).read_text(encoding="utf-8") if args.jd else ""
    card = distill(DeepSeekClient(), pathlib.Path(args.material_dir), jd)
    out = pathlib.Path(args.out or "card.json")
    out.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"角色卡已写出：{out}（导入操作台或 --cast 即用，引擎一行不改）")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 测试（FakeLLM）**

断言：N 份材料=N 次 stage1 调用+1 次 stage2；产卡过 Cast 校验；JD 传入时出现在两段 user 里；stage2 摘要 JSON 含全部 stage1 产物。

- [ ] **Step 5: [LIVE] 蒸馏闭环验收**

`python -m sandbox3.distill data/materials_zhou --out card_zhou_distilled.json` → 与沈雯卡拼成名单 → `python -m sandbox3.run --scenes 2 --cast <拼合json>` → 人判：行为可辨认地顺材料证据（含那条故意埋的视角分歧有没有进人设）。证据存 `evidence/p2/`。**停下等作者过目。**

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: P2 蒸馏器两段式+三纪律+JD 接通 + live 闭环验收"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 17: P3 场景库扩充

对应 tasks.md 5.1-5.3（5.1 持久化已在 Task 5 完成）。

- [ ] **Step 1: 扩充内容**

与作者商定目标量（建议 +8~12 条，混合手写与共创产出）；新场景一律走 `SceneBank.add_custom` 或直接编辑 `data/scene_bank.json`（进预设须保持六类均衡）。每条新场景 [LIVE] 用 `--scenes 1 --start <id>` 各冒烟一次。

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: P3 场景库扩充至 N 条（逐条 live 冒烟）"
```

archived-with: 2026-06-08-sandbox-v3-core
---

### Task 18: 收尾——全量回归 + README + 标杆局

对应 tasks.md 6.1-6.3。

- [ ] **Step 1: 全量回归**

`python -m unittest discover -s tests -v` 全绿；`python -m sandbox3.aggregate --runs 5 --scenes 4` [LIVE] 出聚合报告；操作台聚合视图读到该批次。

- [ ] **Step 2: README.md**

内容：一句话定位／快速开始（server/run/aggregate/distill 四命令）／架构图（文件全景）／诚实工程边界（红线清单照 Design Doc 抄）／已知边界（据实列）。

- [ ] **Step 3: 标杆局**

从 5-run 批次里与作者挑 demo 主秀局；操作台一镜到底走一遍。

- [ ] **Step 4: Commit + 阶段守卫**

```bash
git add -A && git commit -m "chore: 收尾——全量回归+README+标杆局选定"
```

随后按 comet 流程跑 `comet-guard sandbox-v3-core build --apply` 进 verify 阶段。

archived-with: 2026-06-08-sandbox-v3-core
---

## 自检记录（writing-plans Self-Review）

- **Spec 覆盖**：rollout-engine→Task 2/8/9/12；info-firewall→Task 4/9（隔离测试）/11（leakcheck）/14.4.3；reason-audit→Task 6/7/9；multi-agent-cast→Task 3/6/9/15；persona-distill→Task 16；jd-context→Task 6（scene_init jd 参数）/16（蒸馏 jd）；scene-bank→Task 5/14（结晶持久化）/17；run-aggregation→Task 13/18；console→Task 14。
- **JD 不评分**（jd-context spec）：实现层无任何评分代码路径——靠"不写"满足；Task 14.4.6 脚注复核时顺带确认页面无匹配分。
- **类型一致性**：`run_simulation(cast, llm, bank, ...)` 签名在 Task 9/12/13/14 一致；`ledger.entry/visible/ledger_text` 在 Task 4 定义、Task 6/9 使用；`Cast.from_cards/load_default/persona_block/names/candidate/others` 在 Task 3 定义、6/7/9/12/16 使用。
- **占位说明**：fixtures 卡片与 data 导出处的 `<逐字拷贝…>` 是**搬运指令**（源路径明确、执行时 Read 后替换），非待定设计；陈磊卡/蒸馏 prompt/材料包要点为全文新写已给出。
- **断点恢复**：每 Task 独立提交；恢复时按 tasks.md 勾选与 git log 找断点（comet build 协议）。



