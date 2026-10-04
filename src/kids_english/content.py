"""种子内容（M03.F01）：主题词库 + 原创小故事。

全部文案原创；角色名仅用于扮演场景（见 characters.py）。
完整性由 tests/test_content.py 把关：故事目标词必须落在词库、句子长度受限。
"""
from __future__ import annotations


def _w(text: str, phonetic: str, meaning_cn: str, theme: str, example_en: str, example_cn: str, level: int = 1) -> dict:
    return {
        "id": "w_" + text.replace(" ", "_"),
        "text": text,
        "phonetic": phonetic,
        "meaning_cn": meaning_cn,
        "theme": theme,
        "example_en": example_en,
        "example_cn": example_cn,
        "level": level,
    }


def seed_words() -> list[dict]:
    return [
        # colors
        _w("red", "/red/", "红色", "colors", "The apple is red.", "苹果是红色的。"),
        _w("blue", "/bluː/", "蓝色", "colors", "The sky is blue.", "天空是蓝色的。"),
        _w("yellow", "/ˈjeloʊ/", "黄色", "colors", "The banana is yellow.", "香蕉是黄色的。"),
        _w("green", "/ɡriːn/", "绿色", "colors", "The grass is green.", "草是绿色的。"),
        _w("pink", "/pɪŋk/", "粉色", "colors", "I like a pink dress.", "我喜欢粉裙子。"),
        _w("black", "/blæk/", "黑色", "colors", "The cat is black.", "猫是黑色的。"),
        _w("white", "/waɪt/", "白色", "colors", "The snow is white.", "雪是白色的。"),
        # animals
        _w("cat", "/kæt/", "猫", "animals", "The cat says meow.", "猫喵喵叫。"),
        _w("dog", "/dɒɡ/", "狗", "animals", "The dog can run.", "狗会跑。"),
        _w("bird", "/bɜːrd/", "鸟", "animals", "A bird can fly.", "鸟会飞。"),
        _w("fish", "/fɪʃ/", "鱼", "animals", "A fish can swim.", "鱼会游泳。"),
        _w("duck", "/dʌk/", "鸭子", "animals", "The duck is in the water.", "鸭子在水里。"),
        _w("rabbit", "/ˈræbɪt/", "兔子", "animals", "The rabbit can jump.", "兔子会跳。", level=2),
        _w("bear", "/ber/", "熊", "animals", "The bear is big.", "熊很大。", level=2),
        _w("mouse", "/maʊs/", "老鼠", "animals", "A little mouse.", "一只小老鼠。", level=2),
        # food
        _w("apple", "/ˈæpl/", "苹果", "food", "I eat an apple.", "我吃一个苹果。"),
        _w("banana", "/bəˈnænə/", "香蕉", "food", "Peel the banana.", "剥香蕉。"),
        _w("bread", "/bred/", "面包", "food", "The bread is soft.", "面包软软的。"),
        _w("milk", "/mɪlk/", "牛奶", "food", "I drink milk.", "我喝牛奶。"),
        _w("egg", "/eɡ/", "鸡蛋", "food", "One egg, please.", "请给我一个鸡蛋。"),
        _w("cake", "/keɪk/", "蛋糕", "food", "The cake is yummy.", "蛋糕真好吃。"),
        _w("juice", "/dʒuːs/", "果汁", "food", "Apple juice, please.", "请给我苹果汁。"),
        # numbers
        _w("one", "/wʌn/", "一", "numbers", "One apple, please.", "请给我一个苹果。"),
        _w("two", "/tuː/", "二", "numbers", "Two little hands.", "两只小手。"),
        _w("three", "/θriː/", "三", "numbers", "One, two, three!", "一、二、三！"),
        _w("four", "/fɔːr/", "四", "numbers", "Four little ducks.", "四只小鸭子。"),
        _w("five", "/faɪv/", "五", "numbers", "High five!", "击个掌！"),
        # actions
        _w("run", "/rʌn/", "跑", "actions", "I can run fast.", "我能跑得快。"),
        _w("jump", "/dʒʌmp/", "跳", "actions", "Jump! Jump! Jump!", "跳！跳！跳！"),
        _w("eat", "/iːt/", "吃", "actions", "Let's eat the cake.", "我们吃蛋糕吧。"),
        _w("sleep", "/sliːp/", "睡觉", "actions", "Time to sleep.", "到睡觉时间啦。"),
        _w("play", "/pleɪ/", "玩", "actions", "Let's play together.", "我们一起玩吧。"),
        _w("sing", "/sɪŋ/", "唱歌", "actions", "Sing with me!", "跟我一起唱！"),
        _w("dance", "/dæns/", "跳舞", "actions", "Bear dances slowly.", "熊跳得很慢。", level=2),
        _w("hug", "/hʌɡ/", "抱抱", "actions", "Give me a hug.", "抱一个。", level=2),
        # body
        _w("hand", "/hænd/", "手", "body", "Wash your hands.", "洗洗小手。"),
        _w("foot", "/fʊt/", "脚", "body", "One foot, two feet.", "一只脚，两只脚。"),
        _w("eye", "/aɪ/", "眼睛", "body", "Close your eyes.", "闭上眼睛。"),
        _w("ear", "/ɪr/", "耳朵", "body", "I hear with my ears.", "我用耳朵听。"),
        _w("nose", "/noʊz/", "鼻子", "body", "Touch your nose.", "摸摸鼻子。"),
        _w("mouth", "/maʊθ/", "嘴巴", "body", "Open your mouth.", "张开嘴巴。"),
        # family
        _w("mama", "/ˈmɑːmə/", "妈妈", "family", "I love mama.", "我爱妈妈。"),
        _w("papa", "/ˈpɑːpə/", "爸爸", "family", "Papa is tall.", "爸爸个子高。"),
        _w("baby", "/ˈbeɪbi/", "宝宝", "family", "The baby sleeps.", "宝宝睡觉了。"),
        _w("grandma", "/ˈɡrænmɑː/", "奶奶/外婆", "family", "Grandma makes cake.", "奶奶做蛋糕。", level=2),
        _w("grandpa", "/ˈɡrænpɑː/", "爷爷/外公", "family", "Grandpa reads to me.", "爷爷给我读故事。", level=2),
        # weather
        _w("sun", "/sʌn/", "太阳", "weather", "The sun is bright.", "太阳亮亮的。"),
        _w("rain", "/reɪn/", "雨", "weather", "Pitter-patter, rain!", "滴答滴答，下雨！"),
        _w("wind", "/wɪnd/", "风", "weather", "The wind blows.", "风吹呀吹。"),
        _w("snow", "/snoʊ/", "雪", "weather", "White snow falls.", "白雪飘下来。", level=2),
        _w("cloud", "/klaʊd/", "云", "weather", "A big white cloud.", "一朵大白云。", level=2),
        # toys
        _w("ball", "/bɔːl/", "球", "toys", "Roll the ball.", "滚滚球。"),
        _w("kite", "/kaɪt/", "风筝", "toys", "The kite flies high.", "风筝飞得高。", level=2),
        _w("boat", "/boʊt/", "小船", "toys", "The boat floats.", "小船漂呀漂。", level=2),
        _w("car", "/kɑːr/", "小汽车", "toys", "The car goes vroom.", "小汽车嘀嘀。"),
        _w("doll", "/dɒl/", "娃娃", "toys", "Hug the doll.", "抱抱娃娃。", level=2),
        # greetings
        _w("hello", "/həˈloʊ/", "你好", "greetings", "Hello, friend!", "你好，朋友！"),
        _w("bye", "/baɪ/", "再见", "greetings", "Bye-bye, see you!", "再见，回头见！"),
        _w("thank you", "/θæŋk juː/", "谢谢", "greetings", "Thank you, mama!", "谢谢妈妈！"),
        _w("please", "/pliːz/", "请", "greetings", "More milk, please.", "请再来点牛奶。"),
        _w("good morning", "/ɡʊd ˈmɔːrnɪŋ/", "早上好", "greetings", "Good morning, sun!", "早上好，太阳！"),
        _w("good night", "/ɡʊd naɪt/", "晚安", "greetings", "Good night, moon.", "晚安，月亮。"),
    ]


def seed_stories() -> list[dict]:
    """原创迷你故事：每页一句（≤9 词），目标词取自词库。"""
    return [
        {
            "id": "st_red_balloon",
            "title_en": "The Red Balloon",
            "title_cn": "红气球",
            "character_id": "maisy",
            "theme": "colors",
            "pages": [
                {"en": "Maisy has a red balloon.", "cn": "波波有一个红气球。", "words": ["red"]},
                {"en": "Her friend has a yellow balloon.", "cn": "她的朋友有一个黄气球。", "words": ["yellow"]},
                {"en": "They see a big blue sky.", "cn": "她们看到大大的蓝天。", "words": ["blue"]},
                {"en": "Green grass! Let's play!", "cn": "绿绿的草地！一起玩吧！", "words": ["green", "play"]},
                {"en": "Oh no! The red balloon flies away!", "cn": "哎呀！红气球飞走了！", "words": ["red"]},
                {"en": "Bye-bye, red balloon!", "cn": "再见啦，红气球！", "words": ["red", "bye"]},
            ],
        },
        {
            "id": "st_picnic",
            "title_en": "A Picnic with Maisy",
            "title_cn": "和波波去野餐",
            "character_id": "maisy",
            "theme": "food",
            "pages": [
                {"en": "Maisy has one big apple.", "cn": "波波有一个大苹果。", "words": ["apple", "one"]},
                {"en": "Her friend brings two bananas.", "cn": "她的朋友带来两根香蕉。", "words": ["banana", "two"]},
                {"en": "Three pieces of bread for us!", "cn": "给我们三块面包！", "words": ["bread", "three"]},
                {"en": "Here is milk for everyone.", "cn": "这是给大家的牛奶。", "words": ["milk"]},
                {"en": "Yummy! Thank you, Maisy!", "cn": "真好吃！谢谢你，波波！", "words": ["thank you"]},
                {"en": "Let's eat and play!", "cn": "我们一起吃喝玩耍吧！", "words": ["eat", "play"]},
            ],
        },
        {
            "id": "st_sleepy_puppy",
            "title_en": "The Sleepy Puppy",
            "title_cn": "犯困的小狗",
            "character_id": "chase",
            "theme": "animals",
            "pages": [
                {"en": "Chase sees a little dog.", "cn": "阿奇看见一只小狗。", "words": ["dog"]},
                {"en": "The dog wants to sleep.", "cn": "小狗想睡觉了。", "words": ["sleep"]},
                {"en": "A cat runs by.", "cn": "一只小猫跑过去。", "words": ["cat", "run"]},
                {"en": "A bird sings a soft song.", "cn": "一只小鸟唱着轻轻的歌。", "words": ["bird", "sing"]},
                {"en": "Shh! The puppy is sleeping.", "cn": "嘘！小狗在睡觉呢。", "words": []},
                {"en": "Good night, little dog.", "cn": "晚安，小狗。", "words": ["good night"]},
            ],
        },
        {
            "id": "st_rainy_day",
            "title_en": "Rainy Day Fun",
            "title_cn": "下雨天也好玩",
            "character_id": "penelope",
            "theme": "weather",
            "pages": [
                {"en": "Penelope hears the rain.", "cn": "蓝色小考拉听到雨声。", "words": ["rain"]},
                {"en": "No sun today.", "cn": "今天没有太阳。", "words": ["sun"]},
                {"en": "The wind blows her hat.", "cn": "风吹走了她的小帽子。", "words": ["wind"]},
                {"en": "Let's sing a song!", "cn": "我们唱首歌吧！", "words": ["sing"]},
                {"en": "We can play inside.", "cn": "我们可以在屋里玩。", "words": ["play"]},
                {"en": "Rain, rain, go away!", "cn": "雨呀雨呀快走开！", "words": ["rain"]},
            ],
        },
        {
            "id": "st_birthday",
            "title_en": "Peppa's Birthday Cake",
            "title_cn": "佩奇的生日蛋糕",
            "character_id": "peppa",
            "theme": "numbers",
            "pages": [
                {"en": "Today is Peppa's big day.", "cn": "今天是佩奇的大日子。", "words": []},
                {"en": "Mama makes a big cake.", "cn": "妈妈做了个大蛋糕。", "words": ["mama", "cake"]},
                {"en": "One, two, three candles!", "cn": "一、二、三根蜡烛！", "words": ["one", "two", "three"]},
                {"en": "Hello, friends! Come in!", "cn": "朋友们好！快进来！", "words": ["hello"]},
                {"en": "Thank you for the cake!", "cn": "谢谢你们的蛋糕！", "words": ["thank you", "cake"]},
                {"en": "Yummy! Let's dance!", "cn": "真好吃！我们跳舞吧！", "words": ["dance"]},
            ],
        },
    ]
