"""一键自检：不打开浏览器也能确认整条链路是通的。

用法（服务已经在跑）：
    python scripts/smoke_test.py
"""

from __future__ import annotations

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"

# Windows 下重定向到文件时默认用 GBK，中文会乱码，这里强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def main() -> int:
    # trust_env=False：不读取系统代理，避免本地请求被代理拦截
    with httpx.Client(base_url=BASE, timeout=60, trust_env=False) as c:
        health = c.get("/api/health").json()
        print("health :", health)

        demo = c.post("/api/demo").json()
        print("demo   :", demo["pet"]["name"], "posts =", len(demo["posts"]))
        for item in demo["posts"]:
            print("   -", item["caption"])

        pet = c.post(
            "/api/pet",
            json={"name": "测试猫", "species": "橘猫", "age": "1 岁", "traits": "贪吃,高冷"},
        ).json()
        print("persona:", pet["persona"]["tags"], pet["persona"]["catchphrase"])

        post = c.post("/api/post", json={"event": "偷吃了半块蛋黄酥"}).json()
        print("post   :", post["post"]["caption"])
        for item in post["post"]["comments"]:
            print(f"         {item['friend']}: {item['text']}")
        print("exp    :", post["exp_gain"], "->", post["pet"]["level"]["title"])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
