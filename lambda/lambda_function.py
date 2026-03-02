"""
Lambda Function: sqs-processor
Trigger  : SQS Queue (file-upload-queue)
Purpose  : Process S3 upload events from SQS and write structured logs to CloudWatch
"""

import json
import logging
import os
from datetime import datetime

# CloudWatch logging is automatic for Lambda — just use Python's logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Main Lambda handler.
    Called automatically when a message arrives in the SQS queue.
    """
    logger.info(f"=== Lambda triggered at {datetime.utcnow().isoformat()} ===")
    logger.info(f"Number of SQS records received: {len(event.get('Records', []))}")

    processed = 0
    errors     = 0

    for idx, record in enumerate(event.get("Records", [])):
        try:
            process_sqs_record(idx, record)
            processed += 1
        except Exception as e:
            logger.error(f"[Record {idx}] Failed to process: {str(e)}", exc_info=True)
            errors += 1

    summary = {
        "total":     len(event.get("Records", [])),
        "processed": processed,
        "errors":    errors,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"Processing summary: {json.dumps(summary)}")

    return {
        "statusCode": 200,
        "body": json.dumps(summary)
    }


def process_sqs_record(idx, record):
    """Parse one SQS record and extract S3 event details."""
    message_id   = record.get("messageId", "unknown")
    receipt_handle = record.get("receiptHandle", "")
    
    logger.info(f"[Record {idx}] MessageId: {message_id}")

    # SQS body contains the S3 event as a JSON string
    raw_body = record.get("body", "{}")
    
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning(f"[Record {idx}] Body is not valid JSON: {raw_body[:200]}")
        return

    # S3 Test notification (sent when you first configure the event)
    if "Event" in body and body["Event"] == "s3:TestEvent":
        logger.info(f"[Record {idx}] ✅ S3 test notification received — configuration is working!")
        return

    # Real S3 event
    s3_records = body.get("Records", [])
    if not s3_records:
        logger.warning(f"[Record {idx}] No S3 Records found in body")
        return

    for s3_record in s3_records:
        event_name = s3_record.get("eventName", "unknown")
        event_time = s3_record.get("eventTime", "unknown")
        s3_info    = s3_record.get("s3", {})

        bucket_name = s3_info.get("bucket", {}).get("name", "unknown")
        object_key  = s3_info.get("object", {}).get("key", "unknown")
        object_size = s3_info.get("object", {}).get("size", 0)

        # ── Structured log — visible in CloudWatch Logs ───────────────────
        log_entry = {
            "event":       "S3_FILE_UPLOADED",
            "eventName":   event_name,
            "eventTime":   event_time,
            "bucket":      bucket_name,
            "key":         object_key,
            "sizeBytes":   object_size,
            "messageId":   message_id,
            "processedAt": datetime.utcnow().isoformat()
        }

        logger.info(f"[Record {idx}] S3 Upload Event: {json.dumps(log_entry)}")

        # ── Business logic: categorize file type ─────────────────────────
        file_extension = object_key.split(".")[-1].lower() if "." in object_key else "unknown"
        categorize_file(object_key, file_extension, object_size, idx)


def categorize_file(key, extension, size_bytes, idx):
    """Log additional info based on file type."""
    image_types  = {"jpg", "jpeg", "png", "gif", "webp", "svg"}
    doc_types    = {"pdf", "docx", "txt", "csv", "xlsx"}
    video_types  = {"mp4", "avi", "mov", "mkv"}

    size_kb = round(size_bytes / 1024, 2)
    size_mb = round(size_bytes / (1024 * 1024), 2)

    if extension in image_types:
        category = "IMAGE"
    elif extension in doc_types:
        category = "DOCUMENT"
    elif extension in video_types:
        category = "VIDEO"
    else:
        category = "OTHER"

    logger.info(
        f"[Record {idx}] File Category: {category} | "
        f"Extension: .{extension} | "
        f"Size: {size_kb} KB ({size_mb} MB)"
    )

    # Alert for large files (> 10MB)
    if size_bytes > 10 * 1024 * 1024:
        logger.warning(
            f"[Record {idx}] ⚠️  LARGE FILE ALERT: {key} is {size_mb} MB — consider compression"
        )
