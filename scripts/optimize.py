"""Repeat the angle search for the selected workload without accessing hardware."""

import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution, linprog, minimize

ROOT = Path(__file__).resolve().parents[1]
VISIBILITY = 0.96  # Planning assumption, not a measured device fidelity.
SIZES = np.array([2 / 11, 20 / 11])
WEIGHTS = 2 * np.outer(SIZES, SIZES) + (SIZES[:, None] + SIZES) / 4
BASE = 2221 / 484

# Each local rule maps short and long jobs to one of two signs (server choices).
RULES = list(itertools.product([-1, 1], repeat=2))
CLASSICAL_CORRELATIONS = np.array([
    np.outer(rule_a, rule_b) for rule_a in RULES for rule_b in RULES
])
CLASSICAL_SPLIT_RATES = np.mean((1 - CLASSICAL_CORRELATIONS) / 2, axis=(1, 2))
CLASSICAL_PAYOFFS = -np.mean(WEIGHTS * CLASSICAL_CORRELATIONS, axis=(1, 2))


def evaluate(angles):
    """Compare one quantum strategy with the best matched classical mixture.

    Angles use the plan's theta convention; physical Ry angles are -2*theta.
    Correlations here describe routing bits, including B's software flip.
    """
    difference = 2 * (angles[:2, None] - angles[None, 2:])
    correlations = VISIBILITY * np.cos(difference)
    split_rate = np.mean((1 - correlations) / 2)
    quantum_payoff = -np.mean(WEIGHTS * correlations)

    # Mixture weights sum to one and must reproduce this overall splitting rate.
    mixture = linprog(
        -CLASSICAL_PAYOFFS,
        A_eq=[np.ones(16), CLASSICAL_SPLIT_RATES],
        b_eq=[1, split_rate],
        bounds=(0, None),
        method='highs',
    )
    if not mixture.success:
        raise RuntimeError(mixture.message)
    classical_payoff = -mixture.fun
    classical_slope = float(-mixture.eqlin.marginals[1])
    gain_percent = 100 * (quantum_payoff - classical_payoff) / (2 * BASE - classical_payoff)
    return gain_percent, classical_slope, split_rate, quantum_payoff, classical_payoff


def objective(angles):
    """Return the negative gain and its gradient for the local search."""
    gain, slope, split_rate, quantum_payoff, classical_payoff = evaluate(angles)
    sine = VISIBILITY * np.sin(2 * (angles[:2, None] - angles[None, 2:]))
    split_gradient = np.r_[sine.sum(axis=1), -sine.sum(axis=0)] / 4
    payoff_gradient = np.r_[
        2 * (WEIGHTS * sine).sum(axis=1),
        -2 * (WEIGHTS * sine).sum(axis=0),
    ] / 4
    denominator = 2 * BASE - classical_payoff
    gradient = (
        (payoff_gradient - slope * split_gradient) * denominator
        + (quantum_payoff - classical_payoff) * slope * split_gradient
    ) / denominator**2
    return -gain, -100 * gradient


def main():
    plan = json.loads((ROOT / 'data/plan.json').read_text())
    rng = np.random.default_rng(20260941)
    local_fits = [
        minimize(
            objective, rng.uniform(-np.pi, np.pi, 4), jac=True,
            method='L-BFGS-B', options={'maxiter': 250, 'ftol': 1e-12},
        )
        for _ in range(6)
    ]

    # Only angle differences matter, so one angle can be fixed to zero here.
    population_fit = differential_evolution(
        lambda angles: -evaluate(np.r_[angles, 0.0])[0],
        [(-np.pi / 2, np.pi / 2)] * 3,
        seed=20260928, tol=1e-8, maxiter=200, popsize=12, polish=True,
    )
    saved_gain = evaluate(np.array(plan['angles']))[0]
    local_gain = float(-min(fit.fun for fit in local_fits))
    population_gain = float(-population_fit.fun)
    if abs(saved_gain - plan['expected_096_gain_percent']) >= 1e-8:
        raise ValueError('The saved strategy does not reproduce its prediction')
    if max(abs(local_gain - saved_gain), abs(population_gain - saved_gain)) >= 1e-4:
        raise ValueError('The searches did not recover the saved prediction')

    print(json.dumps({
        'saved_strategy_predicted_percent': saved_gain,
        'six_start_best_percent': local_gain,
        'population_search_percent': population_gain,
        'global_optimality_proved': False,
    }, indent=2))


if __name__ == '__main__':
    main()
