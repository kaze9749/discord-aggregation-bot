import time
import emoji_utils
from datetime import datetime, timezone

async def collect_impl(ctx, args):
    """
    集計処理本体。
    ctx: コマンドやBot送信用のcontext
    args: コマンド引数やパラメータ（listまたはdict想定）
    """
    start_time = time.time()  # 計測開始
    p = emoji_utils.parse_args(args, ctx, ctx.bot if hasattr(ctx, 'bot') else None)

    # 日付
    def parse_date(date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    start_dt = parse_date(p["from"]) if p["from"] else None
    end_dt = parse_date(p["to"]) if p["to"] else None

    emoji_counts = {emoji: 0 for emoji in p["emojis"]}
    user_post_counts = {}

    await ctx.send(f'集計開始...（対象: {p["channel"].mention}）')

    async for message in p["channel"].history(
        limit=None, after=start_dt, before=end_dt
    ):
        if p["user"] and message.author != p["user"]:
            continue
        if p["image_only"]:
            # 添付ファイルに画像がなければスキップ
            if not message.attachments or not any(
                att.content_type and att.content_type.startswith("image/")
                for att in message.attachments
            ):
                continue

        message_emojis = {str(reaction.emoji) for reaction in message.reactions}
        matched = False
        for emoji in p["emojis"]:
            if emoji in message_emojis:
                emoji_counts[emoji] += 1
                matched = True
        if matched:
            user_post_counts[message.author] = (
                user_post_counts.get(message.author, 0) + 1
            )

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

# --- コマンド登録部分 ---
def setup_commands(bot):
    @bot.command()
    async def collect(ctx, *args):
        await collect_impl(ctx, args)