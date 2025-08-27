
# Trading Strategy Backtester

A Python backtesting tool with a **Streamlit UI** to validate trading strategies on historical data.  
Built with **Pandas** for data handling, **Matplotlib** for charts, and **Alpha Vantage** for optional data fetching.

## ✨ Features
- Load data from **CSV** or **Alpha Vantage API**.
- Strategies included:
  - **SMA Crossover** (trend following)
  - **RSI Mean-Reversion**
  - **Bollinger Mean-Reversion**
- Backtest options:
  - Position sizing: **fixed shares** or **% of cash**
  - **Commission ($)** per trade and **slippage (%)**
  - Execution at **close** or **next open**
- Metrics: total return, annualized return (CAGR), max drawdown, Sharpe, Sortino, trade stats.
- Plots: price + signals, equity curve, drawdown.
- One-click CSV downloads for signals, portfolio, and trades.

## 📦 Project Structure
```
trading-backtester/
├── app.py                     # Streamlit UI (localhost app)
├── main.py                    # CLI example (no UI)
├── backtester/
│   ├── __init__.py
│   ├── data_loader.py         # CSV + Alpha Vantage loader
│   ├── indicators.py          # SMA, RSI, Bollinger
│   ├── strategy.py            # Strategy classes
│   ├── backtest_engine.py     # Engine w/ sizing, costs, slippage
│   └── performance.py         # Metrics and plots
├── data/
│   └── sample_data.csv        # Synthetic sample OHLCV
├── requirements.txt
└── README.md
```

## 🚀 Quick Start (UI on localhost)

1. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the UI**:
   ```bash
   streamlit run app.py
   ```
   Streamlit will open in your browser at **http://localhost:8501**.

4. **Load data**:
   - Upload a CSV with columns: `Date, Open, High, Low, Close, Volume` (Adj Close optional), or
   - Enter your **Alpha Vantage** API key and a symbol, then click **Fetch Data**.

### CSV Format
- Required: `Date` column (any ISO-like format), and at least `Close`.  
- Recommended: `Open, High, Low, Close, Volume`.  
- Example file is provided at `data/sample_data.csv` (synthetic).

## 🧪 CLI Example (no UI)
Run a quick backtest from the terminal:
```bash
python main.py
```

## ⚙️ Configuration Notes
- **Position sizing**:
  - `fixed_shares`: buy this many shares on each buy signal.
  - `pct_equity`: allocate a fraction of *current cash* at each entry.
- **Costs & slippage**:
  - Commission is a fixed dollar cost **per trade**.
  - Slippage is a percentage applied to the execution price.
- **Execution**:
  - `close`: uses same-day close for fills.
  - `next_open`: uses next day's open (falls back to close for the last row).

## 📈 Strategy Ideas To Add Next
- Momentum, MACD, SMA-EMA cross, multi-asset, short-selling, stop-loss/take-profit, walk-forward validation.

## 🔑 Alpha Vantage Setup (Optional)
1. Get a free key from Alpha Vantage.
2. Enter it in the Streamlit sidebar when selecting **Alpha Vantage**.
   - Or set an env var: `export ALPHAVANTAGE_API_KEY=your_key`

## ✅ Requirements
- Python 3.10+
- See `requirements.txt` for exact versions.

## 📝 License
MIT
