"""一键载入演示数据：一只叫豆花的英短，和它 24 天的朋友圈。

纯粹为了让第一次打开的人（和评审）不用注册、不用传图，就能看到成品长什么样。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import db, offline

DEMO_PET = {
    "name": "豆花",
    "species": "英短蓝猫",
    "age": "2 岁",
    "traits": "嘴硬心软,贪吃,白天睡觉晚上跑酷",
}

DEMO_EVENTS = [
    ("偷吃了半个蛋黄酥，还留着渣在嘴边", "eat"),
    ("把新买的纸箱占为己有，拒绝出来", "daily"),
    ("凌晨三点在走廊跑了六圈", "play"),
    ("被吸尘器吓到，躲进衣柜待了四十分钟", "destroy"),
    ("第一次见到雪，伸爪子试了三下", "outside"),
    ("把主人的耳机线咬出三个洞", "destroy"),
    ("洗完澡吹毛时骂了十分钟", "clean"),
    ("称体重胖了 0.4 公斤，主人笑了很久", "daily"),
    ("在阳台看了四十分钟鸟，一动不动", "daily"),
    ("打翻了水杯，然后假装在喝水", "destroy"),
    ("和镜子里的自己打了一架，输了", "play"),
    ("把主人的枕头拖到客厅，摆成窝", "destroy"),
    ("今天叫了二十七次，没人理我", "daily"),
    ("误食一片猫草，很上头，在客厅转圈", "eat"),
    ("生病去医院，全程没叫，回家就哭了", "sick"),
    ("试图自己开柜门，未遂，卡住五分钟", "destroy"),
    ("霸占键盘，主人工作停滞两小时", "daily"),
    ("抓到一只飞蛾，想了想又放它走了", "play"),
    ("在沙发上留下一个很深的坑", "sleep"),
    ("偷看主人洗澡，被赶出来两次", "daily"),
    ("把拖鞋藏到床底，一共七只", "destroy"),
    ("晒太阳晒到翻身，从桌上掉下去", "sleep"),
    ("下雨天，一整天没出门，心情很差", "daily"),
    ("主人加班到凌晨一点，我在门口等", "sleep"),
]


def load_demo() -> dict:
    db.reset_all()
    persona = offline.make_persona(
        DEMO_PET["name"], DEMO_PET["species"], DEMO_PET["age"], DEMO_PET["traits"]
    )
    pet = db.save_pet(
        DEMO_PET["name"], DEMO_PET["species"], DEMO_PET["age"], persona, is_demo=1
    )

    total = len(DEMO_EVENTS)
    today = datetime.now()
    recent: list[str] = []
    for index, (event, _kind) in enumerate(DEMO_EVENTS):
        days_ago = total - index
        stamp = today - timedelta(days=days_ago, hours=(index * 7) % 9)
        streak = index + 1
        result = offline.make_post(pet, event, min(streak, 8), recent[-8:])
        recent.append(result["caption"])
        db.add_post(
            caption=result["caption"],
            mood=result["mood"],
            event=event,
            photo="",
            comments=result["comments"],
            likes=result["likes"],
            exp_gain=14,
            created_at=stamp.isoformat(timespec="seconds"),
        )

    # 让时间轴显示"连续 7 天"的状态
    with db.connect() as conn:
        conn.execute(
            "UPDATE pet SET streak = 7, last_post = ? WHERE id = 1",
            ((today - timedelta(days=1)).date().isoformat(),),
        )
    return db.get_pet() or {}
