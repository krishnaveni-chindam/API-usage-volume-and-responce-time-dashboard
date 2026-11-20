"""
API Usage Volume & Response Time Dashboard — Synthetic Data Generator
=======================================================================

BUSINESS PROBLEM
-----------------
The platform team needs to understand: "Which API endpoints are being used
most heavily, by which customers, and where are we seeing latency or
reliability problems that could hurt customer experience or breach SLAs?"

This script generates a star schema:
    - dim_customer.csv     (customers/API consumers)
    - dim_endpoint.csv     (API endpoints/services)
    - fact_api_requests.csv (individual API call log — the fact table)

Designed for: MySQL import -> pandas analysis -> Power BI dashboard.

Realism built in:
    - Growth trend: request volume increases steadily from 2024 -> 2025
    - Seasonality: business-hours + weekday pattern in traffic
    - Anomaly cluster: a simulated 6-day production incident with
      elevated latency + 5xx errors in July 2025
    - ~4% missing response_time_ms (simulates logging/agent failures)
    - ~1% duplicate fact rows (simulates ingestion duplication)
    - Inconsistent text casing/spacing in dim_customer (for cleaning practice)
    - Logical consistency: response_size scales with request type,
      status codes align with response time (errors tend slower or instant-fail)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import string

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

N_CUSTOMERS = 150
N_ENDPOINTS = 20
N_FACT_ROWS = 5000

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 12, 31, 23, 59, 59)

# Simulated incident window (anomaly cluster): a Payments outage
INCIDENT_START = datetime(2025, 7, 14)
INCIDENT_END = datetime(2025, 7, 19, 23, 59, 59)

OUT_DIR = "/mnt/user-data/outputs"

# ----------------------------------------------------------------------
# 1. DIM_CUSTOMER
# ----------------------------------------------------------------------
company_roots = [
    "Nimbus", "Vertex", "Cascade", "Orbital", "Lumen", "Sable", "Harborlight",
    "Northwind", "Quanta", "Fernbridge", "Ironclad", "BluePeak", "Solace",
    "Driftwood", "Cobalt", "Ridgeline", "Meridian", "Amberly", "Foxglove",
    "Palisade", "Everline", "Truenorth", "Kestrel", "Wildcard", "Anchorpoint",
    "Silverline", "Redshift", "Greywolf", "Fieldstone", "Copperline"
]
company_suffixes = ["Inc", "LLC", "Labs", "Technologies", "Systems", "Group", "Co", "Solutions"]

industries = ["Fintech", "Healthcare", "Retail", "SaaS", "Gaming",
              "Logistics", "EdTech", "Media", "Travel", "Manufacturing"]
industry_weights = [0.18, 0.10, 0.14, 0.20, 0.08, 0.08, 0.06, 0.06, 0.05, 0.05]

plan_tiers = ["Free", "Basic", "Pro", "Enterprise"]
plan_weights = [0.35, 0.30, 0.25, 0.10]  # most consumers on lower tiers (long tail)

regions = ["North America", "Europe", "APAC", "LATAM", "MEA"]
region_weights = [0.40, 0.28, 0.20, 0.08, 0.04]


def make_company_name(i):
    root = random.choice(company_roots)
    suffix = random.choice(company_suffixes)
    return f"{root} {suffix}"


def messy_text(text):
    """Introduce inconsistent casing/spacing for data-cleaning practice."""
    r = random.random()
    if r < 0.12:
        return text.upper()
    elif r < 0.22:
        return text.lower()
    elif r < 0.30:
        return f"  {text}  "  # stray whitespace
    elif r < 0.34:
        return text.replace(" ", "  ")  # double space
    return text


customer_ids = np.arange(1, N_CUSTOMERS + 1)
customer_names = [make_company_name(i) for i in customer_ids]
# apply messiness to ~30% of names
customer_names = [messy_text(n) if random.random() < 0.30 else n for n in customer_names]

# signup dates: mostly before the fact-data window starts, some during
signup_dates = [
    START_DATE - timedelta(days=int(np.random.exponential(180)) + 1)
    if random.random() < 0.7
    else START_DATE + timedelta(days=random.randint(0, 600))
    for _ in customer_ids
]

dim_customer = pd.DataFrame({
    "customer_id": customer_ids,
    "customer_name": customer_names,
    "plan_tier": np.random.choice(plan_tiers, size=N_CUSTOMERS, p=plan_weights),
    "industry": np.random.choice(industries, size=N_CUSTOMERS, p=industry_weights),
    "region": np.random.choice(regions, size=N_CUSTOMERS, p=region_weights),
    "signup_date": [d.date() for d in signup_dates],
})

# inject ~3% missing industry (simulates incomplete onboarding data)
missing_idx = dim_customer.sample(frac=0.03, random_state=SEED).index
dim_customer.loc[missing_idx, "industry"] = np.nan

# a couple of exact duplicate customer rows (data entry mistake)
dupes = dim_customer.sample(n=2, random_state=SEED)
dim_customer = pd.concat([dim_customer, dupes], ignore_index=True)

# ----------------------------------------------------------------------
# 2. DIM_ENDPOINT
# ----------------------------------------------------------------------
endpoint_catalog = [
    ("/v1/auth/login",        "Identity",  "Auth",       False),
    ("/v1/auth/refresh",      "Identity",  "Auth",       False),
    ("/v1/users",             "Core",      "Read",       False),
    ("/v1/users/{id}",        "Core",      "Read",       False),
    ("/v1/orders",            "Commerce",  "Write",      False),
    ("/v1/orders/{id}",       "Commerce",  "Read",       False),
    ("/v1/payments/charge",   "Payments",  "Write",      False),
    ("/v1/payments/refund",   "Payments",  "Write",      False),
    ("/v1/search",            "Search",    "Search",     False),
    ("/v1/search/suggest",    "Search",    "Search",     False),
    ("/v1/notifications",     "Growth",    "Write",      False),
    ("/v1/inventory",         "Commerce",  "Read",       False),
    ("/v1/inventory/update",  "Commerce",  "Write",      False),
    ("/v1/analytics/events",  "Platform",  "Write",      False),
    ("/v1/reports/summary",   "Platform",  "Reporting",  False),
    ("/v1/reports/export",    "Platform",  "Reporting",  False),
    ("/v1/webhooks/register", "Platform",  "Write",      False),
    ("/v0/legacy/users",      "Core",      "Read",       True),
    ("/v0/legacy/orders",     "Commerce",  "Read",       True),
    ("/v1/health",            "Platform",  "Read",       False),
]
assert len(endpoint_catalog) == N_ENDPOINTS

dim_endpoint = pd.DataFrame(endpoint_catalog,
                             columns=["endpoint_path", "service_owner", "category", "is_deprecated"])
dim_endpoint.insert(0, "endpoint_id", np.arange(1, N_ENDPOINTS + 1))

# base latency profile (ms) per category -> used by the fact generator
category_latency_base = {
    "Auth": 80, "Read": 120, "Write": 180, "Search": 220, "Reporting": 650,
}
# relative popularity weight per category (Reporting/legacy called less often)
endpoint_weight_map = {
    "Auth": 0.9, "Read": 1.3, "Write": 1.0, "Search": 0.8, "Reporting": 0.3,
}
dim_endpoint["_popularity_weight"] = dim_endpoint["category"].map(endpoint_weight_map)
dim_endpoint.loc[dim_endpoint["is_deprecated"], "_popularity_weight"] *= 0.15

# ----------------------------------------------------------------------
# 3. FACT_API_REQUESTS
# ----------------------------------------------------------------------
total_days = (END_DATE - START_DATE).days

# --- TREND: monthly growth weight (more calls in later months) ---
month_index = np.arange(0, 24)  # 24 months across 2024-2025
growth_weights = 1 + (month_index / 23) * 2.2  # ~3.2x growth by end of window

day_pool = []
day_weights = []
d = START_DATE
while d <= END_DATE:
    months_elapsed = (d.year - START_DATE.year) * 12 + (d.month - START_DATE.month)
    base_w = growth_weights[months_elapsed]

    # --- SEASONALITY: weekday >> weekend ---
    weekday_factor = 1.0 if d.weekday() < 5 else 0.35

    day_pool.append(d)
    day_weights.append(base_w * weekday_factor)
    d += timedelta(days=1)

day_weights = np.array(day_weights)
day_weights = day_weights / day_weights.sum()

chosen_days = np.random.choice(len(day_pool), size=N_FACT_ROWS, p=day_weights)

# --- hour-of-day seasonality: business hours peak (9-18), quiet overnight ---
hour_choices = list(range(24))
hour_weights = np.array([
    0.015, 0.010, 0.008, 0.006, 0.006, 0.010,   # 0-5 (overnight, quiet)
    0.020, 0.035, 0.055, 0.075, 0.085, 0.085,   # 6-11 (ramp up)
    0.080, 0.085, 0.085, 0.080, 0.070, 0.060,   # 12-17 (business hours peak)
    0.045, 0.035, 0.025, 0.020, 0.015, 0.012,   # 18-23 (wind down)
])
hour_weights = hour_weights / hour_weights.sum()

timestamps = []
for day_idx in chosen_days:
    day = day_pool[day_idx]
    hour = np.random.choice(hour_choices, p=hour_weights)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    timestamps.append(day.replace(hour=hour, minute=minute, second=second))

# --- assign customer & endpoint ---
customer_weights = np.where(dim_customer["plan_tier"].values[:N_CUSTOMERS] == "Enterprise", 4.0,
                    np.where(dim_customer["plan_tier"].values[:N_CUSTOMERS] == "Pro", 2.2,
                    np.where(dim_customer["plan_tier"].values[:N_CUSTOMERS] == "Basic", 1.3, 1.0)))
customer_weights = customer_weights / customer_weights.sum()

assigned_customers = np.random.choice(dim_customer["customer_id"].values[:N_CUSTOMERS],
                                       size=N_FACT_ROWS, p=customer_weights)

endpoint_weights = dim_endpoint["_popularity_weight"].values
endpoint_weights = endpoint_weights / endpoint_weights.sum()
assigned_endpoints = np.random.choice(dim_endpoint["endpoint_id"].values,
                                       size=N_FACT_ROWS, p=endpoint_weights)

endpoint_lookup = dim_endpoint.set_index("endpoint_id")

http_method_map = {
    "Auth": ["POST"],
    "Read": ["GET"],
    "Write": ["POST", "PUT"],
    "Search": ["GET"],
    "Reporting": ["GET", "POST"],
}

rows = []
for i in range(N_FACT_ROWS):
    ts = timestamps[i]
    ep_id = assigned_endpoints[i]
    ep = endpoint_lookup.loc[ep_id]
    category = ep["category"]
    is_deprecated = ep["is_deprecated"]

    method = random.choice(http_method_map[category])

    in_incident = INCIDENT_START <= ts <= INCIDENT_END and category in ("Write", "Read") \
        and ep["service_owner"] == "Payments"

    # --- status code distribution ---
    if in_incident:
        status_code = np.random.choice(
            [200, 201, 429, 500, 502, 503],
            p=[0.35, 0.05, 0.10, 0.25, 0.15, 0.10]
        )
    elif is_deprecated:
        status_code = np.random.choice(
            [200, 404, 410, 500],
            p=[0.55, 0.20, 0.15, 0.10]
        )
    else:
        status_code = np.random.choice(
            [200, 201, 204, 400, 401, 404, 429, 500, 503],
            p=[0.78, 0.06, 0.03, 0.045, 0.02, 0.02, 0.02, 0.015, 0.01]
        )

    # --- response time: base by category, right-skewed, incident spike ---
    base = category_latency_base[category]
    noise = np.random.gamma(shape=2.0, scale=base / 2.0)
    response_time = base * 0.4 + noise

    if in_incident:
        response_time *= np.random.uniform(4, 9)  # incident latency spike
    if status_code >= 500:
        response_time *= np.random.uniform(1.2, 2.0)  # errors tend slower
    if status_code == 429:
        response_time = np.random.uniform(5, 30)  # rate-limited: fails fast

    response_time = round(min(response_time, 15000), 1)  # cap outliers at 15s

    # --- payload sizes ---
    if method == "GET":
        req_size = int(np.random.uniform(150, 600))
    else:
        req_size = int(np.random.gamma(shape=2.0, scale=400))
    resp_size = int(req_size * np.random.uniform(0.8, 3.5)) if status_code < 400 else int(np.random.uniform(80, 300))

    is_cached = (category == "Read") and (random.random() < 0.25) and status_code == 200
    rate_limited = status_code == 429

    sdk_version = np.random.choice(["1.4.2", "1.5.0", "1.5.1", "2.0.0", "2.0.1"],
                                    p=[0.10, 0.15, 0.20, 0.30, 0.25])
    environment = np.random.choice(["production", "staging"], p=[0.92, 0.08])
    customer_region = dim_customer.set_index("customer_id").loc[assigned_customers[i], "region"]
    if isinstance(customer_region, pd.Series):  # in case of duplicate id after dupe injection
        customer_region = customer_region.iloc[0]

    rows.append({
        "request_id": f"req_{i+1:07d}",
        "request_timestamp": ts,
        "customer_id": assigned_customers[i],
        "endpoint_id": ep_id,
        "http_method": method,
        "status_code": int(status_code),
        "response_time_ms": response_time,
        "request_size_bytes": max(req_size, 20),
        "response_size_bytes": max(resp_size, 20),
        "request_region": customer_region,
        "is_cached": bool(is_cached),
        "rate_limited": bool(rate_limited),
        "sdk_version": sdk_version,
        "environment": environment,
    })

fact_api_requests = pd.DataFrame(rows)
fact_api_requests.sort_values("request_timestamp", inplace=True)
fact_api_requests.reset_index(drop=True, inplace=True)

# --- MESSINESS: ~4% missing response_time_ms (simulated logging gaps) ---
missing_rt_idx = fact_api_requests.sample(frac=0.04, random_state=SEED).index
fact_api_requests.loc[missing_rt_idx, "response_time_ms"] = np.nan

# --- MESSINESS: ~1% missing request_region ---
missing_region_idx = fact_api_requests.sample(frac=0.01, random_state=SEED + 1).index
fact_api_requests.loc[missing_region_idx, "request_region"] = np.nan

# --- MESSINESS: ~1% duplicate rows (ingestion duplication) ---
dupe_rows = fact_api_requests.sample(frac=0.01, random_state=SEED + 2)
fact_api_requests = pd.concat([fact_api_requests, dupe_rows], ignore_index=True)

# shuffle slightly so duplicates aren't all at the bottom, then keep a stable id order
fact_api_requests = fact_api_requests.sample(frac=1, random_state=SEED).reset_index(drop=True)

# drop helper column from dim_endpoint before export
dim_endpoint_export = dim_endpoint.drop(columns=["_popularity_weight"])

# ----------------------------------------------------------------------
# 4. EXPORT
# ----------------------------------------------------------------------
import os
os.makedirs(OUT_DIR, exist_ok=True)

dim_customer.to_csv(f"{OUT_DIR}/dim_customer.csv", index=False)
dim_endpoint_export.to_csv(f"{OUT_DIR}/dim_endpoint.csv", index=False)
fact_api_requests.to_csv(f"{OUT_DIR}/fact_api_requests.csv", index=False)

print("dim_customer:", dim_customer.shape)
print("dim_endpoint:", dim_endpoint_export.shape)
print("fact_api_requests:", fact_api_requests.shape)
print("\nMissing values in fact table:\n", fact_api_requests.isna().sum())
print("\nDuplicate full rows in fact table:", fact_api_requests.duplicated().sum())
print("\nIncident window row count (should show elevated latency/errors):")
incident_mask = (fact_api_requests["request_timestamp"] >= INCIDENT_START) & \
                 (fact_api_requests["request_timestamp"] <= INCIDENT_END)
print(fact_api_requests.loc[incident_mask, "response_time_ms"].describe())
