# Scalability Analysis

## Current Design

The application processes the TSV file **line by line** using Python's `csv.DictReader` as a generator. This means:

- **File reading is streamed** — the entire file is never loaded into memory at once.
- **Session tracking uses an in-memory dict** — stores `{IP: (domain, keyword)}`.
- **Revenue aggregation uses an in-memory dict** — stores `{(domain, keyword): revenue}`.

## How It Scales

| File Size | Session Dict Size | Will It Work? |
|-----------|------------------|---------------|
| < 1 GB   | ~10K-100K IPs (~10 MB) | Works perfectly |
| 1-5 GB   | ~1M IPs (~100 MB) | Works fine on a machine with 1+ GB RAM |
| 5-10 GB  | ~5M IPs (~500 MB) | Works, but approaching limits for Lambda (10 GB max memory) |
| 10+ GB   | ~10M+ IPs (~1+ GB) | Needs optimization |

**The bottleneck is NOT file I/O** (streaming handles that). **The bottleneck is the session dict** that grows with the number of unique IPs.

## Scaling Strategies

### Short-Term: Disk-Backed Session Store (10-50 GB files)

Replace the in-memory session dict with **SQLite**:

```python
import sqlite3

class DiskSessionTracker:
    def __init__(self, db_path="/tmp/sessions.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions (ip TEXT PRIMARY KEY, domain TEXT, keyword TEXT)"
        )

    def track(self, ip, domain, keyword):
        self.conn.execute(
            "INSERT OR IGNORE INTO sessions VALUES (?, ?, ?)",
            (ip, domain, keyword)
        )

    def get_referral(self, ip):
        row = self.conn.execute(
            "SELECT domain, keyword FROM sessions WHERE ip = ?", (ip,)
        ).fetchone()
        return row if row else None
```

This offloads memory to disk while keeping the same logic. SQLite handles billions of rows efficiently.

### Medium-Term: AWS Glue ETL (50-500 GB files)

- Use **AWS Glue** with PySpark for distributed processing.
- Data stored in S3, partitioned by date.
- Glue crawls the data, creates a catalog, and runs the Spark job.
- Results written back to S3 or to Amazon Redshift.

### Long-Term: Amazon EMR + Spark (500+ GB, recurring workloads)

- Provision an **EMR cluster** with Apache Spark.
- Read directly from S3 using `spark.read.csv()`.
- Spark handles partitioning, shuffling, and aggregation across the cluster.
- Scales horizontally — add nodes to handle larger files.

```python
# PySpark equivalent
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum

spark = SparkSession.builder.appName("SearchKeywordRevenue").getOrCreate()

df = spark.read.option("delimiter", "\t").option("header", True).csv("s3://bucket/data.sql")
# ... session tracking via window functions, joins, and aggregation
```

### Alternative: Chunked Lambda Processing

For files up to ~100 GB on S3:
1. Use **S3 Select** or **byte-range reads** to split the file into chunks.
2. Invoke multiple Lambda functions in parallel (one per chunk) using **Step Functions**.
3. Each Lambda processes its chunk and writes partial results.
4. A final Lambda aggregates partial results.

## Recommendation

| Scale | Solution | Cost |
|-------|----------|------|
| Up to 10 GB | Current approach (streaming + in-memory dict) | Free tier Lambda |
| 10-50 GB | SQLite-backed session store on Lambda/EC2 | ~$1-5/run |
| 50-500 GB | AWS Glue ETL job | ~$10-50/run |
| 500+ GB | Amazon EMR + Spark cluster | ~$50-200/run |

For the team's typical use case of **10+ GB files**, the **SQLite-backed session store** is the most practical first step — minimal code change, no new infrastructure, and handles 10-50x the current capacity.
