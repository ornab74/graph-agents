# 08_deployment_rollout.md

# Deployment and Rollout

## Delivery is where abstractions cash out

A mission graph matters only if it can move from code and verification into production safely.

Deployment must be modeled as a controlled stochastic process, not an afterthought.

## Rollout state

Let $\tau_t \in [0,1]$ denote rollout fraction at time $t$, where:

- $\tau_t = 0$ means no traffic
- $\tau_t = 1$ means full rollout

Deployment state may include error budget, health metrics, and rollback position:

$$
d_t = (\tau_t, e_t, s_t, \kappa_t).
$$

## Canary dynamics

A simple rollout law is

$$
\tau_{t+1}
=
\tau_t
+
u_t,
$$

where $u_t$ is the rollout increment.  
Admissible control requires

$$
0 \le \tau_{t+1} \le 1.
$$

More conservatively, use health-aware rollout:

$$
u_t
=
\bar{u}
\cdot
\mathbf{1}\{h_t \ge h_{\min}\}
-
\bar{r}
\cdot
\mathbf{1}\{h_t < h_{\min}\},
$$

where $h_t$ is deployment health score.

## Health score

Let monitored signals include error rate $e_t$, latency inflation $\ell_t$, and saturation $s_t$.  
Define

$$
h_t
=
w_1(1-e_t)
+
w_2(1-\ell_t)
+
w_3(1-s_t).
$$

A rollout may proceed only if $h_t \ge h_{\min}$.

## Bayesian update for defect probability

Suppose the probability of deployment defect is $\theta$.  
With prior $\theta \sim \operatorname{Beta}(\alpha,\beta)$ and observed bad events $k$ out of $n$ canary windows, posterior is

$$
\theta \mid k,n
\sim
\operatorname{Beta}(\alpha+k,\beta+n-k).
$$

Advance rollout only if

$$
\Pr(\theta \le \theta_{\max}\mid k,n) \ge 1-\delta.
$$

## Error-budget coupling

Let service-level objective target be $S^\star$ and observed performance $S_t$.  
Error-budget depletion can be modeled as

$$
E_{t+1} = E_t - \max(0, S^\star - S_t).
$$

A safe deployment policy must satisfy

$$
E_t \ge E_{\min}.
$$

When $E_t$ is low, rollout increments should shrink:

$$
u_t = \bar{u}\cdot \frac{E_t}{E_0}.
$$

## Rollback policy

Let expected future utility of continuing rollout be $Q_{\text{cont}}(d_t)$ and rollback utility be $Q_{\text{rb}}(d_t)$.  
Rollback if

$$
Q_{\text{rb}}(d_t) > Q_{\text{cont}}(d_t).
$$

A simple approximation:

$$
Q_{\text{cont}} - Q_{\text{rb}}
=
V_{\text{feature}}
-
\lambda_{\text{inc}} \Pr(\text{incident}\mid d_t)
-
C_{\text{recovery}}.
$$

If this quantity is negative, rollback is optimal.

## Multi-stage rollout optimization

For rollout checkpoints $\tau^{(1)}<\dots<\tau^{(m)}$, solve

$$
\max_{\{\tau^{(j)}\}}
\sum_{j=1}^{m}
\left(
\Delta V_j
-
\lambda \Delta R_j
-
\mu \Delta T_j
\right),
$$

where $\Delta V_j$ is value gained, $\Delta R_j$ incremental risk, and $\Delta T_j$ time cost at stage $j$.

## Counterfactual deployment scoring

Given historical traffic $x_{1:n}$ and candidate behavior model $\hat{f}$, estimate offline deployment loss:

$$
\hat{L}_{\text{cf}}
=
\frac{1}{n}
\sum_{i=1}^{n}
\ell\bigl(\hat{f}(x_i), y_i\bigr).
$$

For policy-controlled systems, one may use importance weighting:

$$
\hat{V}_{\text{IPS}}
=
\frac{1}{n}
\sum_{i=1}^{n}
\frac{\pi(a_i\mid x_i)}{\pi_0(a_i\mid x_i)} r_i.
$$

This supports shadow deployment and pre-production evaluation.

## SLO-safe controller

A simple model-predictive rollout controller solves

$$
\min_{u_{t:t+H}}
\sum_{k=t}^{t+H}
\left[
\lambda_1 (1-\tau_k)^2
+
\lambda_2 \max(0,S^\star - S_k)^2
+
\lambda_3 u_k^2
\right]
$$

subject to deployment dynamics and safety constraints.

This is the mathematically clean way to stage rollout aggressively without becoming reckless.

## Summary

Deployment in mission graphs should be:

- staged
- probabilistic
- health-aware
- error-budget coupled
- rollback-optimized
- evaluable offline before production

That is what turns autonomous software generation into autonomous software delivery.
