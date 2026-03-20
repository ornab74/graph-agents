# 03_context_memory.md

# Context and Memory

## Why context is a control problem

In a mission graph, context is not just prompt stuffing.  
It is a constrained information-routing problem:

- too little context increases failure probability
- too much context increases latency, confusion, and cost
- stale context creates policy drift
- inconsistent context produces branch divergence

The goal is to maximize useful information delivered to a node under token, latency, and reliability budgets.

## Memory model

Let the memory state be

$$
m_t = (m_t^{\text{episodic}},\, m_t^{\text{semantic}},\, m_t^{\text{artifact}},\, m_t^{\text{policy}}).
$$

Interpretation:

- episodic memory: what happened in this mission
- semantic memory: reusable knowledge across missions
- artifact memory: code, diffs, tests, logs, docs
- policy memory: rules, permissions, compliance constraints

## Retrieval objective

For node $v$, retrieve a context bundle $c_t^{(v)}$ from memory $m_t$ by solving

$$
c_t^{(v)}
=
\arg\max_{c \subseteq m_t}
\Bigl[
I(c; y_t^{(v)} \mid o_t^{(v)})
-
\lambda_{\text{tok}} |c|
-
\lambda_{\text{stale}} S(c)
\Bigr],
$$

where:

- $I(c; y_t^{(v)} \mid o_t^{(v)})$ = conditional mutual information between retrieved context and desired node output
- $|c|$ = token or context size
- $S(c)$ = staleness penalty

This casts retrieval as an information bottleneck problem.

## Context value density

Define value density:

$$
\operatorname{VD}(c)
=
\frac{
I(c; y_t^{(v)} \mid o_t^{(v)})
}{
\operatorname{cost}(c)
}.
$$

A scheduler should prefer context elements with high value density rather than high raw relevance.

## Memory update law

After node execution, memory updates via

$$
m_{t+1}
=
\mathcal{U}\bigl(
m_t,\,
o_t,\,
a_t,\,
\hat{y}_t,\,
\Gamma_t,\,
\zeta_t
\bigr),
$$

where $\Gamma_t$ are verifier outputs and $\zeta_t$ are environment outcomes such as test results or deployment health.

A concrete parametrization is

$$
m_{t+1}
=
(1-\alpha_t)m_t
+
\alpha_t \Phi(o_t,a_t,\hat{y}_t,\Gamma_t,\zeta_t),
$$

with adaptive write coefficient $\alpha_t$.

## Staleness dynamics

Each memory item $i$ has freshness score $f_{i,t}$:

$$
f_{i,t+1}
=
\rho_i f_{i,t}
+
\chi_i \mathbf{1}\{\text{validated at } t\}
-
\omega_i \mathbf{1}\{\text{contradicted at } t\}.
$$

Retrieved memory should satisfy

$$
f_{i,t} \ge f_{\min}.
$$

## Summarization as lossy compression

Let raw history be $h_t$ and summary be $s_t = \Sigma(h_t)$.  
A useful objective is

$$
\min_{\Sigma}
\;
\mathbb{E}\left[
d\bigl(h_t,\hat{h}_t(s_t)\bigr)
\right]
+
\beta |s_t|,
$$

where $d(\cdot,\cdot)$ is task-relevant distortion and $\hat{h}_t$ reconstructs the latent decision state.

This avoids a common mistake: compressing for readability rather than control fidelity.

## Retrieval consistency across branches

If branches $b_1$ and $b_2$ retrieve context sets $c^{(1)}$ and $c^{(2)}$, define contextual inconsistency:

$$
\Delta_c
=
1
-
\frac{
|c^{(1)} \cap c^{(2)}|
}{
|c^{(1)} \cup c^{(2)}|
}.
$$

More generally, if using embeddings,

$$
\Delta_c^{\text{emb}}
=
\left\|
\frac{1}{|c^{(1)}|}\sum_{u\in c^{(1)}} e_u
-
\frac{1}{|c^{(2)}|}\sum_{u\in c^{(2)}} e_u
\right\|_2.
$$

Large divergence should trigger a merge warning.

## Memory trust score

Each memory record $i$ gets a trust estimate

$$
T_i
=
\sigma\!\left(
\beta_0
+
\beta_1 \cdot \text{verifier\_pass}_i
+
\beta_2 \cdot \text{recency}_i
+
\beta_3 \cdot \text{source\_authority}_i
-
\beta_4 \cdot \text{contradictions}_i
\right).
$$

Then retrieval can be constrained:

$$
\sum_{i \in c_t^{(v)}} (1 - T_i) \le \epsilon_T.
$$

## Memory-aware node policy

A node should be memory-conditioned:

$$
a_t^{(v)}
\sim
\pi_v\!\left(
a \mid o_t^{(v)}, R(m_t, o_t^{(v)}), b_t
\right),
$$

where $R(\cdot)$ is the retrieval operator.

This makes memory a first-class control input.

## Entropy management

Let the uncertainty over the correct next action be $H(A_t \mid o_t,m_t)$.  
A good context system should reduce entropy per unit cost:

$$
\operatorname{ECE}
=
\frac{
H(A_t \mid o_t) - H(A_t \mid o_t,m_t)
}{
\operatorname{cost}(m_t \to c_t)
}.
$$

Call this **entropy-collapse efficiency**.

## Summary

Mission graphs require a context system that is:

- persistent
- freshness-aware
- trust-scored
- compression-aware
- branch-consistent
- budget-constrained

Without that, “more context” just becomes a noisier failure mode.
