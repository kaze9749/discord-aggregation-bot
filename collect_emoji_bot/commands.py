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

    # すべての絵文字を収集するためのdict（EMOJISの絵文字は0で初期化）
    emoji_counts = {}
    # 設定された絵文字は0で初期化
    for emoji in p["emojis"]:
        emoji_counts[emoji] = 0
    
    user_post_counts = {}

    # 複数チャンネル対応
    if p["channels"]:
        # すべてのチャンネルを対象にする場合
        channel_count = len(p["channels"])
        thread_count = sum(1 for ch in p["channels"] if hasattr(ch, 'parent') and ch.parent)
        regular_count = channel_count - thread_count
        
        if thread_count > 0:
            await ctx.send(f'集計開始...（対象: チャンネル {regular_count}個、スレッド {thread_count}個、合計 {channel_count}個）')
        else:
            await ctx.send(f'集計開始...（対象: 全チャンネル {channel_count}個）')
        target_channels = p["channels"]
    else:
        # 単一チャンネルの場合
        if hasattr(p["channel"], 'parent') and p["channel"].parent:
            await ctx.send(f'集計開始...（対象: スレッド {p["channel"].mention}）')
        else:
            await ctx.send(f'集計開始...（対象: {p["channel"].mention}）')
        target_channels = [p["channel"]]

    # アクセス可能なチャンネルのみフィルタリング
    accessible_channels = []
    skipped_channels = []
    
    for channel in target_channels:
        try:
            # チャンネルにアクセス権限があるかチェック
            if hasattr(channel, 'permissions_for'):
                permissions = channel.permissions_for(ctx.guild.me)
                if permissions.read_messages and permissions.read_message_history:
                    accessible_channels.append(channel)
                else:
                    skipped_channels.append(channel)
                    print(f"[権限不足] チャンネル '{channel.name}' (ID: {channel.id}) をスキップ - read_messages: {permissions.read_messages}, read_message_history: {permissions.read_message_history}")
            else:
                # permissions_forが無い場合（古いバージョン対応）
                accessible_channels.append(channel)
        except Exception as e:
            # 権限チェックでエラーが発生した場合はスキップ
            skipped_channels.append(channel)
            print(f"[権限チェックエラー] チャンネル '{channel.name}' (ID: {channel.id}) をスキップ - エラー: {e}")
    
    if skipped_channels:
        skipped_count = len(skipped_channels)
        print(f"[集計情報] 権限不足により {skipped_count} 個のチャンネルをスキップしました")
        await ctx.send(f'⚠️ アクセス権限がないため {skipped_count} 個のチャンネルをスキップしました。')
    
    if not accessible_channels:
        print("[集計エラー] アクセス可能なチャンネルがありません")
        await ctx.send('❌ アクセス可能なチャンネルがありません。')
        return
    
    target_channels = accessible_channels

    for channel in target_channels:
        try:
            async for message in channel.history(
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
                
                # すべての絵文字をカウント
                for emoji in message_emojis:
                    if emoji not in emoji_counts:
                        emoji_counts[emoji] = 0
                    emoji_counts[emoji] += 1
                    matched = True
                
                if matched:
                    user_post_counts[message.author] = (
                        user_post_counts.get(message.author, 0) + 1
                    )
        except Exception as e:
            # 個別のチャンネルでエラーが発生した場合はスキップ
            await ctx.send(f'⚠️ {channel.mention} でエラーが発生しました: {str(e)}')
            continue

    total_messages = sum(emoji_counts.values())
    if total_messages == 0:
        await ctx.send("該当する投稿が見つかりませんでした。")
        return

    results = "【絵文字ごとの投稿件数】\n"
    
    # EMOJISの順序で表示（0件でも表示）
    config_emojis = set(p["emojis"])
    
    for emoji in p["emojis"]:
        count = emoji_counts.get(emoji, 0)
        results += f"{emoji}: {count} 件\n"
    
    # EMOJISにない絵文字をスタンプ数・名前順でソート（5件以上のもののみ）
    other_emojis = {}
    for emoji, count in emoji_counts.items():
        if emoji not in config_emojis and count >= 5:
            other_emojis[emoji] = count
    
    if other_emojis:
        results += "\n【その他の絵文字】\n"
        # スタンプ数の降順、同じ数の場合は名前順でソート
        sorted_other_emojis = sorted(other_emojis.items(), key=lambda x: (-x[1], x[0]))
        for emoji, count in sorted_other_emojis:
            results += f"{emoji}: {count} 件\n"

    if p["show_top_user"] and user_post_counts:
        top_user, top_count = max(user_post_counts.items(), key=lambda x: x[1])
        results += f"\n最も投稿数の多かったユーザ: {top_user.display_name}（{top_count}件）"

    elapsed = time.time() - start_time  # 計測終了

    # 処理時間を表示
    results += f"\n処理時間: {elapsed:.2f}秒"

    # メッセージを分割して送信（Discord の 2000文字制限対応）
    await send_long_message(ctx, results)

async def send_long_message(ctx, message, max_length=2000):
    """
    長いメッセージを分割して送信する
    """
    if len(message) <= max_length:
        await ctx.send(message)
        return
    
    # メッセージを行単位で分割
    lines = message.split('\n')
    current_message = ""
    
    for line in lines:
        # 次の行を追加しても制限を超えない場合
        if len(current_message + line + '\n') <= max_length:
            current_message += line + '\n'
        else:
            # 現在のメッセージを送信
            if current_message.strip():
                await ctx.send(current_message.strip())
            
            # 単一行が制限を超える場合はさらに分割
            if len(line) > max_length:
                # 長い行を文字数で分割
                for i in range(0, len(line), max_length - 10):  # 少し余裕を持たせる
                    chunk = line[i:i + max_length - 10]
                    await ctx.send(chunk)
                current_message = ""
            else:
                current_message = line + '\n'
    
    # 最後のメッセージを送信
    if current_message.strip():
        await ctx.send(current_message.strip())

# --- コマンド登録部分 ---
def setup_commands(bot):
    @bot.command()
    async def collect(ctx, *args):
        await collect_impl(ctx, args)