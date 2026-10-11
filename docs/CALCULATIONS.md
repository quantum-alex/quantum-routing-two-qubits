# Routing probabilities and waiting times

This page connects the circuit probabilities, the classical comparison, and the resulting waiting times. The accompanying scripts calculate the same quantities from the recorded measurements.

## The classical separation limit

Each dispatcher has two inputs—short or long—and two possible destinations. A deterministic local rule is one of four maps from job type to server. Pairing the dispatchers’ rules gives 16 possibilities. Shared randomness lets them choose mixtures of those rule pairs in advance.

Write $r_{SS},r_{SL},r_{LS},r_{LL}$ for their conditional splitting probabilities. Every deterministic rule pair satisfies

$$r_{LL}\leq r_{SS}+r_{SL}+r_{LS}.$$

To see why, suppose a rule bunches SS, SL, and LS. Those three conditions force both dispatchers to give the same answer for both inputs. It must then bunch LL too. A rule that splits LL therefore splits at least one other pair. Averaging over shared randomness preserves the inequality.

Because the four input pairs are equally likely, the overall splitting rate is

$$p=\frac{r_{SS}+r_{SL}+r_{LS}+r_{LL}}{4}.$$

Combining the two expressions gives the long–long separation ceiling:

$$r_{LL}\leq 2p.$$

The measured value is $p=0.33403778076171875$. The classical ceiling is therefore **0.6680755615234375**, compared with the measured quantum LL rate of **0.855072021484375**.

For this workload, the best classical waiting result at the measured p is attained by

$$[r_{SS},r_{SL},r_{LS},r_{LL}]=[0,p,p,2p].$$

This is a mixture of always bunching (weight $1-2p$) and two rules where only one dispatcher sends long jobs to the other server (weight p each). A shared fair server-label swap balances the destinations. The verifier checks a supporting-line bound against all 16 rule pairs and checks that this mixture attains it; the comparison is not just against a few hand-picked classical policies.

The bound assumes local current inputs and no exchange of those inputs. A central dispatcher that sees both jobs is outside this model.

## From the circuit to splitting probabilities

The circuit prepares the singlet

$$|\psi^-\rangle=\frac{|01\rangle-|10\rangle}{\sqrt{2}}.$$

A keeps its measured bit; B flips its bit before routing. Thus raw 00 and 11 correspond to different destinations.

The [Ry gate](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RYGate) acts on a qubit as follows:

$$R_y(\alpha)|0\rangle=\cos(\alpha/2)|0\rangle+\sin(\alpha/2)|1\rangle,$$

$$R_y(\alpha)|1\rangle=-\sin(\alpha/2)|0\rangle+\cos(\alpha/2)|1\rangle.$$

Apply rotations with angles $\alpha$ and $\beta$ to the two qubits. In A,B order, with $\Delta=\alpha-\beta$, the state becomes

$$\frac{\sin(\Delta/2)(|00\rangle+|11\rangle)+\cos(\Delta/2)(|01\rangle-|10\rangle)}{\sqrt{2}}.$$

The probabilities of 00 and 11 are each $\sin^2(\Delta/2)/2$. Adding them gives

$$r(x,y)=\sin^2\!\left(\frac{\alpha(x)-\beta(y)}{2}\right).$$

Here x and y denote the local job types. Equal angles bunch the jobs; a 180° difference splits them every time. The four chosen angles tune the probabilities between those extremes.

The plan stores parameters θ; the physical gate angle is **α = −2θ**, in radians. The planning noise model replaces the ideal probability r with **0.96r + 0.02**. That is a hypothetical mixture, not a measured fidelity. The hardware result uses the recorded counts directly.

## From splitting probabilities to waiting

A job waits for earlier work in its server’s queue. If the other member of its pair joins the same queue ahead of it, it also waits for that job. The paper combines these contributions using the Pollaczek–Khinchine queueing identity; see [Appendix A.2–A.4, equations 22–26](https://arxiv.org/html/2602.04588v1).

For this workload, let x and y be the two job durations. The short duration is 2/11 and the long duration is 20/11. The mean duration is one, and the load is 0.8. The calculation becomes

$$W=\frac14\sum_{x,y}\left[(x+y)^2-2r(x,y)xy+\frac{(1-r(x,y))(x+y)}4\right].$$

The sum runs over SS, SL, LS, and LL. Bunching contributes a squared workload $(x+y)^2$; splitting contributes $x^2+y^2$, smaller by $2xy$. The coefficient for this contribution is one because the general coefficient is arrival rate divided by $4(1-\text{load})$: $0.8/(4\times0.2)=1$.

The last term is the wait behind the partner in a bunched pair. Half the jobs wait for the partner, whose average duration is $(x+y)/2$.

Substituting the two durations gives

$$W=5.838843-0.039256r_{SS}-0.290289(r_{SL}+r_{LS})-1.880165r_{LL}.$$

These displayed coefficients are rounded. The verifier uses exact fractions. The large LL coefficient explains why separating long–long pairs matters so much in this workload.

## Putting in the measurements

The recorded splitting probabilities are:

| Pair | Splitting probability |
| --- | ---: |
| SS | 0.107666015625 |
| SL | 0.186370849609375 |
| LS | 0.187042236328125 |
| LL | 0.855072021484375 |

Using these values, and the matched classical mixture, gives:

| Quantity | Value |
| --- | ---: |
| Classical mean waiting | 4.388815335990969 |
| Quantum mean waiting | 4.118541875161416 |
| Waiting reduction | 6.158232692388444% |
| Conservative 99% lower bound | 5.778292390741708% |

The percentage reduction is $100(W_c-W_q)/W_c$. Waiting is expressed in units of the mean job duration. [The experiment record](EXPERIMENT-RECORD.md) explains the statistical bounds and their assumptions.

The LL ceiling comparison and the CHSH summary describe the same recorded measurements. They are not separate preselected statistical tests, and this single-chip run is not a loophole-free Bell experiment.
