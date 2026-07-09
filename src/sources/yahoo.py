from __future__ import annotations

import logging
import time

import requests

from ..config import YahooConfig
from ..rules import Item

logger = logging.getLogger(__name__)

SEARCH_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
SOURCE_NAME = "yahoo"

# 汎用的なUser-Agent(curlのデフォルト等)だと403 Forbiddenになるため、
# 実ブラウザに近いUser-Agentを明示的に送る(実APIで確認済み)。
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 連続リクエストで429(レート制限)になるのを避けるための待機時間(秒)
REQUEST_INTERVAL_SECONDS = 1.0


def _to_item(raw_item: dict) -> Item:
    price_label = raw_item.get("priceLabel") or {}
    list_price = price_label.get("fixedPrice")

    image = raw_item.get("image") or {}

    return Item(
        source=SOURCE_NAME,
        item_id=raw_item["code"],
        title=raw_item.get("name", ""),
        url=raw_item.get("url", ""),
        image_url=image.get("medium") or image.get("small"),
        shop=(raw_item.get("seller") or {}).get("name"),
        price=int(raw_item.get("price", 0)),
        list_price=int(list_price) if list_price else None,
    )


def _request(params: dict) -> list[dict]:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("hits", [])


def fetch_items(config: YahooConfig) -> list[Item]:
    if not config.client_id:
        logger.warning("YAHOO_CLIENT_ID が未設定のためYahoo!ショッピングの取得をスキップします")
        return []

    items: dict[str, Item] = {}

    for keyword in config.keywords:
        params = {
            "appid": config.client_id,
            "query": keyword,
            "results": config.hits_per_query,
            "sort": "-review_count",
        }
        try:
            raw_items = _request(params)
        except requests.RequestException:
            logger.exception("Yahoo!ショッピングキーワード検索に失敗しました: %s", keyword)
            continue
        finally:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        for raw in raw_items:
            item = _to_item(raw)
            items[item.item_id] = item

    for genre_id in config.genre_category_ids:
        params = {
            "appid": config.client_id,
            "genre_category_id": genre_id,
            "results": config.hits_per_query,
            "sort": "-review_count",
        }
        try:
            raw_items = _request(params)
        except requests.RequestException:
            logger.exception(
                "Yahoo!ショッピングジャンル取得に失敗しました: genre_category_id=%s", genre_id
            )
            continue
        finally:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        for raw in raw_items:
            item = _to_item(raw)
            items[item.item_id] = item

    return list(items.values())
