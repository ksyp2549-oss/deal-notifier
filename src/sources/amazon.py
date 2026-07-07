from __future__ import annotations

import logging

from ..config import AmazonConfig
from ..rules import Item

logger = logging.getLogger(__name__)
SOURCE_NAME = "amazon"

# PA-API(旧Product Advertising API)は2026年5月15日に廃止済みのため、後継の
# Amazon Creators API(amazon_creatorsapi, OAuth2認証)を利用する。


def _country_enum(code: str):
    from amazon_creatorsapi import Country

    try:
        return getattr(Country, code.upper())
    except AttributeError:
        logger.warning("未対応の国コードのため Country.US にフォールバックします: %s", code)
        return Country.US


def _dig(obj, *attrs):
    """Optional なフィールドを辿り、途中でNoneに当たったらNoneを返す。"""
    for attr in attrs:
        if obj is None:
            return None
        obj = getattr(obj, attr, None)
    return obj


def _to_item(raw) -> Item | None:
    asin = _dig(raw, "asin")
    title = _dig(raw, "item_info", "title", "display_value")
    if not asin or not title:
        return None

    listings = _dig(raw, "offers_v2", "listings") or []
    if not listings:
        return None
    listing = listings[0]

    price_amount = _dig(listing, "price", "money", "amount")
    if price_amount is None:
        return None
    price = int(price_amount)

    list_price = None
    saving_basis_amount = _dig(listing, "price", "saving_basis", "money", "amount")
    if saving_basis_amount is not None:
        list_price = int(saving_basis_amount)

    return Item(
        source=SOURCE_NAME,
        item_id=asin,
        title=title,
        url=_dig(raw, "detail_page_url") or f"https://www.amazon.co.jp/dp/{asin}",
        image_url=_dig(raw, "images", "primary", "large", "url"),
        shop=_dig(listing, "merchant_info", "name"),
        price=price,
        list_price=list_price,
    )


def fetch_items(config: AmazonConfig) -> list[Item]:
    if not (config.credential_id and config.credential_secret and config.partner_tag):
        logger.warning("Amazon Creators API の認証情報が未設定のためスキップします")
        return []

    from amazon_creatorsapi import AmazonCreatorsApi

    api = AmazonCreatorsApi(
        credential_id=config.credential_id,
        credential_secret=config.credential_secret,
        version="2.2",
        tag=config.partner_tag,
        country=_country_enum(config.country),
    )

    items: list[Item] = []
    for keyword in config.keywords:
        try:
            results = api.search_items(keywords=keyword, item_count=config.item_count)
        except Exception:
            logger.exception("Amazon検索に失敗しました: %s", keyword)
            continue
        for raw in getattr(results, "items", None) or []:
            item = _to_item(raw)
            if item is not None:
                items.append(item)

    return items
