# 11_context_routing_policy.md

# Context Routing Policy

## Context is an execution layer

The mission graph does not merely execute nodes. It also routes information.

At graph scale, the context system must decide:

- what evidence is routed to which node
- what is cached vs recomputed
- what is shared across branches
- what is written as durable memory
- what is withheld due to permissions

This chapter specifies a context-routing policy as a first-class control law.

## Objects

Let the global memory store at time $t$ be a set of records

$$
\mathcal{M}_t = \{m_1,\dots,m_N\}.
$$

Each record $m_i$ has metadata:

$$
m_i = (\text{id}_i,\; \text{payload}_i,\; \text{type}_i,\; f_{i,t},\; T_{i,t},\; \theta_i),
$$

where:

- $f_{i,t}\in[0,1]$ is freshness
- $T_{i,t}\in[0,1]$ is trust
- $\theta_i$ is a permission label (who may read/use it)

For each node $v$, define a context bundle $c_t^{(v)} \subset \mathcal{M}_t$.

## Router policy

Define a router that selects context for node $v$ given observations $o_t^{(v)}$, global state $x_t$, and budgets $b_t$:

$$
c_t^{(v)} \sim \mathcal{R}_v(\cdot \mid o_t^{(v)}, x_t, b_t).
$$

The router can be deterministic (argmax) or stochastic (soft selection) depending on exploration needs.

### Router objective

Let the node output be $\hat{y}_t^{(v)}$ and the downstream value be $U(\hat{y}_t^{(v)})$. A useful routing objective is

$$
\max_{c \subseteq \mathcal{M}_t}
\;
\mathbb{E}\left[
U(\hat{y}_t^{(v)}) \mid c, o_t^{(v)}
\right]
-
\lambda_{\text{tok}} \, \operatorname{Tok}(c)
-
\lambda_{\text{lat}} \, \operatorname{Lat}(c)
-
\lambda_{\text{stale}} \, \operatorname{Stale}(c)
$$

subject to:

$$
\sum_{m_i \in c} (1 - T_{i,t}) \le \epsilon_T,
\qquad
\min_{m_i \in c} f_{i,t} \ge f_{\min},
\qquad
\operatorname{Perm}(v, c)=1.
$$

Interpretation:

- maximize expected utility conditional on the context
- pay explicit costs for tokens, latency, and staleness
- constrain total distrust mass, minimum freshness, and permissions

## Context budgets

Each node has a context budget vector:

$$
\kappa_v
=
\begin{bmatrix}
\kappa_v^{\text{tokens}} \\
\kappa_v^{\text{latency}} \\
\kappa_v^{\text{sources}}
\end{bmatrix}.
$$

Routing must satisfy:

$$
\operatorname{Tok}(c_t^{(v)}) \le \kappa_v^{\text{tokens}},
\qquad
\operatorname{Lat}(c_t^{(v)}) \le \kappa_v^{\text{latency}},
\qquad
|c_t^{(v)}| \le \kappa_v^{\text{sources}}.
$$

This forces the router to prefer high-density evidence rather than large piles of loosely related text.

## Evidence bundles

At graph scale, memory records should be grouped into evidence bundles to preserve provenance.

Define an evidence bundle $B$ as

$$
B = (S,\; \text{claim},\; \text{tests},\; \text{logs},\; \text{diffs}),
$$

where $S$ is a set of sources (files, commands, traces), and "claim" is what the bundle asserts.

Routing should prefer bundles over orphaned facts because bundles can be audited and revalidated.

## Provenance graph and audit distance

Bundles preserve provenance locally. At mission scale, provenance must also be graph-shaped.

Define a provenance graph

$$
\mathcal{P}_t = (\mathcal{M}_t, \mathcal{E}_t^{\text{prov}}),
$$

where $(m_i \to m_j) \in \mathcal{E}_t^{\text{prov}}$ means record $m_j$ was derived from $m_i$
(summarized, transformed, inferred, or otherwise computed from it).

Let $\mathcal{S}_t \subseteq \mathcal{M}_t$ denote ground-truth sources: command outputs, file snapshots,
build logs, test reports, deployment telemetry, and signed approvals. These are the roots of audit.

### Provenance radius (new concept)

Define the **provenance radius** of record $m$ as its audit distance to sources:

$$
\operatorname{PR}_t(m)
=
\min_{s \in \mathcal{S}_t} \operatorname{dist}_{\mathcal{P}_t}(s, m),
$$

with $\operatorname{PR}_t(m)=\infty$ if $m$ is not reachable from any source in $\mathcal{P}_t$.

Interpretation:

- $\operatorname{PR}=0$ means directly observed
- larger $\operatorname{PR}$ means more derived
- $\operatorname{PR}=\infty$ means orphaned assertion

High-stakes nodes should operate under a provenance cap:

$$
\max_{m_i \in c_t^{(v)}} \operatorname{PR}_t(m_i) \le \kappa_v^{\text{prov}}.
$$

This is not redundant with trust. Trust is a learned estimate; provenance radius is a structural guarantee about how far
inference has moved away from evidence.

### Audit distance as a routing cost

In addition to tokens, latency, and staleness, route with an explicit audit cost:

$$
\operatorname{Audit}(c)
=
\sum_{m_i \in c} \omega_{\text{prov}} \operatorname{PR}_t(m_i).
$$

Then the router objective can include:

$$
- \lambda_{\text{audit}} \operatorname{Audit}(c).
$$

Operational reading: for critical decisions, it is worth paying extra tokens to stay near sources.

## Evidence economics and liquidity

Context selection is not merely "what is relevant", but "what is worth paying for now".
Two common waste modes in autonomous work are:

- low-value context that consumes the token budget and increases confusion
- high-risk context that is cheap to include but expensive to be wrong about

### Evidence exchange rate (new concept)

Define the **evidence exchange rate** (EER) of a record $m_i$ for node $v$ as expected risk reduction per unit cost:

$$
\operatorname{EER}_{v,t}(m_i)
=
\frac{
\mathbb{E}\left[R_t^{\text{before}} - R_t^{\text{after}} \mid m_i, o_t^{(v)}\right]
}{
\operatorname{Tok}(m_i) + \eta \operatorname{Lat}(m_i)
}.
$$

High $\operatorname{EER}$ items are cheap safety. Low $\operatorname{EER}$ items are expensive noise.
Routers can enforce a floor:

$$
\min_{m_i \in c_t^{(v)}} \operatorname{EER}_{v,t}(m_i) \ge \tau_{\text{eer}}^{(v)},
$$

or equivalently allocate most of the budget to the top quantile of $\operatorname{EER}$ items.

### Context liquidity (new concept)

Some evidence can be revalidated quickly (re-run a unit test), while other evidence is costly to refresh
(a long integration suite, production canary windows, or a human approval).

Define **context liquidity** of record $m_i$ as inverse revalidation cost:

$$
L_{i,t}
=
\frac{1}{\operatorname{cost}(\operatorname{Revalidate}(m_i)) + \epsilon}.
$$

Low liquidity implies that if the mission drifts, the record is likely to become stale before it can be cheaply reconfirmed.
One simple mechanism is liquidity-aware trust:

$$
T'_{i,t}
=
T_{i,t}
-
\xi \cdot (1 - L_{i,t}).
$$

Then apply the existing distrust-mass constraint using $T'_{i,t}$ in place of $T_{i,t}$.

## Context gates

Just as code transitions are gated, context routing can be gated.

Define a context gate for node $v$:

$$
\Gamma^{\text{ctx}}_v(c_t^{(v)}, x_t) \in \{0,1\}.
$$

Examples:

- forbid untrusted memory for high-stakes nodes (deploy, security)
- require presence of a test result bundle before integration steps
- require a "repo census" bundle before any write to the codebase

If the gate fails, route to an information-gathering node rather than letting execution proceed with weak context.

## Context shock and firebreaks

Freshness and trust are not enough if a single wrong assumption can propagate through the graph.
At mission scale, routing needs containment semantics.

### Context shock index (new concept)

Let $\mathcal{K}_t$ be a set of mission-critical claims the current plan depends on (API behavior assumptions, build tooling
assumptions, deployment guardrails, and invariants that gate promotion). When a new observation contradicts existing memory,
define a **context shock index**:

$$
\operatorname{CSI}_t
=
\frac{
|\{k \in \mathcal{K}_t : k \text{ contradicted at } t\}|
}{
|\mathcal{K}_t| + \epsilon
}.
$$

If $\operatorname{CSI}_t$ exceeds a threshold, the right response is not to "retry harder" but to change routing mode:

- freeze writes from derived records with high provenance radius
- require lower provenance radius caps for all high-stakes nodes
- route to information-gathering actions (repo census, telemetry scan, spec refresh)

In other words, contradiction density becomes a control signal.

### Context firebreak (new concept)

Implement a **context firebreak** as a graph-level rule that prevents suspected records from crossing into sensitive nodes.
Let $\mathcal{C}_t^{\text{sus}} \subseteq \mathcal{M}_t$ be suspected records (low trust, high PR, or recently contradicted).
Define:

$$
\operatorname{Firebreak}(v, c)
=
\mathbf{1}\{c \cap \mathcal{C}_t^{\text{sus}} = \emptyset\}.
$$

Then strengthen the context gate for high-stakes nodes:

$$
\Gamma^{\text{ctx}}_v(c_t^{(v)}, x_t) = 1
\Rightarrow
\operatorname{Firebreak}(v, c_t^{(v)}) = 1.
$$

Operationally, the firebreak forces safe fallback: the router must use source-near evidence even if the contaminated
derived memory looks "relevant".

## Write policy as memory transactions

Node outputs should not be written to durable memory automatically. They should be committed under a transaction rule.

Let $w_t^{(v)}$ be the proposed memory write set from node $v$. Commit if:

$$
\Gamma^{\text{write}}_v(w_t^{(v)}, x_t) = 1
$$

and the write is bounded:

$$
\operatorname{Tok}(w_t^{(v)}) \le \kappa_v^{\text{write}}.
$$

### Two-phase commit intuition

Use a simple two-phase commit across critical writes:

1. **prepare**: write to a staging area with provenance and verifiers attached
2. **commit**: promote to durable memory only after verifiers pass

This prevents "confidence-shaped memory" from contaminating future routing.

## Consistency across branches

Branching creates competing narratives. The context system must choose a consistency model.

Let branches be $b \in \{1,\dots,B\}$ with memory projections $\mathcal{M}_t^{(b)}$.

Define a shared core

$$
\mathcal{M}_t^{\text{core}} = \bigcap_b \mathcal{M}_t^{(b)}
$$

and branch-local deltas

$$
\Delta \mathcal{M}_t^{(b)} = \mathcal{M}_t^{(b)} \setminus \mathcal{M}_t^{\text{core}}.
$$

Routing policy:

- deploy, security, and governance nodes route only from $\mathcal{M}_t^{\text{core}}$ unless explicitly overridden
- exploration nodes may route from $\Delta \mathcal{M}_t^{(b)}$ to preserve diversity

### Core-delta leases (new concept)

A static core/delta split is not enough. Branches evolve, and the meaning of "core" should expire unless renewed.

Define a **core-delta lease** $\ell$ as:

$$
\ell = (\mathcal{M}^{\text{core}},\; t_{\text{start}},\; t_{\text{ttl}},\; \pi_{\text{renew}}),
$$

where $t_{\text{ttl}}$ is a lease duration and $\pi_{\text{renew}}$ is a renewal policy (what evidence is required to extend the lease).

Reads from the core for high-stakes nodes are permitted only under an active lease:

$$
\operatorname{LeaseOK}(t)
=
\mathbf{1}\{t - t_{\text{start}} \le t_{\text{ttl}}\}.
$$

Then enforce:

$$
\Gamma^{\text{ctx}}_v(c_t^{(v)}, x_t) = 1
\Rightarrow
\operatorname{LeaseOK}(t)=1
\quad \text{for high-stakes } v.
$$

If the lease expires, route to renewal actions: regenerate a repo census, rerun key tests, or request human confirmation.
This turns branch consistency from a vague guarantee into a timed contract that is explicitly maintained.

### Merge precondition

Before branch merge, require contextual alignment:

$$
\Delta_c
=
1 - \frac{|\mathcal{M}_t^{(b_1)} \cap \mathcal{M}_t^{(b_2)}|}{|\mathcal{M}_t^{(b_1)} \cup \mathcal{M}_t^{(b_2)}|}
\le \epsilon_{\text{ctx-merge}}.
$$

If not, route to a reconciliation node that resolves contradictions and produces a new core bundle.

## Staleness and invalidation

Memory must decay unless revalidated.

Let freshness evolve as

$$
f_{i,t+1}
=
\rho_i f_{i,t}
+
\chi_i \mathbf{1}\{\text{revalidated at } t\}
-
\omega_i \mathbf{1}\{\text{contradicted at } t\}.
$$

An invalidation rule for critical records:

$$
f_{i,t} < f_{\min}
\;\Rightarrow\;
m_i \text{ becomes non-routable for high-stakes nodes.}
$$

This ensures that old assumptions do not silently become active constraints.

## Privacy and permissioned routing

Context routing is a privilege boundary.

Let $\theta_i$ be the label on record $m_i$, and let $\Theta_v$ be the node's permission set. Define:

$$
\operatorname{Perm}(v, c)
=
\mathbf{1}\{\forall m_i \in c:\; \theta_i \in \Theta_v\}.
$$

If permission fails, the router should:

- redact the record to a weaker, approved representation
- request an approval edge (human or governor)
- or route to an alternative evidence source

Never silently route disallowed memory; that creates governance violations disguised as "helpful context."

## Caching and reuse

Many context computations are expensive (repo scans, dependency graphs, test inventories).

Let $g$ be a computed context artifact with compute cost $C(g)$ and reuse probability $p_{\text{reuse}}$. Cache if:

$$
p_{\text{reuse}} \cdot C(g) > C_{\text{store}}(g) + C_{\text{invalidate}}(g).
$$

This turns caching into an explicit economic decision rather than an ad-hoc implementation detail.

## Summary

Context routing is a policy layer that must be:

- budgeted (tokens, latency, sources)
- gated (context gates before execution)
- permissioned (no silent leakage)
- transactional (staged writes with verifiers)
- branch-consistent (core vs delta memory)
- freshness-aware (invalidation and revalidation)
- provenance-aware (audit distance and provenance caps)
- economics-aware (exchange rate and liquidity)
- shock-aware (firebreaks and safe-mode routing)

## What this chapter adds

This chapter upgrades memory from "retrieve relevant stuff" into a graph-level routing and consistency policy: explicit router objectives, context budgets, context gates, transactional writes, branch consistency rules, and permissioned routing. It makes context a controllable, auditable layer of mission execution rather than an informal prompt ingredient.

## New concepts introduced

- **Provenance radius (PR)**: distance from records to ground-truth sources in the provenance graph, used as a hard cap and as an audit cost in routing.
- **Evidence exchange rate (EER)**: expected risk reduction per token/latency cost, used to allocate scarce context budget to cheap safety.
- **Context liquidity**: inverse revalidation cost, used to penalize claims that are hard to refresh under drift.
- **Context shock index (CSI)**: contradiction density over mission-critical claims, used as a control signal to freeze writes and intensify evidence gathering.
- **Context firebreak**: a containment rule preventing suspected records from being routed into high-stakes nodes.
- **Core-delta leases**: time-bounded contracts on shared core memory, forcing periodic renewal and preventing stale "core" assumptions from persisting across long missions.
