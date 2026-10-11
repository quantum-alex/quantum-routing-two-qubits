"""Search short/long workloads for a predicted routing benefit.
All results are model predictions; this script does not access hardware.
"""

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
SHORT_PROBABILITIES = (0.5, 0.8, 0.95)
SIZE_RATIOS = (2.0, 5.0, 10.0, 50.0)
UTILIZATIONS = (0.01, 0.1, 0.5, 0.8)
VISIBILITIES = (1.0, 0.96)
RANDOM_SEED = 20260941
OPTIMIZATION_STARTS = 6

# Each row maps (short, long) to one of two server-choice signs.
LOCAL_RULES = np.array([[1, 1], [-1, 1], [1, -1], [-1, -1]])


@dataclass
class Workload:
    short_probability: float
    size_ratio: float
    utilization: float
    probabilities: np.ndarray
    durations: np.ndarray
    pair_probabilities: np.ndarray
    waiting_weights: np.ndarray
    waiting_base: float


@dataclass
class ClassicalFrontier:
    split_rates: np.ndarray
    payoffs: np.ndarray

    def payoff_and_slope(self, split_rate):
        """Interpolate the best classical mixture at a given splitting rate."""
        payoff = np.interp(split_rate, self.split_rates, self.payoffs)
        right = int(np.clip(
            np.searchsorted(self.split_rates, split_rate),
            1, len(self.split_rates) - 1,
        ))
        left = right - 1
        slope = (
            (self.payoffs[right] - self.payoffs[left])
            / (self.split_rates[right] - self.split_rates[left])
        )
        return payoff, slope


def make_workload(short_probability, size_ratio, utilization):
    """Normalize mean job duration to one and calculate the waiting weights."""
    probabilities = np.array([short_probability, 1 - short_probability])
    durations = np.array([1.0, size_ratio])
    durations /= probabilities @ durations
    pair_probabilities = probabilities[:, None] * probabilities

    # Previously queued work grows with load. Waiting behind the other job
    # in a bunched pair contributes the additional (x+y)/4 term.
    queue_factor = utilization / (2 * (1 - utilization))
    waiting_weights = (
        queue_factor * durations[:, None] * durations
        + 0.25 * (durations[:, None] + durations)
    )
    waiting_base = (
        utilization * (2 * (probabilities @ (durations * durations)) + 2)
        / (4 * (1 - utilization))
        + 0.5 - (queue_factor + 0.5) / 2
    )
    return Workload(
        short_probability, size_ratio, utilization,
        probabilities, durations, pair_probabilities,
        waiting_weights, waiting_base,
    )


def classical_strategy_points(workload):
    """Calculate the splitting rate and payoff of all 16 local rule pairs."""
    probabilities = workload.probabilities
    weighted_durations = probabilities * workload.durations
    mean_signs = LOCAL_RULES @ probabilities
    duration_weighted_signs = LOCAL_RULES @ weighted_durations
    queue_factor = workload.utilization / (2 * (1 - workload.utilization))

    split_rates = ((1 - mean_signs[:, None] * mean_signs) / 2).ravel()
    payoffs = (
        -queue_factor * duration_weighted_signs[:, None] * duration_weighted_signs
        -0.25 * (
            duration_weighted_signs[:, None] * mean_signs
            + mean_signs[:, None] * duration_weighted_signs
        )
    ).ravel()
    return split_rates, payoffs


def classical_frontier(workload):
    """Keep the upper boundary of the classical strategy points.

    Shared randomness permits mixtures. A line between two boundary points
    gives the payoff of their mixture, so the upper convex boundary is the
    best classical payoff at each splitting rate.
    """
    split_rates, payoffs = classical_strategy_points(workload)
    boundary = []
    for index in np.lexsort((payoffs, split_rates)):
        # At an identical rate, only the highest payoff matters.
        if boundary and split_rates[index] == split_rates[boundary[-1]]:
            boundary.pop()
        while len(boundary) > 1:
            left, middle = boundary[-2:]
            turn = (
                (split_rates[middle] - split_rates[left])
                * (payoffs[index] - payoffs[left])
                - (split_rates[index] - split_rates[left])
                * (payoffs[middle] - payoffs[left])
            )
            if turn < 0:
                break
            boundary.pop()
        boundary.append(index)
    return ClassicalFrontier(split_rates[boundary], payoffs[boundary])


def objective(angles, workload, frontier, visibility):
    """Return negative waiting reduction and its gradient for minimization.

    The four angles are theta_A(short), theta_A(long), theta_B(short),
    theta_B(long). Physical Ry angles are -2*theta. Visibility scales the
    ideal routing correlations; it is an assumed noise level, not fidelity.
    """
    differences = 2 * (angles[:2, None] - angles[None, 2:])
    correlations = visibility * np.cos(differences)
    sine_terms = visibility * np.sin(differences)
    pair_probabilities = workload.pair_probabilities
    weights = workload.waiting_weights

    split_rate = float(np.sum(pair_probabilities * (1 - correlations)) / 2)
    quantum_payoff = float(-np.sum(pair_probabilities * weights * correlations))
    classical_payoff, classical_slope = frontier.payoff_and_slope(split_rate)

    # Mean waiting is base - payoff/2. Thus the relative reduction is
    # (quantum_payoff - classical_payoff) / (2*base - classical_payoff).
    denominator = 2 * workload.waiting_base - classical_payoff
    reduction = (quantum_payoff - classical_payoff) / denominator

    split_gradient = np.r_[
        np.sum(pair_probabilities * sine_terms, axis=1),
        -np.sum(pair_probabilities * sine_terms, axis=0),
    ]
    payoff_gradient = np.r_[
        2 * np.sum(pair_probabilities * weights * sine_terms, axis=1),
        -2 * np.sum(pair_probabilities * weights * sine_terms, axis=0),
    ]
    gradient = (
        (payoff_gradient - classical_slope * split_gradient) * denominator
        + (quantum_payoff - classical_payoff) * classical_slope * split_gradient
    ) / denominator**2
    return -reduction, -gradient


def search_angles(workload, frontier, visibility, rng):
    """Keep the best of six local searches, as in the archived exploration."""
    fits = [
        minimize(
            objective, rng.uniform(-np.pi, np.pi, 4),
            args=(workload, frontier, visibility), jac=True,
            method='L-BFGS-B', options={'maxiter': 250, 'ftol': 1e-12},
        )
        for _ in range(OPTIMIZATION_STARTS)
    ]
    best = min(fits, key=lambda fit: fit.fun)
    return {
        'short_probability': workload.short_probability,
        'long_to_short_size_ratio': workload.size_ratio,
        'utilization': workload.utilization,
        'visibility': visibility,
        'wait_reduction_percent': float(-100 * best.fun),
        'angles': best.x.tolist(),
        'optimizer_success': bool(best.success),
    }


def run_search():
    """Use the original case order so each case receives the same RNG starts."""
    rng = np.random.default_rng(RANDOM_SEED)
    records = []
    for short_probability, size_ratio, utilization in itertools.product(
        SHORT_PROBABILITIES, SIZE_RATIOS, UTILIZATIONS,
    ):
        workload = make_workload(short_probability, size_ratio, utilization)
        frontier = classical_frontier(workload)
        for visibility in VISIBILITIES:
            records.append(search_angles(workload, frontier, visibility, rng))
        if len(records) % 12 == 0:
            print(f'Completed {len(records)} of 96 cases', flush=True)
    return records


def check_reference(records, tolerance=1e-6):
    """Compare every gain with the saved sweep, in percentage points.

    Equivalent angle choices can describe the same strategy, so the check
    compares gains rather than requiring identical angle parameters.
    """
    reference = json.loads((ROOT / 'provenance/two_size_search.json').read_text())
    expected = reference['records']
    if len(records) != len(expected):
        raise ValueError('Different number of workload cases')
    parameters = (
        'short_probability', 'long_to_short_size_ratio', 'utilization', 'visibility',
    )
    differences = []
    for actual, saved in zip(records, expected):
        if any(actual[key] != saved[key] for key in parameters):
            raise ValueError('Workload case order differs from the saved sweep')
        differences.append(abs(
            actual['wait_reduction_percent'] - saved['wait_reduction_percent']
        ))
    maximum_difference = max(differences)
    if not all(np.isfinite(value) for value in differences) or maximum_difference > tolerance:
        raise ValueError(f'Saved gains differ by up to {maximum_difference} points')
    print(f'All 96 saved gains reproduced; maximum difference: {maximum_difference:.3g}')
    return maximum_difference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output', type=Path, default=ROOT / 'results/two_size_search.json',
        help='Where to save new predictions (default: results/two_size_search.json)',
    )
    parser.add_argument(
        '--check-reference', action='store_true',
        help='Compare all 96 predicted gains with the archived sweep',
    )
    args = parser.parse_args()
    if args.output.resolve() == (ROOT / 'provenance/two_size_search.json').resolve():
        parser.error('Choose a new output path; the archived sweep must be preserved')

    records = run_search()
    if args.check_reference:
        check_reference(records)
    report = {
        'scope': (
            'Exploratory two-size workloads; classical comparator exhaustively '
            'enumerates all local binary rules and shared randomness. Six random '
            'local optimization starts per case, not a global bound. Noise '
            'visibility is hypothetical. No new hardware data.'
        ),
        'records': records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Saved predictions to {args.output}')
    for visibility in VISIBILITIES:
        best = max(
            (record for record in records if record['visibility'] == visibility),
            key=lambda record: record['wait_reduction_percent'],
        )
        print(f'Best predicted result at visibility {visibility}: {best}')


if __name__ == '__main__':
    main()
