# Search Keyword Performance Analyzer

A Python application that processes Adobe Analytics **hit-level data** to determine how much revenue external search engines (Google, Yahoo, Bing/MSN) generate, and which search keywords perform best.

Built for deployment on **AWS Lambda** with **S3** integration, and also runs locally from the command line.

---

## Table of Contents

1. [Business Problem](#business-problem)
2. [How It Works](#how-it-works)
3. [Architecture & Flow Diagram](#architecture--flow-diagram)
4. [Data Flow — Step by Step](#data-flow--step-by-step)
5. [Project Structure](#project-structure)
6. [Setup & Installation](#setup--installation)
7. [Running the Application](#running-the-application)
8. [Running Tests](#running-tests)
9. [Configuration](#configuration)
10. [Logging & Debugging](#logging--debugging)
11. [AWS Deployment](#aws-deployment)
12. [Sample Output](#sample-output)
13. [Scalability](#scalability)

---

## Business Problem

An e-commerce client (**esshopzilla.com**) wants answers to:

> *"How much revenue are we getting from external search engines like Google, Yahoo, and Bing — and which search keywords are driving the most revenue?"*

### Why this matters
- The client pays for SEO and SEM (Search Engine Marketing).
- They need to know which **keywords** bring in the most **revenue** (not just traffic).
- This helps them optimize ad spend and focus on high-performing keywords.

---

## How It Works

### The Challenge

A visitor's journey spans **multiple page hits**. The search engine referrer only appears on the **first hit** (when the visitor arrives from Google/Bing/Yahoo). By the time they purchase, the referrer is an internal checkout page.

**Example — Visitor from Google searching "Ipod":**
```
Hit 1: Home page         ← referrer: google.com?q=Ipod  (this is where we capture the keyword)
Hit 2: Search Results     ← referrer: esshopzilla.com   (internal — no keyword here)
Hit 3: Product Page       ← referrer: esshopzilla.com
Hit 4: Shopping Cart      ← referrer: esshopzilla.com
Hit 5: Checkout           ← referrer: esshopzilla.com
Hit 6: Order Complete     ← referrer: esshopzilla.com   (purchase happens here — revenue = $290)
```

If we only looked at the referrer on Hit 6 (purchase row), we'd miss the Google attribution entirely.

### The Solution — Session-Based Attribution

1. **Track sessions by IP address** — when a visitor first arrives from a search engine, store the `(search_engine, keyword)` pair.
2. **When a purchase event occurs** (event code `1`), look up that visitor's session to find which search engine/keyword brought them in.
3. **Extract revenue** from the `product_list` field and attribute it to the keyword.

---

## Architecture & Flow Diagram

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AWS Cloud (us-east-1)                        │
│                                                                     │
│  ┌──────────┐    trigger    ┌──────────────────┐    write    ┌──────────┐
│  │  S3      │ ──────────►  │  AWS Lambda       │ ──────────► │  S3      │
│  │ /input/  │              │  (Python 3.13)    │             │ /output/ │
│  │ data.sql │              │                   │             │ .tab file│
│  └──────────┘              └──────────────────┘             └──────────┘
│                                    │                                │
│                                    ▼                                │
│                            CloudWatch Logs                          │
│                         (full pipeline trace)                       │
└─────────────────────────────────────────────────────────────────────┘

         ── OR run locally ──

┌──────────┐              ┌──────────────────┐              ┌──────────┐
│  Local   │  CLI arg     │  Python App      │  writes      │  Local   │
│  data.sql│ ──────────►  │  (src/main.py)   │ ──────────►  │ output/  │
└──────────┘              └──────────────────┘              │ .tab file│
                                  │                         └──────────┘
                                  ▼
                           logs/pipeline.log
                         (full pipeline trace)
```

### Data Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HitDataProcessor                                │
│                                                                         │
│  ┌─────────────┐                                                        │
│  │ Read TSV    │  Stream line by line (memory-efficient)                │
│  │ row by row  │                                                        │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────┐     ┌───────────────────┐                          │
│  │ ReferrerParser   │────►│ SessionTracker     │                         │
│  │                  │     │                    │                         │
│  │ - Parse URL      │     │ IP → (engine,      │                         │
│  │ - Detect engine  │     │       keyword)     │                         │
│  │ - Extract keyword│     │                    │                         │
│  └─────────────────┘     │ Only stores FIRST  │                         │
│                           │ search referral    │                         │
│         │                 │ per IP             │                         │
│         ▼                 └────────┬───────────┘                         │
│  ┌─────────────────┐              │                                     │
│  │ Is Purchase?    │              │ lookup                              │
│  │ (event_list     │              │                                     │
│  │  contains "1")  │              ▼                                     │
│  └────────┬────────┘     ┌───────────────────┐                          │
│      YES  │              │ ProductListParser  │                          │
│           │              │                    │                          │
│           └─────────────►│ - Split by , and ; │                          │
│                          │ - Extract revenue  │                          │
│                          │   (field index 3)  │                          │
│                          └────────┬───────────┘                          │
│                                   │                                     │
│                                   ▼                                     │
│                          ┌───────────────────┐                          │
│                          │ Revenue Aggregator │                          │
│                          │                    │                          │
│                          │ (engine, keyword)  │                          │
│                          │   → total revenue  │                          │
│                          └────────┬───────────┘                          │
│                                   │                                     │
│                                   ▼                                     │
│                          ┌───────────────────┐                          │
│                          │ Sort by revenue    │                          │
│                          │ (descending)       │                          │
│                          │ → Write .tab file  │                          │
│                          └───────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Class Diagram

```
┌────────────────────────────┐
│         Config             │  Singleton — loads config/config.yaml
│ (src/config.py)            │  Provides all settings to every module
├────────────────────────────┤
│ + search_engines           │
│ + purchase_event           │
│ + input_delimiter          │
│ + column_ip / referrer ... │
│ + output_directory         │
│ + aws_region / s3_*        │
└────────────┬───────────────┘
             │ used by
             ▼
┌────────────────────────────┐       ┌─────────────────────────┐
│    HitDataProcessor        │──────►│    ReferrerParser        │
│    (src/processor.py)      │       │    (src/parsers.py)      │
├────────────────────────────┤       ├─────────────────────────┤
│ + process_file(path)       │       │ + parse(url)            │
│ + write_output(results)    │       │   → (domain, keyword)   │
│ - _process_row(row)        │       │ - _extract_root_domain()│
│ - _is_purchase_event()     │       └─────────────────────────┘
│ - _validate_columns()      │
└──────┬─────────────────────┘       ┌─────────────────────────┐
       │                      ──────►│    ProductListParser     │
       │                             │    (src/parsers.py)      │
       │                             ├─────────────────────────┤
       │                             │ + parse_revenue(list)    │
       │                             │   → float               │
       │                             └─────────────────────────┘
       │
       │                             ┌─────────────────────────┐
       └────────────────────────────►│    SessionTracker        │
                                     │    (src/session.py)      │
                                     ├─────────────────────────┤
                                     │ + track(ip, domain, kw)  │
                                     │ + get_referral(ip)       │
                                     │ + has_referral(ip)       │
                                     │ + total_sessions         │
                                     └─────────────────────────┘
```

---

## Data Flow — Step by Step

Here's exactly what happens when you run `python -m src.main data.sql`:

### Step 1: Load Configuration
```
config/config.yaml → Config singleton
- Search engines: google(q), bing(q), yahoo(p), msn(q)
- Purchase event code: "1"
- Input delimiter: tab (\t)
- Output format: YYYY-mm-dd_SearchKeywordPerformance.tab
```

### Step 2: Read Input File
```
data.sql (tab-separated, 21 rows + header)
Each row = one page hit from a visitor
```

### Step 3: For Each Row — Detect Search Engine
The `referrer` field is parsed. If it matches a configured search engine:
```
http://www.google.com/search?q=Ipod  →  ("google.com", "Ipod")
http://www.bing.com/search?q=Zune    →  ("bing.com", "Zune")
http://search.yahoo.com/search?p=cd+player  →  ("yahoo.com", "cd player")
```
The **(IP → engine, keyword)** pair is stored in the SessionTracker.
Only the **first** search engine referral per IP is kept.

### Step 4: For Each Row — Check for Purchase
If `event_list` contains `1` (Purchase):
1. Look up the visitor's IP in SessionTracker.
2. Parse `product_list` to extract revenue (4th semicolon-delimited field).
3. Add revenue to the `(engine, keyword)` aggregation.

```
product_list: "Electronics;Ipod - Touch - 32GB;1;290;"
                                                ^^^
                                            Revenue = $290.00
```

### Step 5: Sort & Write Output
Results are sorted by revenue (highest first) and written as a `.tab` file:

```
Search Engine Domain    Search Keyword    Revenue
google.com              Ipod              290.0
bing.com                Zune              250.0
google.com              ipod              190.0
```

---

## Project Structure

```
adobe-search-keyword-performance/
│
├── config/
│   └── config.yaml              # All configurable settings (search engines, events, delimiters, AWS)
│
├── src/
│   ├── __init__.py
│   ├── config.py                # Config singleton — loads config.yaml, provides settings to all modules
│   ├── parsers.py               # ReferrerParser (URL → engine + keyword) & ProductListParser (→ revenue)
│   ├── processor.py             # HitDataProcessor — main orchestrator class, ties everything together
│   ├── session.py               # SessionTracker — maps IP → (search engine, keyword)
│   └── main.py                  # CLI entry point — argparse, logging setup, console output
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared test fixtures (Config reset between tests)
│   ├── test_config.py           # Tests for config loading, singleton, missing file handling
│   ├── test_parsers.py          # Tests for referrer parsing (Google/Bing/Yahoo/MSN/edge cases)
│   ├── test_session.py          # Tests for session tracking (first-referral-only, multi-IP)
│   └── test_processor.py        # End-to-end tests with sample data + actual data.sql
│
├── deployment/
│   ├── template.yaml            # AWS SAM template — Lambda function + S3 bucket + IAM
│   └── deploy.sh                # One-command deployment script (sam build + sam deploy)
│
├── lambda_handler.py            # AWS Lambda entry point — S3 download/upload with retry logic
├── data.sql                     # Input: tab-separated hit-level data (21 rows)
├── output/                      # Generated output .tab files land here
├── logs/                        # Pipeline log files (auto-created on first run)
│   └── pipeline.log             # Full DEBUG-level trace of every run
│
├── requirements.txt             # Python dependencies: pytest, boto3, pyyaml
├── SCALABILITY.md               # Analysis of how to handle 10GB+ files
├── .gitignore
└── README.md                    # You are here
```

### What Each File Does

| File | Purpose |
|------|---------|
| `config/config.yaml` | Single source of truth for all settings. Change search engines, event codes, column names, output format — no code changes needed. |
| `src/config.py` | Loads `config.yaml` as a singleton. Every module reads settings from here. |
| `src/parsers.py` | Two parsers: `ReferrerParser` extracts (domain, keyword) from referrer URLs. `ProductListParser` extracts revenue from the semicolon-delimited product list. |
| `src/session.py` | `SessionTracker` stores the first search engine referral per visitor IP. When a purchase happens, we look up which keyword brought the visitor. |
| `src/processor.py` | `HitDataProcessor` — the main class. Reads the file row-by-row, coordinates parsers + session tracker, aggregates revenue, writes output. |
| `src/main.py` | CLI entry point. Parses arguments, sets up logging, runs the processor, prints results to console. |
| `lambda_handler.py` | AWS Lambda handler. Downloads from S3, processes, uploads results back to S3. Includes retry logic with exponential backoff. |

---

## Setup & Installation

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.9+ | Application runtime |
| pip | any | Package installer |
| AWS CLI | 2.x | AWS deployment (optional — only for cloud deployment) |
| AWS SAM CLI | 1.x | Serverless deployment (optional — only for cloud deployment) |

### Step 1 — Clone the Repository
```bash
git clone https://github.com/<your-username>/adobe-search-keyword-performance.git
cd adobe-search-keyword-performance
```

### Step 2 — Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Verify Installation
```bash
python -m pytest tests/ -v
```
You should see **35 tests passed**.

---

## Running the Application

### Basic Usage
```bash
python -m src.main data.sql
```

### With Custom Output Directory
```bash
python -m src.main data.sql --output-dir /path/to/results
```

### With Custom Config File
```bash
python -m src.main data.sql --config /path/to/custom_config.yaml
```

### With Debug Logging (verbose console output)
```bash
python -m src.main data.sql --log-level DEBUG
```

### All Options
```bash
python -m src.main --help
```
```
usage: main.py [-h] [--output-dir OUTPUT_DIR] [--config CONFIG]
               [--log-level {DEBUG,INFO,WARNING,ERROR}] file

positional arguments:
  file                  Path to the tab-separated hit-level data file

optional arguments:
  --output-dir          Directory for output file (default: from config.yaml)
  --config              Path to config.yaml (default: config/config.yaml)
  --log-level           Console log level (default: INFO)
```

---

## Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Tests for a Specific Module
```bash
python -m pytest tests/test_parsers.py -v     # Parser tests only
python -m pytest tests/test_session.py -v      # Session tracker tests only
python -m pytest tests/test_processor.py -v    # End-to-end tests
python -m pytest tests/test_config.py -v       # Config loader tests
```

### Test Coverage Summary (35 tests)

| Test File | Tests | What's Covered |
|-----------|-------|----------------|
| `test_config.py` | 4 | Config loading, singleton pattern, missing file error |
| `test_parsers.py` | 13 | Google/Bing/Yahoo/MSN parsing, edge cases (empty, null, malformed, no keyword), custom engines, custom revenue index |
| `test_session.py` | 5 | Track + retrieve, first-referral-only rule, unknown IP, multiple IPs |
| `test_processor.py` | 6 | End-to-end with sample data, no-purchase scenario, direct traffic exclusion, file-not-found, output file format, integration with actual data.sql |

---

## Configuration

All settings live in `config/config.yaml`. You can change any of these **without modifying code**:

### Search Engines
```yaml
search_engines:
  google: "q"       # google.com → keyword in ?q= parameter
  bing: "q"         # bing.com → keyword in ?q= parameter
  yahoo: "p"        # yahoo.com → keyword in ?p= parameter
  msn: "q"          # msn.com → keyword in ?q= parameter
```
To add a new search engine (e.g., DuckDuckGo), just add a line:
```yaml
  duckduckgo: "q"
```

### Event Codes
```yaml
events:
  purchase: "1"      # Only count revenue when this event is in event_list
```

### Column Mapping
```yaml
input:
  columns:
    ip: "ip"                   # Column name for visitor IP
    referrer: "referrer"       # Column name for referrer URL
    event_list: "event_list"   # Column name for events
    product_list: "product_list"  # Column name for product data
```
If the client's file uses different column names, just update here.

### Product List Parsing
```yaml
product_list:
  product_delimiter: ","    # Products separated by comma
  field_delimiter: ";"      # Fields within a product separated by semicolon
  revenue_field_index: 3    # Revenue is the 4th field (0-indexed)
```

### Output Format
```yaml
output:
  directory: "output"
  filename_template: "{date}_SearchKeywordPerformance.tab"
  date_format: "%Y-%m-%d"
  delimiter: "\t"
  headers:
    - "Search Engine Domain"
    - "Search Keyword"
    - "Revenue"
```

---

## Logging & Debugging

The application has **two log destinations**:

| Destination | Level | Purpose |
|-------------|-------|---------|
| **Console** (stdout) | Configurable via `--log-level` (default: INFO) | See pipeline progress in real-time |
| **Log file** (`logs/pipeline.log`) | Always DEBUG | Full trace for post-run debugging |

### What Gets Logged

| Log Level | Examples |
|-----------|----------|
| **DEBUG** | Referrer URL parsing details, column validation, every product_list parse |
| **INFO** | Pipeline start/end, new session tracked, revenue attributed, processing summary |
| **WARNING** | Skipped rows, non-numeric revenue, purchase with no revenue in product_list |
| **ERROR** | File not found, permission denied, S3 failures, config errors |

### Example: INFO-level Console Output
```
09:01:31 | INFO     | Search Keyword Performance Analyzer — Starting
09:01:31 | INFO     | Configuration loaded. Search engines: ['google', 'bing', 'yahoo', 'msn']
09:01:31 | INFO     | New session tracked: ip=67.98.123.1, engine=google.com, keyword='Ipod'
09:01:31 | INFO     | Revenue attributed: ip=23.8.61.21, engine=bing.com, keyword='Zune', revenue=250.00
09:01:31 | INFO     | Processing complete. Rows processed: 21, Rows skipped: 0
09:01:31 | INFO     | Pipeline completed successfully. Total revenue: $730.00
```

### Example: Debugging a Problem
```bash
# Run with full debug output
python -m src.main data.sql --log-level DEBUG

# Or check the log file after any run
cat logs/pipeline.log
```

### Lambda / AWS Debugging
All logs automatically go to **CloudWatch Logs** in the AWS console. Search for the Lambda function name to find execution logs.

---

## AWS Deployment

### Prerequisites
```bash
brew install awscli aws-sam-cli    # macOS
aws configure                       # Enter your Access Key + Secret + region (us-east-1)
```

### Step 1 — Deploy
```bash
cd adobe-search-keyword-performance
sam build --template-file deployment/template.yaml
sam deploy \
  --stack-name adobe-search-keyword-processor \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset
```

### Step 2 — Upload Data to S3
```bash
# Find your bucket name (contains your AWS account ID)
aws s3 ls | grep adobe

# Upload
aws s3 cp data.sql s3://adobe-hit-level-data-<ACCOUNT_ID>/input/data.sql
```

### Step 3 — Invoke Lambda
```bash
aws lambda invoke \
  --function-name SearchKeywordPerformanceProcessor \
  --payload '{"bucket": "adobe-hit-level-data-<ACCOUNT_ID>", "key": "input/data.sql"}' \
  response.json

cat response.json
```

### Step 4 — Download Results
```bash
aws s3 cp s3://adobe-hit-level-data-<ACCOUNT_ID>/output/ ./output/ --recursive
cat output/*_SearchKeywordPerformance.tab
```

### S3 Auto-Trigger
You can also just upload a `.sql` file to the `input/` folder in S3 — the Lambda function triggers automatically and writes results to `output/`.

### Retry Logic (Lambda)
S3 operations (download/upload) have built-in retry logic:
- **3 retries** with exponential backoff (2s, 4s, 8s)
- Retries on transient errors (throttling, timeouts, 5xx)
- Fails immediately on permission errors (403) or not-found (404) — with clear error messages

---

## Sample Output

### Console Output
```
Search Engine Domain      Search Keyword          Revenue
---------------------------------------------------------
google.com                Ipod                     290.00
bing.com                  Zune                     250.00
google.com                ipod                     190.00
---------------------------------------------------------
TOTAL                                              730.00
```

### Output File
File: `output/2026-03-12_SearchKeywordPerformance.tab`
```
Search Engine Domain	Search Keyword	Revenue
google.com	Ipod	290.0
bing.com	Zune	250.0
google.com	ipod	190.0
```

### Key Observations
- **Google** drives the most revenue ($480 total across two keywords)
- **"Ipod"** (capitalized) is the highest-revenue keyword at $290
- **Bing** contributed $250 from the keyword "Zune"
- **Yahoo** had a visitor searching "cd player" but they did **not** purchase — so $0 revenue attributed

---

## Scalability

This application streams the file line-by-line (never loads the full file into memory), making it efficient for moderate file sizes. For the team's 10GB+ files, see [SCALABILITY.md](SCALABILITY.md) for a detailed analysis and recommended solutions:

| File Size | Recommended Approach |
|-----------|---------------------|
| Up to 10 GB | Current approach (streaming + in-memory session dict) |
| 10–50 GB | SQLite-backed session store |
| 50–500 GB | AWS Glue ETL with PySpark |
| 500+ GB | Amazon EMR + Spark cluster |
