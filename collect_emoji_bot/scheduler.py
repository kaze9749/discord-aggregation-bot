from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
import commands
from config import (
    TARGET_CHANNEL_ID,
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
            # キャッシュにない場合はAPIで取得（非同期で！）
            channel = await bot.fetch_channel(REPORT_CHANNEL_ID)
        # Botのコマンド実装がasync def collect(ctx, *args)の場合
        # メッセージ送信からctxを取得
        msg = await channel.send(
            f"【自動集計】{from_str}〜{to_str}の集計を開始します。"
        )
        ctx = await bot.get_context(msg)
        args = [
            f"channel={TARGET_CHANNEL_ID}",
            f"from={from_str}",
            f"to={to_str}",
            f'emoji={",".join(EMOJIS)}',
            f"image_only={str(IMAGE_ONLY)}",
            f"show_top_user={str(SHOW_TOP_USER)}",
        ]
        await commands.collect_impl(ctx, args)

    @bot.event
    async def on_ready():
        print(f"ログイン完了: {bot.user}")
        if not hasattr(bot, "scheduler_started"):
            scheduler = AsyncIOScheduler()
            # 毎月1日0時に実行
            scheduler.add_job(monthly_collect_job, "cron", day=1, hour=0, minute=0)
            scheduler.start()
            bot.scheduler_started = True  # 多重起動防止
