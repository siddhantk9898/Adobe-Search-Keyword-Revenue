"""Unit tests for HitDataProcessor (end-to-end with sample data)."""

import os
import tempfile
import pytest
from src.config import Config
from src.processor import HitDataProcessor


SAMPLE_DATA = (
    "hit_time_gmt\tdate_time\tuser_agent\tip\tevent_list\tgeo_city\tgeo_region\t"
    "geo_country\tpagename\tpage_url\tproduct_list\treferrer\n"
    '1254033280\t2009-09-27 06:34:40\tMozilla/5.0\t67.98.123.1\t\tSalem\tOR\tUS\t'
    'Home\thttp://www.esshopzilla.com\t\t'
    'http://www.google.com/search?hl=en&q=Ipod&aq=f\n'
    '1254033379\t2009-09-27 06:36:19\tMozilla/5.0\t23.8.61.21\t2\tRochester\tNY\tUS\t'
    'Zune - 32 GB\thttp://www.esshopzilla.com/product/?pid=asfe13\t'
    'Electronics;Zune - 328GB;1;;\t'
    'http://www.bing.com/search?q=Zune&go=&form=QBLH\n'
    '1254034666\t2009-09-27 06:57:46\tMozilla/5.0\t23.8.61.21\t1\tRochester\tNY\tUS\t'
    'Order Complete\thttps://www.esshopzilla.com/checkout/?a=complete\t'
    'Electronics;Zune - 32GB;1;250;\t'
    'https://www.esshopzilla.com/checkout/?a=confirm\n'
    '1254035260\t2009-09-27 07:07:40\tMozilla/5.0\t67.98.123.1\t1\tSalem\tOR\tUS\t'
    'Order Complete\thttps://www.esshopzilla.com/checkout/?a=complete\t'
    'Electronics;Ipod - Touch - 32GB;1;290;\t'
    'https://www.esshopzilla.com/checkout/?a=confirm\n'
)


def _get_config():
    """Load Config from the project's config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    return Config(config_path)


class TestHitDataProcessor:
    """End-to-end tests for the processor."""

    def test_process_sample_data(self):
        """Verify correct revenue attribution from sample data."""
        config = _get_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(SAMPLE_DATA)
            temp_path = f.name

        try:
            processor = HitDataProcessor(config)
            results = processor.process_file(temp_path)

            assert len(results) == 2

            # Sorted by revenue descending (keywords are lowercased)
            assert results[0] == ("google.com", "ipod", 290.0)
            assert results[1] == ("bing.com", "zune", 250.0)
        finally:
            os.unlink(temp_path)

    def test_no_purchase_events(self):
        """Visitors without purchase events should produce no revenue."""
        config = _get_config()
        data = (
            "hit_time_gmt\tdate_time\tuser_agent\tip\tevent_list\tgeo_city\tgeo_region\t"
            "geo_country\tpagename\tpage_url\tproduct_list\treferrer\n"
            '1254033280\t2009-09-27 06:34:40\tMozilla/5.0\t1.1.1.1\t2\tCity\tST\tUS\t'
            'Product\thttp://example.com\tElectronics;Item;1;100;\t'
            'http://www.google.com/search?q=test\n'
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(data)
            temp_path = f.name

        try:
            processor = HitDataProcessor(config)
            results = processor.process_file(temp_path)
            assert len(results) == 0
        finally:
            os.unlink(temp_path)

    def test_purchase_without_search_engine(self):
        """Purchase from direct traffic (no search engine) should be excluded."""
        config = _get_config()
        data = (
            "hit_time_gmt\tdate_time\tuser_agent\tip\tevent_list\tgeo_city\tgeo_region\t"
            "geo_country\tpagename\tpage_url\tproduct_list\treferrer\n"
            '1254033280\t2009-09-27 06:34:40\tMozilla/5.0\t1.1.1.1\t1\tCity\tST\tUS\t'
            'Order Complete\thttp://example.com\tElectronics;Item;1;100;\t'
            'http://www.esshopzilla.com/cart/\n'
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(data)
            temp_path = f.name

        try:
            processor = HitDataProcessor(config)
            results = processor.process_file(temp_path)
            assert len(results) == 0
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing file."""
        config = _get_config()
        processor = HitDataProcessor(config)
        with pytest.raises(FileNotFoundError):
            processor.process_file("/nonexistent/path.tsv")

    def test_write_output(self):
        """Verify output file naming and content."""
        config = _get_config()
        processor = HitDataProcessor(config)
        results = [
            ("google.com", "ipod", 290.0),
            ("bing.com", "zune", 250.0),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = processor.write_output(results, tmpdir)

            assert output_path.endswith("_SearchKeywordPerformance.tab")
            assert os.path.exists(output_path)

            with open(output_path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 3  # header + 2 data rows
                assert "Search Engine Domain" in lines[0]
                assert "google.com" in lines[1]
                assert "290" in lines[1]

    def test_end_to_end_process_and_write_output(self):
        """Full integration: process fixture file → write output → verify file contents."""
        config = _get_config()
        # Multi-visitor fixture: 2 search engine visitors with purchases, 1 direct visitor
        fixture_data = (
            "hit_time_gmt\tdate_time\tuser_agent\tip\tevent_list\tgeo_city\tgeo_region\t"
            "geo_country\tpagename\tpage_url\tproduct_list\treferrer\n"
            # Visitor A: Google "laptop" → browse → purchase $500
            '1254033280\t2009-09-27 06:34:40\tMozilla/5.0\t10.0.0.1\t2\tCity\tST\tUS\t'
            'Home\thttp://example.com\t\t'
            'http://www.google.com/search?q=Laptop\n'
            '1254033380\t2009-09-27 06:36:20\tMozilla/5.0\t10.0.0.1\t1\tCity\tST\tUS\t'
            'Order Complete\thttp://example.com/checkout\t'
            'Computers;Laptop Pro;1;500;\t'
            'http://example.com/cart\n'
            # Visitor B: Bing "headphones" → purchase $75
            '1254033480\t2009-09-27 06:38:00\tMozilla/5.0\t10.0.0.2\t\tCity\tST\tUS\t'
            'Home\thttp://example.com\t\t'
            'http://www.bing.com/search?q=Headphones\n'
            '1254033580\t2009-09-27 06:39:40\tMozilla/5.0\t10.0.0.2\t1\tCity\tST\tUS\t'
            'Order Complete\thttp://example.com/checkout\t'
            'Audio;Headphones;1;75;\t'
            'http://example.com/cart\n'
            # Visitor C: Direct traffic → purchase $200 (should NOT appear in output)
            '1254033680\t2009-09-27 06:41:20\tMozilla/5.0\t10.0.0.3\t1\tCity\tST\tUS\t'
            'Order Complete\thttp://example.com/checkout\t'
            'Electronics;Speaker;1;200;\t'
            'http://example.com/products\n'
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as f:
            f.write(fixture_data)
            input_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                processor = HitDataProcessor(config)
                results = processor.process_file(input_path)
                output_path = processor.write_output(results, tmpdir)

                # Verify output file exists and has correct name
                assert os.path.exists(output_path)
                assert output_path.endswith("_SearchKeywordPerformance.tab")

                # Read and verify file contents
                with open(output_path, "r") as f:
                    lines = f.readlines()

                # Header + 2 data rows (direct traffic excluded)
                assert len(lines) == 3

                # Header
                assert "Search Engine Domain" in lines[0]
                assert "Search Keyword" in lines[0]
                assert "Revenue" in lines[0]

                # Row 1: google.com, laptop, 500 (highest revenue first)
                assert "google.com" in lines[1]
                assert "laptop" in lines[1]
                assert "500" in lines[1]

                # Row 2: bing.com, headphones, 75
                assert "bing.com" in lines[2]
                assert "headphones" in lines[2]
                assert "75" in lines[2]
        finally:
            os.unlink(input_path)

    def test_process_actual_data_file(self):
        """Integration test with the actual data.sql file."""
        config = _get_config()
        data_path = os.path.join(os.path.dirname(__file__), "..", "data.sql")
        if not os.path.exists(data_path):
            pytest.skip("data.sql not found")

        processor = HitDataProcessor(config)
        results = processor.process_file(data_path)

        # We expect 2 results (keywords are case-insensitive, so "Ipod" and "ipod" merge)
        assert len(results) == 2

        # Verify sorted by revenue descending
        revenues = [r[2] for r in results]
        assert revenues == sorted(revenues, reverse=True)

        # Verify total revenue
        total = sum(r[2] for r in results)
        assert total == 730.0  # 480 (ipod) + 250 (zune)
