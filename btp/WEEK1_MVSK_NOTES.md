# BTP Week 1 Notes (post-2020, code-first)
# Multi-Objective Portfolio Optimisation Using Higher-Order Moments

**Cover paper (implement this):** Muteba Mwamba, Mbucici & Mba (2025) — NSGA-III on MVSK  
**Code this week:** `python -m btp.mvsk_nsga3`  
**Older theory (cite only):** Jondeau & Rockinger 2006, Lai 1991

---

## 1. Cover for the first meeting

**Title**

> Multi-Objective Mean–Variance–Skewness–Kurtosis Portfolio Optimisation using NSGA-III

**One-line problem**

Markowitz uses two moments. Real returns need four: max return, min variance, max skewness, min kurtosis. Those conflict. This project uses **NSGA-III** (2025 application paper) to trace the Pareto set and compares it with mean–variance in code.

**What you will build**

| Piece | Library | Paper |
|---|---|---|
| 4-objective Pareto front | `pymoo` NSGA-III | Muteba Mwamba et al. (2025) |
| Algorithm definition | `pymoo` | Deb & Jain (2014) — cite in methods |
| Optional convex MVSK | `riskfolio` | Cajas (2022, 2025) |
| Data | `yfinance` | your universe (Nifty / US) |
| Baseline | `scipy` / quadratic | Markowitz (1952) |

Starter already in this folder: [`mvsk_nsga3.py`](mvsk_nsga3.py).

---

## 2. Best post-2020 paper (the one to implement)

**Muteba Mwamba, J. W., Mbucici, L. M. & Mba, J. C. (2025).**  
*Multi-Objective Portfolio Optimization: An Application of the Non-Dominated Sorting Genetic Algorithm III.*  
*International Journal of Financial Studies*, 13(1), 15.  
DOI: [10.3390/ijfs13010015](https://doi.org/10.3390/ijfs13010015)  
Open PDF: [https://www.mdpi.com/2227-7072/13/1/15/pdf](https://www.mdpi.com/2227-7072/13/1/15/pdf)  
Preprint (same experiment): [https://www.preprints.org/manuscript/202409.1019/v1](https://www.preprints.org/manuscript/202409.1019/v1)

**Why this is the cover paper now**

- After 2020, open access, and they **wrote Python for NSGA-III**.
- Same four objectives you want: max \(f_1\) return, min \(f_2\) variance, max \(f_3\) skewness, min \(f_4\) kurtosis.
- Direct comparison with Markowitz — that is your Week 1–4 experiment.
- Data they used: global indices (FTSE100, S&P500, NASDAQ, DAX, ALSI, MOEX, BOVESPA, Shanghai, Sensex, Hang Seng) plus ZAR/USD, 2005–2024.

**What they report**

NSGA-III gives a more diverse Pareto set than mean–variance, with higher Sharpe, better skewness, and lower kurtosis.

**Honest limits (write this in the literature review)**

- IJFS is applied, not a top theory journal. Cite **Deb & Jain (2014)** as the algorithm source.
- They do not solve the non-convex MVSK problem to global optimality. Neither will you. Say “approximate Pareto front.”
- Replicate on **Indian names** (or your own universe). That is a clean BTP gap.

**Must-cite algorithm paper (2014, but you need it)**

Deb, K. & Jain, H. (2014). *An Evolutionary Many-Objective Optimization Algorithm Using Reference-Point-Based Nondominated Sorting Approach, Part I: Solving Problems With Box Constraints.* IEEE Trans. Evolutionary Computation, 18(4), 577–601.

---

## 3. Post-2020 papers ranked for a coding BTP

| Pri | Paper | Year | Code path | Use |
|---|---|---|---|---|
| **P0** | Muteba Mwamba, Mbucici & Mba, IJFS | 2025 | `pymoo` NSGA-III | Cover + replicate |
| **P0** | Deb & Jain, IEEE TEVC | 2014 | `pymoo` | Methods chapter (algorithm) |
| **P1** | Cajas, *Convex Optimization of Portfolio Kurtosis* | 2022 | `riskfolio` | Convex / SDP baseline |
| **P1** | Cajas, *Semidefinite Relaxation of Higher Portfolio Moments* | 2025 | `riskfolio` | Skewness SDP |
| **P1** | Noravesh & Kerstens, arXiv:2201.00205 | 2022 | — | Method map |
| **P1** | Convex scalarizations of MVSK, arXiv:2302.10573 | 2023 | `scipy` / CVXPY | When weighted MVSK is convex |
| **P2** | Ma, Chen, Sun & Zhu, *Swarm Evol. Comput.* | 2021 | custom EA | 5-obj MVSK + entropy |
| **P2** | Joshi & Dhodiya, *Computers & Industrial Eng.* | 2025 | NSGA-III + LSTM | Indian stocks; do **not** start here |
| **P3** | yand-mvsk / YAND algorithm | 2026 | `yand-mvsk` | Fast scalar MVSK, not Pareto |

**Downloads**

- Muteba et al. 2025 — [MDPI PDF](https://www.mdpi.com/2227-7072/13/1/15/pdf)
- Noravesh & Kerstens 2022 — [arXiv PDF](https://arxiv.org/pdf/2201.00205)
- Convex MVSK 2023 — [arXiv PDF](https://arxiv.org/pdf/2302.10573)
- Cajas kurtosis 2022 — [SSRN 4202967](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4202967)
- Cajas SDP 2025 — [SSRN 5284483](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5284483)
- Joshi & Dhodiya 2025 — [DOI 10.1016/j.cie.2025.111159](https://doi.org/10.1016/j.cie.2025.111159)
- Ma et al. 2021 — [DOI 10.1016/j.swevo.2021.100862](https://doi.org/10.1016/j.swevo.2021.100862)
- Riskfolio-Lib (Cajas code) — [GitHub](https://github.com/dcajasn/Riskfolio-Lib)
- pymoo NSGA-III docs — [https://pymoo.org/algorithms/moo/nsga3.html](https://pymoo.org/algorithms/moo/nsga3.html)

**Background only (do not make these the cover)**

- Lai (1991) — PGP origin  
- Jondeau & Rockinger (2006) — utility / Taylor  
- Harvey et al. (2010) — Bayesian skew-normal  

---

## 4. The model you will code

Objectives on weights \(w \ge 0\), \(\sum w_i = 1\):

\[
\max f_1 = \mu_p,\quad
\min f_2 = \sigma_p^2,\quad
\max f_3 = \text{skew}_p,\quad
\min f_4 = \text{kurt}_p
\]

**Code trick (use this, not \(n^4\) tensors):** for each candidate \(w\), form the portfolio series \(r_p = R w\) and take sample mean, variance, skewness, kurtosis. Cost is \(O(Tn)\) per evaluation. This is what a 2025 computational paper is doing.

In `pymoo` everything is minimised, so the fitness vector is:

\[
F = \big(-\mu_p,\; \sigma_p^2,\; -\text{skew}_p,\; \text{kurt}_p\big)
\]

Repair every individual: \(w \leftarrow w / \sum w_i\).

---

## 5. Two code tracks (pick one as main)

### Track A — Pareto front (recommended)

Paper: Muteba Mwamba et al. (2025)  
Solver: `pymoo.algorithms.moo.nsga3.NSGA3`  
Output: many portfolios on the front; pick min-variance, max-Sharpe, max-skew, min-kurt.

### Track B — one convex MVSK point (optional baseline)

Paper: Cajas (2022, 2025)  
Solver: `riskfolio` + CVXPY (MOSEK if you have it)  
Output: one (or a few scalarised) portfolios. Faster to explain, not a true four-objective front.

Do **not** start with Joshi & Dhodiya (2025) LSTM+GRU+CNN+NSGA-III. That is a second-semester stretch.

---

## 6. Week 1 work (code + paper)

### Day 1–2

- [ ] Download Muteba et al. (2025) PDF and read §§1–3 (problem + NSGA-III setup).
- [ ] Skim Deb & Jain (2014) figures for reference points (or the pymoo NSGA-III page).
- [ ] Freeze title and universe: **n ≤ 12** liquid names.

### Day 3–4 — run the starter

```bash
cd /path/to/algo-trade-simulator
pip install -r btp/requirements.txt
python -m btp.mvsk_nsga3 --synthetic          # always works
python -m btp.mvsk_nsga3 --universe nifty     # needs network
```

- [ ] Confirm `btp/output/pareto_front.csv` and the scatter plot exist.
- [ ] Write ½ page: what NSGA-III is doing (non-dominated sort + reference points).

### Day 5

- [ ] Jarque–Bera on each asset. If everything is Gaussian, change universe.
- [ ] Save Markowitz min-variance and max-Sharpe from the same script.

### Day 6–7 — 6 slides

1. Title + 2025 cover paper  
2. Four objectives + why MV fails  
3. NSGA-III in 6 bullets  
4. Your first Pareto plot  
5. Markowitz vs one NSGA-III portfolio (Sharpe, skew, kurt)  
6. Next: out-of-sample walk-forward, Indian data, maybe Riskfolio baseline  

---

## 7. Draft problem statement

Asset returns are skewed and fat-tailed, so mean–variance understates tail risk. This project formulates long-only portfolio selection as a four-objective MVSK problem and approximates the Pareto front with NSGA-III, following Muteba Mwamba, Mbucici and Mba (2025). Results are compared with the classical mean–variance frontier on out-of-sample Sharpe, CVaR, skewness and kurtosis. An optional convex MVSK point from Cajas (2022, 2025) / Riskfolio-Lib is used as a second baseline.

**Scope:** single period, long-only, \(n \le 12\), no costs in v1. Approximate front, not global optimum.

---

## 8. Do not do this week

- Do not implement coskewness / cokurtosis tensors.
- Do not add LSTM price prediction.
- Do not claim NSGA-III finds the global MVSK optimum.
- Do not start with 50 stocks.

---

## 9. Suggested reading order (about 7 hours)

| Hours | What | Output |
|---|---|---|
| 2.0 | Muteba et al. (2025) full paper | 1-page summary + objective formulas |
| 1.0 | pymoo NSGA-III docs + Deb & Jain intro | methods bullets |
| 1.0 | Noravesh & Kerstens (2022) §§1–3 | “why EA vs utility” paragraph |
| 0.5 | Cajas 2022 abstract + Riskfolio MVSK page | optional Track B |
| 2.5 | Run `mvsk_nsga3.py`, inspect CSV, one plot | Week 1 empirical slide |
