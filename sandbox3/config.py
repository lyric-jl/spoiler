# sandbox3/config.py
"""全局常量。改这里不改散落各处。"""
from __future__ import annotations
import pathlib

# ---- 多模型分工（2026-06-12 作者拍定：四工种三厂商，各取所长 + 审计与演员不同源） ----
# 端点：厂商名 → (chat 接口地址, API Key 环境变量名)。三家都是 OpenAI 兼容接口。
ENDPOINTS = {
    "deepseek":    ("https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY"),
    "moonshot":    ("https://api.moonshot.cn/v1/chat/completions", "MOONSHOT_API_KEY"),
    "siliconflow": ("https://api.siliconflow.cn/v1/chat/completions", "SILICONFLOW_API_KEY"),
}
# 工种：编剧=出题/蒸馏/搭团队/场景重着色/答卷（低频高质量，中文文笔第一档）；
#       导演=Scene Master 五件（推理深度）；演员=情绪评价+选项决策（海量调用，要快且人设稳）；
#       审计=理由审计员（指令遵循第一档，且与演员/编剧不同源=异构独立审计）。
# 模型名均为 2026-06-12 调各平台 /models 接口核实的挂牌真名。
ROLES = {
    "writer":   ("moonshot",    "kimi-k2.6"),
    "director": ("deepseek",    "deepseek-v4-pro"),
    "actor":    ("siliconflow", "Qwen/Qwen3.6-35B-A3B"),
    "auditor":  ("siliconflow", "Pro/zai-org/GLM-5.1"),
}
SERVER_PORT = 8781                      # 故意避开 relate_mvp 的 8780，两台可同时起
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
VOTE_ROUNDS = 3                         # 换序三问
MAX_BEATS = 3                           # 每幕节骨眼上限
MAX_CAST = 6                            # 名单上限（含候选人）
