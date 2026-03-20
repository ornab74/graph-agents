# 06_verification_evals.md

# Verification and Evals

## Verification is the backbone

A mission graph without verifiers is just a graph of confident guesses.

Verification must operate at multiple levels:

- syntax and type correctness
- test success
- semantic correctness
- security and policy conformance
- deployment safety
- outcome realization

## Gate function

Each important transition is controlled by a gate:

$$
\Gamma_i(x_t, \hat{y}_t, z_t) \in \{0,1\}.
$$

A transition is permitted only if

$$
\Gamma_i = 1.
$$

In richer settings, gates emit confidence scores

$$
g_i \in [0,1],
$$

and transitions require $g_i \ge \tau_i$.

## Composite verifier score

Let a node output receive $M$ verifier signals $v_1,\dots,v_M$.  
Then the aggregate confidence can be

$$
\hat{c}
=
\sigma\!\left(
\beta_0 + \sum_{m=1}^{M}\beta_m v_m
\right).
$$

Or more conservatively,

$$
\hat{c}_{\min} = \min_m v_m.
$$

Use the conservative form when any single failure mode is critical.

## Statistical acceptance

Suppose a patch is accepted if defect rate $p$ is below threshold $p_0$.  
Given $k$ failures in $n$ tests, one can use a posterior

$$
p \mid k,n \sim \operatorname{Beta}(\alpha + k,\; \beta + n - k).
$$

Accept only if

$$
\Pr(p \le p_0 \mid k,n) \ge 1-\delta.
$$

This is better than binary “tests passed” thinking.

## Sequential testing

For live or repeated verification, use a sequential probability ratio test.  
Test:

$$
H_0: p \le p_0
\qquad\text{vs}\qquad
H_1: p \ge p_1.
$$

After observations $x_1,\dots,x_n$, compute likelihood ratio

$$
\Lambda_n
=
\prod_{i=1}^{n}
\frac{P(x_i\mid H_1)}{P(x_i\mid H_0)}.
$$

Stop and accept $H_1$ if $\Lambda_n \ge A$, accept $H_0$ if $\Lambda_n \le B$, otherwise continue.

## Semantic distance check

Let desired behavior embedding be $e^\star$ and candidate artifact embedding be $\hat{e}$.  
A semantic verifier may require

$$
\|\hat{e} - e^\star\|_2 \le \epsilon_{\text{sem}}.
$$

This does not replace tests, but it can cheaply filter obviously incorrect branches.

## Formal contract satisfaction

For a node contract $\varphi$, define

$$
\operatorname{Sat}(\hat{y}, \varphi)
=
\begin{cases}
1 & \text{if } \hat{y}\models \varphi,\\
0 & \text{otherwise.}
\end{cases}
$$

Examples:

- required files created
- interfaces preserved
- migration is reversible
- no privileged tool call occurred without approval

## Calibrated verification

Verifier scores must be calibrated.  
If predicted confidence is $\hat{c}$ and empirical correctness is $y\in\{0,1\}$, then Brier score is

$$
\operatorname{BS}
=
\frac{1}{N}
\sum_{i=1}^{N}
(\hat{c}_i - y_i)^2.
$$

Mission graphs should continuously minimize calibration error on verifiers.

## False-negative aware gating

Let the cost of a false negative be $C_{\text{FN}}$ and false positive be $C_{\text{FP}}$.  
The optimal threshold under a score model is not generic; it depends on

$$
\tau^\star
=
\arg\min_{\tau}
\Bigl(
C_{\text{FP}} \Pr(\hat{c}\ge \tau, y=0)
+
C_{\text{FN}} \Pr(\hat{c}<\tau, y=1)
\Bigr).
$$

For deployment gates, false negatives are often far more expensive.

## Verification coverage

Let $\mathcal{F}$ be the set of important failure modes and $\mathcal{V}$ the set of active verifiers.  
Coverage can be measured as

$$
\operatorname{Cov}
=
\frac{
\left|
\bigcup_{v\in\mathcal{V}} \operatorname{Detect}(v)
\right|
}{
|\mathcal{F}|
}.
$$

A graph with low coverage is fragile no matter how persuasive its outputs look.

## Value of another eval

If an additional eval $e$ changes decision quality, its expected value is

$$
\operatorname{VOE}(e)
=
\mathbb{E}\left[
U(\text{decision with } e) - U(\text{decision without } e)
\right]
-
\operatorname{cost}(e).
$$

This allows dynamic evaluator selection.

## Summary

Verification in mission graphs should be:

- multi-level
- calibrated
- sequential when appropriate
- risk-sensitive
- coverage-aware
- tightly coupled to transition permissions

That is how you convert autonomous work from plausible to trustworthy.
