import os
from typing import Optional
import pandas as pd
import requests

class DataLoader:
    """Handles loading price data from CSV, Alpha Vantage, or Yahoo Finance."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")

    # -------- CSV --------
    def load_from_csv(self, file_path: str, date_col: str = "Date") -> pd.DataFrame:
        df = pd.read_csv(file_path)
        if date_col not in df.columns:
            raise ValueError(f"CSV must include a '{date_col}' column.")
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col).sort_index()

        rename_map = {
            "adj close": "Adj Close",
            "adjclose": "Adj Close",
            "close": "Close",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "volume": "Volume",
        }
        for col in list(df.columns):
            key = col.strip().lower()
            if key in rename_map:
                df.rename(columns={col: rename_map[key]}, inplace=True)

        if "Adj Close" not in df.columns and "Close" in df.columns:
            df["Adj Close"] = df["Close"]
        return df

    # -------- Alpha Vantage --------
    def load_from_alpha_vantage(
        self,
        symbol: str,
        adjusted: bool = False,
        outputsize: str = "full",
        timeout: int = 30,
    ) -> pd.DataFrame:
        if not self.api_key:
            raise ValueError("Alpha Vantage API key required. Set ALPHAVANTAGE_API_KEY or pass api_key.")

        function = "TIME_SERIES_DAILY_ADJUSTED" if adjusted else "TIME_SERIES_DAILY"
        url = "https://www.alphavantage.co/query"
        params = {
            "function": function,
            "symbol": symbol,
            "outputsize": outputsize,
            "datatype": "json",
            "apikey": self.api_key,
        }

        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        j = r.json()

        if "Error Message" in j:
            raise RuntimeError(f"Alpha Vantage error: {j['Error Message']}")
        if "Note" in j:
            raise RuntimeError(f"Alpha Vantage note: {j['Note']}")
        if "Information" in j:
            raise RuntimeError(f"Alpha Vantage info: {j['Information']}")

        key = "Time Series (Daily)"
        if key not in j:
            raise RuntimeError(f"Alpha Vantage response missing data key. Full response: {j}")

        data = pd.DataFrame(j[key]).T
        data.index = pd.to_datetime(data.index)
        data = data.sort_index()

        col_map = {}
        for c in data.columns:
            c_low = c.lower()
            if "1. open" in c_low: col_map[c] = "Open"
            elif "2. high" in c_low: col_map[c] = "High"
            elif "3. low" in c_low: col_map[c] = "Low"
            elif "4. close" in c_low: col_map[c] = "Close"
            elif "5. adjusted close" in c_low: col_map[c] = "Adj Close"
            elif "5. volume" in c_low or "6. volume" in c_low: col_map[c] = "Volume"
        data = data.rename(columns=col_map)

        for col in ["Open", "High", "Low", "Close", "Adj Close"]:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors="coerce")
        if "Volume" in data.columns:
            data["Volume"] = pd.to_numeric(data["Volume"], errors="coerce").astype("Int64")

        if "Adj Close" not in data.columns and "Close" in data.columns:
            data["Adj Close"] = data["Close"]

        ordered_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in data.columns]
        return data[ordered_cols]

    # -------- Yahoo Finance (no key) --------
    def load_from_yahoo(self, symbol: str, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        import yfinance as yf  # local import so package is optional until used
        df = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
        if df.empty:
            raise RuntimeError(f"No data returned from Yahoo for symbol '{symbol}'.")
        # yfinance returns columns already as Open, High, Low, Close, Adj Close, Volume
        df.index.name = "Date"
        return df
