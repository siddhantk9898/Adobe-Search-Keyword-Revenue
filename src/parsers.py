"""
Parsers for referrer URLs and product list fields from Adobe Analytics hit-level data.
"""

import logging
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ReferrerParser:
    """Parses referrer URLs to extract search engine domain and search keyword."""

    def __init__(self, search_engines: Dict[str, str]):
        """
        Args:
            search_engines: Mapping of engine keyword to URL query parameter.
                            e.g., {"google": "q", "yahoo": "p", "bing": "q"}
        """
        self._search_engines = search_engines
        logger.debug("ReferrerParser initialized with engines: %s",
                      list(self._search_engines.keys()))

    def parse(self, referrer: str) -> Optional[Tuple[str, str]]:
        """
        Extract search engine domain and keyword from a referrer URL.

        Returns:
            (search_engine_domain, keyword) or None if not a search engine.
        """
        if not referrer:
            return None

        try:
            parsed = urlparse(referrer)
            hostname = parsed.hostname
            if not hostname:
                logger.warning("Could not extract hostname from referrer: %s", referrer)
                return None

            for engine_key, query_param in self._search_engines.items():
                if engine_key in hostname:
                    domain = self._extract_root_domain(hostname, engine_key)
                    query_params = parse_qs(parsed.query)
                    keywords = query_params.get(query_param, [])

                    if keywords and keywords[0].strip():
                        keyword = keywords[0].strip().lower()
                        logger.debug("Search engine referral: domain=%s, keyword='%s'",
                                     domain, keyword)
                        return (domain, keyword)
                    else:
                        logger.debug("Engine '%s' found but no keyword (param='%s'): %s",
                                     engine_key, query_param, referrer)
            return None

        except Exception as e:
            logger.error("Failed to parse referrer URL '%s': %s", referrer, e)
            return None

    def _extract_root_domain(self, hostname: str, engine_key: str) -> str:
        """
        Extract root domain: 'www.google.com' -> 'google.com'
        """
        parts = hostname.split(".")
        for i, part in enumerate(parts):
            if engine_key in part:
                return ".".join(parts[i:])
        return hostname


class ProductListParser:
    """Parses the product_list field from Adobe Analytics hit-level data."""

    def __init__(self, product_delimiter: str = ",", field_delimiter: str = ";",
                 revenue_field_index: int = 3):
        """
        Args:
            product_delimiter: Delimiter between products (default: ',').
            field_delimiter: Delimiter between fields within a product (default: ';').
            revenue_field_index: Zero-based index of the revenue field (default: 3).
        """
        self._product_delimiter = product_delimiter
        self._field_delimiter = field_delimiter
        self._revenue_field_index = revenue_field_index

    def parse_revenue(self, product_list: str) -> float:
        """
        Extract total revenue from a product_list string.

        Format: Category;Name;Quantity;Revenue;CustomEvent
        Multiple products are comma-separated.
        Revenue is only meaningful when purchase event (1) is in event_list.

        Returns:
            Total revenue as a float.
        """
        if not product_list or not product_list.strip():
            return 0.0

        total_revenue = 0.0

        for product in product_list.split(self._product_delimiter):
            fields = product.split(self._field_delimiter)
            if len(fields) > self._revenue_field_index and fields[self._revenue_field_index].strip():
                try:
                    total_revenue += float(fields[self._revenue_field_index].strip())
                except ValueError:
                    logger.warning("Non-numeric revenue value: '%s' in product_list: '%s'",
                                   fields[self._revenue_field_index], product_list)

        if total_revenue > 0:
            logger.debug("Parsed revenue=%.2f from product_list: %s",
                         total_revenue, product_list)

        return total_revenue
