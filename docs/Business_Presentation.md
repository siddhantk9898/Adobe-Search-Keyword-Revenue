# Search Keyword Revenue Attribution Analysis
### Adobe ACS Data Engineering — Business Presentation

---

## 1. Executive Summary

This report presents the findings from analyzing **esshopzilla.com's** hit-level web analytics data to answer a critical business question:

> **"How much revenue is the client getting from external search engines (Google, Yahoo, Bing/MSN), and which search keywords are driving the most revenue?"**

### Key Findings

| Metric | Value |
|--------|-------|
| **Total Revenue from Search Engines** | **$730.00** |
| **Top Keyword** | "Ipod" via Google — **$290.00** |
| **Top Search Engine** | Google — **$480.00** (65.8% of total) |
| **Number of Search Engine Visitors** | 4 |
| **Conversion Rate (Search → Purchase)** | 75% (3 of 4 visitors purchased) |

---

## 2. Business Context

### What is Hit-Level Data?

Hit-level data captures **every single interaction** (page view, click, cart action, purchase) a visitor makes on the client's website. Each row in the data file represents one "hit" — a single page load or event.

For esshopzilla.com, the data includes:
- **When** the visitor arrived (timestamp)
- **Where** they came from (referrer URL — Google, Bing, Yahoo, direct, etc.)
- **What** they viewed (product pages, search results, cart)
- **What** they did (viewed product, added to cart, checked out, purchased)
- **How much** they spent (revenue in the product list)

### Why This Analysis Matters

The client invests in **Search Engine Optimization (SEO)** and **Search Engine Marketing (SEM)** to drive traffic from Google, Bing, and Yahoo. They need to understand:

1. **Which search engines are generating the most revenue?** — Not just traffic, but actual dollars.
2. **Which keywords convert to sales?** — To optimize ad spend and SEO strategy.
3. **Are there search engines or keywords underperforming?** — Potential areas to improve or cut.

Without this analysis, the client is spending marketing budget blindly — paying for keywords that may drive traffic but not revenue.

---

## 3. The Challenge — Why This Isn't Straightforward

### The Multi-Hit Visitor Journey

A visitor doesn't arrive from Google and immediately purchase. Their journey spans **multiple page hits**:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Visitor Journey (IP: 67.98.123.1)                  │
│                                                                      │
│  Hit 1: Google Search "Ipod"                                         │
│         ↓  (referrer: google.com?q=Ipod)                             │
│  Hit 2: esshopzilla.com — Home Page                                 │
│         ↓                                                            │
│  Hit 3: esshopzilla.com — Search "Ipod"                             │
│         ↓                                                            │
│  Hit 4: esshopzilla.com — Ipod Nano 8GB (Product View)              │
│         ↓                                                            │
│  Hit 5: esshopzilla.com — Search Results                            │
│         ↓                                                            │
│  Hit 6: esshopzilla.com — Ipod Touch 32GB (Product View)            │
│         ↓                                                            │
│  Hit 7: esshopzilla.com — Shopping Cart (Add to Cart)               │
│         ↓                                                            │
│  Hit 8: esshopzilla.com — Checkout Details                          │
│         ↓                                                            │
│  Hit 9: esshopzilla.com — Order Confirmation                        │
│         ↓                                                            │
│  Hit 10: esshopzilla.com — ORDER COMPLETE ← Revenue = $290.00      │
│                                                                      │
│  ⚠ The referrer on Hit 10 is the internal checkout page,            │
│    NOT Google. We need to look back at Hit 1 to attribute            │
│    this $290 to Google + "Ipod".                                     │
└──────────────────────────────────────────────────────────────────────┘
```

### The Problem

The **search engine referrer** (Google, Bing, Yahoo) only appears on the **first hit** — when the visitor initially arrives from the search engine. By the time they purchase (hit 10), the referrer is an internal checkout page.

**If we only looked at the referrer on the purchase row, we would attribute $0 to search engines.**

### The Solution — Session-Based Attribution

We track each visitor's **session** by their IP address:

1. **First hit from a search engine** → Store the `(search_engine, keyword)` pair.
2. **Later, when a purchase occurs** → Look up the visitor's session to find which search engine and keyword originally brought them to the site.
3. **Attribute the revenue** to that search engine + keyword combination.

---

## 4. Data Analysis — Complete Visitor Breakdown

### Visitor 1: IP 67.98.123.1 (Salem, OR)

| Hit | Time | Page | Event | Referrer |
|-----|------|------|-------|----------|
| 1 | 06:34:40 | Home | — | **google.com ?q=Ipod** |
| 2 | 06:41:16 | Search Results (Ipod) | — | esshopzilla.com |
| 3 | 06:46:13 | Ipod Nano 8GB | Product View | esshopzilla.com |
| 4 | 06:51:10 | Search Results (Ipod) | — | esshopzilla.com |
| 5 | 06:56:07 | Ipod Touch 32GB | Product View | esshopzilla.com |
| 6 | 07:01:04 | Shopping Cart | Cart Add | esshopzilla.com |
| 7 | 07:04:22 | Checkout Details | Checkout | esshopzilla.com |
| 8 | 07:06:01 | Order Confirmation | — | esshopzilla.com |
| 9 | 07:07:40 | **Order Complete** | **Purchase** | esshopzilla.com |

**Attribution:** Google → keyword "Ipod" → **$290.00** (Ipod Touch 32GB)

**Insight:** This visitor compared products (viewed Nano, then Touch) before purchasing the premium option. The keyword "Ipod" successfully captured a high-value buyer.

---

### Visitor 2: IP 23.8.61.21 (Rochester, NY)

| Hit | Time | Page | Event | Referrer |
|-----|------|------|-------|----------|
| 1 | 06:36:19 | Zune 32GB | Product View | **bing.com ?q=Zune** |
| 2 | 06:42:55 | Shopping Cart | Cart Add | esshopzilla.com |
| 3 | 06:47:52 | Checkout Details | Checkout | esshopzilla.com |
| 4 | 06:52:49 | Order Confirmation | — | esshopzilla.com |
| 5 | 06:57:46 | **Order Complete** | **Purchase** | esshopzilla.com |

**Attribution:** Bing → keyword "Zune" → **$250.00** (Zune 32GB)

**Insight:** This visitor had a very direct path — landed on the product page, added to cart, and purchased. High intent buyer from Bing. Fastest conversion in the dataset.

---

### Visitor 3: IP 44.12.96.2 (Duncan, OK)

| Hit | Time | Page | Event | Referrer |
|-----|------|------|-------|----------|
| 1 | 06:37:58 | Hot Buys | — | **google.com ?q=ipod** |
| 2 | 06:44:34 | Ipod Nano 8GB | Product View | esshopzilla.com |
| 3 | 06:49:31 | Shopping Cart | Cart Add | esshopzilla.com |
| 4 | 06:54:28 | Checkout Details | Checkout | esshopzilla.com |
| 5 | 06:59:25 | Order Confirmation | — | esshopzilla.com |
| 6 | 07:02:43 | **Order Complete** | **Purchase** | esshopzilla.com |

**Attribution:** Google → keyword "ipod" → **$190.00** (Ipod Nano 8GB)

**Insight:** This visitor searched with lowercase "ipod" and landed on the Hot Buys page first, then went to the specific product. They chose the more affordable Nano model.

---

### Visitor 4: IP 112.33.98.231 (Salt Lake City, UT)

| Hit | Time | Page | Event | Referrer |
|-----|------|------|-------|----------|
| 1 | 06:37:58 | Home | — | **yahoo.com ?p=cd+player** |

**Attribution:** Yahoo → keyword "cd player" → **$0.00** (No purchase)

**Insight:** This visitor arrived searching for "cd player" — a product esshopzilla.com may not carry or prominently feature. They left after just one page view. This suggests a **keyword mismatch** — the visitor's intent didn't match the site's offerings.

---

## 5. Results — Revenue by Search Engine & Keyword

### Output File: `2026-03-12_SearchKeywordPerformance.tab`

```
Search Engine Domain    Search Keyword    Revenue
google.com              Ipod              290.0
bing.com                Zune              250.0
google.com              ipod              190.0
```

### Revenue by Search Engine

```
┌────────────────────────────────────────────────────────────┐
│                Revenue by Search Engine                      │
│                                                              │
│  Google     ████████████████████████████████████  $480.00    │
│             (65.8%)                                          │
│                                                              │
│  Bing       ████████████████████████             $250.00    │
│             (34.2%)                                          │
│                                                              │
│  Yahoo      ░                                    $0.00      │
│             (0.0%)                                           │
│                                                              │
│  TOTAL ─────────────────────────────────────────  $730.00    │
└────────────────────────────────────────────────────────────┘
```

### Revenue by Keyword

```
┌────────────────────────────────────────────────────────────┐
│                Revenue by Keyword                            │
│                                                              │
│  "Ipod"      ████████████████████████████████████  $290.00  │
│  (Google)    (39.7%)                                         │
│                                                              │
│  "Zune"      ████████████████████████████         $250.00  │
│  (Bing)      (34.2%)                                         │
│                                                              │
│  "ipod"      ██████████████████████               $190.00  │
│  (Google)    (26.0%)                                         │
│                                                              │
│  "cd player" ░                                    $0.00    │
│  (Yahoo)     (0.0%)                                          │
└────────────────────────────────────────────────────────────┘
```

---

## 6. Business Insights & Recommendations

### Insight 1: Google is the Dominant Revenue Driver
- Google accounts for **$480 (65.8%)** of total search engine revenue.
- Both Google keywords ("Ipod" and "ipod") converted to purchases.
- **Recommendation:** Continue investing in Google SEO/SEM for electronics keywords.

### Insight 2: Bing Delivers High-Intent Buyers
- Bing generated **$250** from a single keyword ("Zune") with the **fastest conversion path** (5 hits).
- The visitor went directly from search → product → cart → purchase.
- **Recommendation:** Don't overlook Bing. Despite lower traffic volume, Bing visitors may have higher purchase intent. Consider increasing Bing ad spend.

### Insight 3: Yahoo Has Traffic but No Revenue
- Yahoo drove one visitor searching "cd player" but they **left without purchasing**.
- The keyword "cd player" may indicate a product-market mismatch.
- **Recommendation:**
  - Review what products appear when visitors search "cd player" on esshopzilla.com.
  - Either stock CD players or adjust Yahoo ad targeting to exclude irrelevant keywords.

### Insight 4: Keyword Case Sensitivity Reveals Different Audiences
- "Ipod" (capitalized) → $290 purchase (premium Ipod Touch 32GB).
- "ipod" (lowercase) → $190 purchase (budget Ipod Nano 8GB).
- Different search behaviors may correlate with different buyer personas and price sensitivity.
- **Recommendation:** Analyze whether keyword casing patterns correlate with higher-value purchases across larger datasets.

### Insight 5: Product Comparison Drives Higher Revenue
- Visitor 1 (Google, "Ipod") browsed **two products** before buying the more expensive one ($290).
- Visitor 3 (Google, "ipod") went straight to one product and bought it ($190).
- **Recommendation:** Ensure product comparison features are prominent — visitors who compare tend to buy premium options.

---

## 7. Technical Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud (us-east-1)                           │
│                                                                         │
│                                                                         │
│  ┌─────────────────┐                      ┌─────────────────────┐       │
│  │    Amazon S3     │    auto-trigger      │    AWS Lambda        │       │
│  │                  │    on upload to      │    (Python 3.13)     │       │
│  │  /input/         │ ──────────────────►  │                      │       │
│  │    data.sql      │                      │  ┌────────────────┐  │       │
│  │                  │                      │  │ HitDataProcessor│  │       │
│  └─────────────────┘                      │  │ ReferrerParser  │  │       │
│                                            │  │ ProductParser   │  │       │
│                                            │  │ SessionTracker  │  │       │
│  ┌─────────────────┐                      │  └────────────────┘  │       │
│  │    Amazon S3     │    write results     │                      │       │
│  │                  │ ◄──────────────────  │  Retry logic (3x)   │       │
│  │  /output/        │                      │  Exponential backoff │       │
│  │   YYYY-mm-dd_    │                      └─────────────────────┘       │
│  │   SearchKeyword  │                              │                     │
│  │   Performance.tab│                              ▼                     │
│  └─────────────────┘                      ┌─────────────────────┐       │
│                                            │  Amazon CloudWatch   │       │
│                                            │  (Logs & Monitoring) │       │
│                                            └─────────────────────┘       │
│                                                                         │
│  S3 Bucket: adobe-hit-level-data-214888068638                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Processing Pipeline                                │
│                                                                          │
│   INPUT                    PROCESS                         OUTPUT         │
│                                                                          │
│  ┌──────────┐     ┌─────────────────────────┐     ┌──────────────────┐  │
│  │          │     │  For each row:           │     │                  │  │
│  │ data.sql │     │                          │     │ Tab-delimited    │  │
│  │ (TSV)    │────►│  1. Parse referrer URL   │────►│ output file      │  │
│  │          │     │     ↓                    │     │                  │  │
│  │ 21 rows  │     │  Is it Google/Bing/Yahoo?│     │ Sorted by        │  │
│  │ 12 cols  │     │     ↓ YES               │     │ revenue (desc)   │  │
│  │          │     │  2. Store session        │     │                  │  │
│  └──────────┘     │     IP → (engine, kw)   │     │ 3 columns:       │  │
│                   │     ↓                    │     │ - Engine Domain  │  │
│  Streamed         │  3. Is purchase event?   │     │ - Keyword        │  │
│  line-by-line     │     (event_list = "1")   │     │ - Revenue        │  │
│  (memory          │     ↓ YES               │     │                  │  │
│   efficient)      │  4. Extract revenue from │     └──────────────────┘  │
│                   │     product_list         │                           │
│                   │     ↓                    │                           │
│                   │  5. Attribute to session  │                           │
│                   │     (engine + keyword)   │                           │
│                   │     ↓                    │                           │
│                   │  6. Aggregate & sort     │                           │
│                   └─────────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Application Architecture (Class Diagram)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  config/config.yaml ──► Config (Singleton)                           │
│                          │                                           │
│                          │ provides settings to                      │
│                          ▼                                           │
│                    HitDataProcessor (src/processor.py)                │
│                    ┌─────────────────────────────────┐               │
│                    │ - Reads TSV row by row           │               │
│                    │ - Coordinates all components     │               │
│                    │ - Aggregates revenue             │               │
│                    │ - Writes output .tab file        │               │
│                    └──────────┬───────────────────────┘               │
│                               │                                      │
│              ┌────────────────┼────────────────┐                     │
│              ▼                ▼                ▼                      │
│    ReferrerParser      SessionTracker    ProductListParser            │
│    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│    │ URL parsing   │   │ IP → (engine │   │ Semicolon    │           │
│    │ Engine detect │   │    keyword)  │   │ delimited    │           │
│    │ Keyword       │   │              │   │ revenue      │           │
│    │ extraction    │   │ First        │   │ extraction   │           │
│    │               │   │ referral     │   │              │           │
│    │ google.com→q  │   │ only         │   │ Field[3] =   │           │
│    │ bing.com→q    │   │ per IP       │   │ revenue      │           │
│    │ yahoo.com→p   │   │              │   │              │           │
│    └──────────────┘   └──────────────┘   └──────────────┘           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 8. Technical Approach & Design Decisions

### Decision 1: Session Tracking by IP Address

**Why IP?** The data file doesn't include cookies or visitor IDs. IP address is the only consistent identifier across hits from the same visitor.

**Limitation:** In production, multiple users behind the same corporate IP could be incorrectly merged into one session. A more robust approach would use a combination of IP + User Agent + timestamp proximity.

**For this dataset:** All 4 IPs are unique and clearly represent individual visitors, so IP-based tracking is accurate.

### Decision 2: First-Touch Attribution

When a visitor arrives from a search engine, we record that as their attribution source. If they later return from a different search engine, we **keep the first one**.

**Why?** First-touch attribution credits the channel that originally **discovered** the customer. This is the most common model for SEO/SEM analysis.

**Alternative:** Last-touch attribution would credit the most recent search engine before purchase. Both are valid — the choice depends on the client's marketing strategy.

### Decision 3: Config-Driven Architecture

All settings (search engine definitions, event codes, column names, output format) are stored in `config/config.yaml`. This means:

- **Adding a new search engine** (e.g., DuckDuckGo) requires adding one line to config — no code changes.
- **Different clients** with different column names can use the same code with different config files.
- **Event codes** can be updated if the client's Adobe Analytics implementation changes.

### Decision 4: Streaming File Processing

The file is read **line by line** using Python's `csv.DictReader` generator. The entire file is never loaded into memory. This makes the application capable of handling files much larger than available RAM.

---

## 9. Scalability — Handling 10GB+ Files

The current application uses streaming I/O (line-by-line reading) which handles the file reading efficiently. The main memory concern is the **session tracking dictionary** which grows with the number of unique visitor IPs.

| File Size | Expected Unique IPs | Session Dict Memory | Solution |
|-----------|-------------------|-------------------|----------|
| < 1 GB | ~100K | ~10 MB | Current approach works |
| 1–10 GB | ~1M | ~100 MB | Current approach works |
| 10–50 GB | ~5M | ~500 MB | Switch to SQLite-backed sessions |
| 50–500 GB | ~50M | ~5 GB | AWS Glue + PySpark |
| 500+ GB | ~100M+ | ~10+ GB | Amazon EMR + Spark cluster |

### Recommended Next Step for 10GB+ Files

Replace the in-memory session dictionary with **SQLite** — a disk-backed database that ships with Python. This requires minimal code changes (swap the dict for SQLite queries) and can handle billions of session records.

For details, see [SCALABILITY.md](../SCALABILITY.md).

---

## 10. Quality Assurance

### Test Coverage

| Test Area | Tests | What's Validated |
|-----------|-------|-----------------|
| Config Loader | 4 | YAML loading, singleton pattern, missing file error, reset |
| Referrer Parser | 11 | Google/Bing/Yahoo/MSN extraction, internal URLs, empty/null/malformed URLs, custom engines |
| Product List Parser | 8 | Single/multiple products, decimal revenue, empty/null, custom field index |
| Session Tracker | 5 | Track + retrieve, first-referral-only, unknown IP, multiple IPs |
| End-to-End Processor | 6 | Full pipeline with sample data, no-purchase scenario, direct traffic exclusion, output format, actual data.sql validation |
| **Total** | **35** | |

### Logging & Monitoring

Every step of the pipeline is logged at appropriate levels:

| What Gets Logged | Log Level | Example |
|-----------------|-----------|---------|
| Pipeline start/end | INFO | `Search Keyword Performance Analyzer — Starting` |
| New session detected | INFO | `New session tracked: ip=67.98.123.1, engine=google.com, keyword='Ipod'` |
| Revenue attributed | INFO | `Revenue attributed: ip=23.8.61.21, engine=bing.com, keyword='Zune', revenue=250.00` |
| Processing summary | INFO | `Rows processed: 21, Rows skipped: 0, Purchase events: 3` |
| Skipped/malformed rows | WARNING | `Skipping row 15 due to error: ...` |
| File/permission errors | ERROR | `Data file not found: /path/to/file` |
| Parser internals | DEBUG | `Detected search engine referral: domain=google.com, keyword='Ipod'` |

In AWS, all logs are automatically available in **Amazon CloudWatch** for real-time monitoring and historical analysis.

---

## 11. How to Reproduce Results

### Option A: Run Locally
```bash
# 1. Clone the repository
git clone https://github.com/<username>/adobe-search-keyword-performance.git
cd adobe-search-keyword-performance

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python -m src.main data.sql

# 5. View the output
cat output/2026-03-12_SearchKeywordPerformance.tab
```

### Option B: Run on AWS
```bash
# Upload data to S3
aws s3 cp data.sql s3://adobe-hit-level-data-214888068638/input/data.sql

# Invoke Lambda
aws lambda invoke \
  --function-name SearchKeywordPerformanceProcessor \
  --payload '{"bucket": "adobe-hit-level-data-214888068638", "key": "input/data.sql"}' \
  response.json

# Download results
aws s3 cp s3://adobe-hit-level-data-214888068638/output/ ./output/ --recursive
```

### Option C: Run Tests
```bash
python -m pytest tests/ -v    # 35 tests, all passing
```

---

## 12. Summary

| Question | Answer |
|----------|--------|
| **Total search engine revenue?** | **$730.00** |
| **Which engine drives the most revenue?** | **Google — $480.00 (65.8%)** |
| **Which keyword performs best?** | **"Ipod" via Google — $290.00** |
| **Are there underperforming channels?** | **Yahoo — $0 revenue** (keyword mismatch: "cd player") |
| **Does Bing matter?** | **Yes — $250 from a single high-intent buyer** |

### Actionable Recommendations

1. **Double down on Google electronics keywords** — "Ipod" variants alone generated $480.
2. **Invest in Bing** — Lower volume but higher purchase intent (fastest conversion).
3. **Fix Yahoo keyword targeting** — "cd player" visitors aren't finding what they need.
4. **Enable product comparison features** — Visitors who compare products buy premium options.
5. **Run this analysis monthly** on the full dataset to track keyword performance trends.

---

*Report generated by the Search Keyword Performance Analyzer*
*Data source: esshopzilla.com hit-level data (data.sql)*
*S3 Bucket: adobe-hit-level-data-214888068638*
