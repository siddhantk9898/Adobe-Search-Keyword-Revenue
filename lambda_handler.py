"""
AWS Lambda handler for processing hit-level data from S3.

This handler:
    1. Receives an S3 event (or manual invocation with bucket/key).
    2. Downloads the hit-level data file from S3 (with retry logic).
    3. Processes it using HitDataProcessor.
    4. Uploads the output .tab file back to S3 (with retry logic).
"""

import json
import logging
import os
import tempfile
import time

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from src.config import Config, ConfigLoadError
from src.processor import HitDataProcessor, DataFileError, OutputWriteError

# Configure logging for Lambda (CloudWatch)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add a handler if none exist (Lambda provides one, but ensure formatting)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s"
    ))
    logger.addHandler(handler)

# Also set the root logger so child modules (src.*) are captured
logging.getLogger("src").setLevel(logging.DEBUG)

s3_client = boto3.client("s3")

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds — exponential backoff: 2, 4, 8


def _retry_s3_operation(operation_name, func, *args, **kwargs):
    """
    Execute an S3 operation with exponential backoff retry logic.

    Retries on transient errors (throttling, timeouts, 5xx).
    Does NOT retry on permission errors (403) or not-found (404).

    Args:
        operation_name: Human-readable name for logging (e.g., 'download', 'upload').
        func: The S3 function to call.
        *args, **kwargs: Arguments passed to the function.

    Returns:
        The return value of the function.

    Raises:
        ClientError: If all retries are exhausted or a non-retryable error occurs.
    """
    last_exception = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 1:
                logger.info("S3 %s succeeded on attempt %d/%d",
                            operation_name, attempt, MAX_RETRIES)
            return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            http_status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)

            # Non-retryable errors — fail immediately
            if http_status in (403, 404) or error_code in ("AccessDenied", "NoSuchKey", "NoSuchBucket"):
                logger.error("S3 %s failed with non-retryable error: %s (HTTP %s). "
                             "Check IAM permissions and bucket/key path.",
                             operation_name, error_code, http_status)
                raise

            # Retryable errors — backoff and retry
            last_exception = e
            wait_time = RETRY_BACKOFF_BASE ** attempt
            logger.warning("S3 %s failed (attempt %d/%d): %s (HTTP %s). "
                           "Retrying in %ds...",
                           operation_name, attempt, MAX_RETRIES,
                           error_code, http_status, wait_time)
            time.sleep(wait_time)

        except BotoCoreError as e:
            # Network-level errors (connection timeout, DNS failure)
            last_exception = e
            wait_time = RETRY_BACKOFF_BASE ** attempt
            logger.warning("S3 %s network error (attempt %d/%d): %s. "
                           "Retrying in %ds...",
                           operation_name, attempt, MAX_RETRIES, e, wait_time)
            time.sleep(wait_time)

    logger.error("S3 %s failed after %d attempts. Last error: %s",
                 operation_name, MAX_RETRIES, last_exception)
    raise last_exception


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Accepts either:
        - An S3 event trigger (automatic)
        - A manual invocation with {"bucket": "...", "key": "..."}

    Returns:
        dict with statusCode and body containing results or error details.
    """
    logger.info("=" * 60)
    logger.info("Lambda invocation started")
    logger.info("Event: %s", json.dumps(event, default=str))

    # Load configuration
    try:
        config = Config()
        logger.info("Configuration loaded successfully")
    except (FileNotFoundError, ConfigLoadError) as e:
        logger.error("Failed to load configuration: %s", e)
        return _error_response(500, f"Configuration error: {e}")

    # Extract bucket and key from the event
    try:
        bucket, key = _parse_event(event)
        logger.info("Processing file: s3://%s/%s", bucket, key)
    except (ValueError, KeyError) as e:
        logger.error("Failed to parse event: %s", e)
        return _error_response(400, f"Invalid event format: {e}")

    # Create a temp directory for processing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download the input file from S3 (with retry)
        input_path = os.path.join(tmpdir, "input_data.tsv")
        try:
            _retry_s3_operation(
                "download",
                s3_client.download_file,
                bucket, key, input_path
            )
            file_size = os.path.getsize(input_path)
            logger.info("Downloaded s3://%s/%s (%.2f KB)", bucket, key, file_size / 1024)
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to download from S3 after retries: %s", e)
            return _error_response(500, f"S3 download failed: {e}")

        # Process the file
        try:
            processor = HitDataProcessor(config)
            results = processor.process_file(input_path)
            logger.info("File processed. Results: %d keyword-engine combinations", len(results))
        except (DataFileError, FileNotFoundError) as e:
            logger.error("Failed to process data file: %s", e)
            return _error_response(500, f"Data processing error: {e}")

        if not results:
            logger.warning("No revenue data found from external search engines")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "No revenue data found from external search engines.",
                    "results": []
                })
            }

        # Write output file locally
        try:
            output_path = processor.write_output(results, tmpdir)
            output_filename = os.path.basename(output_path)
            logger.info("Output file written locally: %s", output_path)
        except OutputWriteError as e:
            logger.error("Failed to write output file: %s", e)
            return _error_response(500, f"Output write error: {e}")

        # Upload output file to S3 (with retry)
        output_key = f"{config.s3_output_prefix}{output_filename}"
        try:
            _retry_s3_operation(
                "upload",
                s3_client.upload_file,
                output_path, bucket, output_key
            )
            logger.info("Uploaded results to s3://%s/%s", bucket, output_key)
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to upload to S3 after retries: %s", e)
            return _error_response(500, f"S3 upload failed: {e}")

        # Build response
        results_list = [
            {
                "search_engine_domain": domain,
                "search_keyword": keyword,
                "revenue": revenue
            }
            for domain, keyword, revenue in results
        ]

        total_revenue = sum(r[2] for r in results)
        logger.info("Pipeline completed successfully. Total revenue: $%.2f", total_revenue)
        logger.info("=" * 60)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Successfully processed. Output: s3://{bucket}/{output_key}",
                "output_file": f"s3://{bucket}/{output_key}",
                "total_revenue": total_revenue,
                "results": results_list
            })
        }


def _parse_event(event):
    """
    Extract S3 bucket and key from Lambda event.

    Supports:
        - S3 trigger events (Records[0].s3.bucket.name / object.key)
        - Manual invocation ({"bucket": "...", "key": "..."})

    Raises:
        ValueError: If the event format is not recognized.
    """
    if "Records" in event:
        try:
            record = event["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
            logger.debug("Parsed S3 trigger event: bucket=%s, key=%s", bucket, key)
        except (KeyError, IndexError) as e:
            raise ValueError(f"Malformed S3 event record: {e}") from e
    elif "bucket" in event and "key" in event:
        bucket = event["bucket"]
        key = event["key"]
        logger.debug("Parsed manual invocation event: bucket=%s, key=%s", bucket, key)
    else:
        raise ValueError(
            "Event must contain either S3 Records or 'bucket'/'key' fields. "
            f"Received keys: {list(event.keys())}"
        )
    return bucket, key


def _error_response(status_code: int, message: str) -> dict:
    """Build a standardized error response."""
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": True,
            "message": message
        })
    }
