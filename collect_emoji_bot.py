import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import time

import re

def clean_value(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # 空白・ゼロ幅スペース・全角スペース・WORD JOINER
    pattern = r'[\u200B\u200C\u200D\uFEFF\u3000\u2060\s]+'
    return re.sub(pattern, '', s)

def parse_emoji_string(val):
    # カンマ・空白両方で区切る
    # まず不可視文字など消してから
    val = clean_value(val)
    # カンマ or 空白でsplit
    emoji_chunks = re.split(r'[, ]+', val)
    # 空欄を除いて全部1文字ずつバラす
    emojis = []
    for chunk in emoji_chunks:
        chunk = chunk.strip()
        if chunk:
            # 1文字ずつバラす（複数絵文字を連続指定も対応）
            emojis.extend([e for e in chunk])
    # 絵文字のみ（空文字の混入防止）
    return [e for e in emojis if e]

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

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
