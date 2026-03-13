"""Unit tests for ReferrerParser and ProductListParser."""

import pytest
from src.parsers import ReferrerParser, ProductListParser


# Default search engines for tests (avoids needing config.yaml loaded)
TEST_SEARCH_ENGINES = {
    "google": "q",
    "bing": "q",
    "yahoo": "p",
    "msn": "q",
}


class TestReferrerParser:
    """Tests for ReferrerParser.parse()."""

    def setup_method(self):
        self.parser = ReferrerParser(search_engines=TEST_SEARCH_ENGINES)

    # --- Google ---
    def test_google_referrer(self):
        url = "http://www.google.com/search?hl=en&q=Ipod&aq=f"
        result = self.parser.parse(url)
        assert result == ("google.com", "ipod")

    def test_google_referrer_with_encoded_keyword(self):
        url = "http://www.google.com/search?q=cd+player&oq=cd+player"
        result = self.parser.parse(url)
        assert result == ("google.com", "cd player")

    # --- Bing ---
    def test_bing_referrer(self):
        url = "http://www.bing.com/search?q=Zune&go=&form=QBLH"
        result = self.parser.parse(url)
        assert result == ("bing.com", "zune")

    # --- Yahoo ---
    def test_yahoo_referrer(self):
        url = "http://search.yahoo.com/search?p=cd+player&toggle=1&cop=mss"
        result = self.parser.parse(url)
        assert result == ("yahoo.com", "cd player")

    # --- MSN ---
    def test_msn_referrer(self):
        url = "http://www.msn.com/search?q=laptop"
        result = self.parser.parse(url)
        assert result == ("msn.com", "laptop")

    # --- Non-search engine ---
    def test_internal_referrer_returns_none(self):
        url = "http://www.esshopzilla.com/product/?pid=as32213"
        result = self.parser.parse(url)
        assert result is None

    def test_empty_referrer_returns_none(self):
        assert self.parser.parse("") is None

    def test_none_referrer_returns_none(self):
        assert self.parser.parse(None) is None

    def test_search_engine_without_keyword_returns_none(self):
        url = "http://www.google.com/search?hl=en"
        result = self.parser.parse(url)
        assert result is None

    def test_malformed_url_returns_none(self):
        result = self.parser.parse("not-a-url")
        assert result is None

    # --- Case insensitivity ---
    def test_keywords_are_lowercased(self):
        """Keywords should be normalized to lowercase for aggregation."""
        url = "http://www.google.com/search?q=IPOD"
        result = self.parser.parse(url)
        assert result == ("google.com", "ipod")

    # --- Config-driven: custom search engine ---
    def test_custom_search_engine(self):
        custom_engines = {"duckduckgo": "q"}
        parser = ReferrerParser(search_engines=custom_engines)
        url = "http://www.duckduckgo.com/search?q=headphones"
        result = parser.parse(url)
        assert result == ("duckduckgo.com", "headphones")


class TestProductListParser:
    """Tests for ProductListParser.parse_revenue()."""

    def setup_method(self):
        self.parser = ProductListParser(
            product_delimiter=",", field_delimiter=";", revenue_field_index=3
        )

    def test_single_product_with_revenue(self):
        product_list = "Electronics;Zune - 32GB;1;250;"
        assert self.parser.parse_revenue(product_list) == 250.0

    def test_single_product_decimal_revenue(self):
        product_list = "Electronics;Ipod - Nano - 8GB;1;190.50;"
        assert self.parser.parse_revenue(product_list) == 190.50

    def test_multiple_products(self):
        product_list = "Computers;HP Pavillion;1;1000;200|201,Office Supplies;Red Folders;4;4.00;205"
        assert self.parser.parse_revenue(product_list) == 1004.0

    def test_empty_product_list(self):
        assert self.parser.parse_revenue("") == 0.0

    def test_none_product_list(self):
        assert self.parser.parse_revenue(None) == 0.0

    def test_product_without_revenue(self):
        product_list = "Electronics;Zune - 32GB;1;;"
        assert self.parser.parse_revenue(product_list) == 0.0

    def test_product_with_no_revenue_field(self):
        product_list = "Electronics;Zune - 32GB"
        assert self.parser.parse_revenue(product_list) == 0.0

    def test_custom_revenue_field_index(self):
        """Revenue at a different index (e.g., index 2 instead of 3)."""
        parser = ProductListParser(
            product_delimiter=",", field_delimiter=";", revenue_field_index=2
        )
        product_list = "Electronics;Zune;500;extra"
        assert parser.parse_revenue(product_list) == 500.0
