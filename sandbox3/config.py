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
