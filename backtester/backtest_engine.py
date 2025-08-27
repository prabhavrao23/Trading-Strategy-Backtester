
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    position_type: str = "fixed_shares"  # 'fixed_shares' or 'pct_equity'
    position_value: float = 100  # shares if fixed_shares, fraction (0..1) if pct_equity
    commission_per_trade: float = 0.0    # fixed commission per trade
    slippage_pct: float = 0.0            # percent price slippage (0.001 = 0.1%)
    fill_price: str = "close"            # 'close' or 'next_open'

class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.c = config

    def _fill_price_series(self, df: pd.DataFrame) -> pd.Series:
        if self.c.fill_price == "close" or "Open" not in df.columns:
            return df["Close"]
        # next_open uses next day's open; last day falls back to same day's close
        price = df["Open"].shift(-1)
        price.iloc[-1] = df["Close"].iloc[-1]
        return price

    def run(self, signals: pd.DataFrame) -> pd.DataFrame:
        df = signals.copy()
        if "signal" not in df.columns or "positions" not in df.columns:
            raise ValueError("signals DataFrame must contain 'signal' and 'positions' columns.")
        price_exec = self._fill_price_series(df)
        price_close = df["Close"]

        cash = self.c.initial_capital
        shares = 0
        equity_list = []
        cash_list = []
        shares_list = []
        trades = []

        for i, (ts, row) in enumerate(df.iterrows()):
            pos_change = int(row["positions"])  # +1 buy, -1 sell, 0 hold
            px = float(price_exec.iloc[i])
            px_with_slip_buy = px * (1 + self.c.slippage_pct)
            px_with_slip_sell = px * (1 - self.c.slippage_pct)

            # Execute trades at execution price
            if pos_change > 0 and int(row["signal"]) == 1:
                # entering long
                if self.c.position_type == "fixed_shares":
                    target_shares = int(self.c.position_value)
                else:  # pct_equity
                    target_value = cash * float(self.c.position_value)
                    target_shares = int(target_value // px_with_slip_buy)
                if target_shares > 0:
                    cost = target_shares * px_with_slip_buy + self.c.commission_per_trade
                    if cost <= cash:
                        cash -= cost
                        shares += target_shares
                        trades.append({"time": ts, "action": "BUY", "shares": target_shares, "price": px_with_slip_buy, "cash": cash})
            elif pos_change < 0 and int(row["signal"]) == 0:
                # exiting long
                if shares > 0:
                    proceeds = shares * px_with_slip_sell - self.c.commission_per_trade
                    cash += proceeds
                    trades.append({"time": ts, "action": "SELL", "shares": shares, "price": px_with_slip_sell, "cash": cash})
                    shares = 0

            # Mark-to-market end-of-day using close price
            equity = cash + shares * float(price_close.iloc[i])
            equity_list.append(equity)
            cash_list.append(cash)
            shares_list.append(shares)

        out = pd.DataFrame(index=df.index)
        out["cash"] = cash_list
        out["shares"] = shares_list
        out["holdings"] = out["shares"] * price_close
        out["total"] = equity_list
        out["returns"] = out["total"].pct_change().fillna(0)
        out["drawdown"] = (out["total"] / out["total"].cummax() - 1.0).fillna(0)

        self.trades_ = pd.DataFrame(trades) if trades else pd.DataFrame(columns=["time","action","shares","price","cash"])
        return out
