"""
FRED API service layer.
Fetches, caches, and processes macroeconomic data from FRED.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache

from .fred_config import FRED_SERIES

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
CACHE_TTL = 60 * 60 * 4  # 4-hour cache


def _get_api_key() -> str:
    key = getattr(settings, "FRED_API_KEY", "")
    if not key:
        raise ValueError(
            "FRED_API_KEY is not set. "
            "Set it in your environment or .env file."
        )
    return key


def _fred_get(endpoint: str, params: dict) -> Optional[dict]:
    """Make a FRED API GET request with error handling."""
    try:
        params["api_key"] = _get_api_key()
        params["file_type"] = "json"
        r = requests.get(f"{FRED_BASE_URL}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except ValueError as e:
        logger.error("FRED config error: %s", e)
        return None
    except requests.RequestException as e:
        logger.error("FRED request failed for %s: %s", endpoint, e)
        return None


def _observation_window() -> tuple[str, str]:
    """Return (start_date, end_date) covering 5 quarters back for context."""
    today = datetime.today()
    end = today.strftime("%Y-%m-%d")
    start = (today - timedelta(days=1500)).strftime("%Y-%m-%d")
    return start, end


def fetch_series_observations(series_id: str, use_cache: bool = True) -> Optional[dict]:
    """
    Fetch the most recent observations for a series.
    Returns a dict with metadata + observations list.
    """
    cache_key = f"fred_obs_{series_id}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    start, end = _observation_window()
    meta = FRED_SERIES.get(series_id, {})

    # Fetch observations
    obs_data = _fred_get(
        "series/observations",
        {
            "series_id": series_id,
            "observation_start": start,
            "observation_end": end,
            "sort_order": "asc",
        },
    )
    if not obs_data:
        return None

    # Fetch series info for units/title confirmation
    info_data = _fred_get("series", {"series_id": series_id})
    series_info = {}
    if info_data and info_data.get("seriess"):
        s = info_data["seriess"][0]
        series_info = {
            "title": s.get("title", meta.get("name", series_id)),
            "units": s.get("units", meta.get("units", "")),
            "frequency": s.get("frequency_short", meta.get("frequency", "M")),
            "last_updated": s.get("last_updated", ""),
            "seasonal_adjustment": s.get("seasonal_adjustment_short", ""),
        }

    # Parse observations into clean records
    observations = []
    for obs in obs_data.get("observations", []):
        val = obs.get("value", ".")
        if val == ".":
            continue
        try:
            observations.append({
                "date": obs["date"],
                "value": float(val),
            })
        except (ValueError, KeyError):
            continue

    if not observations:
        return None

    # Compute YoY and QoQ changes
    obs_with_changes = _add_changes(observations, meta.get("frequency", "M"))

    result = {
        "series_id": series_id,
        "meta": {**meta, **series_info},
        "observations": obs_with_changes,
        "latest": obs_with_changes[-1] if obs_with_changes else None,
        "fetched_at": datetime.now().isoformat(),
    }

    if use_cache:
        cache.set(cache_key, result, CACHE_TTL)

    return result


def _add_changes(observations: list[dict], frequency: str) -> list[dict]:
    """Add period-over-period and year-over-year change fields."""
    # Number of periods in a year per frequency
    periods_per_year = {"D": 252, "M": 12, "Q": 4, "A": 1}
    n = periods_per_year.get(frequency, 12)

    enriched = []
    for i, obs in enumerate(observations):
        entry = {**obs}

        # Period-over-period change
        if i > 0:
            prev = observations[i - 1]["value"]
            if prev != 0:
                entry["pop_change"] = obs["value"] - prev
                entry["pop_pct"] = ((obs["value"] - prev) / abs(prev)) * 100
            else:
                entry["pop_change"] = None
                entry["pop_pct"] = None
        else:
            entry["pop_change"] = None
            entry["pop_pct"] = None

        # Year-over-year change
        yoy_idx = i - n
        if yoy_idx >= 0:
            prev_yr = observations[yoy_idx]["value"]
            if prev_yr != 0:
                entry["yoy_change"] = obs["value"] - prev_yr
                entry["yoy_pct"] = ((obs["value"] - prev_yr) / abs(prev_yr)) * 100
            else:
                entry["yoy_change"] = None
                entry["yoy_pct"] = None
        else:
            entry["yoy_change"] = None
            entry["yoy_pct"] = None

        enriched.append(entry)
    return enriched


def fetch_all_series(use_cache: bool = True) -> dict:
    """Fetch all configured series and return as a dict keyed by series_id."""
    results = {}
    for series_id in FRED_SERIES:
        data = fetch_series_observations(series_id, use_cache=use_cache)
        if data:
            results[series_id] = data
        else:
            logger.warning("No data returned for %s", series_id)
    return results


def fetch_category_series(category: str, use_cache: bool = True) -> dict:
    """Fetch only series belonging to a specific category."""
    series_ids = [
        sid for sid, meta in FRED_SERIES.items()
        if meta.get("category") == category
    ]
    results = {}
    for series_id in series_ids:
        data = fetch_series_observations(series_id, use_cache=use_cache)
        if data:
            results[series_id] = data
    return results


def get_dashboard_summary(use_cache: bool = True) -> dict:
    """
    Returns a high-level summary card for each series:
    latest value, period change, YoY change, and trend direction.
    """
    all_data = fetch_all_series(use_cache=use_cache)
    summary = {}

    for series_id, data in all_data.items():
        latest = data.get("latest")
        if not latest:
            continue

        meta = data["meta"]
        trend = _determine_trend(latest.get("yoy_pct"), series_id)

        summary[series_id] = {
            "name": meta.get("name", series_id),
            "category": meta.get("category", ""),
            "latest_date": latest["date"],
            "latest_value": latest["value"],
            "pop_pct": latest.get("pop_pct"),
            "yoy_pct": latest.get("yoy_pct"),
            "trend": trend,
            "units": meta.get("units", ""),
            "prefix": meta.get("prefix", ""),
            "suffix": meta.get("suffix", ""),
            "format": meta.get("format", ".2f"),
            "color": meta.get("color", "#6b7280"),
            "description": meta.get("description", ""),
            "observations": data.get("observations", []),
        }

    return summary


def _determine_trend(yoy_pct: Optional[float], series_id: str) -> str:
    """
    Returns 'up', 'down', or 'neutral'.
    For some series (like unemployment), 'down' is actually good.
    """
    if yoy_pct is None:
        return "neutral"
    # Series where lower is better
    lower_is_better = {"UNRATE", "CPIAUCSL", "CPILFESL", "PCEPI", "PCEPILFE",
                        "PPIACO", "FEDFUNDS", "BAA10Y"}
    if abs(yoy_pct) < 0.1:
        return "neutral"
    if yoy_pct > 0:
        return "down" if series_id in lower_is_better else "up"
    else:
        return "up" if series_id in lower_is_better else "down"
