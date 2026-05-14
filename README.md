# US Macro Dashboard — Django + FRED

A Django application that pulls live macroeconomic data from the Federal Reserve's FRED API to give a complete picture of the US economy over the last 4 quarters.

## Indicators Covered (25 series)

| Category | Series |
|---|---|
| **GDP & Output** | Real GDP (GDPC1), Industrial Production (INDPRO) |
| **Inflation** | CPI (CPIAUCSL), Core CPI (CPILFESL), PCE (PCEPI), Core PCE (PCEPILFE), PPI (PPIACO) |
| **Labor Market** | Unemployment (UNRATE), Nonfarm Payrolls (PAYEMS), LFPR (CIVPART), Avg Hourly Earnings |
| **Sentiment** | UMich Consumer Sentiment (UMCSENT) |
| **Monetary Policy** | Fed Funds Rate (FEDFUNDS), 10Y Treasury (GS10), Yield Curve (T10Y2Y) |
| **Financial Conditions** | S&P 500 (SP500), BAA Spread (BAA10Y), Consumer Credit (TOTALSL) |
| **International Trade** | Trade Balance (NETEXP), Exports (EXPGS), Imports (IMPGS) |
| **Housing** | Housing Starts (HOUST), New Home Sales (NHSLTOT), Case-Shiller (CSUSHPINSA) |

## Quick Start

### 1. Get a FRED API Key (free)
Register at https://fred.stlouisfed.org/docs/api/api_key.html

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
cp .env.example .env
# Edit .env and add your FRED_API_KEY
export FRED_API_KEY=your_key_here
```

### 4. Run the server
```bash
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

### 5. (Optional) Prefetch and inspect data from the CLI
```bash
# Fetch all series
python manage.py fetch_fred

# Fetch specific series
python manage.py fetch_fred --series GDPC1 UNRATE FEDFUNDS

# Filter by category
python manage.py fetch_fred --category "Inflation"

# Force fresh fetch (bypass cache)
python manage.py fetch_fred --no-cache
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard UI |
| `GET /api/summary/` | Latest value + YoY change for all series |
| `GET /api/series/<SERIES_ID>/` | Full observation history for one series |
| `GET /api/category/<CATEGORY>/` | All series in a category |
| `GET /api/health/` | Health check |

Add `?refresh=true` to any API endpoint to bypass the 4-hour cache.

## Caching

Data is cached in Django's default (in-memory) cache for **4 hours** per series to avoid hammering the FRED API. To switch to Redis or another backend, update `CACHES` in `settings.py`.

## Project Structure

```
macro_dashboard/        Django project config
fred_data/
  fred_config.py        All series definitions and metadata
  fred_service.py       FRED API fetching, caching, transformation
  views.py              Dashboard + JSON API views
  urls.py               URL routing
  management/commands/  CLI commands (fetch_fred)
templates/
  fred_data/
    dashboard.html      Single-page dashboard UI
requirements.txt
.env.example
```
# FRED
