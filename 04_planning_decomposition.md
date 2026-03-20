# 04_planning_decomposition.md

# Planning and Decomposition

## Planning as hierarchical control

A mission graph must plan across multiple horizons:

- immediate tool calls
- node-level completion
- milestone-level sequencing
- release-level delivery

The natural formalism is hierarchical control or a hierarchical partially observable Markov decision process.

## Hierarchical objective

Let $g$ be the top-level mission goal and $s$ the current state.  
A planner chooses subgoals $\omega \in \Omega$ with policy $\mu(\omega \mid s,g)$, while node-level policies act under option $\omega$.

The objective is

$$
V^\mu(s,g)
=
\max_{\mu}
\mathbb{E}
\left[
\sum_{t=0}^{T}
\gamma^t r_t
\;\middle|\;
s_0=s,\; g
\right].
$$

At the option level,

$$
Q^\mu(s,\omega)
=
\mathbb{E}
\left[
\sum_{k=0}^{\tau_\omega-1}
\gamma^k r_{t+k}
+
\gamma^{\tau_\omega} V^\mu(s_{t+\tau_\omega}, g)
\right].
$$

## Decomposition criterion

A task should be decomposed if decomposition improves expected utility:

$$
\Delta_{\text{decomp}}
=
\mathbb{E}[J_{\text{decomp}} - J_{\text{monolithic}}] > 0.
$$

Expand the decomposition gain as

$$
\Delta_{\text{decomp}}
=
\underbrace{\Delta q}_{\text{quality gain}}
+
\underbrace{\Delta v}_{\text{verifiability gain}}
+
\underbrace{\Delta p}_{\text{parallelism gain}}
-
\underbrace{\Delta c}_{\text{coordination cost}}
-
\underbrace{\Delta d}_{\text{delay overhead}}.
$$

This explains why naive over-decomposition is harmful.

## Partial-order planning

Let the planner output a partially ordered set of tasks $\mathcal{T}$ with precedence constraints:

$$
t_i \prec t_j \quad \Longrightarrow \quad \text{$t_i$ must finish before $t_j$ starts.}
$$

A valid plan is a topological ordering $\sigma$ satisfying all precedence constraints.

The planner can solve

$$
\min_{\sigma}
\sum_{i=1}^{N}
w_i C_i(\sigma),
$$

where $C_i(\sigma)$ is completion time of task $i$ under ordering $\sigma$.

## Lagrangian task planning

Introduce constraints on risk, budget, and approvals.  
Then solve

$$
\max_{\pi,\sigma}
\;
\mathbb{E}\left[
\sum_{t=0}^{T}\gamma^t r_t
\right]
-
\lambda_B \bigl(\mathbb{E}[C]-B\bigr)
-
\lambda_R \bigl(\mathbb{E}[\rho]-R_{\max}\bigr)
-
\lambda_H \bigl(\mathbb{E}[H]-H_{\max}\bigr).
$$

The multipliers $\lambda_B,\lambda_R,\lambda_H$ quantify how aggressively the planner should trade value for constraint slack.

## Belief-state planning

The planner rarely knows the true state of the repo or environment.  
Instead it maintains a belief $b_t(x)$ over latent states.

Bayes update:

$$
b_{t+1}(x')
\propto
P(o_{t+1}\mid x',a_t)
\sum_x
P(x'\mid x,a_t)b_t(x).
$$

Planning then happens over beliefs rather than raw states.

## Information-gathering actions

A strong planner will choose to inspect before acting when the expected value of information is positive.

Define

$$
\operatorname{EVI}(u)
=
\mathbb{E}\left[
\max_a \mathbb{E}[R \mid u,a]
\right]
-
\max_a \mathbb{E}[R \mid a],
$$

where $u$ is a prospective information-gathering action.  
If $\operatorname{EVI}(u) > \operatorname{cost}(u)$, gather the information.

This is the formal basis for scout nodes and diagnostic subroutines.

## Replanning trigger

Replanning should occur when model error exceeds tolerance.  
Let predicted next state be $\hat{x}_{t+1}$ and actual observed state be $x_{t+1}$.

Define planning drift:

$$
\delta_t = \|x_{t+1} - \hat{x}_{t+1}\|_{\Sigma^{-1}}^2.
$$

If

$$
\delta_t > \tau_{\text{replan}},
$$

then the planner should update the graph structure or route to recovery nodes.

## Goal satisfaction score

For a mission with goals $g_1,\dots,g_m$, define

$$
S_{\text{goal}}
=
\sum_{i=1}^{m}
\omega_i \mathbf{1}\{g_i \text{ satisfied}\}
-
\sum_{j=1}^{J}
\psi_j \mathbf{1}\{c_j \text{ violated}\}.
$$

This makes explicit that “done” is not just a conversational judgment; it is a constrained satisfaction relation.

## Multi-objective decomposition frontier

Planning is often multi-objective.  
Let

$$
F(\pi) = \bigl(Q(\pi),\, -C(\pi),\, -\rho(\pi),\, -H(\pi)\bigr).
$$

The system should seek Pareto-efficient plans rather than optimizing a single scalar unless business requirements specify weights.

## Summary

Planning in mission graphs is not a prompt engineering exercise.  
It is a disciplined process of:

- belief maintenance
- subgoal selection
- decomposition control
- ordering under constraints
- value-of-information reasoning
- replanning under drift

That is what enables the graph to operate across long horizons rather than merely react turn by turn.
