"""交互式填 key：不用找隐藏文件、不用改格式，粘一下就写进 .env。

    python scripts/set_key.py

做完它会自动跑一遍连通性测试，通了就告诉你重启服务。
"""

from __future__ import annotations

import getpass
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# 常见平台预设：序号 → (名字, base_url, model, 备注)
PLATFORMS = [
    ("DeepSeek", "https://api.deepseek.com/v1", "deepseek-chat", "便宜，几块钱能玩很久"),
    (
        "智谱 GLM-4-Flash",
        "https://open.bigmodel.cn/api/paas/v4",
        "glm-4-flash",
        "模型本身免费，适合先试",
    ),
    (
        "通义千问",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
        "阿里云百炼，新号有免费额度",
    ),
    ("Kimi", "https://api.moonshot.cn/v1", "moonshot-v1-8k", "上下文长"),
    ("本地 Ollama", "http://localhost:11434/v1", "qwen2.5:7b", "完全免费，但要先下载模型"),
]


def read_lines() -> list[str]:
    if ENV_FILE.exists():
        return ENV_FILE.read_text(encoding="utf-8").splitlines()
    if EXAMPLE.exists():
        return EXAMPLE.read_text(encoding="utf-8").splitlines()
    return ["LLM_API_KEY=", "LLM_BASE_URL=https://api.deepseek.com/v1", "LLM_MODEL=deepseek-chat"]


def set_value(lines: list[str], key: str, value: str) -> list[str]:
    """替换 key=... 这一行；没有就追加。其它注释行原样保留。"""
    out: list[str] = []
    hit = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        name = stripped.split("=", 1)[0].strip()
        if name == key:
            out.append(f"{key}={value}")
            hit = True
        else:
            out.append(line)
    if not hit:
        out.append(f"{key}={value}")
    return out


def choose_platform() -> tuple[str, str, str]:
    print("用哪个平台的 key？直接回车 = 1（DeepSeek）\n")
    for i, (name, _url, model, note) in enumerate(PLATFORMS, start=1):
        print(f"  {i}. {name:<18}{note}（模型 {model}）")
    print("  0. 我自己填 base_url 和模型名")
    print()

    raw = input("序号 > ").strip().lstrip("\ufeff") or "1"
    if raw == "0":
        url = input("base_url（结尾要带 /v1 这类的版本号）> ").strip()
        model = input("模型名 > ").strip()
        return "自定义", url, model
    if not raw.isdigit() or not 1 <= int(raw) <= len(PLATFORMS):
        print("序号看不懂，先按默认 DeepSeek 来。")
        raw = "1"
    name, url, model, _note = PLATFORMS[int(raw) - 1]
    return name, url, model


def clean_key(raw: str) -> str:
    key = raw.strip()
    # 有人会把整行 `LLM_API_KEY=sk-xxx` 粘进来，或者带上引号
    if "=" in key and "sk-" in key:
        key = key.split("=", 1)[1].strip()
    return key.strip().strip('"').strip("'").strip()


def main(argv: list[str]) -> int:
    print("=" * 62)
    print("填 API Key")
    print("=" * 62)

    name, url, model = choose_platform()

    print(f"\n平台：{name}")
    print(f"base_url：{url}")
    print(f"模型：{model}")
    print("\n把这个平台的 key 粘贴进来，回车确认。")
    print("提示：粘贴时屏幕上不会显示任何内容，这是正常的。\n")

    if len(argv) > 1 and argv[1] == "--key":
        raw = sys.stdin.readline()
    else:
        raw = getpass.getpass("key > ")
    key = clean_key(raw)

    # 本地 Ollama 不校验 key，但要占位，否则会被当成"没填"
    if "11434" in url and not key:
        key = "ollama"

    if not key:
        print("\n没读到内容，什么都没改。重新运行一次，粘贴完记得按回车。")
        return 1
    if len(key) < 16:
        print(f"\n这个 key 只有 {len(key)} 位，正常是 30 位以上，可能没粘全。已中止，没有写入。")
        return 1

    lines = read_lines()
    lines = set_value(lines, "LLM_API_KEY", key)
    lines = set_value(lines, "LLM_BASE_URL", url)
    lines = set_value(lines, "LLM_MODEL", model)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n已写入 {ENV_FILE}")
    print("key 打码后长这样：" + key[:5] + "…" + key[-4:])

    print("\n跑一次连通性测试 …\n")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_llm.py")], check=False)

    print("\n测试通过的话，重启服务就会切到 AI 模式：")
    print("  先按 Ctrl+C 停掉旧服务，再执行")
    print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8010")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
