# 12_verification_orchestration.md

# Verification Orchestration

## Verification is a system, not a checkbox

Chapter 06 defined gates and verifier scores. This chapter specifies how a mission graph *runs* verification at scale:

- compose many verifiers into a single promotion decision
- route evals adaptively under budget and risk constraints
- express "proof obligations" as machine-checkable evidence requirements
- schedule, cache, and reuse verification work across retries and branches

The goal is to make verification a first-class control loop rather than an afterthought.

## Verifier graph

Treat verification itself as a graph.

Let the verifier set be nodes $U = \{u_1,\dots,u_M\}$ and let $F \subseteq U \times U$ be dependencies (for example, typecheck before integration tests).

Define the verifier graph

$$
\mathcal{V} = (U, F).
$$

Each verifier emits a signal

$$
v_{m,t} \in [0,1] \cup \{\bot\},
$$

where $\bot$ means "not run" or "not applicable".

### Verifier bottlenecks and verification cuts

At scale, verification delays behave like graph bottlenecks: a small subset of expensive verifiers can dominate time-to-promotion.

Define a verifier schedule state $\mathcal{A}_t \subseteq U$ (verifiers currently running). Let $d(u_m)$ be expected duration and let $\operatorname{crit}(u_m)$ be a criticality weight (how often it lies on the critical path to promotion).

Define the **verification cut** (a proposed construct) as the set of verifiers that, if delayed, disconnect the mission from a promote-able state under the current obligation set:

$$
\operatorname{Cut}_{i\to j}
=
\{u_m \in U : u_m \text{ is required to discharge some } \varphi \in \mathcal{O}_{i\to j}\}.
$$

Then define cut pressure:

$$
P_{\text{cut}}
=
\sum_{u_m \in \operatorname{Cut}_{i\to j}} \operatorname{crit}(u_m)\, d(u_m).
$$

High $P_{\text{cut}}$ suggests the graph should either:

- introduce disjunctive evidence (alternative verifiers), refactor obligations into cheaper-to-discharge forms, or stage/cached-run cut verifiers earlier.

## Gate composition

For a promotion edge $(i \to j)$, define a composed gate $\Gamma_{i\to j}$ over a set of verifier signals:

$$
\Gamma_{i\to j}(x_t, \hat{y}_t, z_t)
=
\mathbf{1}\{g_{i\to j}(v_t) \ge \tau_{i\to j}\}.
$$

### Hard composition (logical)

For critical safety constraints, use conservative composition:

$$
g_{\min}(v_t) = \min_{m \in \mathcal{M}} v_{m,t}.
$$

This implements an AND gate: any single failure blocks promotion.

### Soft composition (risk-weighted)

For non-critical edges, use a calibrated aggregator:

$$
g_{\text{logit}}(v_t)
=
\sigma\!\left(\beta_0 + \sum_{m \in \mathcal{M}} \beta_m \cdot \operatorname{logit}(v_{m,t})\right).
$$

This supports trading off redundant verifiers without being reckless.

### Disjunctive composition (evidence alternatives)

Sometimes multiple forms of evidence can satisfy the same intent (for example, fuzzing OR property-based tests).

Represent this as:

$$
\Gamma = \Gamma^{(a)} \lor \Gamma^{(b)} \lor \cdots
$$

where each alternative is itself a composed sub-gate.

## Proof obligations

Mission graphs should state what must be proven before promotion.

For edge $(i \to j)$ define an obligation set:

$$
\mathcal{O}_{i\to j} = \{\varphi_1,\dots,\varphi_K\},
$$

where each $\varphi_k$ is a checkable claim such as:

- interfaces preserved
- migrations are reversible
- no secret material is logged
- performance regression below threshold
- deployment guardrails configured

Define a discharge function that maps artifacts and verifier outputs into satisfaction:

$$
\operatorname{Discharge}(\varphi_k; z_t, v_t, e_t) \in \{0,1\},
$$

where $e_t$ is an evidence bundle (logs, traces, reports, attestations).

Promotion is allowed only if

$$
\prod_{k=1}^{K} \operatorname{Discharge}(\varphi_k; z_t, v_t, e_t) = 1.
$$

This turns "quality" into explicit obligations rather than vibes.

### Obligation algebra (obligation lattice and frontier)

Proof obligations are not merely a list; they have internal structure.
Two obligations can overlap (one implies another), and some obligations allow multiple evidence paths (OR).

Define a partial order over obligations by semantic implication:

$$
\varphi_a \preceq \varphi_b
\quad \Longleftrightarrow \quad
(\varphi_b \Rightarrow \varphi_a).
$$

Read this as: satisfying $\varphi_b$ is at least as strong as satisfying $\varphi_a$.
Under $\preceq$, obligations form an **obligation lattice** (proposed construct) with:

- meet (conjunction): $\varphi_a \wedge \varphi_b$
- join (weakest common strengthening): $\varphi_a \vee \varphi_b$

This matters operationally because the orchestrator can reduce redundant work by selecting an *antichain* (a minimal set of non-implied obligations) and discharging only that set.

Let $\operatorname{Min}(\mathcal{O}_{i\to j})$ denote the minimal antichain under $\preceq$. Replace the naive discharge test with:

$$
\prod_{\varphi \in \operatorname{Min}(\mathcal{O}_{i\to j})}
\operatorname{Discharge}(\varphi; z_t, v_t, e_t)
=
1.
$$

Now add costs. Let $C(\varphi)$ be expected cost to discharge $\varphi$ (compute + latency + human).
Let $\Delta R(\varphi)$ be expected reduction in tail risk from discharging it (under current belief).
Define an **obligation frontier** (proposed construct) as the Pareto set:

$$
\mathcal{F}_{i\to j}
=
\operatorname{Pareto}
\left\{
(C(\varphi),\; -\Delta R(\varphi))
:\;
\varphi \in \operatorname{Min}(\mathcal{O}_{i\to j})
\right\}.
$$

The frontier makes explicit which obligations are "expensive but safety-critical" versus "cheap and low-impact", enabling principled staging and deferral policies.

## Eval routing policy

Running every verifier every time is wasteful and often slower than shipping. Routing chooses *which* evals to run next.

Let $\mathcal{E}(z_t)$ be the set of eligible evals for artifact state $z_t$.
The orchestrator chooses a subset $S_t \subseteq \mathcal{E}(z_t)$.

One principled objective is value-of-eval under constraints:

$$
\max_{S_t}
\;
\operatorname{VOE}(S_t \mid x_t)
\quad \text{s.t.}\quad
\sum_{e \in S_t} c(e) \preceq b_t.
$$

Where:

- $c(e)$ is the cost vector of eval $e$ (compute, time, tokens, human)
- $b_t$ is remaining budget

### Risk-conditioned routing

Let predicted tail risk of promoting without extra evals be $\widehat{\operatorname{CVaR}}_\alpha(L \mid x_t)$.

Route additional evals when:

$$
\widehat{\operatorname{CVaR}}_\alpha(L \mid x_t) > R_{\max}(b_t).
$$

This couples verification intensity to risk tolerance and remaining slack.

### Change-aware routing

Let change impact score be $\Delta(z_t)$ (for example, lines touched, dependency centrality, surface area).
Then require a minimum eval set size:

$$
|S_t| \ge s_0 + s_1 \Delta(z_t).
$$

This prevents "tiny evals" from approving large, high-impact diffs.

### Sequential eval cascades (verification as active measurement)

In practice, eval routing is sequential: run a cheap test, update belief, then decide whether a more expensive suite is still worth it.

Let the orchestrator maintain a belief $b_t$ over latent failure modes $\mathcal{F}$ (not to be confused with the frontier above), and let each eval $e$ be an information-gathering action that updates the belief.

Let $c(e)$ be a cost vector and scalarize it as $\tilde{c}(e) = \langle w, c(e)\rangle$ for weights $w \succeq 0$.

Define a one-step **verification cascade** rule (proposed construct):

$$
e_t^\star
=
\arg\max_{e \in \mathcal{E}(z_t)}
\frac{
\mathbb{E}\bigl[\Delta \widehat{\operatorname{CVaR}}_\alpha(L)\mid e, x_t\bigr]
}{
\tilde{c}(e)
},
$$

where $\Delta \widehat{\operatorname{CVaR}}_\alpha(L)$ is the expected reduction in predicted tail risk if $e$ is run and incorporated.
The cascade runs evals in descending risk-reduction density until promotion confidence clears the threshold or budget is exhausted.

This gives the orchestrator a concrete policy that naturally prefers:

- cheap, high-signal evals early
- expensive, low-signal evals only when risk remains high
- and stage-specific suites when change impact $\Delta(z_t)$ is large

### Calibration debt (when verifier scores become liabilities)

Soft gating relies on calibrated scores. But calibration decays as codebases, test suites, and threat models drift.

Define an empirical calibration error for verifier $u_m$ over a rolling window:

$$
\operatorname{CE}_t(u_m) = \mathbb{E}\left[(v_{m,t} - y_t)^2\right],
$$

where $y_t \in \{0,1\}$ is eventual correctness of the promoted artifact (measured by regressions, incidents, or downstream audits).

Define **calibration debt** (proposed construct) as a cumulative liability:

$$
D_t(u_m)
=
\rho D_{t-1}(u_m)
 \operatorname{CE}_t(u_m)
 \lambda_{\text{miss}} \mathbf{1}\{v_{m,t}=\bot \text{ when required}\}.
$$

When $D_t(u_m)$ is high, the orchestrator should respond by:

- tightening thresholds on gates that depend on $u_m$
- routing to alternative evidence paths (disjunctive composition)
- or scheduling a "recalibration mission" (repair the verifier, not the code)

This treats verifier degradation as first-class technical debt rather than mysterious flakiness.

## Orchestrating verification across the mission graph

Verification should not be attached only at the end.

Define verification stages:

- pre-change (spec + risk scan)
- post-change local (lint, typecheck, unit tests)
- integration (integration/regression, contract checks)
- pre-deploy (security, performance, release checks)
- canary (online health gates)

Each stage corresponds to a gate family $\Gamma^{\text{stage}}$ and obligation family $\mathcal{O}^{\text{stage}}$.

## Scheduling and caching

Verifier orchestration is a scheduling problem with reuse.

Let an eval $e$ produce a result $r(e, z)$ and evidence $\eta(e, z)$.
Cache it keyed by an artifact fingerprint $h(z)$:

$$
\operatorname{cache}[e, h(z)] = (r, \eta).
$$

An eval is reusable if its dependency closure has not changed:

$$
\operatorname{Reuse}(e, z_t, z_{t'}) = 1
\iff
h(\operatorname{deps}(e, z_t)) = h(\operatorname{deps}(e, z_{t'})).
$$

This is how mission graphs avoid re-running expensive suites after trivial edits.

## Counterexample-driven loops

When a verifier fails, the system should not simply retry blindly.

Let a verifier produce a counterexample set $C_t$ (failing tests, repro steps, traces).
Route to a repair node with objective:

$$
\min_{\text{patch}}
\;
\operatorname{cost}(\text{patch})
\quad \text{s.t.}\quad
\forall c \in C_t: \; \Gamma(c \mid \text{patch}) = 1.
$$

This makes failure information a structured control input.

### Counterexample reservoirs (cross-mission regression memory)

Counterexamples are the highest-value verification artifacts: they compress failures into reproducible evidence.
But raw failure streams are noisy, and storing everything is expensive.

Define a persistent **counterexample reservoir** (proposed construct) $\mathcal{R}$, an evolving set of counterexamples retained across missions.
Each counterexample $c \in \mathcal{R}$ has:

$$
c = (\text{repro},\; \text{severity},\; \text{novelty},\; \text{scope},\; \text{last\_seen}).
$$

Retain counterexamples under a budget $|\mathcal{R}| \le R_{\max}$ by maximizing a portfolio objective:

$$
\max_{\mathcal{R}}
\sum_{c \in \mathcal{R}}
\left(
w_1 \text{severity}(c)
+ w_2 \text{novelty}(c)
+ w_3 \text{scope}(c)
- w_4 \text{staleness}(c)
\right).
$$

The reservoir becomes a reusable regression suite that is:

- diversity-preserving (novelty term)
- risk-sensitive (severity term)
- and self-cleaning (staleness term)

This closes the loop between verification and learning without requiring full policy-gradient machinery.

## Verifier health and drift

Verifiers themselves can degrade (flaky tests, stale policies, noisy analyzers).

Track verifier reliability:

$$
\operatorname{Rel}(u_m)
=
1 - \Pr(\text{flake} \mid u_m).
$$

Downweight or quarantine verifiers with low reliability:

$$
\beta_m \leftarrow \beta_m \cdot \mathbf{1}\{\operatorname{Rel}(u_m) \ge r_{\min}\}.
$$

Without this, gating becomes a source of delay and mistrust rather than safety.

### Reliability as a posterior, not a guess

To make reliability actionable, model it explicitly.
Let a verifier $u_m$ have latent flake rate $\pi_m$.
Track outcomes of repeated runs on stable artifacts (or on replayed evidence bundles):

- $f_m$ flaky failures (non-reproducible)
- $s_m$ stable outcomes (reproducible pass/fail)

Use a Beta posterior:

$$
\pi_m \mid f_m, s_m \sim \operatorname{Beta}(\alpha_0 + f_m,\; \beta_0 + s_m).
$$

Then define a conservative reliability score:

$$
\operatorname{Rel}(u_m) = 1 - \Pr(\pi_m \ge \pi_{\max} \mid f_m, s_m).
$$

This integrates naturally into soft composition by downweighting verifiers with high posterior flake probability.

## Evidence ledger

To support governance and postmortems, the mission graph should store evidence as append-only records:

$$
\mathcal{L}_t = \mathcal{L}_{t-1} \cup \{(t, z_t, S_t, v_t, e_t)\}.
$$

The ledger makes two things possible:

- reproducibility: rerun the same checks against the same artifact fingerprint
- auditability: answer "why did we promote" with concrete evidence

### Evidence-to-obligation attestation

The strongest form of auditability is an explicit map from each obligation to the evidence that discharged it.

Define an attestation map:

$$
\mathcal{A}_{i\to j}(\varphi_k)
=
\{(u_m,\; \eta(u_m, z_t)) : \operatorname{Discharge}(\varphi_k; z_t, v_t, e_t)=1\}.
$$

Then define obligation completeness:

$$
\operatorname{Comp}(\mathcal{O}_{i\to j})
=
\frac{
\left|\{\varphi_k \in \mathcal{O}_{i\to j} : \mathcal{A}_{i\to j}(\varphi_k) \ne \emptyset\}\right|
}{
|\mathcal{O}_{i\to j}|
}.
$$

This creates an operational invariant: promotion requires $\operatorname{Comp}=1$.
If a gate is passed but completeness is low, the system has a governance bug (evidence is missing, not merely low-scoring).

## Summary

This chapter adds a mission-graph-scale verification layer:

- a verifier graph $\mathcal{V}$ with dependencies
- composed gates for hard, soft, and disjunctive evidence
- proof obligations $\mathcal{O}_{i\to j}$ discharged by evidence
- eval routing policies that couple verification intensity to risk and budget
- scheduling and caching rules to avoid waste across retries and branches

The net effect is that verification becomes an explicit, optimizable subsystem of the mission graph.

New concepts introduced in this chapter:

- **Verification cuts** and **cut pressure**: identify verifier bottlenecks that dominate time-to-promotion.
- **Obligation lattice** and **obligation frontier**: structure obligations to remove redundancy and expose cost vs risk tradeoffs.
- **Verification cascades**: sequential eval routing that maximizes risk-reduction density under budget constraints.
- **Calibration debt**: treat miscalibrated verifier scores as accumulating liabilities that force stricter gates or verifier repair.
- **Counterexample reservoirs**: persist diverse, high-severity counterexamples across missions as a budgeted regression memory.
