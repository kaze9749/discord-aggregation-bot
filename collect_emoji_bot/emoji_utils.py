import re
import discord

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

def clean_value(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # 空白・ゼロ幅スペース・全角スペース・WORD JOINER
    pattern = r'[\u200B\u200C\u200D\uFEFF\u3000\u2060\s]+'
    return re.sub(pattern, '', s)

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