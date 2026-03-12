"""
Main processor for hit-level data analysis.
Reads a TSV file, tracks sessions, and calculates revenue by search engine keyword.
"""

import csv
import logging
import os
from collections import defaultdict
from datetime import date
from typing import Dict, List, Tuple

from src.config import Config
from src.parsers import ReferrerParser, ProductListParser
from src.session import SessionTracker

logger = logging.getLogger(__name__)


class DataFileError(Exception):
    """Raised when the input data file cannot be read or is malformed."""
    pass


class OutputWriteError(Exception):
    """Raised when the output file cannot be written."""
    pass


class HitDataProcessor:
    """
    Processes Adobe Analytics hit-level data to determine revenue
    attributed to external search engine keywords.

    Workflow:
        1. Stream the TSV file line by line (memory-efficient).
        2. For each hit, check if the referrer is from a search engine
           and track the session (IP -> search engine + keyword).
        3. When a purchase event is found, attribute the revenue to the
           search engine keyword from the visitor's session.
        4. Aggregate and output the results sorted by revenue descending.
    """

    def __init__(self, config: Config = None):
        self._config = config or Config()
        self.referrer_parser = ReferrerParser(self._config.search_engines)
        self.product_parser = ProductListParser(
            product_delimiter=self._config.product_delimiter,
            field_delimiter=self._config.field_delimiter,
            revenue_field_index=self._config.revenue_field_index,
        )
        self.session_tracker = SessionTracker()
        self.revenue_data: Dict[Tuple[str, str], float] = defaultdict(float)
        self._rows_processed = 0
        self._rows_skipped = 0
        self._purchase_events_found = 0

        logger.info("HitDataProcessor initialized with purchase_event='%s'",
                     self._config.purchase_event)

    def process_file(self, file_path: str) -> List[Tuple[str, str, float]]:
        """
        Process a hit-level TSV data file and return revenue by search keyword.

        Args:
            file_path: Path to the tab-separated hit-level data file.

        Returns:
            List of (search_engine_domain, keyword, revenue) tuples,
            sorted by revenue descending.

        Raises:
            FileNotFoundError: If the data file does not exist.
            DataFileError: If the file cannot be read or parsed.
        """
        if not os.path.exists(file_path):
            logger.error("Data file not found: %s", file_path)
            raise FileNotFoundError(f"Data file not found: {file_path}")

        file_size = os.path.getsize(file_path)
        logger.info("Starting to process file: %s (%.2f KB)", file_path, file_size / 1024)

        try:
            with open(file_path, "r", encoding=self._config.input_encoding) as f:
                reader = csv.DictReader(f, delimiter=self._config.input_delimiter)

                # Validate that required columns exist in the header
                if reader.fieldnames:
                    self._validate_columns(reader.fieldnames)

                for row_number, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                    try:
                        self._process_row(row)
                        self._rows_processed += 1
                    except Exception as e:
                        self._rows_skipped += 1
                        logger.warning("Skipping row %d due to error: %s — Row data: %s",
                                       row_number, e, dict(row))
                        continue

        except UnicodeDecodeError as e:
            logger.error("Encoding error reading file %s with encoding '%s': %s",
                         file_path, self._config.input_encoding, e)
            raise DataFileError(
                f"Cannot read file with encoding '{self._config.input_encoding}': {e}"
            ) from e
        except csv.Error as e:
            logger.error("CSV parsing error in file %s: %s", file_path, e)
            raise DataFileError(f"CSV parsing error: {e}") from e

        # Log processing summary
        logger.info("Processing complete. Rows processed: %d, Rows skipped: %d, "
                     "Purchase events found: %d, Unique sessions: %d, "
                     "Unique keyword-engine combinations: %d",
                     self._rows_processed, self._rows_skipped,
                     self._purchase_events_found,
                     self.session_tracker.total_sessions,
                     len(self.revenue_data))

        if self._rows_skipped > 0:
            logger.warning("%d rows were skipped due to errors. "
                           "Review warnings above for details.", self._rows_skipped)

        return self._get_sorted_results()

    def _validate_columns(self, fieldnames: list) -> None:
        """Validate that all required columns exist in the file header."""
        required_columns = [
            self._config.column_ip,
            self._config.column_referrer,
            self._config.column_event_list,
            self._config.column_product_list,
        ]
        missing = [col for col in required_columns if col not in fieldnames]
        if missing:
            logger.error("Missing required columns in data file: %s. "
                         "Available columns: %s", missing, fieldnames)
            raise DataFileError(
                f"Missing required columns: {missing}. "
                f"Available columns: {fieldnames}"
            )
        logger.debug("Column validation passed. Required columns found: %s", required_columns)

    def _process_row(self, row: dict) -> None:
        """
        Process a single hit record.

        Steps:
            1. Check referrer for search engine -> update session tracker.
            2. Check event_list for purchase event -> extract revenue.
        """
        ip = row.get(self._config.column_ip, "").strip()
        referrer = row.get(self._config.column_referrer, "").strip()
        event_list = row.get(self._config.column_event_list, "").strip()
        product_list = row.get(self._config.column_product_list, "").strip()

        if not ip:
            logger.debug("Row has empty IP address, skipping session tracking")
            return

        # Step 1: Track search engine referral for this visitor's session
        if referrer:
            result = self.referrer_parser.parse(referrer)
            if result:
                domain, keyword = result
                self.session_tracker.track(ip, domain, keyword)

        # Step 2: If this is a purchase event, attribute revenue
        if self._is_purchase_event(event_list):
            self._purchase_events_found += 1
            referral = self.session_tracker.get_referral(ip)

            if referral:
                domain, keyword = referral
                revenue = self.product_parser.parse_revenue(product_list)
                if revenue > 0:
                    self.revenue_data[(domain, keyword)] += revenue
                    logger.info("Revenue attributed: ip=%s, engine=%s, "
                                "keyword='%s', revenue=%.2f",
                                ip, domain, keyword, revenue)
                else:
                    logger.warning("Purchase event found for ip=%s but no revenue "
                                   "in product_list: '%s'", ip, product_list)
            else:
                logger.debug("Purchase event for ip=%s but no search engine "
                             "referral in session — not attributed", ip)

    def _is_purchase_event(self, event_list: str) -> bool:
        """Check if the event_list contains a purchase event."""
        if not event_list:
            return False
        events = [e.strip() for e in event_list.split(",")]
        return self._config.purchase_event in events

    def _get_sorted_results(self) -> List[Tuple[str, str, float]]:
        """Return results sorted by revenue descending."""
        results = [
            (domain, keyword, revenue)
            for (domain, keyword), revenue in self.revenue_data.items()
        ]
        results.sort(key=lambda x: x[2], reverse=True)
        return results

    def write_output(self, results: List[Tuple[str, str, float]], output_dir: str = None) -> str:
        """
        Write results to a tab-delimited file with the naming convention
        defined in config.yaml.

        Args:
            results: List of (domain, keyword, revenue) tuples.
            output_dir: Directory to write the output file. Defaults to config value.

        Returns:
            The full path to the output file.

        Raises:
            OutputWriteError: If the output file cannot be written.
        """
        output_dir = output_dir or self._config.output_directory
        today = date.today().strftime(self._config.output_date_format)
        filename = self._config.output_filename_template.format(date=today)
        output_path = os.path.join(output_dir, filename)

        logger.info("Writing output file: %s (%d result rows)", output_path, len(results))

        try:
            with open(output_path, "w", encoding=self._config.input_encoding, newline="") as f:
                writer = csv.writer(f, delimiter=self._config.output_delimiter)
                writer.writerow(self._config.output_headers)
                for domain, keyword, revenue in results:
                    writer.writerow([domain, keyword, round(revenue, 2)])

            file_size = os.path.getsize(output_path)
            logger.info("Output file written successfully: %s (%.2f KB)",
                        output_path, file_size / 1024)

        except OSError as e:
            logger.error("Failed to write output file %s: %s", output_path, e)
            raise OutputWriteError(f"Cannot write output file: {e}") from e

        return output_path
