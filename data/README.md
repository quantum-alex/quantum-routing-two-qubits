# Reading the saved data

These files let you trace the result back to the settings and individual outcomes. The JSON and QPY files are unchanged from the earlier experiment package.

| File | What it contains |
| --- | --- |
| `plan.json` | The settings, workload, allocation of measurements, primary test, and compiled-circuit hash fixed before submission. |
| `submitted_job.json` | IBM job ID, plan hash, and execution-time cap. |
| `hardware_results.json` | All raw bitstrings, their counts, and execution metadata for the eight circuits. |
| `circuits.qpy` | Archived logical circuits in Qiskit’s binary QPY format. |
| `compiled_circuits.qpy` | The device-compiled circuits used for the job. |
| `analysis.json` | The saved pooled result and the two block results. |
| `assessment.json` | The strategy prediction and sensitivity calculations made before the run. |
| `independent_audit.json` | Later arithmetic and measurement diagnostics. Passing these checks does not establish that systematic errors are absent. |

## Turning bits into routing decisions

Qiskit stores the two-bit strings in **B,A** order. Dispatcher A keeps its bit; dispatcher B flips its bit in software. Consequently, raw `00` and `11` mean the jobs go to different servers. Raw `01` and `10` mean they stay together.

For each setting, the splitting probability is therefore:

```text
(count("00") + count("11")) / total measurements
```

The four settings are short–short, short–long, long–short, and long–long. Each appears once in each block, with 16,384 measurements per circuit. Pooling the blocks gives 32,768 measurements per setting.

The plan stores angle parameters as `theta_a` and `theta_b`. The physical Ry gate angles are **−2θ**, in radians. `scripts/circuit.py` uses that conversion explicitly.

## Checking integrity

From the repository root, run:

```bash
python3 scripts/verify.py
```

It verifies the hashes in `MANIFEST.json`, checks each list of bitstrings against its recorded counts, and recalculates the results. Hashes detect file changes; they are not an external certificate of when the experiment plan was created.
