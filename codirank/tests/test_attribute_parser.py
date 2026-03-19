from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.codirank.attribute_parser import AttributeParser


@pytest.mark.asyncio
async def test_parse_calls_client():
    mock_client = MagicMock()
    mock_client.extract_attributes = AsyncMock(
        return_value={
            "category": "медитация",
            "monetization": "free_only",
            "has_ads": False,
            "has_iap": None,
            "languages": ["ru"],
            "platform": "ios",
            "excluded_apps": [],
            "excluded_categories": [],
            "context": "перед сном",
            "sentiment": "positive",
        }
    )
    parser = AttributeParser(mock_client)
    result = await parser.parse("Хочу приложение для медитации на iOS, бесплатное")
    assert result["category"] == "медитация"
    assert result["platform"] == "ios"
    assert result["monetization"] == "free_only"


def test_merge_lists_union():
    mock_client = MagicMock()
    parser = AttributeParser(mock_client)
    existing = {"languages": ["ru"], "excluded_apps": ["Headspace"]}
    new = {"languages": ["en"], "excluded_apps": ["Calm"], "category": "медитация"}
    merged = parser.merge(existing, new)
    assert set(merged["languages"]) == {"ru", "en"}
    assert set(merged["excluded_apps"]) == {"Headspace", "Calm"}
    assert merged["category"] == "медитация"


def test_merge_null_does_not_overwrite():
    mock_client = MagicMock()
    parser = AttributeParser(mock_client)
    existing = {"category": "игры"}
    new = {"category": None, "platform": "android"}
    merged = parser.merge(existing, new)
    assert merged["category"] == "игры"
    assert merged["platform"] == "android"
