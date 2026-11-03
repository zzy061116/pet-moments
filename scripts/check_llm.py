"""大模型连通性自检：填完 .env 之后跑这一个脚本就够了。

    python scripts/check_llm.py

它会依次做三件事：
1. 打印当前读到配置（key 打码），确认 .env 真的被读到了；
2. 用真实的人设卡 prompt 请求一次，看返回的 JSON 对不对；
3. 用人设卡再发一条朋友圈，看文案和评论是不是模型写的。

失败时会直接给出排查方向（key / 模型名 / 网络代理），不用去翻日志。
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from app import config, llm, service  # noqa: E402


def mask(key: str) -> str:
    if not key:
        return "（空）"
    if len(key) <= 8:
        return key[:2] + "*" * (len(key) - 2)
    return f"{key[:5]}…{key[-4:]}（共 {len(key)} 位）"


def diagnose(error: str) -> list[str]:
    text = error.lower()
    tips: list[str] = []
    if "401" in text or "invalid_api_key" in text or "unauthorized" in text:
        tips.append("key 被拒了：确认没粘多空格/换行，也没把别家平台的 key 拿来用")
    if "404" in text or "model_not_found" in text:
        tips.append("404 通常是模型名或 base_url 不对：base_url 要带 /v1，model 要和平台文档一致")
    if "402" in text or "insufficient" in text or "quota" in text:
        tips.append("余额不足：DeepSeek 新号需要先充值，百炼有免费额度但要开通模型服务")
    if "timeout" in text or "connect" in text or "ssl" in text:
        tips.append(
            "连不上：可能是网络或系统代理。可以试 SSL 证书问题设 HTTPS_PROXY 直连，或者换成国内平台"
        )
    if "json" in text:
        tips.append("返回的不是 JSON：可能模型不支持 response_format，换 deepseek-chat / qwen-plus 这类")
    if not tips:
        tips.append("把上面这段报错原样发我，我按具体平台给改法")
    return tips


async def main() -> int:
    print("=" * 62)
    print("宠物朋友圈 · 大模型连通性自检")
    print("=" * 62)
    print(f"模式      : {config.MODE}")
    print(f"base_url  : {config.BASE_URL}")
    print(f"model     : {config.MODEL}")
    print(f"api_key   : {mask(config.API_KEY)}")
    print(f".env 位置 : {config.ROOT / '.env'}（存在={ (config.ROOT / '.env').exists() }）")

    if not config.LLM_ENABLED:
        print("\n[跳过] 没有读到可用的 LLM_API_KEY，当前是离线演示模式。")
        print(f"       打开 {config.ROOT / '.env'}，把 key 填到这一行后面：")
        print("       LLM_API_KEY=sk-你的key")
        print("       存盘后重新运行本脚本即可验证，不用先重启服务。")
        return 1

    print("\n[1/2] 生成人设卡 …")
    started = time.time()
    persona = await service.build_persona("豆花", "英短蓝猫", "2 岁", "贪吃,高冷")
    cost = time.time() - started
    if persona.get("offline"):
        print(f"  失败（{cost:.1f}s）：模型没返回可用内容，已降级到离线引擎")
        print(f"  错误：{llm.last_error() or '未知（返回内容无法解析成 JSON）'}")
        for tip in diagnose(llm.last_error()):
            print(f"  → {tip}")
        return 1
    print(f"  成功（{cost:.1f}s）")
    for key in ("tags", "nickname", "catchphrase", "obsession", "fear", "tone"):
        print(f"  {key:<12}: {persona.get(key)}")
    print(f"  voice_sample: {persona.get('voice_sample')}")

    print("\n[2/2] 发一条朋友圈 …")
    pet = {"name": "豆花", "species": "英短蓝猫", "age": "2 岁", "persona": persona}
    started = time.time()
    post = await service.build_post(pet, "偷吃了半块蛋黄酥，嘴边还留着渣", 3, [])
    cost = time.time() - started
    if post.get("offline"):
        print(f"  失败（{cost:.1f}s）：降级到离线文案")
        print(f"  错误：{llm.last_error() or '返回内容缺字段（caption 太短）'}")
        for tip in diagnose(llm.last_error()):
            print(f"  → {tip}")
        return 1
    print(f"  成功（{cost:.1f}s）")
    print(f"  正文：{post['caption']}")
    print(f"  心情：{post['mood']}")
    for item in post["comments"]:
        print(f"  {item['friend']}: {item['text']}")
    print(f"  点赞：{'、'.join(post['likes'])}")

    print("\n" + "=" * 62)
    print("结论：模型接通了。重启服务后，页面上的状态标签会显示「AI 在线」。")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
