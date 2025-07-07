from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import commands
from config import (
    REPORT_CHANNEL_ID,
    EMOJIS,
    IMAGE_ONLY,
    SHOW_TOP_USER,
)


def setup_scheduler(bot):
    async def monthly_collect_job():

        today = datetime.date.today()
        first_day_this_month = today.replace(day=1)
        first_day_last_month = (
            first_day_this_month - datetime.timedelta(days=1)
        ).replace(day=1)
        last_day_last_month = first_day_this_month - datetime.timedelta(days=1)

        from_str = first_day_last_month.strftime("%Y-%m-%d")
        to_str = last_day_last_month.strftime("%Y-%m-%d")
        channel = bot.get_channel(REPORT_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(REPORT_CHANNEL_ID)

        msg = await channel.send(
            f"【定期自動集計】{from_str}〜{to_str}の集計を開始します。"
        )
        print(f"[定期集計] {from_str}〜{to_str}の集計を開始 - 報告チャンネル: {channel.name} (ID: {channel.id})")
        ctx = await bot.get_context(msg)
        args = [
            f"channel=all",  # すべてのチャンネルを対象にする
            f"from={from_str}",
            f"to={to_str}",
            f'emoji={",".join(EMOJIS)}',
            f"image_only={str(IMAGE_ONLY)}",
            f"show_top_user={str(SHOW_TOP_USER)}",
        ]
        try:
            await commands.collect_impl(ctx, args)
            print(f"[定期集計] {from_str}〜{to_str}の集計完了")
        except Exception as e:
            print(f"[定期集計エラー] {from_str}〜{to_str}の集計中にエラー: {e}")
            await channel.send(f"❌ 定期集計中にエラーが発生しました: {str(e)}")
            raise

    @bot.event
    async def on_ready():
        print(f"ログイン完了: {bot.user}")
        if not hasattr(bot, "scheduler_started"):
            scheduler = AsyncIOScheduler()
            # テスト用: 毎月7日9時15分に実行
            # 本番用: 毎月2日0時0分に実行する場合は day=2, hour=0, minute=0 に変更
            scheduler.add_job(monthly_collect_job, "cron", day=7, hour=10, minute=57)
            scheduler.start()
            bot.scheduler_started = True  # 多重起動防止
