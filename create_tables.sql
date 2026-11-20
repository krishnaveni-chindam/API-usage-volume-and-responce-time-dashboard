-- ============================================================
-- API Usage Volume & Response Time Dashboard — Schema (MySQL)
-- Star schema: 1 fact table + 2 dimension tables
-- ============================================================

DROP TABLE IF EXISTS fact_api_requests;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_endpoint;

-- ------------------------------------------------------------
-- DIM_CUSTOMER
-- ------------------------------------------------------------
CREATE TABLE dim_customer (
    customer_id     INT             NOT NULL,
    customer_name   VARCHAR(150)    NULL,       -- has raw casing/whitespace issues for cleaning
    plan_tier       VARCHAR(20)     NULL,        -- Free / Basic / Pro / Enterprise
    industry        VARCHAR(50)     NULL,        -- ~3% missing (NULL)
    region          VARCHAR(50)     NULL,        -- North America / Europe / APAC / LATAM / MEA
    signup_date     DATE            NULL,
    PRIMARY KEY (customer_id)
    -- NOTE: source CSV contains a couple of intentional duplicate customer_id rows
    -- for cleaning practice; PK is enforced here, so dedupe in pandas BEFORE loading,
    -- or load into a staging table without a PK first.
);

-- ------------------------------------------------------------
-- DIM_ENDPOINT
-- ------------------------------------------------------------
CREATE TABLE dim_endpoint (
    endpoint_id     INT             NOT NULL,
    endpoint_path   VARCHAR(100)    NOT NULL,
    service_owner   VARCHAR(50)     NOT NULL,   -- owning team, e.g. Payments, Identity
    category        VARCHAR(20)     NOT NULL,   -- Auth / Read / Write / Search / Reporting
    is_deprecated   BOOLEAN         NOT NULL DEFAULT FALSE,
    PRIMARY KEY (endpoint_id)
);

-- ------------------------------------------------------------
-- FACT_API_REQUESTS
-- ------------------------------------------------------------
CREATE TABLE fact_api_requests (
    request_id            VARCHAR(20)   NOT NULL,
    request_timestamp     DATETIME      NOT NULL,
    customer_id           INT           NOT NULL,
    endpoint_id            INT           NOT NULL,
    http_method             VARCHAR(10)   NOT NULL,   -- GET/POST/PUT/DELETE
    status_code             SMALLINT      NOT NULL,
    response_time_ms        DECIMAL(10,1) NULL,        -- ~4% missing (NULL) — logging gaps
    request_size_bytes      INT           NULL,
    response_size_bytes     INT           NULL,
    request_region          VARCHAR(50)   NULL,        -- ~1% missing (NULL)
    is_cached                BOOLEAN       NOT NULL DEFAULT FALSE,
    rate_limited              BOOLEAN       NOT NULL DEFAULT FALSE,
    sdk_version                VARCHAR(10)   NULL,
    environment                 VARCHAR(20)   NOT NULL DEFAULT 'production',
    -- NOTE: source CSV contains ~1% duplicate rows on purpose (ingestion-duplication
    -- practice). No PRIMARY KEY on request_id here so the raw duplicates can load;
    -- add a PK / dedupe step in your Python cleaning pass, then promote to a
    -- cleaned table if you want request_id enforced unique.
    INDEX idx_customer (customer_id),
    INDEX idx_endpoint (endpoint_id),
    INDEX idx_timestamp (request_timestamp),
    INDEX idx_status (status_code),
    CONSTRAINT fk_fact_customer FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    CONSTRAINT fk_fact_endpoint FOREIGN KEY (endpoint_id) REFERENCES dim_endpoint(endpoint_id)
);

-- ------------------------------------------------------------
-- LOAD DATA (adjust path to wherever the CSVs sit on your MySQL server)
-- Run first if needed:
--   SET GLOBAL local_infile = 1;
-- ------------------------------------------------------------

-- LOAD DATA LOCAL INFILE '/path/to/dim_customer.csv'
-- INTO TABLE dim_customer
-- FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;

-- LOAD DATA LOCAL INFILE '/path/to/dim_endpoint.csv'
-- INTO TABLE dim_endpoint
-- FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;

-- LOAD DATA LOCAL INFILE '/path/to/fact_api_requests.csv'
-- INTO TABLE fact_api_requests
-- FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS
-- (request_id, request_timestamp, customer_id, endpoint_id, http_method, status_code,
--  @response_time_ms, request_size_bytes, response_size_bytes, request_region,
--  is_cached, rate_limited, sdk_version, environment)
-- SET response_time_ms = NULLIF(@response_time_ms, '');
