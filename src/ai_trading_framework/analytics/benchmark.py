from __future__ import annotations

from ai_trading_framework.models import Recommendation, StrategyBenchmark


class BenchmarkService:
    def compare(self, recommendations: list[Recommendation]) -> list[StrategyBenchmark]:
        by_strategy: dict[str, list[Recommendation]] = {}
        for recommendation in recommendations:
            by_strategy.setdefault(recommendation.strategy_name, []).append(recommendation)
        benchmarks: list[StrategyBenchmark] = []
        for strategy_name, items in by_strategy.items():
            avg_conf = sum(item.confidence for item in items) / max(len(items), 1)
            benchmarks.append(
                StrategyBenchmark(
                    strategy_name=strategy_name,
                    sharpe_ratio=round(avg_conf * 1.6, 2),
                    win_rate=round(min(max(avg_conf, 0.0), 1.0), 2),
                    max_drawdown=round(0.08 + (1 - avg_conf) * 0.12, 2),
                    approval_rate=round(avg_conf, 2),
                    execution_slippage_bps=round((1 - avg_conf) * 12, 2),
                )
            )
        return benchmarks
