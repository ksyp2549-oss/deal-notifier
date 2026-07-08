from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass
class RulesConfig:
    min_discount_percent: float
    price_drop_from_history_percent: float
    sale_keywords: list[str]
    renotify_cooldown_hours: float
    # None なら全期間の最安値と比較する
    price_history_window_days: float | None = None
    # 指定した場合、この価格帯の商品のみを通知対象にする
    price_min: int | None = None
    price_max: int | None = None


@dataclass
class RakutenConfig:
    enabled: bool
    application_id: str
    access_key: str
    affiliate_id: str
    poll_interval_minutes: int
    keywords: list[str]
    ranking_genre_ids: list[int]
    hits_per_query: int


@dataclass
class AmazonConfig:
    enabled: bool
    credential_id: str
    credential_secret: str
    partner_tag: str
    country: str
    poll_interval_minutes: int
    keywords: list[str]
    item_count: int


@dataclass
class DiscordConfig:
    webhook_url: str
    mention_role_id: str | None


@dataclass
class AppConfig:
    rakuten: RakutenConfig
    amazon: AmazonConfig
    discord: DiscordConfig
    rules: RulesConfig
    amazon_rules: RulesConfig
    db_path: Path = field(default_factory=lambda: ROOT_DIR / "data" / "deals.db")


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or ROOT_DIR / "config.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rakuten_raw = raw["rakuten"]
    amazon_raw = raw["amazon"]
    rules_raw = raw["rules"]
    discord_raw = raw["discord"]

    rakuten = RakutenConfig(
        enabled=rakuten_raw["enabled"],
        application_id=os.environ.get("RAKUTEN_APPLICATION_ID", ""),
        access_key=os.environ.get("RAKUTEN_ACCESS_KEY", ""),
        affiliate_id=os.environ.get("RAKUTEN_AFFILIATE_ID", ""),
        poll_interval_minutes=rakuten_raw["poll_interval_minutes"],
        keywords=rakuten_raw.get("keywords", []),
        ranking_genre_ids=rakuten_raw.get("ranking_genre_ids", []),
        hits_per_query=rakuten_raw.get("hits_per_query", 30),
    )

    amazon = AmazonConfig(
        enabled=amazon_raw["enabled"],
        credential_id=os.environ.get("AMAZON_CREDENTIAL_ID", ""),
        credential_secret=os.environ.get("AMAZON_CREDENTIAL_SECRET", ""),
        partner_tag=os.environ.get("AMAZON_PARTNER_TAG", ""),
        country=os.environ.get("AMAZON_COUNTRY", "JP"),
        poll_interval_minutes=amazon_raw["poll_interval_minutes"],
        keywords=amazon_raw.get("keywords", []),
        item_count=amazon_raw.get("item_count", 10),
    )

    discord = DiscordConfig(
        webhook_url=os.environ.get("DISCORD_WEBHOOK_URL", ""),
        mention_role_id=discord_raw.get("mention_role_id"),
    )

    rules = RulesConfig(
        min_discount_percent=rules_raw["min_discount_percent"],
        price_drop_from_history_percent=rules_raw["price_drop_from_history_percent"],
        sale_keywords=rules_raw.get("sale_keywords", []),
        renotify_cooldown_hours=rules_raw.get("renotify_cooldown_hours", 24),
        price_history_window_days=rules_raw.get("price_history_window_days"),
        price_min=rules_raw.get("price_min"),
        price_max=rules_raw.get("price_max"),
    )

    # amazon.rules に指定があればそのフィールドだけ上書きし、それ以外は共通の rules を引き継ぐ
    amazon_rules_raw = amazon_raw.get("rules", {})
    amazon_rules = RulesConfig(
        min_discount_percent=amazon_rules_raw.get("min_discount_percent", rules.min_discount_percent),
        price_drop_from_history_percent=amazon_rules_raw.get(
            "price_drop_from_history_percent", rules.price_drop_from_history_percent
        ),
        sale_keywords=amazon_rules_raw.get("sale_keywords", rules.sale_keywords),
        renotify_cooldown_hours=amazon_rules_raw.get("renotify_cooldown_hours", rules.renotify_cooldown_hours),
        price_history_window_days=amazon_rules_raw.get(
            "price_history_window_days", rules.price_history_window_days
        ),
        price_min=amazon_rules_raw.get("price_min", rules.price_min),
        price_max=amazon_rules_raw.get("price_max", rules.price_max),
    )

    return AppConfig(
        rakuten=rakuten, amazon=amazon, discord=discord, rules=rules, amazon_rules=amazon_rules
    )
