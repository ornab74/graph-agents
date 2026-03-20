# 01_mission_graphs_overview.md

# Mission Graphs Overview

## Executive framing

Subagents are useful, but they are not the right top-level abstraction for long-horizon delivery.  
They describe **who** performs a subtask, but not **how work persists, is verified, is budgeted, and is shipped**.

A mission graph is the stronger abstraction:

- a directed execution graph
- with persistent state
- explicit control laws
- measurable gates
- bounded privileges
- deployment semantics
- replayable history

## Formal definition

Define a mission graph as:

$$
\mathcal{G}
=
(V, E, \Theta, \Lambda, \Gamma, \Pi, \mathcal{M}, \mathcal{D})
$$

where:

- $V = \{v_1,\dots,v_n\}$ are nodes
- $E$ are precedence or information-flow edges
- $\Theta_v$ are node-local tools and permissions
- $\Lambda_v$ are node-local loss functions
- $\Gamma$ are gate functions
- $\Pi = \{\pi_v\}_{v\in V}$ are policies
- $\mathcal{M}$ is shared memory and artifact state
- $\mathcal{D}$ is deployment and rollback state

Each node executes a policy

$$
a_t^{(v)} \sim \pi_v\!\left(a \mid o_t^{(v)}, m_t, b_t\right),
$$

where $o_t^{(v)}$ is a node-local observation, $m_t$ is global memory, and $b_t$ is remaining budget.

## Why this dominates subagents

Subagents optimize local task completion.  
Mission graphs optimize **end-to-end delivery under constraints**.

A useful abstraction is:

$$
\text{Subagent} \subset \text{Node} \subset \text{Mission Graph}.
$$

That is, a subagent may implement a node, but cannot by itself model the system-level dynamics.

## Architectural layers

### 1. Semantic layer
The problem statement, repo state, goals, policies, and contracts.

### 2. Control layer
Task decomposition, routing, scheduling, retries, and escalation.

### 3. Verification layer
Tests, proofs, evals, approvals, and confidence estimates.

### 4. Delivery layer
Canarying, rollback, observability, and post-deploy learning.

## Mission utility

Define the instantaneous utility as

$$
u_t
=
\alpha_q q_t
+
\alpha_s s_t
+
\alpha_v v_t
-
\alpha_c c_t
-
\alpha_r \rho_t
-
\alpha_h h_t,
$$

where:

- $q_t$ = quality signal
- $s_t$ = speed signal
- $v_t$ = business value signal
- $c_t$ = compute or money cost
- $\rho_t$ = risk signal
- $h_t$ = required human intervention load

The mission objective is

$$
J(\Pi)
=
\mathbb{E}\left[
\sum_{t=0}^{T}\gamma^t u_t
\right].
$$

## Node semantics

Every node $v$ has:

- input contract $\mathcal{I}_v$
- output contract $\mathcal{O}_v$
- privilege boundary $\Theta_v$
- verifier set $\Gamma_v$
- recovery rule $\kappa_v$

A node transition is valid only if

$$
\Gamma_v\bigl(\mathcal{O}_v, x_t\bigr)=1.
$$

If not, the graph must either:

1. retry with altered context
2. branch to a repair node
3. escalate to a human
4. terminate and checkpoint failure

## Mission graph as constrained optimal control

Let the global state be $x_t$.  
The dynamics are

$$
x_{t+1}
=
f\bigl(x_t, a_t, w_t\bigr),
$$

where $w_t$ is exogenous uncertainty.  
The system solves

$$
\min_{\Pi}
\mathbb{E}
\left[
\sum_{t=0}^{T}
\ell(x_t, a_t)
\right]
$$

subject to:

$$
g_j(x_t, a_t) \le 0,\qquad j=1,\dots,m.
$$

This reveals the correct interpretation: a mission graph is a **constrained stochastic control system** over software artifacts and deployment states.

## Product shape

A practical product built around mission graphs should expose:

- graph editor or graph generator
- node templates
- budget and permission rules
- verifier registry
- deployment policies
- checkpoint explorer
- audit timeline
- cross-mission learning store

## Minimal viable mission graph

A strong first graph for software delivery:

1. **Scout**
2. **Planner**
3. **Builder**
4. **Tester**
5. **Security Reviewer**
6. **Integrator**
7. **Canary Deployer**
8. **Historian**
9. **Governor**

## Node scoring

Define a node score

$$
\phi_v
=
\beta_1 \cdot \text{accuracy}_v
+
\beta_2 \cdot \text{coverage}_v
+
\beta_3 \cdot \text{latency}^{-1}_v
-
\beta_4 \cdot \text{risk}_v.
$$

Then prioritize nodes in execution queues by

$$
\operatorname{priority}(v)
=
\eta_1 \phi_v
+
\eta_2 \operatorname{crit}(v)
+
\eta_3 \operatorname{slack}^{-1}(v).
$$

## Failure modes

Mission graphs are valuable partly because they explicitly model failure:

- silent context drift
- repeated low-value retries
- verifier blind spots
- deployment overreach
- budget exhaustion
- state inconsistency across branches

These must be treated as graph-level phenomena, not agent-level quirks.

## Summary

A mission graph is not just a coordination device.  
It is a **delivery calculus** for autonomous engineering work.

The rest of this pack defines the state dynamics, memory formalism, planning methods, scheduling rules, verification machinery, risk equations, deployment control, and learning system needed to make it real.
