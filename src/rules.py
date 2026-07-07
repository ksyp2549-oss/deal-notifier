from __future__ import annotations

from dataclasses import dataclass

from .config import RulesConfig
from .storage import Storage


@dataclass
class Item:
    source: str
    item_id: str
    title: str
    url: str
    image_url: str | None
    shop: str | None
    price: int
    list_price: int | None = None


@dataclass
class DealResult:
    item: Item
    reasons: list[str]
    discount_percent: float


def evaluate(item: Item, storage: Storage, rules: RulesConfig) -> DealResult | None:
    storage.record_price(item.source, item.item_id, item.price)

    reasons: list[str] = []
    best_discount = 0.0

    if item.list_price and item.list_price > item.price:
        discount = (1 - item.price / item.list_price) * 100
        if discount >= rules.min_discount_percent:
            reasons.append(f"定価{item.list_price}円より{discount:.0f}%オフ")
            best_discount = max(best_discount, discount)

    min_price, _sample_count = storage.get_price_history_stats(item.source, item.item_id)
    if min_price is not None and item.price < min_price:
        drop = (1 - item.price / min_price) * 100
        if drop >= rules.price_drop_from_history_percent:
            reasons.append(f"過去最安値({min_price}円)から{drop:.0f}%値下がり")
            best_discount = max(best_discount, drop)

    matched_keywords = [kw for kw in rules.sale_keywords if kw in item.title]
    if matched_keywords:
        reasons.append(f"セールキーワード検出: {', '.join(matched_keywords)}")

    if not reasons:
        return None

    if storage.was_notified_recently(item.source, item.item_id, rules.renotify_cooldown_hours):
        return None

    return DealResult(item=item, reasons=reasons, discount_percent=best_discount)
