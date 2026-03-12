"""Unit tests for Config loader."""

import os
import tempfile
import pytest
from src.config import Config


SAMPLE_CONFIG = """
search_engines:
  google: "q"
  bing: "q"
  yahoo: "p"

events:
  purchase: "1"

input:
  delimiter: "\\t"
  encoding: "utf-8"
  columns:
    ip: "ip"
    referrer: "referrer"
    event_list: "event_list"
    product_list: "product_list"

product_list:
  product_delimiter: ","
  field_delimiter: ";"
  revenue_field_index: 3

output:
  directory: "output"
  filename_template: "{date}_SearchKeywordPerformance.tab"
  date_format: "%Y-%m-%d"
  delimiter: "\\t"
  headers:
    - "Search Engine Domain"
    - "Search Keyword"
    - "Revenue"

aws:
  region: "us-east-1"
  s3:
    input_prefix: "input/"
    output_prefix: "output/"
"""


class TestConfig:
    """Tests for the Config singleton."""

    def test_load_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(SAMPLE_CONFIG)
            temp_path = f.name

        try:
            config = Config(temp_path)
            assert config.search_engines == {"google": "q", "bing": "q", "yahoo": "p"}
            assert config.purchase_event == "1"
            assert config.column_ip == "ip"
            assert config.revenue_field_index == 3
            assert config.output_directory == "output"
            assert config.aws_region == "us-east-1"
            assert len(config.output_headers) == 3
        finally:
            os.unlink(temp_path)

    def test_missing_config_file(self):
        with pytest.raises(FileNotFoundError):
            Config("/nonexistent/config.yaml")

    def test_singleton_returns_same_instance(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config.yaml"
        )
        config1 = Config(config_path)
        config2 = Config()
        assert config1 is config2

    def test_reset_clears_singleton(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config.yaml"
        )
        config1 = Config(config_path)
        Config.reset()
        config2 = Config(config_path)
        assert config1 is not config2
