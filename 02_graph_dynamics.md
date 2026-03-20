# 02_graph_dynamics.md

# Graph Dynamics

## State-space view

Let the mission state at time $t$ be

$$
x_t = \begin{bmatrix}
z_t \\
m_t \\
b_t \\
d_t
\end{bmatrix},
$$

where:

- $z_t$ = artifact and repo state
- $m_t$ = memory / context state
- $b_t$ = remaining budget vector
- $d_t$ = deployment and environment state

The dynamics evolve under node actions $a_t$:

$$
x_{t+1} = f(x_t, a_t, \xi_t),
$$

with uncertainty $\xi_t$ representing runtime noise, test flakiness, missing observability, and external changes.

## Dependency graph

Let $A$ be the adjacency matrix of the mission graph:

$$
A_{ij} =
\begin{cases}
1 & \text{if } (v_i,v_j)\in E,\\
0 & \text{otherwise.}
\end{cases}
$$

The graph Laplacian is

$$
L = D - A,
$$

where $D$ is the diagonal out-degree matrix.

This matters because bottlenecks, weak cuts, and central coordination load can be analyzed via spectral properties of $L$.

## Spectral bottleneck metric

Let $\lambda_2(L)$ denote the algebraic connectivity.  
Low $\lambda_2(L)$ implies fragile coordination.

A graph robustness score can be written as

$$
\mathcal{R}_{\text{graph}} = \omega_1 \lambda_2(L) - \omega_2 \kappa(L),
$$

where $\kappa(L)$ is a condition or imbalance measure.

## Dynamic readiness

Each node has a readiness variable $r_t^{(i)} \in [0,1]$:

$$
r_{t+1}^{(i)}
=
\sigma\!\left(
\sum_{j=1}^{n} A_{ji} y_t^{(j)}
-
\sum_{k=1}^{K} \mu_k c_{k,t}^{(i)}
+
\theta_i
\right),
$$

where:

- $y_t^{(j)}$ = quality-adjusted completion signal from predecessor $j$
- $c_{k,t}^{(i)}$ = unsatisfied prerequisite constraint $k$
- $\sigma(\cdot)$ = logistic link

A node may execute only if $r_t^{(i)} \ge \tau_i$.

## Graph flow of artifacts

Let $q_t^{(i)}$ be the artifact quality at node $i$.  
A simple propagation model is

$$
q_{t+1}^{(i)}
=
\alpha_i q_t^{(i)}
+
\sum_{j=1}^{n} W_{ji} q_t^{(j)}
-
\delta_i e_t^{(i)},
$$

where:

- $W$ is a weighted transfer matrix
- $e_t^{(i)}$ is node-local error injection
- $\alpha_i$ captures self-refinement

This formalizes a key idea: downstream quality is a graph-coupled process, not an isolated node output.

## Branching and merge consistency

Suppose the graph branches into states $x_t^{(1)},\dots,x_t^{(B)}$.  
A merge operator $\mathcal{M}$ produces

$$
x_t^{\text{merge}} = \mathcal{M}(x_t^{(1)},\dots,x_t^{(B)}).
$$

Define branch divergence as

$$
\Delta_{\text{branch}}
=
\sum_{i<j}
\| \psi(x_t^{(i)}) - \psi(x_t^{(j)}) \|_2^2,
$$

where $\psi(\cdot)$ projects states into a semantic or artifact embedding space.

A merge should be accepted only if

$$
\Delta_{\text{branch}} \le \epsilon_{\text{merge}}
$$

or if explicit reconciliation steps reduce it below threshold.

## Reachability

Let $\mathcal{X}_{\text{ship}}$ denote the set of shippable states.  
Then the mission is viable if there exists a policy $\Pi$ such that

$$
\Pr_\Pi\bigl(\exists t \le T : x_t \in \mathcal{X}_{\text{ship}}\bigr) \ge p_{\min}.
$$

This is the correct mission-level success criterion.

## Controllability intuition

Linearizing around an operating point gives

$$
x_{t+1} \approx F x_t + G a_t.
$$

The controllability matrix is

$$
\mathcal{C} = [G,\; FG,\; F^2G,\; \dots,\; F^{n-1}G].
$$

If $\operatorname{rank}(\mathcal{C})$ is low, the graph cannot adequately steer mission state toward delivery targets.  
In practice, this means you have either:

- insufficient node diversity
- poor fallback edges
- missing intervention channels
- too little observability

## Delay-sensitive graph dynamics

Some edges have delay $\delta_{ij}$.  
Then

$$
x_{t+1}
=
f\!\left(
x_t,\,
a_t,\,
\{a_{t-\delta_{ij}}^{(j)}\}_{(j,i)\in E}
\right).
$$

This is crucial for modeling:

- async code review
- delayed test results
- human approvals
- deployment health feedback

## Stability criterion

Define a Lyapunov candidate $V(x_t)\ge 0$.  
If

$$
\mathbb{E}[V(x_{t+1}) - V(x_t) \mid x_t] \le -\alpha \|x_t\|^2 + \beta
$$

for $\alpha>0$, then the mission process is mean-square stable up to noise floor $\beta$.

Operationally, stability means the system does not explode into retry storms, budget collapse, or incoherent branching.

## Graph observability

Let observations be

$$
o_t = Hx_t + \nu_t.
$$

The observability matrix is

$$
\mathcal{O}
=
\begin{bmatrix}
H \\
HF \\
HF^2 \\
\vdots \\
HF^{n-1}
\end{bmatrix}.
$$

Low observability means the system cannot tell whether it is making progress or merely generating artifacts.

## Summary

Mission graphs must be analyzed as dynamical systems.  
The useful questions are not merely “what agent should I spawn?” but:

- Is the graph connected enough?
- Are shipping states reachable?
- Are merges consistent?
- Is the system stable under retries and delays?
- Can state be observed well enough to control?

That shift is what makes the architecture stronger than subagents.
