"""
Entry point for the Search Keyword Performance application.

Usage:
    python -m src.main <path_to_data_file>

Example:
    python -m src.main data.sql
    python -m src.main data.sql --log-level DEBUG
"""

import argparse
import logging
import sys
import os

from src.config import Config, ConfigLoadError
from src.processor import HitDataProcessor, DataFileError, OutputWriteError

logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the application.

    Logs are written to both console (stdout) and a log file.
    Format includes timestamp, module name, level, and message
    for easy debugging and pipeline monitoring.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    # Console handler (INFO+ by default, or whatever user sets)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)

    # File handler (always DEBUG level for full pipeline trace)
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/pipeline.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze hit-level data to determine revenue by search engine keyword."
    )
    parser.add_argument(
        "file",
        help="Path to the tab-separated hit-level data file to process."
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write the output file (default: from config.yaml)"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: config/config.yaml)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level (default: INFO). Log file always captures DEBUG."
    )
    args = parser.parse_args()

    # Setup logging first so all subsequent operations are logged
    setup_logging(args.log_level)
    logger.info("=" * 60)
    logger.info("Search Keyword Performance Analyzer — Starting")
    logger.info("=" * 60)

    # Load configuration
    try:
        if args.config:
            Config.reset()
            Config(args.config)
        config = Config()
        logger.info("Configuration loaded. Search engines: %s",
                     list(config.search_engines.keys()))
    except (FileNotFoundError, ConfigLoadError) as e:
        logger.error("Failed to load configuration: %s", e)
        sys.exit(1)

    # Validate input file exists
    if not os.path.exists(args.file):
        logger.error("Input file not found: %s", args.file)
        sys.exit(1)

    # Determine output directory (CLI arg > config > default)
    output_dir = args.output_dir or config.output_directory
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    # Process the file
    try:
        processor = HitDataProcessor(config)
        logger.info("Processing file: %s", args.file)
        results = processor.process_file(args.file)
    except (DataFileError, FileNotFoundError) as e:
        logger.error("Failed to process data file: %s", e)
        sys.exit(1)

    if not results:
        logger.warning("No revenue data found from external search engines.")
        sys.exit(0)

    # Write output
    try:
        output_path = processor.write_output(results, output_dir)
        logger.info("Output written to: %s", output_path)
    except OutputWriteError as e:
        logger.error("Failed to write output file: %s", e)
        sys.exit(1)

    # Print summary to console
    headers = config.output_headers
    print(f"\n{headers[0]:<25} {headers[1]:<20} {headers[2]:>10}")
    print("-" * 57)
    for domain, keyword, revenue in results:
        print(f"{domain:<25} {keyword:<20} {revenue:>10.2f}")
    print("-" * 57)
    total = sum(r[2] for r in results)
    print(f"{'TOTAL':<46} {total:>10.2f}")

    logger.info("Pipeline completed successfully. "
                "Total revenue from search engines: $%.2f", total)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
