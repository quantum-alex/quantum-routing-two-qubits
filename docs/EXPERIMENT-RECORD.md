# Experiment record

The hardware run took place on **27 September 2026**. I had explored several workloads beforehand, then fixed the workload, angles, sample allocation, and primary test before submitting this job. The files in `data/` preserve that plan and the resulting measurements.

## The workload

Each dispatcher receives one job. It is short or long with equal probability, independently of the other dispatcher’s job. A long job takes ten times as long as a short one. In units where the mean duration is one, the two durations are **2/11** and **20/11**.

Pairs arrive according to a Poisson process at rate 0.8. There are two identical first-come-first-served servers, each with 80% utilization from customer work. Background work can be interrupted immediately. When both jobs join one queue, their order is chosen fairly. A common fair swap of the server labels balances traffic for both strategies.

Each routing decision uses only the current local job type and resources shared in advance. The comparison does not give either dispatcher fresh information about the other job or the queues. It matches the overall splitting rate and the paper’s background-work conditions. These restrictions are part of the model, not a description of every real load balancer.

## Choosing the angles

I used a numerical search to find four angles: one for each short/long choice at each dispatcher. For each candidate, the calculation predicts the four splitting probabilities, converts them into waiting, and compares them with the best classical mixture at the same overall splitting rate.

The planning model keeps 96% of the ideal correlations and mixes in 4% uncorrelated outcomes. Under that hypothetical noise model, the selected strategy predicted **5.726185%** less waiting. This visibility parameter was a planning assumption, not a measured device fidelity.

A separate differential-evolution search, using a linear program over all 16 classical local rule pairs, recovered the same prediction. `scripts/optimize.py` repeats both searches for the selected workload. It does not rerun the entire exploratory sweep or prove global optimality. The earlier sweep is preserved in `provenance/`.

I did not change the workload or angles after seeing this hardware result.

## The hardware run

| Item | Setting |
| --- | --- |
| Backend | `ibm_marrakesh` |
| Physical qubits | 54 and 55 |
| Job ID | `dasji6rg95ks73efkk60` |
| Circuits | 8: four input pairs in each of two blocks |
| Measurements per circuit | 16,384 |
| Total measurements | 131,072 |
| Execution-time cap | 60 seconds |

The two blocks used different setting orders. They are parts of one job, not independent replications on separate devices. The plan included no automatic hardware retries. All recorded outcomes are included, without discarding outcomes or correcting for device noise.

`plan.json` contains the settings and compiled-circuit hash. `submitted_job.json` and `hardware_results.json` record the plan hash. The verifier checks these links as well as the raw counts.

## The test fixed before submission

The primary question was whether the measurements supported **more than 5% less modeled waiting**, rather than merely a positive improvement. The pass criterion was a positive pooled, one-sided 99% Hoeffding lower bound on a fixed witness for that threshold.

Here is the algebra behind that test. Let A be the routing payoff and p the overall splitting probability. In the notation stored in the plan, the constant base is 2221/484, and:

$$W_q = \mathrm{base} - A/2.$$

Exact enumeration of the classical rules gives

$$A_c(p) \leq kp+b, \qquad k=191/22,\quad b=-5/2.$$

Therefore, a positive value of

$$A-0.95(kp+b)-0.10\,\mathrm{base}$$

is sufficient to establish $W_q<0.95W_c$. This witness is a linear combination of the four measured correlations, with coefficients fixed in the plan. The pooled calculation uses 32,768 measurements for each input pair. Its Hoeffding allowance is

$$\sqrt{2\ln(100)\sum_{ij}K_{ij}^2/n_{ij}}.$$

A roundoff guard of $10^{-12}$ is also subtracted. The measured witness passes this criterion.

The reported **5.78%** conservative lower bound is a separate percentage bound. It combines simultaneous bounds on the advantage and splitting probability, each with failure probability 0.005, then bounds their ratio. It is not a symmetric error bar around 6.16%. `scripts/verify.py` recomputes both calculations.

These confidence statements assume independent measurements and stable setting probabilities. They quantify sampling uncertainty; they do not cover systematic device errors, cross-talk, or the cost of a remote deployment.

## What I checked before the run

With the chosen angles held fixed, 33 of 60 nearby workload combinations predicted more than 5% improvement. That grid covered short-job probabilities from 0.40 to 0.60, duration ratios of 8, 10, and 12, and utilization levels of 0.50, 0.70, 0.80, and 0.90. It is a sensitivity check, not a forecast for real traffic.

At duration ratio 10 and 80% utilization, short-job probabilities of 0.40, 0.45, 0.50, 0.55, and 0.60 gave predicted reductions of 4.42%, 6.20%, 5.73%, 5.02%, and 4.07%. I kept the selected 50/50 workload instead of switching to the higher simulated 45/55 result.

Planning visibilities of 0.92, 0.94, 0.96, and 0.98 gave predictions of 4.64%, 5.18%, 5.73%, and 6.27%. The saved assessment contains these calculations.

## Reading the result

The observed routing probabilities imply **6.1582326924%** less waiting in the stated model. The long–long separation comparison and the CHSH summary are additional descriptions of those same measurements; they were not separate primary tests. The experiment was on one chip and was not a loophole-free Bell test.

To turn this into a useful distributed service, the cost, reliability, and timing of delivering entanglement would have to be included. Real queue information and different traffic could also change the comparison. Those remain questions for a later experiment.
