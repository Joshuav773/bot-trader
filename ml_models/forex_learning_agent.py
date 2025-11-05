"""
Forex Confluence Learning Agent
Specialized agent that optimizes confluence strategy parameters specifically for major forex pairs.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import itertools

from data_ingestion.polygon_client import PolygonDataClient
from backtester.engine import run_backtest
from backtester.strategies.forex_confluence import ForexConfluenceStrategy


MAJOR_FOREX_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"
]


class ForexLearningAgent:
    """
    Learning agent that optimizes confluence strategy for forex markets.
    Tests parameter combinations across major pairs and learns optimal settings.
    """
    
    def __init__(self, api_key: str = None):
        self.client = PolygonDataClient(api_key)
        self.results_cache: Dict[str, Dict[str, Any]] = {}
    
    def optimize_pair(
        self,
        pair: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1d",
        param_ranges: Dict[str, List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize confluence parameters for a single forex pair.
        
        Returns best parameters and performance metrics.
        """
        if param_ranges is None:
            param_ranges = {
                "fast_ma": [5, 10, 15, 20],
                "slow_ma": [30, 50, 100],
                "rsi_oversold": [20, 25, 30],
                "rsi_overbought": [70, 75, 80],
                "min_confirmations": [2, 3, 4],
            }
        
        data = self.client.get_bars(pair, start_date, end_date, timeframe=timeframe)
        if data.empty:
            return {"error": f"No data for {pair}"}
        
        best_result = None
        best_params = None
        best_pnl_pct = float("-inf")
        all_results = []
        
        # Grid search
        for combo in itertools.product(*param_ranges.values()):
            params_dict = dict(zip(param_ranges.keys(), combo))
            
            # Skip invalid combinations
            if params_dict["fast_ma"] >= params_dict["slow_ma"]:
                continue
            if params_dict["rsi_oversold"] >= params_dict["rsi_overbought"]:
                continue
            
            class ParamForex(ForexConfluenceStrategy):
                params = (
                    ("fast_ma", params_dict["fast_ma"]),
                    ("slow_ma", params_dict["slow_ma"]),
                    ("rsi_period", 14),
                    ("rsi_oversold", params_dict["rsi_oversold"]),
                    ("rsi_overbought", params_dict["rsi_overbought"]),
                    ("volume_ma_period", 20),
                    ("volume_threshold", 1.15),
                    ("require_candlestick", True),
                    ("require_news", True),
                    ("news_sentiment_threshold", 0.05),
                    ("news_days_back", 7),
                    ("min_confirmations", params_dict["min_confirmations"]),
                )
            
            try:
                result = run_backtest(ParamForex, data, cash=10000.0, commission=0.0001, ticker=pair)
                pnl_pct = ((result["end_portfolio_value"] - result["start_portfolio_value"]) / 
                          result["start_portfolio_value"]) * 100
                
                all_results.append({
                    "parameters": params_dict,
                    "pnl_percentage": round(pnl_pct, 2),
                    "end_portfolio_value": result["end_portfolio_value"],
                })
                
                if pnl_pct > best_pnl_pct:
                    best_pnl_pct = pnl_pct
                    best_result = result
                    best_params = params_dict
            except Exception:
                continue
        
        if best_result is None:
            return {"error": "No valid combinations found"}
        
        all_results.sort(key=lambda x: x["pnl_percentage"], reverse=True)
        
        return {
            "pair": pair,
            "best_parameters": best_params,
            "best_result": {
                **best_result,
                "pnl_percentage": round(best_pnl_pct, 2),
            },
            "top_5_results": all_results[:5],
        }
    
    def optimize_all_majors(
        self,
        start_date: str,
        end_date: str,
        timeframe: str = "1d",
        param_ranges: Dict[str, List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Optimize confluence strategy across all major forex pairs.
        Returns best parameters per pair and aggregate recommendations.
        """
        results_by_pair = {}
        
        for pair in MAJOR_FOREX_PAIRS:
            print(f"Optimizing {pair}...")
            result = self.optimize_pair(pair, start_date, end_date, timeframe=timeframe, param_ranges=param_ranges)
            if "error" not in result:
                results_by_pair[pair] = result
        
        # Aggregate analysis: find parameters that work well across multiple pairs
        if not results_by_pair:
            return {"error": "No successful optimizations"}
        
        # Find most common best parameters
        param_counts: Dict[str, Dict[Any, int]] = {}
        for pair, result in results_by_pair.items():
            best_params = result.get("best_parameters", {})
            for param, value in best_params.items():
                if param not in param_counts:
                    param_counts[param] = {}
                param_counts[param][value] = param_counts[param].get(value, 0) + 1
        
        # Get most common values
        aggregate_params = {}
        for param, counts in param_counts.items():
            aggregate_params[param] = max(counts.items(), key=lambda x: x[1])[0]
        
        return {
            "results_by_pair": results_by_pair,
            "aggregate_best_parameters": aggregate_params,
            "summary": {
                "pairs_tested": len(results_by_pair),
                "avg_best_pnl": sum(r.get("best_result", {}).get("pnl_percentage", 0) 
                                  for r in results_by_pair.values()) / len(results_by_pair),
            },
        }

