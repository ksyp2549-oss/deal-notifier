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
    # ジャンル/カテゴリIDごとに price_drop_from_history_percent を上書きする
    # (例: {100227: 1.5} で楽天の食品ジャンルだけ1.5%値下がりで通知)
    category_price_drop_overrides: dict[int, float] = field(default_factory=dict)


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
class YahooConfig:
    enabled: bool
    client_id: str
    poll_interval_minutes: int
    keywords: list[str]
    genre_category_ids: list[int]
    hits_per_query: int


@dataclass
class DiscordConfig:
    webhook_url: str
    mention_role_id: str | None


@dataclass
class AppConfig:
    rakuten: RakutenConfig
    amazon: AmazonConfig
    yahoo: YahooConfig
    discord: DiscordConfig
    rules: RulesConfig
    amazon_rules: RulesConfig
    yahoo_rules: RulesConfig
    db_path: Path = field(default_factory=lambda: ROOT_DIR / "data" / "deals.db")


def _build_rules(base: RulesConfig, overrides: dict) -> RulesConfig:
    """overrides に指定があればそのフィールドだけ上書きし、それ以外は base を引き継ぐ"""
    return RulesConfig(
        min_discount_percent=overrides.get("min_discount_percent", base.min_discount_percent),
        price_drop_from_history_percent=overrides.get(
            "price_drop_from_history_percent", base.price_drop_from_history_percent
        ),
        sale_keywords=overrides.get("sale_keywords", base.sale_keywords),
        renotify_cooldown_hours=overrides.get("renotify_cooldown_hours", base.renotify_cooldown_hours),
        price_history_window_days=overrides.get(
            "price_history_window_days", base.price_history_window_days
        ),
        price_min=overrides.get("price_min", base.price_min),
        price_max=overrides.get("price_max", base.price_max),
        category_price_drop_overrides=overrides.get(
            "category_price_drop_overrides", base.category_price_drop_overrides
        ),
    )


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or ROOT_DIR / "config.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rakuten_raw = raw["rakuten"]
    amazon_raw = raw["amazon"]
    yahoo_raw = raw.get("yahoo", {})
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

    yahoo = YahooConfig(
        enabled=yahoo_raw.get("enabled", False),
        client_id=os.environ.get("YAHOO_CLIENT_ID", ""),
        poll_interval_minutes=yahoo_raw.get("poll_interval_minutes", 15),
        keywords=yahoo_raw.get("keywords", []),
        genre_category_ids=yahoo_raw.get("genre_category_ids", []),
        hits_per_query=yahoo_raw.get("hits_per_query", 20),
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
        category_price_drop_overrides=rules_raw.get("category_price_drop_overrides", {}),
    )

    amazon_rules = _build_rules(rules, amazon_raw.get("rules", {}))
    yahoo_rules = _build_rules(rules, yahoo_raw.get("rules", {}))

    return AppConfig(
        rakuten=rakuten,
        amazon=amazon,
        yahoo=yahoo,
        discord=discord,
        rules=rules,
        amazon_rules=amazon_rules,
        yahoo_rules=yahoo_rules,
    )
