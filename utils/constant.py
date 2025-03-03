import enum


class TencentZoneTypes(enum.Enum):
    LIFESTYLE = '生活'
    CUTE_KIDS = '萌娃'
    MUSIC = '音乐'
    KNOWLEDGE = '知识'
    EMOTION = '情感'
    TRAVEL_SCENERY = '旅行风景'
    FASHION = '时尚'
    FOOD = '美食'
    LIFE_HACKS = '生活技巧'
    DANCE = '舞蹈'
    MOVIES_TV_SHOWS = '影视综艺'
    SPORTS = '运动'
    FUNNY = '搞笑'
    CELEBRITIES = '明星名人'
    NEWS_INFO = '新闻资讯'
    GAMING = '游戏'
    AUTOMOTIVE = '车'
    ANIME = '二次元'
    TALENT = '才艺'
    CUTE_PETS = '萌宠'
    INDUSTRY_MACHINERY_CONSTRUCTION = '机械'
    ANIMALS = '动物'
    PARENTING = '育儿'
    TECHNOLOGY = '科技'

class VideoZoneTypes(enum.Enum):
    """
    所有分区枚举

    - MAINPAGE: 主页
    - ANIME: 番剧
        - ANIME_SERIAL: 连载中番剧
        - ANIME_FINISH: 已完结番剧
        - ANIME_INFORMATION: 资讯
        - ANIME_OFFICAL: 官方延伸
    - MOVIE: 电影
    - GUOCHUANG: 国创
        - GUOCHUANG_CHINESE: 国产动画
        - GUOCHUANG_ORIGINAL: 国产原创相关
        - GUOCHUANG_PUPPETRY: 布袋戏
        - GUOCHUANG_MOTIONCOMIC: 动态漫·广播剧
        - GUOCHUANG_INFORMATION: 资讯
    - TELEPLAY: 电视剧
    - DOCUMENTARY: 纪录片
    - DOUGA: 动画
        - DOUGA_MAD: MAD·AMV
        - DOUGA_MMD: MMD·3D
        - DOUGA_VOICE: 短片·手书·配音
        - DOUGA_GARAGE_KIT: 手办·模玩
        - DOUGA_TOKUSATSU: 特摄
        - DOUGA_ACGNTALKS: 动漫杂谈
        - DOUGA_OTHER: 综合
    - GAME: 游戏
        - GAME_STAND_ALONE: 单机游戏
        - GAME_ESPORTS: 电子竞技
        - GAME_MOBILE: 手机游戏
        - GAME_ONLINE: 网络游戏
        - GAME_BOARD: 桌游棋牌
        - GAME_GMV: GMV
        - GAME_MUSIC: 音游
        - GAME_MUGEN: Mugen
    - KICHIKU: 鬼畜
        - KICHIKU_GUIDE: 鬼畜调教
        - KICHIKU_MAD: 音MAD
        - KICHIKU_MANUAL_VOCALOID: 人力VOCALOID
        - KICHIKU_THEATRE: 鬼畜剧场
        - KICHIKU_COURSE: 教程演示
    - MUSIC: 音乐
        - MUSIC_ORIGINAL: 原创音乐
        - MUSIC_COVER: 翻唱
        - MUSIC_PERFORM: 演奏
        - MUSIC_VOCALOID: VOCALOID·UTAU
        - MUSIC_LIVE: 音乐现场
        - MUSIC_MV: MV
        - MUSIC_COMMENTARY: 乐评盘点
        - MUSIC_TUTORIAL: 音乐教学
        - MUSIC_OTHER: 音乐综合
    - DANCE: 舞蹈
        - DANCE_OTAKU: 宅舞
        - DANCE_HIPHOP: 街舞
        - DANCE_STAR: 明星舞蹈
        - DANCE_CHINA: 中国舞
        - DANCE_THREE_D: 舞蹈综合
        - DANCE_DEMO: 舞蹈教程
    - CINEPHILE: 影视
        - CINEPHILE_CINECISM: 影视杂谈
        - CINEPHILE_MONTAGE: 影视剪辑
        - CINEPHILE_SHORTFILM: 小剧场
        - CINEPHILE_TRAILER_INFO: 预告·资讯
    - ENT: 娱乐
        - ENT_VARIETY: 综艺
        - ENT_TALKER: 娱乐杂谈
        - ENT_FANS: 粉丝创作
        - ENT_CELEBRITY: 明星综合
    - KNOWLEDGE: 知识
        - KNOWLEDGE_SCIENCE: 科学科普
        - KNOWLEDGE_SOCIAL_SCIENCE: 社科·法律·心理
        - KNOWLEDGE_HUMANITY_HISTORY: 人文历史
        - KNOWLEDGE_BUSINESS: 财经商业
        - KNOWLEDGE_CAMPUS: 校园学习
        - KNOWLEDGE_CAREER: 职业职场
        - KNOWLEDGE_DESIGN: 设计·创意
        - KNOWLEDGE_SKILL: 野生技能协会
    - TECH: 科技
        - TECH_DIGITAL: 数码
        - TECH_APPLICATION: 软件应用
        - TECH_COMPUTER_TECH: 计算机技术
        - TECH_INDUSTRY: 科工机械
    - INFORMATION: 资讯
        - INFORMATION_HOTSPOT: 热点
        - INFORMATION_GLOBAL: 环球
        - INFORMATION_SOCIAL: 社会
        - INFORMATION_MULTIPLE: 综合
    - FOOD: 美食
        - FOOD_MAKE: 美食制作
        - FOOD_DETECTIVE: 美食侦探
        - FOOD_MEASUREMENT: 美食测评
        - FOOD_RURAL: 田园美食
        - FOOD_RECORD: 美食记录
    - LIFE: 生活
        - LIFE_FUNNY: 搞笑
        - LIFE_TRAVEL: 出行
        - LIFE_RURALLIFE: 三农
        - LIFE_HOME: 家居房产
        - LIFE_HANDMAKE: 手工
        - LIFE_PAINTING: 绘画
        - LIFE_DAILY: 日常
    - CAR: 汽车
        - CAR_RACING: 赛车
        - CAR_MODIFIEDVEHICLE: 改装玩车
        - CAR_NEWENERGYVEHICLE: 新能源车
        - CAR_TOURINGCAR: 房车
        - CAR_MOTORCYCLE: 摩托车
        - CAR_STRATEGY: 购车攻略
        - CAR_LIFE: 汽车生活
    - FASHION: 时尚
        - FASHION_MAKEUP: 美妆护肤
        - FASHION_COS: 仿妆cos
        - FASHION_CLOTHING: 穿搭
        - FASHION_TREND: 时尚潮流
    - SPORTS: 运动
        - SPORTS_BASKETBALL: 篮球
        - SPORTS_FOOTBALL: 足球
        - SPORTS_AEROBICS: 健身
        - SPORTS_ATHLETIC: 竞技体育
        - SPORTS_CULTURE: 运动文化
        - SPORTS_COMPREHENSIVE: 运动综合
    - ANIMAL: 动物圈
        - ANIMAL_CAT: 喵星人
        - ANIMAL_DOG: 汪星人
        - ANIMAL_PANDA: 大熊猫
        - ANIMAL_WILD_ANIMAL: 野生动物
        - ANIMAL_REPTILES: 爬宠
        - ANIMAL_COMPOSITE: 动物综合
    - VLOG: VLOG
    """

    MAINPAGE = 0

    ANIME = 13
    ANIME_SERIAL = 33
    ANIME_FINISH = 32
    ANIME_INFORMATION = 51
    ANIME_OFFICAL = 152

    MOVIE = 23

    GUOCHUANG = 167
    GUOCHUANG_CHINESE = 153
    GUOCHUANG_ORIGINAL = 168
    GUOCHUANG_PUPPETRY = 169
    GUOCHUANG_MOTIONCOMIC = 195
    GUOCHUANG_INFORMATION = 170

    TELEPLAY = 11

    DOCUMENTARY = 177

    DOUGA = 1
    DOUGA_MAD = 24
    DOUGA_MMD = 25
    DOUGA_VOICE = 47
    DOUGA_GARAGE_KIT = 210
    DOUGA_TOKUSATSU = 86
    DOUGA_ACGNTALKS = 253
    DOUGA_OTHER = 27

    GAME = 4
    GAME_STAND_ALONE = 17
    GAME_ESPORTS = 171
    GAME_MOBILE = 172
    GAME_ONLINE = 65
    GAME_BOARD = 173
    GAME_GMV = 121
    GAME_MUSIC = 136
    GAME_MUGEN = 19

    KICHIKU = 119
    KICHIKU_GUIDE = 22
    KICHIKU_MAD = 26
    KICHIKU_MANUAL_VOCALOID = 126
    KICHIKU_THEATRE = 216
    KICHIKU_COURSE = 127

    MUSIC = 3
    MUSIC_ORIGINAL = 28
    MUSIC_COVER = 31
    MUSIC_PERFORM = 59
    MUSIC_VOCALOID = 30
    MUSIC_LIVE = 29
    MUSIC_MV = 193
    MUSIC_COMMENTARY = 243
    MUSIC_TUTORIAL = 244
    MUSIC_OTHER = 130

    DANCE = 129
    DANCE_OTAKU = 20
    DANCE_HIPHOP = 198
    DANCE_STAR = 199
    DANCE_CHINA = 200
    DANCE_THREE_D = 154
    DANCE_DEMO = 156

    CINEPHILE = 181
    CINEPHILE_CINECISM = 182
    CINEPHILE_MONTAGE = 183
    CINEPHILE_SHORTFILM = 85
    CINEPHILE_TRAILER_INFO = 184

    ENT = 5
    ENT_VARIETY = 71
    ENT_TALKER = 241
    ENT_FANS = 242
    ENT_CELEBRITY = 137

    KNOWLEDGE = 36
    KNOWLEDGE_SCIENCE = 201
    KNOWLEDGE_SOCIAL_SCIENCE = 124
    KNOWLEDGE_HUMANITY_HISTORY = 228
    KNOWLEDGE_BUSINESS = 207
    KNOWLEDGE_CAMPUS = 208
    KNOWLEDGE_CAREER = 209
    KNOWLEDGE_DESIGN = 229
    KNOWLEDGE_SKILL = 122

    TECH = 188
    TECH_DIGITAL = 95
    TECH_APPLICATION = 230
    TECH_COMPUTER_TECH = 231
    TECH_INDUSTRY = 232

    INFORMATION = 202
    INFORMATION_HOTSPOT = 203
    INFORMATION_GLOBAL = 204
    INFORMATION_SOCIAL = 205
    INFORMATION_MULTIPLE = 206

    FOOD = 211
    FOOD_MAKE = 76
    FOOD_DETECTIVE = 212
    FOOD_MEASUREMENT = 213
    FOOD_RURAL = 214
    FOOD_RECORD = 215

    LIFE = 160
    LIFE_FUNNY = 138
    LIFE_TRAVEL = 250
    LIFE_RURALLIFE = 251
    LIFE_HOME = 239
    LIFE_HANDMAKE = 161
    LIFE_PAINTING = 162
    LIFE_DAILY = 21

    CAR = 223
    CAR_RACING = 245
    CAR_MODIFIEDVEHICLE = 246
    CAR_NEWENERGYVEHICLE = 247
    CAR_TOURINGCAR = 248
    CAR_MOTORCYCLE = 240
    CAR_STRATEGY = 227
    CAR_LIFE = 176

    FASHION = 155
    FASHION_MAKEUP = 157
    FASHION_COS = 252
    FASHION_CLOTHING = 158
    FASHION_TREND = 159

    SPORTS = 234
    SPORTS_BASKETBALL = 235
    SPORTS_FOOTBALL = 249
    SPORTS_AEROBICS = 164
    SPORTS_ATHLETIC = 236
    SPORTS_CULTURE = 237
    SPORTS_COMPREHENSIVE = 238

    ANIMAL = 217
    ANIMAL_CAT = 218
    ANIMAL_DOG = 219
    ANIMAL_PANDA = 220
    ANIMAL_WILD_ANIMAL = 221
    ANIMAL_REPTILES = 222
    ANIMAL_COMPOSITE = 75

    VLOG = 19
