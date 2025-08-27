
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

TRADING_DAYS = 252

def annualized_return(total_series: pd.Series) -> float:
    if len(total_series) < 2:
        return 0.0
    start_val = total_series.iloc[0]
    end_val = total_series.iloc[-1]
    days = (total_series.index[-1] - total_series.index[0]).days or 1
    years = days / 365.25
    return (end_val / start_val) ** (1/years) - 1 if start_val > 0 else 0.0

def sharpe_ratio(returns: pd.Series, rf: float = 0.0) -> float:
    if returns.std() == 0:
        return 0.0
    return (returns.mean() - rf/TRADING_DAYS) / returns.std() * np.sqrt(TRADING_DAYS)

def sortino_ratio(returns: pd.Series, rf: float = 0.0) -> float:
    downside = returns.where(returns < 0, 0)
    denom = downside.std()
    if denom == 0:
        return 0.0
    return (returns.mean() - rf/TRADING_DAYS) / denom * np.sqrt(TRADING_DAYS)

def max_drawdown(drawdown: pd.Series) -> float:
    return drawdown.min() if not drawdown.empty else 0.0

def trade_stats(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {"trades": 0, "win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0}
    # Assume alternating BUY then SELL; compute PnL per round-trip
    pnl = []
    buys = trades[trades["action"] == "BUY"]
    sells = trades[trades["action"] == "SELL"]
    for i in range(min(len(buys), len(sells))):
        b = buys.iloc[i]
        s = sells.iloc[i]
        pnl.append((s["price"] - b["price"]) * s["shares"])
    pnl = pd.Series(pnl) if pnl else pd.Series(dtype=float)
    wins = (pnl > 0).sum()
    losses = (pnl < 0).sum()
    return {
        "trades": int(len(pnl)),
        "win_rate": float(wins / len(pnl)) if len(pnl) else 0.0,
        "avg_win": float(pnl[pnl > 0].mean()) if wins else 0.0,
        "avg_loss": float(pnl[pnl < 0].mean()) if losses else 0.0,
    }

def plot_price_and_signals(df: pd.DataFrame, signals: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df["Close"], label="Close")
    if "sma_short" in signals.columns:
        ax.plot(signals.index, signals["sma_short"], label="SMA Short")
    if "sma_long" in signals.columns:
        ax.plot(signals.index, signals["sma_long"], label="SMA Long")
    if "bb_upper" in signals.columns:
        ax.plot(signals.index, signals["bb_upper"], label="BB Upper")
        ax.plot(signals.index, signals["bb_mid"], label="BB Mid")
        ax.plot(signals.index, signals["bb_lower"], label="BB Lower")
    # Mark trades
    buys = signals[signals["positions"] > 0]
    sells = signals[signals["positions"] < 0]
    ax.scatter(buys.index, df.loc[buys.index, "Close"], marker="^", s=70, label="Buy")
    ax.scatter(sells.index, df.loc[sells.index, "Close"], marker="v", s=70, label="Sell")
    ax.legend()
    ax.set_title("Price and Signals")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    return fig

def plot_equity_curve(portfolio: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(portfolio.index, portfolio["total"], label="Equity")
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Account Value")
    ax.legend()
    return fig

def plot_drawdown(portfolio: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 2.5))
    ax.fill_between(portfolio.index, portfolio["drawdown"], 0.0, step=None)
    ax.set_title("Drawdown")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    return fig

def summarize(portfolio: pd.DataFrame, trades_df: pd.DataFrame) -> dict:
    total_ret = portfolio["total"].iloc[-1] / portfolio["total"].iloc[0] - 1 if len(portfolio) > 1 else 0.0
    ann_ret = annualized_return(portfolio["total"])
    max_dd = max_drawdown(portfolio["drawdown"])
    sr = sharpe_ratio(portfolio["returns"])
    sor = sortino_ratio(portfolio["returns"])
    tstats = trade_stats(trades_df)
    result = {
        "Total Return": total_ret,
        "Annualized Return": ann_ret,
        "Max Drawdown": max_dd,
        "Sharpe Ratio": sr,
        "Sortino Ratio": sor,
        "Trades": tstats["trades"],
        "Win Rate": tstats["win_rate"],
        "Average Win $": tstats["avg_win"],
        "Average Loss $": tstats["avg_loss"],
    }
    return result
