import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import time
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime


def clean_value(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # 空白・ゼロ幅スペース・全角スペース・WORD JOINER
    pattern = r'[\u200B\u200C\u200D\uFEFF\u3000\u2060\s]+'
    return re.sub(pattern, '', s)

def parse_emoji_string(val):
    # 前処理（不可視文字や全角スペース除去等）は必要に応じて
    val = val.strip().replace('\u200b', '')
    # カンマで区切る（カンマ区切り＋空白区切りの両方をサポートしたい場合は下記コメント参照）
    chunks = re.split(r'[, ]+', val)
    emojis = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # カスタム絵文字（:emoji_30: や <a:xxx:12345> も対象）
        if re.fullmatch(r'<a?:\w+:\d+>', chunk) or re.fullmatch(r':\w+:', chunk):
            emojis.append(chunk)
        # 通常のUnicode絵文字（一文字でOK）
        elif len(chunk) == 1:
            emojis.append(chunk)
        # サポート対象外の場合は無視（またはエラーとして通知も可能）
    return emojis

def find_channel_by_category_and_name(guild, cat_and_channel):
    """
    cat_and_channel: "カテゴリA/general" のような文字列
    """
    if "/" in cat_and_channel:
        category_name, channel_name = cat_and_channel.split("/", 1)
        category_name = category_name.strip()
        channel_name = channel_name.strip()
        for category in guild.categories:
            if category.name == category_name:
                for channel in category.text_channels:
                    if channel.name == channel_name:
                        return channel
    else:
        # "/"が無ければ従来通り
        return discord.utils.get(guild.text_channels, name=cat_and_channel.strip())
    return None


load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

def parse_args(args, ctx, bot):
    params = {
        "channel": ctx.channel,
        "user": None,
        "from": None,
        "to": None,
        "show_top_user": False,
        "image_only": False,
        "emojis": [],
    }
    for arg in args:
        arg = arg.strip()  # ★ ここで空白を一括除去
        if arg.startswith("channel="):
            val = clean_value(arg[len("channel="):])
            if val.startswith("<#") and val.endswith(">"):
                channel_id = int(val.strip('<#>'))
                params["channel"] = bot.get_channel(channel_id)
            elif val.isdigit():
                channel_id = int(val)
                params["channel"] = bot.get_channel(channel_id)
            else:
                # カテゴリ名/チャンネル名対応
                found = find_channel_by_category_and_name(ctx.guild, val)
                if found:
                    params["channel"] = found
                else:
                    params["channel"] = ctx.channel  # fallback
        elif arg.startswith("user="):
            val = arg[len("user="):].strip()
            if val.startswith("<@") and val.endswith(">"):
                user_id = int(val.strip('<@!>'))
                params["user"] = ctx.guild.get_member(user_id)
            else:
                found = discord.utils.get(ctx.guild.members, name=val.lstrip("@"))
                if found:
                    params["user"] = found
        elif arg.startswith("from="):
            params["from"] = arg[len("from="):].strip()
        elif arg.startswith("to="):
            params["to"] = arg[len("to="):].strip()
        elif arg.startswith("show_top_user="):
            params["show_top_user"] = arg[len("show_top_user="):].strip().lower() == "true"
        elif arg.startswith("image_only="):
            params["image_only"] = arg[len("image_only="):].strip().lower() == "true"
        elif arg.startswith("emoji="):
            val = arg[len("emoji="):]
            # emojiパース関数を通す
            params["emojis"].extend(parse_emoji_string(val))
    return params

@bot.command()
async def collect(ctx, *args):
    start_time = time.time()  # 計測開始
    p = parse_args(args, ctx, bot)

    # 日付
    def parse_date(date_str):
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    start_dt = parse_date(p["from"]) if p["from"] else None
    end_dt = parse_date(p["to"]) if p["to"] else None

    emoji_counts = {emoji: 0 for emoji in p["emojis"]}
    user_post_counts = {}

    await ctx.send(f'集計開始...（対象: {p["channel"].mention}）')

    async for message in p["channel"].history(limit=None, after=start_dt, before=end_dt):
        if p["user"] and message.author != p["user"]:
            continue
        if p["image_only"]:
            # 添付ファイルに画像がなければスキップ
            if not message.attachments or not any(att.content_type and att.content_type.startswith('image/') for att in message.attachments):
                continue

        message_emojis = {str(reaction.emoji) for reaction in message.reactions}
        matched = False
        for emoji in p["emojis"]:
            if emoji in message_emojis:
                emoji_counts[emoji] += 1
                matched = True
        if matched:
            user_post_counts[message.author] = user_post_counts.get(message.author, 0) + 1

    total_messages = sum(emoji_counts.values())
    if total_messages == 0:
        await ctx.send("該当する投稿が見つかりませんでした。")
        return

    results = "【絵文字ごとの投稿件数】\n"
    for emoji, count in emoji_counts.items():
        results += f"{emoji}: {count} 件\n"

    if p["show_top_user"] and user_post_counts:
        top_user, top_count = max(user_post_counts.items(), key=lambda x: x[1])
        results += f"\n最も投稿数の多かったユーザ: {top_user.display_name}（{top_count}件）"
    
    elapsed = time.time() - start_time  # 計測終了

    # 処理時間を表示
    results += f"\n処理時間: {elapsed:.2f}秒"

    await ctx.send(results)

async def monthly_collect_job():
    CHANNEL_ID = 1271507705445613589   # 写真館:シャニマス
    EMOJIS = [':mochi_sakuragi_mano:',':mochi_kazano_hiori:',':mochi_hachimiya_meguru:',':mochi_tsukioka_kogane:',':mochi_tanaka_mamimi:',':mochi_shirase_sakuya:',':mochi_mitsumine_yuika:',':mochi_yukoku_kiriko:',':mochi_komiya_kaho~1:',':mochi_sonoda_chiyoko:',':mochi_saijo_juri:',':mochi_morino_rinze:',':mochi_arisugawa_natsuha:',':mochi_osaki_amana:',':mochi_osaki_tenka:',':mochi_kuwayama_chiyuki:',':mochi_serizawa_asahi:',':mochi_mayuzumi_fuyuko:',':mochi_izumi_mei:',':mochi_asakura_toru:',':mochi_higuchi_madoka:',':mochi_fukumaru_koito:',':mochi_ichikawa_hinana:',':mochi_nanakusa_nichika:',':mochi_aketa_mikoto:',':mochi_ikaruga_luca:',':mochi_suzuki_hana:',':mochi_ikuta_haruki:']              # 集計対象の絵文字
    IMAGE_ONLY = True                 # 画像付きのみ集計する場合
    SHOW_TOP_USER=True

    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    first_day_last_month = (first_day_this_month - datetime.timedelta(days=1)).replace(day=1)
    last_day_last_month = first_day_this_month - datetime.timedelta(days=1)

    from_str = first_day_last_month.strftime('%Y-%m-%d')
    to_str   = last_day_last_month.strftime('%Y-%m-%d')

    channel = bot.get_channel(CHANNEL_ID)
    # Botのコマンド実装がasync def collect(ctx, *args)の場合
    # メッセージ送信からctxを取得
    msg = await channel.send(f'【自動集計】{from_str}〜{to_str}の集計を開始します。')
    ctx = await bot.get_context(msg)
    args = [
        f'from={from_str}',
        f'to={to_str}',
        f'emoji={",".join(EMOJIS)}',
        f'image_only={str(IMAGE_ONLY)}',
        f'show_top_user={str(SHOW_TOP_USER)}'
    ]
    await collect(ctx, *args)

@bot.event
async def on_ready():
    print(f'ログイン完了: {bot.user}')
    if not hasattr(bot, "scheduler_started"):
        scheduler = AsyncIOScheduler()
        # 毎月1日0時に実行
        scheduler.add_job(monthly_collect_job, 'cron', day=1, hour=0, minute=0)
        scheduler.start()
        bot.scheduler_started = True  # 多重起動防止

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
