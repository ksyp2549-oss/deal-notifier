from __future__ import annotations

import logging

import requests

from ..config import DiscordConfig
from ..rules import DealResult

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "rakuten": "楽天市場",
    "amazon": "Amazon",
}

EMBED_COLOR_BY_SOURCE = {
    "rakuten": 0xBF0000,
    "amazon": 0xFF9900,
}


def _build_embed(deal: DealResult) -> dict:
    item = deal.item
    fields = [{"name": "価格", "value": f"{item.price:,}円", "inline": True}]
    if item.list_price:
        fields.append({"name": "定価", "value": f"{item.list_price:,}円", "inline": True})
    if deal.discount_percent:
        fields.append({"name": "割引率", "value": f"{deal.discount_percent:.0f}%", "inline": True})
    if item.shop:
        fields.append({"name": "ショップ", "value": item.shop, "inline": True})
    fields.append({"name": "理由", "value": "\n".join(deal.reasons), "inline": False})

    embed = {
        "title": item.title[:256],
        "url": item.url,
        "color": EMBED_COLOR_BY_SOURCE.get(item.source, 0x2ECC71),
        "fields": fields,
        "footer": {"text": SOURCE_LABELS.get(item.source, item.source)},
    }
    if item.image_url:
        embed["thumbnail"] = {"url": item.image_url}
    return embed


def send_deal_notification(config: DiscordConfig, deal: DealResult) -> None:
    if not config.webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL が未設定のため通知をスキップします")
        return

    content = f"<@&{config.mention_role_id}>" if config.mention_role_id else None
    payload = {"embeds": [_build_embed(deal)]}
    if content:
        payload["content"] = content

    resp = requests.post(config.webhook_url, json=payload, timeout=10)
    if resp.status_code >= 300:
        logger.error("Discord通知に失敗しました: %s %s", resp.status_code, resp.text)
        resp.raise_for_status()
