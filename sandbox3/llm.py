# sandbox3/llm.py
"""多模型 LLM 客户端（live-only）。红线：无 mock 回退——失败重试后大声抛错，
绝不静默用假数据冒充推演结果。测试替身在 tests/fakes.py，产品代码无任何 mock 分支。

工种→模型分工见 config.ROLES（编剧 kimi / 导演 deepseek-v4-pro / 演员 qwen3.6 / 审计 glm-5.1）；
三家端点都是 OpenAI 兼容接口，差异只在 URL / 模型名 / Key 环境变量。"""
from __future__ import annotations
import json, os, re, sys, time, urllib.error, urllib.request

from .config import ENDPOINTS, ROLES


class LLMError(RuntimeError):
    pass


_THINK_RE = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


def _strip_fences(s: str) -> str:
    s = _THINK_RE.sub("", s.strip())   # 混合思考模型（qwen3.6/glm-5.1）可能带 <think> 前缀
    if s.startswith("```"):
        nl = s.find("\n")
        s = s[nl + 1:] if nl != -1 else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


class LLMClient:
    """引擎以依赖收下本对象；换实现=换对象，不开运行时分支。
    role ∈ config.ROLES（writer/director/actor/auditor），决定端点+模型+Key。"""

    def __init__(self, role: str = "director", api_key: str | None = None):
        endpoint, self.model = ROLES[role]
        self.url, self.key_env = ENDPOINTS[endpoint]
        self.role = role
        self.api_key = os.environ.get(self.key_env, "") if api_key is None else api_key
        # 模型特例（2026-06-12 全部实测）——三家思考模型统一关思考（作者拍：要快）：
        # kimi-k2.6：思考开则锁温 1、关则锁温 0.6（400 报错亲口说的）；思考不关会把
        #   出题这种长活拖到超时/截断（thinking 也计 max_tokens）。
        # Qwen3.6：关法=enable_thinking:false（不关则正文交白卷）。
        # GLM-5.1：关法=thinking.type=disabled（enable_thinking 是假关——思考照跑
        #   只是藏起来，13s 不省；真关后 13s→0.9s）。
        # v4-pro 比旧 chat 啰嗦，1200 会把 JSON 写一半截断——抬 token 地板。
        if self.model.startswith("kimi-k2"):
            self.forced_temperature = 0.6
            self.extra_payload = {"thinking": {"type": "disabled"}}
        elif "Qwen3.6" in self.model:
            self.forced_temperature = None
            self.extra_payload = {"enable_thinking": False}
        elif "GLM-5" in self.model:
            self.forced_temperature = None
            self.extra_payload = {"thinking": {"type": "disabled"}}
        else:
            self.forced_temperature = None
            self.extra_payload = {}
        # token 地板：v4-pro 啰嗦、kimi 蒸馏人设卡 1200 不够写（实测 char~2000 处截断）
        self.min_tokens = (4000 if self.model == "deepseek-v4-pro"
                           else 3000 if self.model.startswith("kimi-k2") else 0)

    def complete(self, system: str, user: str, *, json_mode: bool = True,
                 temperature: float = 0.7, max_tokens: int = 1200, retries: int = 2) -> str:
        if not self.api_key:
            raise LLMError(f"{self.key_env} 未设置——v3 只跑 live，不提供 mock。")
        if self.forced_temperature is not None:
            temperature = self.forced_temperature
        payload = {"model": self.model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}],
                   "temperature": temperature,
                   "max_tokens": max(max_tokens, self.min_tokens),
                   **self.extra_payload}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(self.url, data=body, method="POST",
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.api_key}"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                    OSError, KeyError, IndexError) as e:
                last = e
                print(f"[sandbox3.llm] {self.role}/{self.model} 第{attempt + 1}次调用失败：{e}",
                      file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        raise LLMError(f"{self.role}/{self.model} 调用在 {retries + 1} 次尝试后仍失败：{last}")

    def complete_json(self, system: str, user: str, *, json_retries: int = 2, **kw) -> dict:
        # 各家即便 json_mode 也偶发吐坏 JSON（尾随逗号/缺引号/思考前缀）——重新取响应重试，
        # 仍失败才大声抛（live-only 红线：不静默吞、不用假数据冒充）。
        last: Exception | None = None
        for attempt in range(json_retries + 1):
            raw = self.complete(system, user, json_mode=True, **kw)
            try:
                out = json.loads(_strip_fences(raw))
            except json.JSONDecodeError as e:
                last = e
                print(f"[sandbox3.llm] {self.role}/{self.model} 第{attempt + 1}次返回不可解析 JSON，"
                      f"重试：{e}", file=sys.stderr)
                continue
            if not isinstance(out, dict):
                raise LLMError(f"模型未返回 JSON 对象，得到 {type(out).__name__}")
            return out
        raise LLMError(f"{self.role}/{self.model} 在 {json_retries + 1} 次尝试后仍返回"
                       f"不可解析 JSON：{last}")


# 旧名兼容：历史代码/测试以 DeepSeekClient 之名构造（缺省 role=director）。
DeepSeekClient = LLMClient
