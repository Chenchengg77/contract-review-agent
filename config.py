"""唯一的配置入口：所有环境变量都从这里读，不要在代码里散落 os.getenv。"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# ---- 模型 ----
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("MODEL", "deepseek-chat")

# ---- 检索增强（可选）：embedding / rerank 用 OpenAI 兼容的 API ----
# 不配置则自动退回纯 BM25，不影响任何功能
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")  # 例：https://api.siliconflow.cn/v1
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# ---- 数据目录 ----
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PLAYBOOK_DIR = DATA_DIR / "playbook"
EVAL_DIR = DATA_DIR / "eval"
RESULTS_DIR = ROOT / "results"


def require_api_key() -> str:
    """缺少 key 时尽早失败，而不是等到第一次调用模型才报错。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，请复制 .env.example 为 .env 并填写")
    return DEEPSEEK_API_KEY
