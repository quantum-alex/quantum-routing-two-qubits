# Workload exploration

`explore_two_sizes.py` and `two_size_search.json` preserve the earlier numerical search that informed the frozen hardware plan. The search varied the job mix, duration ratio, utilization, and assumed noise level before the hardware experiment.

The source expects the original working directory layout and is kept here for inspection. To repeat the search for the selected workload, run `python3 scripts/optimize.py` from the repository root instead.

The scripts in `scripts/` are portable implementations for reproducing the calculations and constructing the logical circuits. They do not submit hardware jobs. The archived circuits and submission record are in `data/`.

The upstream research code is linked in the main README; its license notice is preserved in `UPSTREAM-LICENSE.txt`.
