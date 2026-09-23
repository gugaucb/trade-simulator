from dataclasses import dataclass
from typing import Any
import math
import numpy as np
import pandas as pd

from .indicators import enrich, latest_context
from .strategies import Strategy

@dataclass
class BacktestConfig:
    initial_cash: float = 10000.0
    fee_rate: float = 0.001          # 0.1% Binance spot fee
    slippage_rate: float = 0.0005    # 0.05% estimated slippage
    position_size_pct: float = 1.0   # 100% of available cash per entry
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None

def calculate_metrics(equity_curve: list[float], trades: list[dict[str, Any]], initial_cash: float, candle_interval_seconds: int = 3600) -> dict[str, Any]:
    if not equity_curve:
        return {}

    final_equity = equity_curve[-1]
    total_return_pct = ((final_equity - initial_cash) / initial_cash) * 100.0

    # Drawdown series
    drawdowns = []
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
        drawdowns.append(round(dd, 3))
        if dd > max_dd:
            max_dd = dd

    # Returns series for Sharpe / Sortino
    eq_arr = np.array(equity_curve, dtype=float)
    if len(eq_arr) > 1 and eq_arr[0] > 0:
        returns = np.diff(eq_arr) / eq_arr[:-1]
        mean_ret = float(np.mean(returns))
        std_ret = float(np.std(returns))

        # Periods per year
        seconds_in_year = 365.25 * 24 * 3600
        periods_per_year = seconds_in_year / max(candle_interval_seconds, 60)
        ann_factor = math.sqrt(periods_per_year)

        # CAGR
        total_periods = len(eq_arr)
        years = total_periods / periods_per_year
        if years > 0 and final_equity > 0:
            cagr_pct = (((final_equity / initial_cash) ** (1.0 / years)) - 1.0) * 100.0
        else:
            cagr_pct = total_return_pct

        # Sharpe
        sharpe_ratio = round((mean_ret / (std_ret + 1e-9)) * ann_factor, 2)

        # Sortino
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = float(np.std(downside_returns))
            sortino_ratio = round((mean_ret / (downside_std + 1e-9)) * ann_factor, 2)
        else:
            sortino_ratio = sharpe_ratio * 1.5 if sharpe_ratio > 0 else 0.0
    else:
        cagr_pct = total_return_pct
        sharpe_ratio = 0.0
        sortino_ratio = 0.0

    # Trade statistics
    closed_trades = [t for t in trades if "pnl" in t]
    total_trades = len(closed_trades)
    winning = [t for t in closed_trades if t["pnl"] > 0]
    losing = [t for t in closed_trades if t["pnl"] < 0]

    win_rate_pct = round((len(winning) / total_trades * 100.0), 2) if total_trades > 0 else 0.0
    gross_profit = sum(t["pnl"] for t in winning)
    gross_loss = abs(sum(t["pnl"] for t in losing))

    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        profit_factor = round(gross_profit, 2)
    else:
        profit_factor = 1.0

    avg_trade_pnl = round(sum(t["pnl"] for t in closed_trades) / total_trades, 2) if total_trades > 0 else 0.0

    return {
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "drawdowns": drawdowns,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "avg_trade_pnl": avg_trade_pnl,
    }

class BacktestEngine:
    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run_single(
        self,
        strategy: Strategy,
        candles: list[dict[str, Any]],
        laya_decisions: dict[int, dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if not candles:
            return {"strategy_id": strategy.id, "equity_curve": [], "trades": [], "metrics": {}}

        df = enrich(pd.DataFrame(candles))
        cash = self.config.initial_cash
        quantity = 0.0
        entry_price = 0.0
        trades: list[dict[str, Any]] = []
        equity_curve: list[float] = []
        timestamps: list[int] = []

        total_fee_cost = self.config.fee_rate + self.config.slippage_rate

        for i in range(len(df)):
            candle = candles[i]
            ts = int(candle["time"])
            timestamps.append(ts)
            current_close = float(candle["close"])

            # Indicators context for this candle
            sub_df = df.iloc[:i+1]
            ctx = latest_context(sub_df)
            laya_decision = laya_decisions.get(ts) if laya_decisions else None

            # Check stop loss / take profit if currently holding position
            triggered_exit = None
            if quantity > 0 and entry_price > 0:
                change_pct = (current_close - entry_price) / entry_price
                if self.config.stop_loss_pct is not None and change_pct <= -abs(self.config.stop_loss_pct):
                    triggered_exit = "STOP_LOSS"
                elif self.config.take_profit_pct is not None and change_pct >= abs(self.config.take_profit_pct):
                    triggered_exit = "TAKE_PROFIT"

            # Strategy decision
            if triggered_exit:
                signal = "SELL"
            else:
                signal = strategy.on_candle(candle, ctx, laya_decision, position_qty=quantity)

            # Order Execution Simulation
            if signal == "BUY" and cash > 10.0 and quantity <= 1e-12:
                alloc_cash = cash * self.config.position_size_pct
                exec_price = current_close * (1.0 + self.config.slippage_rate)
                fee = alloc_cash * self.config.fee_rate
                net_cash = alloc_cash - fee
                quantity = net_cash / exec_price
                cash -= alloc_cash
                entry_price = exec_price
                trades.append({
                    "time": ts,
                    "side": "BUY",
                    "price": round(exec_price, 2),
                    "quantity": round(quantity, 6),
                    "fee": round(fee, 2),
                    "reason": triggered_exit or signal
                })

            elif signal == "SELL" and quantity > 0:
                exec_price = current_close * (1.0 - self.config.slippage_rate)
                gross_proceeds = quantity * exec_price
                fee = gross_proceeds * self.config.fee_rate
                net_proceeds = gross_proceeds - fee
                cash += net_proceeds
                
                # Trade PnL
                invested = quantity * entry_price
                trade_pnl = net_proceeds - invested
                ret_pct = ((exec_price - entry_price) / entry_price) * 100.0

                trades.append({
                    "time": ts,
                    "side": "SELL",
                    "price": round(exec_price, 2),
                    "quantity": round(quantity, 6),
                    "fee": round(fee, 2),
                    "pnl": round(trade_pnl, 2),
                    "return_pct": round(ret_pct, 2),
                    "reason": triggered_exit or "STRATEGY_EXIT"
                })
                quantity = 0.0
                entry_price = 0.0

            # Mark to market equity at candle close
            current_portfolio_value = cash + (quantity * current_close)
            equity_curve.append(round(current_portfolio_value, 2))

        # Interval calculation for Sharpe/CAGR
        interval_seconds = 3600
        if len(timestamps) > 1:
            interval_seconds = max(timestamps[1] - timestamps[0], 60)

        metrics = calculate_metrics(equity_curve, trades, self.config.initial_cash, interval_seconds)

        return {
            "strategy_id": strategy.id,
            "strategy_name": strategy.name,
            "equity_curve": equity_curve,
            "timestamps": timestamps,
            "trades": trades,
            "metrics": metrics,
        }

    def run_comparison(
        self,
        strategies: list[Strategy],
        candles: list[dict[str, Any]],
        laya_decisions: dict[int, dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        results = []
        summary = []
        timestamps = [int(c["time"]) for c in candles]

        for strat in strategies:
            res = self.run_single(strat, candles, laya_decisions)
            results.append(res)
            m = res["metrics"]
            summary.append({
                "strategy_id": strat.id,
                "strategy_name": strat.name,
                "total_return_pct": m.get("total_return_pct", 0.0),
                "max_drawdown_pct": m.get("max_drawdown_pct", 0.0),
                "sharpe_ratio": m.get("sharpe_ratio", 0.0),
                "sortino_ratio": m.get("sortino_ratio", 0.0),
                "win_rate_pct": m.get("win_rate_pct", 0.0),
                "profit_factor": m.get("profit_factor", 1.0),
                "total_trades": m.get("total_trades", 0),
                "final_equity": m.get("final_equity", self.config.initial_cash),
            })

        # Rank strategies by total return
        summary.sort(key=lambda s: s["total_return_pct"], reverse=True)

        return {
            "timestamps": timestamps,
            "summary": summary,
            "results": results
        }
