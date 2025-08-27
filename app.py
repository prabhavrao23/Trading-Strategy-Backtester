import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

from backtester.data_loader import DataLoader
from backtester.strategy import (
    MovingAverageCrossStrategy,
    RSIStrategy,
    BollingerMeanReversionStrategy,
)
from backtester.backtest_engine import BacktestEngine, BacktestConfig
from backtester.performance import (
    plot_price_and_signals,
    plot_equity_curve,
    plot_drawdown,
    summarize,
)

st.set_page_config(page_title="Trading Strategy Backtester", layout="wide")
st.title("📈 Trading Strategy Backtester")

# Quick guide on home screen
st.markdown(
    """
**Quick guide**

1. Pick a data source in the sidebar. Upload a CSV or use Alpha Vantage or Yahoo Finance.
2. If using Alpha Vantage, paste your API key and enter a symbol, then click Fetch Data.
3. Choose a strategy and set parameters.
4. Set backtest options like capital and position sizing.
5. Click Run Backtest to see charts, metrics, final value, and total profit.
6. Use the download buttons to save results.
"""
)

# Session state for data
if "df" not in st.session_state:
    st.session_state.df = None

def set_df(df: pd.DataFrame | None):
    st.session_state.df = df

# Sidebar: data source
st.sidebar.header("Data")
source = st.sidebar.radio("Source", ["CSV Upload", "Alpha Vantage API", "Yahoo Finance"])

loader = DataLoader()
df = st.session_state.df

if source == "CSV Upload":
    f = st.sidebar.file_uploader("Upload CSV with Date, Open, High, Low, Close, Volume", type=["csv"])
    if f is not None:
        try:
            tmp = pd.read_csv(f, parse_dates=["Date"]).set_index("Date").sort_index()
            set_df(tmp)
            st.success(f"Loaded {len(tmp)} rows from CSV.")
        except Exception as e:
            st.error(f"CSV error: {e}")

elif source == "Alpha Vantage API":
    api_key = st.sidebar.text_input("Alpha Vantage API Key", type="password", help="Not stored.")
    symbol = st.sidebar.text_input("Symbol", value="AAPL")
    adjusted = st.sidebar.checkbox("Use adjusted endpoint", value=False, help="May require premium")
    if st.sidebar.button("Fetch Data"):
        try:
            loader = DataLoader(api_key=api_key)
            tmp = loader.load_from_alpha_vantage(symbol, adjusted=adjusted)
            set_df(tmp)
            st.success(f"Fetched {len(tmp)} rows for {symbol} from Alpha Vantage.")
        except Exception as e:
            st.error(str(e))

else:  # Yahoo Finance
    y_symbol = st.sidebar.text_input("Symbol", value="AAPL")
    col = st.sidebar.columns(2)
    with col[0]:
        y_start = st.text_input("Start (YYYY-MM-DD)", value="")
    with col[1]:
        y_end = st.text_input("End (YYYY-MM-DD)", value="")
    if st.sidebar.button("Fetch Data"):
        try:
            tmp = loader.load_from_yahoo(y_symbol, start=(y_start or None), end=(y_end or None))
            set_df(tmp)
            st.success(f"Fetched {len(tmp)} rows for {y_symbol} from Yahoo Finance.")
        except Exception as e:
            st.error(str(e))

# Optional: clear data
if st.sidebar.button("Clear Data"):
    set_df(None)
    df = None

# Date filter
if st.session_state.df is not None and not st.session_state.df.empty:
    full = st.session_state.df
    min_d, max_d = full.index.min(), full.index.max()
    start, end = st.sidebar.date_input(
        "Date Range",
        value=[min_d, max_d],
        min_value=min_d,
        max_value=max_d,
    )
    start, end = pd.to_datetime(str(start)), pd.to_datetime(str(end))
    df = full.loc[start:end]
    st.write(f"Loaded **{len(df)}** rows from **{start.date()}** to **{end.date()}**.")
else:
    st.info("Load data to start. You can also run the CLI: `python main.py`.")

# Strategy
st.sidebar.header("Strategy")
strategy_name = st.sidebar.selectbox(
    "Select Strategy",
    ["SMA Crossover", "RSI Mean-Reversion", "Bollinger Mean-Reversion"],
)

if strategy_name == "SMA Crossover":
    short = st.sidebar.number_input("Short Window", min_value=2, max_value=250, value=20, step=1)
    long = st.sidebar.number_input("Long Window", min_value=3, max_value=400, value=50, step=1)
elif strategy_name == "RSI Mean-Reversion":
    period = st.sidebar.number_input("RSI Period", min_value=2, max_value=100, value=14, step=1)
    oversold = st.sidebar.number_input("Oversold", min_value=1, max_value=50, value=30, step=1)
    overbought = st.sidebar.number_input("Overbought", min_value=50, max_value=99, value=70, step=1)
else:
    bb_window = st.sidebar.number_input("BB Window", min_value=5, max_value=200, value=20, step=1)
    bb_std = st.sidebar.number_input("BB Std Dev", min_value=1.0, max_value=4.0, value=2.0, step=0.1)

# Backtest config
st.sidebar.header("Backtest")
initial_capital = st.sidebar.number_input("Initial Capital", min_value=1000.0, value=10000.0, step=500.0)
position_type = st.sidebar.selectbox("Position Sizing", ["fixed_shares", "pct_equity"])
if position_type == "fixed_shares":
    position_value = st.sidebar.number_input("Shares per Entry", min_value=1, value=100, step=1)
else:
    position_value = st.sidebar.number_input("Fraction of Cash per Entry", min_value=0.01, max_value=1.0, value=0.5, step=0.01)
commission = st.sidebar.number_input("Commission per Trade ($)", min_value=0.0, value=0.0, step=0.1)
slippage_pct = st.sidebar.number_input("Slippage (%)", min_value=0.0, max_value=5.0, value=0.0, step=0.05) / 100.0
fill_price = st.sidebar.selectbox("Execution Price", ["close", "next_open"])

run_bt = st.sidebar.button("Run Backtest")

# Run
if run_bt:
    if df is None or df.empty:
        st.warning("No data loaded. Fetch data or upload a CSV first.")
    else:
        if strategy_name == "SMA Crossover":
            strat = MovingAverageCrossStrategy(short_window=short, long_window=long)
        elif strategy_name == "RSI Mean-Reversion":
            strat = RSIStrategy(period=period, oversold=oversold, overbought=overbought)
        else:
            strat = BollingerMeanReversionStrategy(window=bb_window, num_std=bb_std)

        signals = strat.generate_signals(df).data

        cfg = BacktestConfig(
            initial_capital=float(initial_capital),
            position_type=position_type,
            position_value=float(position_value),
            commission_per_trade=float(commission),
            slippage_pct=float(slippage_pct),
            fill_price=fill_price,
        )
        engine = BacktestEngine(cfg)
        portfolio = engine.run(signals)

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.pyplot(plot_price_and_signals(df, signals))
        with col2:
            st.pyplot(plot_equity_curve(portfolio))
            st.pyplot(plot_drawdown(portfolio))

        # Metrics
        st.subheader("Performance Summary")
        summary = summarize(portfolio, getattr(engine, "trades_", None))

        # Final value and profit in dollars
        final_value = float(portfolio["total"].iloc[-1])
        profit = final_value - float(initial_capital)

        grid = pd.DataFrame({
            "Metric": [
                "Total Return",
                "Annualized Return",
                "Max Drawdown",
                "Sharpe Ratio",
                "Sortino Ratio",
                "Final Value",
                "Total Profit",
                "Trades",
                "Win Rate",
                "Average Win $",
                "Average Loss $",
            ],
            "Value": [
                f"{summary['Total Return']:.2%}",
                f"{summary['Annualized Return']:.2%}",
                f"{summary['Max Drawdown']:.2%}",
                f"{summary['Sharpe Ratio']:.2f}",
                f"{summary['Sortino Ratio']:.2f}",
                f"${final_value:,.2f}",
                f"${profit:,.2f}",
                f"{summary['Trades']}",
                f"{summary['Win Rate']:.2%}",
                f"${summary['Average Win $']:.2f}",
                f"${summary['Average Loss $']:.2f}",
            ],
        })
        st.dataframe(grid, use_container_width=True)

        # Downloads
        st.download_button("Download Signals CSV", data=signals.to_csv().encode("utf-8"), file_name="signals.csv")
        st.download_button("Download Portfolio CSV", data=portfolio.to_csv().encode("utf-8"), file_name="portfolio.csv")
        if getattr(engine, "trades_", None) is not None and not engine.trades_.empty:
            st.download_button("Download Trades CSV", data=engine.trades_.to_csv(index=False).encode("utf-8"), file_name="trades.csv")
else:
    st.caption("Configure parameters in the sidebar and click Run Backtest.")
