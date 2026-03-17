# Frontend Documentation

## Overview

The frontend is a single static HTML page (`frontend/index.html`) with no build step or framework. It communicates with the FastAPI backend via `fetch()` calls.

**Dependencies (loaded from CDN):**
- [Plotly.js](https://plotly.com/javascript/) — interactive charts
- [html2canvas](https://html2canvas.hertzen.com/) — screenshot for PDF export
- [jsPDF](https://github.com/parallax/jsPDF) — PDF generation

---

## Layout

```
Header (title, authors, dark mode, Model Info, User Guide)
  │
  ├── Model Info Panel (collapsible)
  ├── User Guide Panel (collapsible)
  │
  ├── Tabs
  │     ├── CSV Upload tab
  │     └── Manual Input tab
  │
  ├── Status Bar (signal + regime + VIX + confidence)
  ├── Transition Warning banner
  ├── Confidence Warning banner
  ├── Spinner
  ├── Summary Stats cards
  ├── Regime Legend pills
  ├── Price Chart (Plotly)
  ├── VIX Chart (Plotly)
  ├── Export Bar (Download CSV, Export PDF)
  ├── Chart Interpretation panel
  └── Training Analysis Plots (collapsible grid)
```

---

## CSV Upload Tab

1. Select your processed CSV file
2. Set "Days to display" (default 250, range 30–2000)
3. Click **Analyze Market Data**

The backend processes the file and returns:
- Current signal + confidence
- Summary stats (total rows, date range, % safe/risk, longest risk streak)
- Chart data for the last N trading days

**Reset button** clears the file input, charts, and all output panels.

---

## Manual Input Tab

Enter values for all 5 features and click **Check Market Signal**.

**Load Default Values** fills in typical calm market conditions:

| Field | Default | Represents |
|-------|---------|------------|
| Returns | 0.0012 | Slight positive day |
| Volatility | 0.0085 | Low volatility |
| RSI | 58.4 | Mildly bullish |
| Momentum | 0.032 | Slight uptrend |
| VIX | 16.5 | Calm market |

**Keyboard shortcut:** Press `Enter` anywhere in the manual form to submit.

**localStorage:** Values are saved automatically on submit and restored on page refresh.

---

## What-If Explorer

Appears after the first manual form submission. Drag sliders to adjust any feature value — the signal updates automatically after a 400ms debounce (no button click needed).

Slider ranges:

| Feature | Min | Max | Step |
|---------|-----|-----|------|
| Returns | -0.15 | 0.15 | 0.001 |
| Volatility | 0 | 0.2 | 0.001 |
| RSI | 0 | 100 | 0.1 |
| Momentum | -300 | 300 | 0.1 |
| VIX | 5 | 80 | 0.1 |

The result box shows: Signal | Regime | VIX | Confidence (color-coded).

---

## Confidence Color Coding

Confidence is displayed in the status bar and What-If result with color:

| Color | Range | Meaning |
|-------|-------|---------|
| Green | ≥ 70% | High confidence — signal is reliable |
| Yellow | 40–70% | Medium confidence — signal is plausible |
| Red | < 40% | Low confidence — signal is uncertain |

An orange warning banner also appears when confidence drops below 40%.

---

## Regime Legend

Displayed after any analysis. Each pill shows:
- Regime number
- Low Risk / High Risk label
- Average VIX for that regime
- `◀ now` marker on the current regime

**Click any pill** to highlight/isolate that regime on the price chart. Click again to deselect.

---

## Charts

**Price Chart** — S&P 500 closing price for the last N days, scatter plot colored by regime. If the riskiest historical period falls within the visible window, it is shaded in red.

**VIX Chart** — VIX values for the same window, also colored by regime.

Both charts are interactive (zoom, pan, hover tooltips) via Plotly.

---

## Chart Interpretation Panel

Rendered below the VIX chart after CSV analysis. Contains:
- Regime breakdown (% of displayed days per regime)
- Current signal explanation
- VIX context description
- How-to-read note

---

## Model Info Panel

Click **Model Info** in the header. Shows:
- Number of regimes
- Covariance type
- Training date and dataset size
- Expandable section with feature means per regime (raw JSON)

---

## User Guide Panel

Click **User Guide** in the header. Shows:
- Explanation of each tab
- Description of each feature with typical values
- Reference table of value combinations that trigger each regime

Model Info and User Guide are mutually exclusive — opening one closes the other.

---

## Dark Mode

Click the 🌙 button in the header. Theme is saved in `localStorage` and persists across sessions.

---

## Export

**Download CSV with Regimes** — sends the uploaded file to `/api/download-csv` and downloads the result with `Regime` and `Regime_Label` columns appended.

**Export Report as PDF** — captures the status bar, summary stats, charts, and interpretation panel using html2canvas and generates a PDF with jsPDF.

---

## Training Analysis Plots

Loaded from `/api/figures` on page load. Displayed in a responsive grid at the bottom of the page. Click the header to collapse/expand the section. Images are lazy-loaded.
