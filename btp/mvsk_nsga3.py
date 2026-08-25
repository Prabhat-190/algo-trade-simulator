"""NSGA-III Mean-Variance-Skewness-Kurtosis starter.

Follows the four-objective setup in Muteba Mwamba, Mbucici & Mba (2025),
IJFS 13(1):15. Moments are computed from the portfolio return series
R @ w (O(T n) per evaluation), not from coskewness/cokurtosis tensors.

Usage:
    python -m btp.mvsk_nsga3 --synthetic
    python -m btp.mvsk_nsga3 --universe nifty
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
from scipy import stats
from scipy.optimize import minimize as scipy_minimize

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

NIFTY_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "ITC.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "LT.NS",
    "KOTAKBANK.NS",
    "AXISBANK.NS",
]

US_TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "JPM", "XOM", "JNJ", "PG", "NVDA", "UNH"]


def _normalise(weights: np.ndarray) -> np.ndarray:
    weights = np.clip(weights, 0.0, None)
    total = weights.sum()
    if total <= 0:
        return np.full(weights.shape, 1.0 / len(weights))
    return weights / total


def portfolio_moments(returns: np.ndarray, weights: np.ndarray) -> tuple[float, float, float, float]:
    """Sample mean, variance, skewness, kurtosis of r_p = R w."""
    weights = _normalise(weights)
    port = returns @ weights
    mean = float(port.mean())
    var = float(port.var(ddof=1))
    skew = float(stats.skew(port, bias=False))
    kurt = float(stats.kurtosis(port, fisher=False, bias=False))
    return mean, var, skew, kurt


class MVSKProblem(ElementwiseProblem):
    """pymoo minimises, so return/skewness are negated."""

    def __init__(self, returns: np.ndarray) -> None:
        n_var = returns.shape[1]
        super().__init__(n_var=n_var, n_obj=4, xl=0.0, xu=1.0)
        self.returns = returns

    def _evaluate(self, x, out, *args, **kwargs) -> None:
        mean, var, skew, kurt = portfolio_moments(self.returns, x)
        out["F"] = [-mean, var, -skew, kurt]


def synthetic_returns(n_assets: int = 10, n_obs: int = 756, seed: int = 7) -> pd.DataFrame:
    """Skewed, fat-tailed returns so MVSK is not the same as Markowitz."""
    rng = np.random.default_rng(seed)
    common = rng.standard_t(df=5, size=n_obs) * 0.008
    idiosyncratic = rng.standard_t(df=6, size=(n_obs, n_assets)) * 0.012
    crash = rng.random(n_obs) < 0.02
    shock = np.zeros(n_obs)
    shock[crash] = rng.uniform(-0.08, -0.03, size=crash.sum())
    raw = 0.0004 + common[:, None] + idiosyncratic + shock[:, None]
    columns = [f"A{i:02d}" for i in range(n_assets)]
    return pd.DataFrame(raw, columns=columns)


def download_returns(tickers: list[str], start: str = "2019-01-01") -> pd.DataFrame:
    import yfinance as yf

    prices = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()
    returns = prices.pct_change().dropna(how="any")
    if returns.empty:
        raise RuntimeError("No return rows after download. Check tickers or try --synthetic.")
    return returns


def markowitz_min_variance(returns: np.ndarray) -> np.ndarray:
    n = returns.shape[1]
    cov = np.cov(returns, rowvar=False)
    x0 = np.full(n, 1.0 / n)

    def objective(w: np.ndarray) -> float:
        w = _normalise(w)
        return float(w @ cov @ w)

    bounds = [(0.0, 1.0)] * n
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    result = scipy_minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=cons)
    return _normalise(result.x)


def markowitz_max_sharpe(returns: np.ndarray, rf_daily: float = 0.0) -> np.ndarray:
    n = returns.shape[1]
    mu = returns.mean(axis=0)
    cov = np.cov(returns, rowvar=False)
    x0 = np.full(n, 1.0 / n)

    def neg_sharpe(w: np.ndarray) -> float:
        w = _normalise(w)
        port_mu = float(w @ mu)
        port_vol = float(np.sqrt(w @ cov @ w))
        if port_vol <= 0:
            return 0.0
        return -(port_mu - rf_daily) / port_vol

    bounds = [(0.0, 1.0)] * n
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    result = scipy_minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=cons)
    return _normalise(result.x)


def jarque_bera_table(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in returns.columns:
        series = returns[name].to_numpy()
        jb_stat, jb_p = stats.jarque_bera(series)
        rows.append(
            {
                "asset": name,
                "mean": series.mean(),
                "std": series.std(ddof=1),
                "skew": stats.skew(series, bias=False),
                "kurtosis": stats.kurtosis(series, fisher=False, bias=False),
                "jarque_bera_p": jb_p,
                "reject_normal_5pct": jb_p < 0.05,
            }
        )
    return pd.DataFrame(rows)


def run_nsga3(returns: np.ndarray, n_partitions: int = 6, n_gen: int = 80, seed: int = 1):
    ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=n_partitions)
    algorithm = NSGA3(pop_size=max(len(ref_dirs), 92), ref_dirs=ref_dirs)
    problem = MVSKProblem(returns)
    return minimize(problem, algorithm, ("n_gen", n_gen), seed=seed, verbose=True)


def summarise_front(returns: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    rows = []
    for w in weights:
        w = _normalise(w)
        mean, var, skew, kurt = portfolio_moments(returns, w)
        vol = np.sqrt(var)
        sharpe = mean / vol if vol > 0 else np.nan
        rows.append(
            {
                "mean": mean,
                "variance": var,
                "vol": vol,
                "skew": skew,
                "kurtosis": kurt,
                "sharpe": sharpe,
                **{f"w{i}": value for i, value in enumerate(w)},
            }
        )
    return pd.DataFrame(rows)


def plot_front(front: pd.DataFrame, baselines: dict[str, pd.Series], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].scatter(front["vol"], front["mean"], s=18, alpha=0.7, label="NSGA-III")
    axes[1].scatter(front["skew"], front["kurtosis"], s=18, alpha=0.7, label="NSGA-III")
    for name, row in baselines.items():
        axes[0].scatter(row["vol"], row["mean"], marker="x", s=80, label=name)
        axes[1].scatter(row["skew"], row["kurtosis"], marker="x", s=80, label=name)
    axes[0].set_xlabel("Volatility")
    axes[0].set_ylabel("Mean return")
    axes[0].set_title("Return vs risk")
    axes[1].set_xlabel("Skewness")
    axes[1].set_ylabel("Kurtosis")
    axes[1].set_title("Higher moments")
    axes[0].legend(fontsize=8)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def load_returns(universe: str) -> pd.DataFrame:
    if universe == "synthetic":
        return synthetic_returns()
    tickers = NIFTY_TICKERS if universe == "nifty" else US_TICKERS
    try:
        return download_returns(tickers)
    except Exception as exc:
        print(f"Download failed ({exc}). Falling back to synthetic returns.")
        return synthetic_returns()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NSGA-III MVSK starter (Muteba et al. 2025).")
    parser.add_argument("--universe", choices=("synthetic", "nifty", "us"), default="synthetic")
    parser.add_argument("--synthetic", action="store_true", help="Alias for --universe synthetic")
    parser.add_argument("--n-gen", type=int, default=80)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.synthetic:
        args.universe = "synthetic"
    return args


def main() -> None:
    args = parse_args()
    returns_df = load_returns(args.universe)
    returns = returns_df.to_numpy(dtype=float)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    jb = jarque_bera_table(returns_df)
    jb.to_csv(OUTPUT_DIR / "jarque_bera.csv", index=False)
    print(jb.to_string(index=False))
    print(f"Assets rejecting normality at 5%: {int(jb['reject_normal_5pct'].sum())}/{len(jb)}")

    result = run_nsga3(returns, n_gen=args.n_gen, seed=args.seed)
    front = summarise_front(returns, result.X)
    front.to_csv(OUTPUT_DIR / "pareto_front.csv", index=False)

    mv = markowitz_min_variance(returns)
    sharpe_w = markowitz_max_sharpe(returns)
    baselines = {
        "min-var": summarise_front(returns, mv[None, :]).iloc[0],
        "max-sharpe": summarise_front(returns, sharpe_w[None, :]).iloc[0],
        "nsga3-best-sharpe": front.loc[front["sharpe"].idxmax()],
    }
    pd.DataFrame(baselines).T.to_csv(OUTPUT_DIR / "baselines.csv")

    plot_path = OUTPUT_DIR / "pareto_front.png"
    plot_front(front, baselines, plot_path)
    print(f"Pareto points: {len(front)}")
    print(f"Wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
