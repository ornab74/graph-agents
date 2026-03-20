# 05_execution_scheduling.md

# Execution and Scheduling

## Why scheduling matters

Once a mission graph exists, execution quality depends on scheduling:

- what runs now
- what runs in parallel
- what waits on verification
- what retries
- what gets escalated
- what gets terminated

Poor scheduling makes a good graph behave badly.

## Resource-constrained scheduling

Let each node $i$ require resource vector $r_i \in \mathbb{R}_+^K$ and duration $d_i$.  
Let available capacity at time $t$ be $R_t$.

A feasible schedule must satisfy

$$
\sum_{i \in \mathcal{A}_t} r_i \le R_t,
$$

where $\mathcal{A}_t$ is the set of active nodes at time $t$.

The scheduler solves a resource-constrained project scheduling problem:

$$
\min_{\text{start times } s_i}
\max_i (s_i + d_i)
$$

subject to precedence and capacity constraints.

## Priority index

Define a dynamic scheduling index

$$
\Pi_i(t)
=
\alpha_1 \cdot \operatorname{crit}_i
+
\alpha_2 \cdot \operatorname{slack}^{-1}_i(t)
+
\alpha_3 \cdot \operatorname{value}_i
+
\alpha_4 \cdot \operatorname{failure\_repair}_i
-
\alpha_5 \cdot \operatorname{risk}_i
-
\alpha_6 \cdot \operatorname{cost}_i.
$$

Nodes with highest $\Pi_i(t)$ are admitted first.

## Queueing model

Suppose node arrivals follow rate $\lambda$ and service rate $\mu$.  
If we approximate a pool as $M/M/1$, expected queue length is

$$
L_q = \frac{\lambda^2}{\mu(\mu-\lambda)},
$$

and expected waiting time is

$$
W_q = \frac{\lambda}{\mu(\mu-\lambda)}.
$$

This reveals why capacity planning matters for agent pools, verifier clusters, or limited deployment channels.

## Parallelism gain

If tasks are independent, ideal speedup with $p$ parallel lanes is

$$
S_p^{\text{ideal}} = p.
$$

In practice, with serial fraction $\alpha$, Amdahl’s law gives

$$
S_p = \frac{1}{\alpha + \frac{1-\alpha}{p}}.
$$

Mission graphs should explicitly estimate $\alpha$ before over-investing in concurrency.

## Retry policy

Let a node succeed with probability $p_i$ per attempt and cost $c_i$ per attempt.  
If retrying up to $K$ times, expected success probability is

$$
P_i^{(K)} = 1 - (1-p_i)^K.
$$

Expected retry cost is

$$
\mathbb{E}[C_i^{(K)}]
=
c_i \sum_{k=1}^{K} k(1-p_i)^{k-1}p_i
+
Kc_i(1-p_i)^K.
$$

A retry is rational only if the marginal expected value exceeds marginal cost.

## Escalation threshold

Let $\hat{p}_i$ be predicted success probability for another autonomous attempt.  
Escalate to a human if

$$
\hat{p}_i V_i - c_i < H_i,
$$

where $V_i$ is expected value of success and $H_i$ is human escalation cost.

Equivalent threshold:

$$
\hat{p}_i < \frac{c_i + H_i}{V_i}.
$$

## Scheduling under uncertainty

Completion times are random variables $D_i$.  
The scheduler may optimize expected makespan:

$$
\min_{\sigma} \mathbb{E}[\max_i C_i(\sigma)],
$$

or a risk-sensitive version:

$$
\min_{\sigma} \operatorname{CVaR}_{\alpha}\!\left(\max_i C_i(\sigma)\right).
$$

For high-stakes delivery, the second form is often better.

## Admission control

To avoid overload, the system can gate new work by requiring

$$
\rho_t = \frac{\lambda_t}{\mu_t} < \rho_{\max}.
$$

If utilization $\rho_t$ exceeds threshold, incoming work is queued, degraded, or rerouted.

## Work conservation vs gate discipline

A fully work-conserving scheduler never idles when work exists.  
Mission graphs often should **not** be fully work-conserving because gated stages require waiting for evidence.

Define wasted work estimate:

$$
W_{\text{waste}}
=
\sum_i
\Pr(\text{upstream gate fails}) \cdot \operatorname{downstream\_cost}_i.
$$

Sometimes deliberate idling reduces expected waste.

## Deadline-aware scheduling

For deadline $D_i^\star$, define lateness

$$
L_i = C_i - D_i^\star.
$$

Weighted tardiness objective:

$$
\min_{\sigma} \sum_i w_i \max(L_i,0).
$$

This is useful for coordinating release windows, freeze periods, or audit deadlines.

## Summary

Execution quality emerges from:

- precedence handling
- resource admission
- parallelism estimation
- retry economics
- escalation rules
- uncertainty-aware scheduling

Mission graphs outperform subagents not because they spawn more helpers, but because they execute under explicit operational laws.
