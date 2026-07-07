from __future__ import annotations

import logging

import requests

from ..config import RakutenConfig
from ..rules import Item

logger = logging.getLogger(__name__)

SEARCH_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
RANKING_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"
SOURCE_NAME = "rakuten"


def _extract_image_url(raw_item: dict) -> str | None:
    images = raw_item.get("mediumImageUrls") or []
    if not images:
        return None
    first = images[0]
    if isinstance(first, dict):
        return first.get("imageUrl")
    return first


def _to_item(raw_item: dict) -> Item:
    return Item(
        source=SOURCE_NAME,
        item_id=raw_item["itemCode"],
        title=raw_item.get("itemName", ""),
        url=raw_item.get("itemUrl", ""),
        image_url=_extract_image_url(raw_item),
        shop=raw_item.get("shopName"),
        price=int(raw_item.get("itemPrice", 0)),
        list_price=None,  # Ichiba Item Search API does not reliably expose a list price
    )


def _request(url: str, params: dict) -> list[dict]:
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [entry["Item"] for entry in data.get("Items", [])]


def fetch_items(config: RakutenConfig) -> list[Item]:
    if not config.application_id:
        logger.warning("RAKUTEN_APPLICATION_ID が未設定のため楽天の取得をスキップします")
        return []

    items: dict[str, Item] = {}

    for keyword in config.keywords:
        params = {
            "applicationId": config.application_id,
            "keyword": keyword,
            "hits": config.hits_per_query,
            "sort": "-reviewCount",
            "format": "json",
        }
        if config.affiliate_id:
            params["affiliateId"] = config.affiliate_id
        try:
            raw_items = _request(SEARCH_URL, params)
        except requests.RequestException:
            logger.exception("楽天キーワード検索に失敗しました: %s", keyword)
            continue
        for raw in raw_items:
            item = _to_item(raw)
            items[item.item_id] = item

    for genre_id in config.ranking_genre_ids:
        params = {
            "applicationId": config.application_id,
            "genreId": genre_id,
            "format": "json",
        }
        if config.affiliate_id:
            params["affiliateId"] = config.affiliate_id
        try:
            raw_items = _request(RANKING_URL, params)
        except requests.RequestException:
            logger.exception("楽天ランキング取得に失敗しました: genreId=%s", genre_id)
            continue
        for raw in raw_items:
            item = _to_item(raw)
            items[item.item_id] = item

    return list(items.values())
