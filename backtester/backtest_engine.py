from dataclasses import dataclass
import pandas as pd

@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    position_type: str = "fixed_shares"   # 'fixed_shares' or 'pct_equity'
    position_value: float = 100           # shares if fixed_shares, fraction (0..1) if pct_equity
    commission_per_trade: float = 0.0     # fixed commission per trade
    slippage_pct: float = 0.0             # percent price slippage (0.001 = 0.1%)
    fill_price: str = "close"             # 'close' or 'next_open'

class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.c = config

    # --- helper: always return a 1-D float Series ---
    @staticmethod
    def _as_series(obj: pd.Series | pd.DataFrame, name: str) -> pd.Series:
        if isinstance(obj, pd.DataFrame):
            s = obj.iloc[:, 0]                     # take the first column if 2-D
        else:
            s = obj
        s = pd.to_numeric(s, errors="coerce").astype(float)
        s.name = name
        return s

    def _fill_price_series(self, df: pd.DataFrame) -> pd.Series:
        if self.c.fill_price == "close" or "Open" not in df.columns:
            return self._as_series(df["Close"], "exec_price")

        pe = df["Open"].shift(-1)
        # last row fallback to same day's close
        last_close = df["Close"]
        if isinstance(last_close, pd.DataFrame):
            last_close = last_close.iloc[:, 0]
        pe.iloc[-1] = pd.to_numeric(last_close, errors="coerce").iloc[-1]
        return self._as_series(pe, "exec_price")

    def run(self, signals: pd.DataFrame) -> pd.DataFrame:
        df = signals.copy()
        if "signal" not in df.columns or "positions" not in df.columns:
            raise ValueError("signals DataFrame must contain 'signal' and 'positions' columns.")

        price_exec  = self._fill_price_series(df)
        price_close = self._as_series(df["Close"], "close_price")

        cash = float(self.c.initial_capital)
        shares = 0
        equity_list, cash_list, shares_list = [], [], []
        trades = []

        for i, (ts, row) in enumerate(df.iterrows()):
            pos_change = int(row["positions"])          # +1 buy, -1 sell, 0 hold
            sig = int(row["signal"])
            px  = float(price_exec.iloc[i])
            px_buy  = px * (1 + self.c.slippage_pct)
            px_sell = px * (1 - self.c.slippage_pct)

            # enter
            if pos_change > 0 and sig == 1:
                if self.c.position_type == "fixed_shares":
                    target_shares = int(self.c.position_value)
                else:
                    target_value  = cash * float(self.c.position_value)
                    target_shares = int(target_value // px_buy)
                if target_shares > 0:
                    cost = target_shares * px_buy + self.c.commission_per_trade
                    if cost <= cash:
                        cash -= cost
                        shares += target_shares
                        trades.append({"time": ts, "action": "BUY", "shares": target_shares, "price": px_buy, "cash": cash})

            # exit
            elif pos_change < 0 and sig == 0 and shares > 0:
                proceeds = shares * px_sell - self.c.commission_per_trade
                cash += proceeds
                trades.append({"time": ts, "action": "SELL", "shares": shares, "price": px_sell, "cash": cash})
                shares = 0

            equity_list.append(cash + shares * float(price_close.iloc[i]))
            cash_list.append(cash)
            shares_list.append(shares)

        out = pd.DataFrame(index=df.index)
        out["cash"]     = cash_list
        out["shares"]   = shares_list
        out["holdings"] = out["shares"].astype(float) * price_close
        out["total"]    = equity_list
        out["returns"]  = out["total"].pct_change().fillna(0)
        out["drawdown"] = (out["total"] / out["total"].cummax() - 1.0).fillna(0)

        self.trades_ = pd.DataFrame(trades) if trades else pd.DataFrame(columns=["time","action","shares","price","cash"])
        return out
