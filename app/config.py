"""全局配置：路径 + 大模型接入参数。

不依赖 python-dotenv，手动解析 .env，减少普通人的安装负担。
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
WEB_DIR = ROOT / "web"
DB_PATH = DATA_DIR / "pet.db"

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"


def _load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # 已经通过真实环境变量设置过的，优先环境变量
        if key and key not in os.environ:
            os.environ[key] = value


_load_env()

API_KEY = os.getenv("LLM_API_KEY", "").strip()
BASE_URL = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
MODEL = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip()

# 没有 key 或 key 还是占位符，就自动走离线演示模式
LLM_ENABLED = bool(API_KEY) and not API_KEY.startswith("sk-xxx") and API_KEY.lower() not in {
    "your-key",
    "none",
}
MODE = "llm" if LLM_ENABLED else "offline"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
