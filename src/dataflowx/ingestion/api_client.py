"""
REST API ingestion.

Pulls product data from a public e-commerce API (fakestoreapi.com by
default, configurable via PRODUCTS_API_BASE_URL). This module demonstrates
the pattern real API ingestion needs: timeouts, retries with backoff,
HTTP status validation and pagination - even though the specific demo API
used here is small enough not to require multiple pages in practice.

No API key is required for this endpoint, so there is nothing to load
from environment secrets here - but if the API required one, it would be
read from settings, never hardcoded.
"""

from typing import Any

import pandas as pd
import requests

from dataflowx.config.settings import settings
from dataflowx.utils.logger import get_logger
from dataflowx.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class ApiRequestError(RuntimeError):
    """Raised when the API returns an unexpected status code or payload."""


@retry_with_backoff(
    max_attempts=3,
    base_delay_seconds=1.0,
    exceptions=(requests.ConnectionError, requests.Timeout),
)
def _get(url: str, params: dict[str, Any] | None = None) -> requests.Response:
    response = requests.get(
        url, params=params, timeout=settings.products_api_timeout_seconds
    )
    if response.status_code != 200:
        raise ApiRequestError(
            f"GET {url} returned status {response.status_code}: {response.text[:200]}"
        )
    return response


def fetch_paginated(
    endpoint: str, page_param: str = "page", page_size_param: str = "limit", page_size: int = 20
) -> list[dict[str, Any]]:
    """
    Fetch all records from a paginated endpoint.

    Stops when a page returns fewer records than page_size (the standard
    signal that the last page was reached), or an empty page.
    """
    base_url = f"{settings.products_api_base_url}{endpoint}"
    all_records: list[dict[str, Any]] = []
    page = 1

    while True:
        response = _get(base_url, params={page_param: page, page_size_param: page_size})
        payload = response.json()

        records = payload if isinstance(payload, list) else payload.get("data", [])
        if not records:
            break

        all_records.extend(records)
        logger.info("Fetched page %d (%d records) from %s", page, len(records), endpoint)

        if len(records) < page_size:
            break
        page += 1

    return all_records


def fetch_products() -> pd.DataFrame:
    """
    Fetch the product catalog from the products API.

    fakestoreapi.com returns its full catalog in a single response
    (it does not implement true offset pagination), so this is a single
    request rather than a fetch_paginated() loop - but it still goes
    through the shared retry/timeout/status-validation logic in _get().
    """
    url = f"{settings.products_api_base_url}/products"
    response = _get(url)
    records = response.json()

    if not isinstance(records, list) or not records:
        raise ApiRequestError(f"Unexpected payload from {url}: {records!r}")

    df = pd.DataFrame(records)
    logger.info("Fetched %d products from API", len(df))
    return df
