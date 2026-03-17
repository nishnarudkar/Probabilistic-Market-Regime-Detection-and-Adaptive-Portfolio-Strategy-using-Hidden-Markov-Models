# Model Documentation

## What is a Hidden Markov Model?

A Hidden Markov Model (HMM) is a statistical model that assumes the system being observed transitions between a fixed number of hidden states over time. In this project:

- **Hidden states** = market regimes (e.g. calm bull, high volatility, crisis)
- **Observations** = the 5 market features measured each trading day

The model learns:
1. **Transition matrix** — probability of moving from regime A to regime B on the next day
2. **Emission distributions** — the mean and covariance of features in each regime
3. **Initial state probabilities** — which regime is most likely at the start

At inference time, the Viterbi algorithm finds the most likely sequence of regimes given the observed feature sequence.

---

## Features

| Feature | Description | Typical Range |
|---------|-------------|---------------|
| `returns` | Daily simple or log return | -0.10 to +0.10 |
| `volatility` | Rolling 20-day std of returns | 0.003 to 0.08 |
| `RSI` | Relative Strength Index | 0 to 100 |
| `momentum` | 10-day price change in points | -732 to +426 |
| `VIX` | CBOE Volatility Index | 9 to 80+ |

All features are standardized with `sklearn.preprocessing.StandardScaler` before being passed to the HMM.

**Strongest regime drivers:** VIX and Volatility. These two features have the most discriminative power between safe and risky regimes in this dataset.

---

## Training Pipeline

```
data/processed_market_data.csv
        │
        ▼
1. Load & sort by Date
        │
        ▼
2. StandardScaler fit on train split (80%)
        │
        ▼
3. AIC/BIC sweep over n_components = 2..6
   → select n with lowest BIC
        │
        ▼
4. GaussianHMM(n_components=best_n, covariance_type="full", n_iter=1000)
   fit on scaled train data
        │
        ▼
5. Predict regimes for all rows (train + test)
        │
        ▼
6. Classify regimes as Safe/High Risk by average VIX
        │
        ▼
7. Save hmm_model.pkl, scaler.pkl, model_metadata.json
        │
        ▼
8. Generate 10 analysis plots
        │
        ▼
9. Backtest regime-aware strategy vs. buy-and-hold
```

---

## Regime Count Selection

The model evaluates HMMs with 2 to 6 components and selects the one with the lowest **BIC (Bayesian Information Criterion)**:

```
BIC = -2 * log_likelihood + n_params * log(n_samples)
```

BIC penalizes model complexity more than AIC, which prevents overfitting to too many regimes. Both curves are saved as `outputs/figures/Model_selection_using_AICbyBIC.png`.

---

## Regime Classification (Safe vs High Risk)

After training, regimes are unlabeled integers. The model classifies them at inference time:

1. Compute average VIX for each regime across the dataset
2. Sort regimes by average VIX (ascending)
3. Bottom half → **Low Risk / Safe**
4. Top half → **High Risk**

This is recalculated every time a CSV is analyzed, so it adapts to the data being uploaded.

For manual/What-If predictions (no CSV), the model uses the learned emission means to estimate each regime's VIX level and applies the same classification.

---

## Confidence Score

The confidence score is the HMM's **posterior probability** for the predicted regime on the last observation:

```python
posteriors = model.predict_proba(scaled_sequence)
confidence = posteriors[-1][predicted_regime] * 100
```

Interpretation:
- **≥ 70%** — High confidence, signal is reliable
- **40–70%** — Medium confidence, signal is plausible but uncertain
- **< 40%** — Low confidence, market conditions are ambiguous — treat signal with caution

For a 6-regime model, random chance = ~16.7%, so even 40% represents a clear preference.

---

## Single-Point Prediction (Warmup Sequence)

The Viterbi algorithm requires a sequence to decode. A single row always produces the same regime regardless of values because there's no history to condition on.

**Solution:** prepend 30 neutral warmup rows before the user's input:

```python
n_warmup = 30
warmup   = np.tile(model.means_.mean(axis=0), (n_warmup, 1))  # average of all regime means
user_row = scaler.transform([[returns, volatility, RSI, momentum, VIX]])
sequence = np.vstack([warmup, user_row])
regime   = model.predict(sequence)[-1]
```

This gives Viterbi enough context to make a meaningful prediction for the final row.

---

## Backtesting

The training script runs a simple regime-aware strategy:

- **Signal = 1 (invested)** when current regime is Low Risk
- **Signal = 0 (cash)** when current regime is High Risk
- Strategy return on day t = signal(t-1) × return(t)

Results are compared against buy-and-hold cumulative returns and plotted in:
- `outputs/figures/HMM_Regime_Based_Trading_Strategy.png`
- `outputs/figures/Drawdown_comparison.png`

> **Disclaimer:** Backtesting uses the same data the model was trained on. Results are illustrative only and do not represent real trading performance.

---

## Limitations

- The model is **unsupervised** — regime labels (Safe/High Risk) are assigned heuristically via VIX, not ground truth
- Regime numbering is arbitrary and may change between training runs
- The model does not account for transaction costs or slippage in backtesting
- Single-point predictions use a synthetic warmup sequence, not real historical context
- The model was trained on S&P 500 data — performance on other assets is untested
