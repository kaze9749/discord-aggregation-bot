import os
from dotenv import load_dotenv

load_dotenv()  # これで.envファイルを読み込む

TOKEN = os.getenv("DISCORD_BOT_TOKEN")


TARGET_CHANNEL_ID = 1271507705445613589  # 集計の対象となるチャンネルID（＝集計範囲）
REPORT_CHANNEL_ID = 1374070679158390856  # 集計結果を送信するチャンネルID


EMOJIS = [
    "<:mochi_sakuragi_mano:1275071944483541012>",
    "<:mochi_kazano_hiori:1275071971947974678>",
    "<:mochi_hachimiya_meguru:1275071991677718528>",
    "<:mochi_tsukioka_kogane:1275479674662813717>",
    "<:mochi_tanaka_mamimi:1275479671194259633>",
    "<:mochi_shirase_sakuya:1275479663191392410>",
    "<:mochi_mitsumine_yuika:1275479632170188944>",
    "<:mochi_yukoku_kiriko:1275479678211063920>",
    "<:mochi_komiya_kaho~1:1275479621076520981>",
    "<:mochi_sonoda_chiyoko:1275479665364176947>",
    "<:mochi_saijo_juri:1275479648507269150>",
    "<:mochi_morino_rinze:1275479636163297391>",
    "<:mochi_arisugawa_natsuha:1275479583550083123>",
    "<:mochi_osaki_amana:1275479640772706317>",
    "<:mochi_osaki_tenka:1275479644547846225>",
    "<:mochi_kuwayama_chiyuki:1275479624901595230>",
    "<:mochi_serizawa_asahi:1275479659701735617>",
    "<:mochi_mayuzumi_fuyuko:1275479628756287661>",
    "<:mochi_izumi_mei:1275479613539094548>",
    "<:mochi_asakura_toru:1275479586305736836>",
    "<:mochi_higuchi_madoka:1275479595579211839>",
    "<:mochi_fukumaru_koito:1275479589572841604>",
    "<:mochi_ichikawa_hinana:1275479599072936021>",
    "<:mochi_nanakusa_nichika:1275479638524821586>",
    "<:mochi_aketa_mikoto:1275479580135915541>",
    "<:mochi_ikaruga_luca:1275479601836982335>",
    "<:mochi_suzuki_hana:1275479668849643601>",
    "<:mochi_ikuta_haruki:1275479610540429435>",
    "<:clap:>",
    "<:emoji_30:1275316913173692487>",
]  # 集計対象の絵文字

IMAGE_ONLY = True  # 画像付きのみ集計する場合
SHOW_TOP_USER = True
