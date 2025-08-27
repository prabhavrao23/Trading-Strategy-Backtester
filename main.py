
from backtester.data_loader import DataLoader
from backtester.strategy import MovingAverageCrossStrategy
from backtester.backtest_engine import BacktestEngine, BacktestConfig
from backtester.performance import summarize

def main():
    loader = DataLoader()
    # Replace with your path or use Alpha Vantage in app.py
    df = loader.load_from_csv("data/sample_data.csv")

    # Strategy
    strat = MovingAverageCrossStrategy(short_window=20, long_window=50)
    signals = strat.generate_signals(df).data

    # Backtest config: with commission and slippage
    cfg = BacktestConfig(initial_capital=10000.0, position_type="fixed_shares", position_value=100,
                         commission_per_trade=1.0, slippage_pct=0.001, fill_price="close")
    engine = BacktestEngine(cfg)
    portfolio = engine.run(signals)

    # Print summary
    stats = summarize(portfolio, getattr(engine, "trades_", None))
    for k, v in stats.items():
        if "Return" in k or "Drawdown" in k or "Rate" in k:
            print(f"{k}: {v:.2%}")
        elif "Ratio" in k:
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
