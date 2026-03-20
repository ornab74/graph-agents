# 07_risk_budgeting.md

# Risk and Budgeting

## Risk-sensitive autonomy

Mission graphs must not maximize throughput alone.  
They must maximize **risk-adjusted value** under bounded budgets.

Let cumulative reward be $G$ and loss event magnitude be $L$.  
Then mission utility should incorporate both expected value and downside exposure.

## Budget vector

Use a multi-dimensional budget:

$$
b_t = \begin{bmatrix}
b_t^{\text{compute}} \\
b_t^{\text{money}} \\
b_t^{\text{tokens}} \\
b_t^{\text{human}} \\
b_t^{\text{deploy}}
\end{bmatrix}.
$$

Dynamics:

$$
b_{t+1} = b_t - c_t(a_t),
$$

where $c_t(a_t)$ is the action-dependent cost vector.

A policy is feasible only if

$$
b_t \succeq 0 \quad \forall t.
$$

## Risk decomposition

Break risk into components:

$$
\rho_t
=
\rho_t^{\text{correctness}}
+
\rho_t^{\text{security}}
+
\rho_t^{\text{operational}}
+
\rho_t^{\text{compliance}}
+
\rho_t^{\text{reputational}}.
$$

Then define weighted aggregate risk

$$
R_t = \sum_{j} \omega_j \rho_t^{(j)}.
$$

## Risk-adjusted objective

A useful objective is

$$
\max_{\Pi}
\;
\mathbb{E}[G]
-
\lambda \operatorname{CVaR}_{\alpha}(L).
$$

Here:

- $G$ = cumulative mission gain
- $L$ = cumulative mission loss
- $\operatorname{CVaR}_{\alpha}$ = conditional value-at-risk at tail level $\alpha$

This explicitly penalizes bad tail events rather than just average risk.

## CVaR definition

For loss random variable $L$, value-at-risk is

$$
\operatorname{VaR}_{\alpha}(L)
=
\inf\{\ell : \Pr(L \le \ell)\ge \alpha\}.
$$

Then

$$
\operatorname{CVaR}_{\alpha}(L)
=
\mathbb{E}[L \mid L \ge \operatorname{VaR}_{\alpha}(L)].
$$

This is particularly relevant for deployment incidents or security regressions.

## Constrained policy optimization

The graph may solve:

$$
\max_{\Pi}\; \mathbb{E}[G]
\quad
\text{s.t.}
\quad
\mathbb{E}[C] \le B,\;
\mathbb{E}[R] \le \bar{R},\;
\mathbb{E}[H] \le \bar{H}.
$$

Equivalent Lagrangian:

$$
\mathcal{L}(\Pi,\lambda)
=
\mathbb{E}[G]
-
\lambda_C(\mathbb{E}[C]-B)
-
\lambda_R(\mathbb{E}[R]-\bar{R})
-
\lambda_H(\mathbb{E}[H]-\bar{H}).
$$

## Opportunity-cost budgeting

Choosing one branch consumes scarce resources that could support another.  
Let branch $i$ have expected net present value

$$
\operatorname{NPV}_i
=
\mathbb{E}[G_i - C_i - \lambda R_i].
$$

Then resource allocation should solve

$$
\max_{x_i \in \{0,1\}}
\sum_i x_i \operatorname{NPV}_i
\quad
\text{s.t.}
\quad
\sum_i x_i c_i \le B.
$$

This is a knapsack-like portfolio view of graph branch selection.

## Dynamic risk threshold

Risk tolerance should depend on remaining budget and deadline pressure.  
A simple adaptive threshold is

$$
\tau_R(t)
=
\tau_0
+
\eta_1 \frac{b_t}{B}
-
\eta_2 \frac{T-t}{T}.
$$

Near deadline, tolerance may tighten or loosen depending on business policy; the equation makes that choice explicit.

## Escalation under risk

Escalate to a human if expected autonomous downside exceeds threshold:

$$
\Pr(L \ge \ell^\star \mid x_t,a_t) \ge \delta.
$$

Or, using expected downside:

$$
\mathbb{E}[L \mid x_t,a_t] \ge \lambda_H^{-1} H_t.
$$

## Risk concentration

Too much mission exposure can accumulate in a small number of nodes.  
Define concentration index

$$
\mathcal{K}
=
\sum_{i=1}^{n}
\left(
\frac{R_i}{\sum_j R_j}
\right)^2.
$$

High $\mathcal{K}$ means a few nodes dominate mission risk; these deserve stronger gates and approvals.

## Budget burn rate

Compute burn rate

$$
\beta_t = \frac{B - b_t}{t+1}.
$$

Projected exhaustion time:

$$
\hat{T}_{\text{exhaust}} = \frac{b_t}{\beta_t}.
$$

The scheduler should replan before $\hat{T}_{\text{exhaust}} < T-t$.

## Summary

Risk and budgeting should be native to mission graphs, not post-hoc dashboards.

A strong system reasons about:

- tail risk
- multi-budget feasibility
- branch portfolio value
- escalation thresholds
- burn rate
- risk concentration

That is what lets autonomous delivery remain commercially and operationally sane.
