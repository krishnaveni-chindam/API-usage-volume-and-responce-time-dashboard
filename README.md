# API Usage Volume & Response Time Dashboard

A real-time monitoring dashboard to track API usage volume, response time, error rate, and endpoint performance.

## Features
- Live API request volume tracking per minute / hour / day
- Average response time monitoring with graphs
- Slowest & most-used endpoints identification
- Error rate (4xx / 5xx) visualization
- Interactive charts with filters by endpoint & time range

## How It Works
- Logs every API request with timestamp, endpoint, status code, and response time
- Stores data in SQLite / CSV
- Dashboard visualizes volume vs latency to detect performance bottlenecks

## Tech Used
Python, Flask, Pandas, SQLite, Chart.js / Plotly, HTML, CSS

## Use Case
Helps developers find which API is slow, when traffic is high, and where optimization is needed.
