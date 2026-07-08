from __future__ import annotations

import argparse
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import AppConfig, DiscordConfig, RulesConfig, load_config
from .notifier.discord import send_deal_notification
from .rules import evaluate
from .sources import amazon, rakuten
from .storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_source(
    name,
    fetch_items,
    source_config,
    rules: RulesConfig,
    discord_config: DiscordConfig,
    storage: Storage,
) -> None:
    if not source_config.enabled:
        return

    logger.info("%s のポーリングを開始します", name)
    try:
        items = fetch_items(source_config)
    except Exception:
        logger.exception("%s の取得中に予期しないエラーが発生しました", name)
        return
    logger.info("%s: %d件取得しました", name, len(items))

    for item in items:
        deal = evaluate(item, storage, rules)
        if deal is None:
            continue
        try:
            send_deal_notification(discord_config, deal)
            storage.record_notification(item.source, item.item_id, item.price)
            logger.info("通知しました: %s (%s)", item.title, " / ".join(deal.reasons))
        except Exception:
            logger.exception("Discord通知の送信に失敗しました: %s", item.title)


def run_once(config: AppConfig, storage: Storage) -> None:
    run_source("rakuten", rakuten.fetch_items, config.rakuten, config.rules, config.discord, storage)
    run_source("amazon", amazon.fetch_items, config.amazon, config.amazon_rules, config.discord, storage)


def run_forever(config: AppConfig, storage: Storage) -> None:
    scheduler = BlockingScheduler(timezone="Asia/Tokyo")

    if config.rakuten.enabled:
        scheduler.add_job(
            run_source,
            "interval",
            minutes=config.rakuten.poll_interval_minutes,
            args=("rakuten", rakuten.fetch_items, config.rakuten, config.rules, config.discord, storage),
            next_run_time=datetime.now(),
            id="rakuten",
        )
    if config.amazon.enabled:
        scheduler.add_job(
            run_source,
            "interval",
            minutes=config.amazon.poll_interval_minutes,
            args=(
                "amazon",
                amazon.fetch_items,
                config.amazon,
                config.amazon_rules,
                config.discord,
                storage,
            ),
            next_run_time=datetime.now(),
            id="amazon",
        )

    if not scheduler.get_jobs():
        logger.warning("有効なソースがありません。config.yaml の enabled を確認してください")
        return

    logger.info("スケジューラを起動します")
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="ECサイト激安情報のDiscord通知")
    parser.add_argument("--once", action="store_true", help="スケジューラを使わず1回だけ実行して終了する")
    args = parser.parse_args()

    config = load_config()
    storage = Storage(config.db_path)

    if args.once:
        run_once(config, storage)
    else:
        run_forever(config, storage)


if __name__ == "__main__":
    main()
