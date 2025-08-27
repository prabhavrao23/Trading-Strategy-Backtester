
from dataclasses import dataclass
import pandas as pd
from .indicators import sma, rsi, bollinger_bands

@dataclass
class StrategyResult:
    data: pd.DataFrame  # includes 'signal' 0/1 and any indicator columns

class BaseStrategy:
    name: str = "Base"

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        raise NotImplementedError

class MovingAverageCrossStrategy(BaseStrategy):
    name = "SMA Crossover"
    def __init__(self, short_window: int = 20, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        df = data.copy()
        df["sma_short"] = sma(df["Close"], self.short_window)
        df["sma_long"] = sma(df["Close"], self.long_window)
        df["signal"] = 0
        df.loc[df.index[self.long_window-1]:, "signal"] = (df["sma_short"][self.long_window-1:] > df["sma_long"][self.long_window-1:]).astype(int)
        df["positions"] = df["signal"].diff().fillna(0)
        return StrategyResult(df)

class RSIStrategy(BaseStrategy):
    name = "RSI Mean-Reversion"
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        df = data.copy()
        df["rsi"] = rsi(df["Close"], self.period)
        df["signal"] = 0
        # Long when RSI < oversold; flat when RSI > overbought
        df.loc[df["rsi"] < self.oversold, "signal"] = 1
        df.loc[df["rsi"] > self.overbought, "signal"] = 0
        df["signal"] = df["signal"].ffill().fillna(0).astype(int)
        df["positions"] = df["signal"].diff().fillna(0)
        return StrategyResult(df)

class BollingerMeanReversionStrategy(BaseStrategy):
    name = "Bollinger Mean-Reversion"
    def __init__(self, window: int = 20, num_std: float = 2.0):
        self.window = window
        self.num_std = num_std

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        df = data.copy()
        mid, upper, lower = bollinger_bands(df["Close"], self.window, self.num_std)
        df["bb_mid"] = mid
        df["bb_upper"] = upper
        df["bb_lower"] = lower
        df["signal"] = 0
        # Enter long when price closes below lower band; exit when back above mid
        df.loc[df["Close"] < df["bb_lower"], "signal"] = 1
        df.loc[df["Close"] > df["bb_mid"], "signal"] = 0
        df["signal"] = df["signal"].ffill().fillna(0).astype(int)
        df["positions"] = df["signal"].diff().fillna(0)
        return StrategyResult(df)
