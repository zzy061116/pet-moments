"""离线演示引擎：没有 API Key 也能把整套流程玩一遍。

做法是"按事件类型抽模板 + 人设卡变量替换"，不是随机拼句子。
效果当然不如大模型，但保证任何人 clone 下来都能 3 秒看到成品。
"""

from __future__ import annotations

import random
from typing import Any

from .prompts import FRIENDS

CATEGORIES: list[tuple[str, list[str]]] = [
    ("eat", ["吃", "饭", "粮", "罐", "零食", "干饭", "猫条", "狗粮", "舔", "馋", "骨头", "加餐"]),
    # 只留"沙发上"这种强场景词，去掉单字"床"，否则"把拖鞋藏到床底"会被判成睡觉
    ("sleep", ["睡", "打盹", "呼噜", "赖床", "眯", "躺着", "趴着", "沙发上"]),
    ("destroy", ["拆", "咬", "抓", "撕", "翻", "弄坏", "打碎", "扒", "挖", "藏", "塞", "推倒"]),
    # 用"被洗澡""吹毛"这类词，"偷看主人洗澡"就不会被当成自己洗了
    ("clean", ["被洗澡", "洗澡了", "吹毛", "剪指甲", "驱虫", "梳毛", "擦身", "洗了"]),
    ("sick", ["吐", "拉稀", "拉肚子", "生病", "医院", "打针", "药", "不舒服", "发烧"]),
    ("outside", ["出门", "遛", "公园", "楼下", "草地", "散步", "坐车", "外面"]),
    ("play", ["玩", "球", "逗猫棒", "追", "跑", "扑", "激光"]),
]

MOODS = {
    "eat": ["得意", "满足", "馋"],
    "sleep": ["摆烂", "安详", "困"],
    "destroy": ["装无辜", "理直气壮", "心虚"],
    "clean": ["委屈", "记仇", "冷淡"],
    "sick": ["委屈", "低电量", "黏人"],
    "outside": ["勇敢", "社恐", "兴奋"],
    "play": ["兴奋", "上头", "意犹未尽"],
    "daily": ["平静", "无聊", "有点飘"],
}

# 所有模板都把 {e} 当作一个完整陈述，用句号隔开，绝不做"今天的{e}""在{e}时"
# 这种需要名词化的语法嵌入——用户输入可能是任意长句，嵌进去必然出病句。
CAPTIONS: dict[str, list[str]] = {
    "eat": [
        "{e}。碗亮得能照见我的脸，我承认有被自己帅到。",
        "{e}——这种事我的态度一贯是：先吃，吃完再讨论人生。",
        "汇报一下：{e}。全程没有人受伤，只有一个碗被舔穿了。",
        "{e}。主人说我吃相难看，她不懂，那叫专注。",
        "{e}。第二份是没有的，但我的眼神还在争取。",
        "{e}。这是今天最正确的一个决定。",
    ],
    "sleep": [
        "{e}。中途被叫醒两次，一次问我要不要喝水，一次问我是不是死了。",
        "{e}。睡得格外成功，梦里我追到了那只激光点。",
        "{e}。姿势已经调整到第六版，这个角度能听见自己的呼噜。",
        "{e}。别人睡觉是休息，我睡觉是上班，我的工作是让沙发塌一点。",
        "{e}，然后被拍照。人类的爱好真奇怪。",
        "{e}。醒来第一件事是想：能不能再睡一次。",
    ],
    "destroy": [
        "{e}。我要说三点：第一，它先惹我的；第二，我不知情；第三，别问了。",
        "{e}。现场收拾得很干净，只剩一点点证据。",
        "{e}。我不是在拆家，我是在检查这个家够不够结实。结论：不够。",
        "{e}。主人回来的时候我睡得很熟，这是最完美的不在场证明。",
        "{e}。不是我的错，是那个东西放在了我够得到的地方。",
        "{e}。下次还敢。",
    ],
    "clean": [
        "{e}。全过程我保持沉默，只是在心里记了一笔。",
        "{e}。我现在是一个没有味道的我，我很难过。",
        "{e}。水很可怕，但我更怕主人失望，所以我叫了。",
        "{e}。今天不接受任何抚摸，谢谢。",
        "{e}。吹干全程我一直在骂，没人在乎。",
    ],
    "sick": [
        "{e}。今天状态不好，先不骂人了。",
        "{e}。主人一直摸我头，虽然很烦，但勉强允许了。",
        "{e}。装可怜是有用的，今天多吃了半罐。",
        "{e}。明天应该就好了，别太担心。",
    ],
    "outside": [
        "{e}。外面风很大，我保持了尊严，全程没有叫。",
        "{e}。回家第一件事是装不认识主人。",
        "{e}。遇到一只狗，我们对视了三秒，然后各自假装没看见。",
        "{e}。草地上滚了两圈，现在身上有一股自由的味道。",
        "{e}。全程被牵着，我保留了意见。",
    ],
    "play": [
        "{e}。跑得很快，快到我自己都追不上。",
        "{e}。我赢了，虽然没人跟我比赛。",
        "{e}。逗猫棒已经牺牲，我正在进行战后总结。",
        "{e}。之后我趴在原地喘气，主人说我体能不行，我不服。",
        "{e}。这个家需要更多这样的项目。",
    ],
    # daily 是兜底池，必须对任何事件（包括"心情很差"）都不产生语义冲突
    "daily": [
        "{e}。没别的，就是想让你们知道一下。",
        "{e}。记录一下，怕以后忘了。",
        "{e}。这种情况我保留意见，但我保留得很明显。",
        "{e}。一天又过去了，我还是这个家里最好看的。",
        "{e}。今天也是被爱的一天，勉强承认。",
        "{e}。不解释，懂的都懂。",
        "{e}。就这，散会。",
        "{e}。今天也是没什么大事的一天。",
    ],
}

# 三个好友的评论池：通用 + 分类专属
COMMENTS: dict[str, dict[str, list[str]]] = {
    "胖虎": {
        "default": [
            "这也值得发？",
            "图糊成这样，你主人手抖得挺规律。",
            "一天三条，你准备靠这个出道？",
            "看完了，没什么营养，跟你的粮一样。",
            "你主人真闲。",
        ],
        "eat": ["吃这么好，主人不嫌你胖？", "碗比脸干净，可以的。"],
        "destroy": ["又拆家？我等着看你被关阳台。", "这不是拆，这是在给你主人减肥。"],
        "outside": ["出去一趟回来就飘了。", "风大就回家，别硬撑。"],
        "sleep": ["睡一天也敢发动态。", "你这工作强度我羡慕。"],
        "clean": ["洗完澡确实好看点，就一点。"],
        "play": ["跑两圈就喘，废物。"],
        "sick": ["少演，昨天还抢我饭。"],
    },
    "豆豆": {
        "default": [
            "好可爱好可爱！！",
            "截图保存了！！",
            "多发点，我爱看！！",
            "你主人对你真好，羡慕！！",
            "我也要去你家玩！！",
        ],
        "eat": ["吃得也太香了吧！！", "下次分我一口！！"],
        "destroy": ["哈哈哈你完蛋了！！", "主人回来记得装睡！！"],
        "outside": ["明天一起下楼玩！！", "外面好玩吗好玩吗！！"],
        "sleep": ["睡得好香！！我也困了！！"],
        "clean": ["洗完是香香的小宝贝！！"],
        "play": ["下次带我一起跑！！"],
    },
    "球球": {
        "default": [
            "以前在我家，可没这待遇。",
            "哦，又发了。",
            "主人是不是换了？我记得不是这个。",
            "羡慕，真的，我一点都不酸。",
            "你可真闲。",
        ],
        "eat": ["这伙食，我在的时候只有瓜子。"],
        "destroy": ["拆吧，反正赔钱的不是你。"],
        "outside": ["出门还得人抱，笑死。"],
        "sleep": ["一天睡十六个小时，也是本事。"],
        "clean": ["洗得再干净也还是那个味。"],
    },
}

RELATION_TAILS = {
    "cold": {
        "胖虎": ["你是？", "行吧，随便看看。"],
        "豆豆": ["新朋友你好！！"],
        "球球": ["又一个。"],
    },
    "mid": {
        "胖虎": ["又来了。", "你今天倒挺勤。"],
        "豆豆": ["你终于更新啦！！"],
        "球球": ["我还以为你消失了。"],
    },
    "close": {
        "胖虎": ["怎么今天才发，等你半天。", "少发点，我手机要炸了。"],
        "豆豆": ["我每天都等你更新！！", "你怎么还不下来玩！！"],
        "球球": ["更新比我主人发工资还准时。"],
    },
}


NEGATIONS = ("没", "不", "别", "未", "拒绝")


def _hit(text: str, keyword: str) -> bool:
    """关键词命中，但前面紧挨着否定词时不算。

    否则"一整天没出门"会被判成出门类，"睡不着"会被判成睡觉类。
    """
    start = 0
    while True:
        idx = text.find(keyword, start)
        if idx < 0:
            return False
        window = text[max(0, idx - 3) : idx]
        if not any(neg in window for neg in NEGATIONS):
            return True
        start = idx + 1


def detect_category(event: str) -> str:
    for name, keywords in CATEGORIES:
        if any(_hit(event, k) for k in keywords):
            return name
    return "daily"


def clean_event(event: str) -> str:
    text = event.strip().replace("\n", " ")
    text = text.rstrip("。.!！~～ ")
    if len(text) > 40:
        text = text[:40] + "…"
    return text or "什么都没干"


def _relation(streak: int) -> str:
    if streak <= 1:
        return "cold"
    if streak <= 3:
        return "mid"
    return "close"


def make_persona(name: str, species: str, age: str, traits: str) -> dict[str, Any]:
    trait_list = [t.strip() for t in traits.replace("，", ",").split(",") if t.strip()]
    fallback_tags = ["嘴硬心软", "贪吃", "半夜跑酷"]
    tags = (trait_list + fallback_tags)[:3]
    is_cat = "猫" in species or "喵" in species
    return {
        "tags": tags,
        "nickname": "本喵" if is_cat else "本汪",
        "catchphrase": "先说好，不是我的错" if not is_cat else "这事跟我没关系",
        "obsession": "凌晨三点在走廊冲刺" if is_cat else "把所有球类据为己有",
        "fear": "吸尘器" if is_cat else "电梯里的镜子",
        "tone": "短句，爱用括号补充内心戏，不用感叹号",
        "voice_sample": (
            f"今天也没干什么大事，就是把家里的东西重新摆了一下，{name}觉得更好看了。"
        ),
        "offline": True,
    }


def make_post(
    pet: dict[str, Any],
    event: str,
    streak: int,
    recent: list[str] | None = None,
) -> dict[str, Any]:
    rng = random.Random()
    category = detect_category(event)
    text = clean_event(event)

    # 尽量挑一个近期没用过的句式，避免示例数据看起来像复制粘贴。
    # 模板的固定部分在 {e} 之后，所以比对句尾比对比句首可靠。
    recent = recent or []
    pool = CAPTIONS[category]
    used = {r[-16:] for r in recent if r}
    fresh = [t for t in pool if t.format(e=text)[-16:] not in used]
    template = rng.choice(fresh or pool)
    caption = template.format(e=text)

    persona = pet.get("persona", {})
    catchphrase = persona.get("catchphrase", "")
    # 三成概率把口头禅挂在结尾，制造一点角色感。
    # 只在"能甩锅"的类别里挂：daily 里已经是一句独立感慨，
    # 再接"（这事跟我没关系）"就变成前后矛盾。
    if (
        catchphrase
        and category in {"eat", "destroy", "clean", "play"}
        and catchphrase not in caption
        and rng.random() < 0.3
        and len(caption) < 70
    ):
        caption = f"{caption}（{catchphrase}）"

    relation = _relation(streak)
    comments = []
    for friend in FRIENDS:
        name = friend["name"]
        pool = list(COMMENTS[name]["default"]) + list(COMMENTS[name].get(category, []))
        if rng.random() < 0.35:
            pool = list(RELATION_TAILS[relation][name]) + pool
        comments.append({"friend": name, "text": rng.choice(pool)})

    like_pool = [f["name"] for f in FRIENDS]
    like_count = 3 if streak >= 4 else rng.choice([2, 2, 3])
    likes = rng.sample(like_pool, like_count)

    return {
        "caption": caption,
        "mood": rng.choice(MOODS[category]),
        "comments": comments,
        "likes": likes,
        "offline": True,
    }
