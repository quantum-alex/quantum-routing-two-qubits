# Two-qubit routing experiment

Two dispatchers each receive a short or long job and choose between two servers. Each sees only its own job; neither can exchange current inputs before choosing. The aim is to keep long jobs apart, since putting them together creates the most waiting.

I tested an entangled two-qubit routing strategy on IBM’s `ibm_marrakesh`. The experiment collected 131,072 measurements and compared the resulting routing probabilities with the best classical strategy under the same information constraints and overall separation rate.

The routing mechanism and queueing model come from [Francisco Ferreira da Silva and Stephanie Wehner](https://arxiv.org/abs/2602.04588). This repository contains the hardware records, calculations, and code for reproducing the comparison.

## What I measured

Both strategies separate **33.4% of all job pairs**. What differs is which pairs they separate:

| Job pair | Best classical strategy for this workload | Measured quantum strategy |
| --- | ---: | ---: |
| Short–short | 0.0% | 10.8% |
| Short–long | 33.4% | 18.6% |
| Long–short | 33.4% | 18.7% |
| Long–long | **66.8%** | **85.5%** |

The classical long–long ceiling is twice the overall separation rate. The verifier checks it against all 16 deterministic local rule pairs; shared randomness cannot lift it. The measured quantum probabilities cross that ceiling.

In the paper’s queueing model, those probabilities give **6.16% less waiting** than the best classical strategy at the same overall separation rate. A conservative 99% lower confidence bound is **5.78%**, subject to the sampling assumptions described in the [experiment record](docs/EXPERIMENT-RECORD.md).

This is a result about constrained coordination. A central computer that sees both jobs has more information and is outside this comparison. I measured quantum outcomes on a chip, then calculated their effect on waiting in the model; I did not measure a deployed service’s latency. The two qubits were on the same chip, and the calculation excludes the cost of supplying entanglement to separate dispatchers.

## Check the result

You need Python 3.10 or newer. The main check uses only Python’s standard library:

```bash
python3 scripts/verify.py
```

It checks the archived file hashes and all 131,072 recorded outcomes, enumerates the classical rules, and recalculates the waiting times and confidence bounds. It also reports each of the two measurement blocks separately. It reads the saved files and does not contact IBM.

The pooled output should include:

```text
predicted_classical_wait:              4.388815335990969
predicted_quantum_wait:                4.118541875161416
wait_reduction_percent:                6.158232692388444
conservative_99_relative_lower_percent: 5.778292390741708
```

Waiting is measured in units of the mean job duration. The last decimal places may vary slightly between Python versions.

## See how the strategy was built

The [circuit](scripts/circuit.py) prepares an entangled pair, rotates each qubit according to that dispatcher’s job type, and measures it. A keeps its measured bit; B flips its bit before routing. These two bits choose the servers. [The calculations](docs/CALCULATIONS.md) explain how the rotation angles set the splitting probabilities and how those probabilities translate into waiting.

To construct the circuits locally and check their ideal probabilities:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-circuit.txt
python scripts/circuit.py
```

To repeat the angle search for the chosen workload:

```bash
python -m pip install -r requirements-model.txt
python scripts/optimize.py
```

The search compares the quantum strategy with mixtures of all classical local rules. Six local searches and a separate population search recover the saved prediction of about **5.73%** under the planning noise model. These are numerical searches, not a proof that the angles are globally optimal.

Neither command submits a hardware job. A new run would need an IBM account, current device calibration, and circuits compiled for the selected device.

## What is in this repository

- [Calculations](docs/CALCULATIONS.md): the classical limit, circuit probabilities, and waiting formula.
- [Experiment record](docs/EXPERIMENT-RECORD.md): workload selection, frozen settings, and the statistical test.
- [Data](data/README.md): raw outcomes, the plan, archived circuits, and saved analyses.
- [Scripts](scripts/): verification, angle search, and circuit construction.
- [Exploration history](provenance/README.md): the earlier workload search that led to this experiment.
- [Validation record](VALIDATION.json): the environment and checks used to prepare this repository.

`MANIFEST.json` records SHA-256 hashes of the saved experiment data, archived circuits, and exploratory source. These files are unchanged from the earlier experiment package. The hashes detect changes; they do not independently certify when the plan was written.

## Credit

The routing idea and queueing analysis belong to **Francisco Ferreira da Silva and Stephanie Wehner**, authors of *[Entanglement improves coordination in distributed systems](https://arxiv.org/abs/2602.04588)*. Their [original repository](https://gitlab.com/FranciscoHS/entanglement-routing-advantage) contains the underlying research code.

My contribution here is a hardware investigation of a selected workload, with the raw measurements and a reproducible comparison. I am not claiming a new quantum mechanism or a production-ready load balancer.

The recorded outcomes are from the hardware run; the numerical claims can be checked with the included scripts.
