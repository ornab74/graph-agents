# paper.md

# Mission Graphs: Persistent, Permissioned, Evaluable Control Systems for Long-Horizon Software Delivery

> Note: This file is a draft scaffold. Sections 7 and 8 are written in full prose; other sections are placeholders.

## 1. Introduction

TODO

## 2. Mission Graph Formalism

TODO

## 3. Graph Synthesis

TODO

## 4. Context Routing as a Control Layer

TODO

## 5. Provenance and Evidence Bundles

TODO

## 6. Verification Orchestration

TODO

## 7. Risk and Governance: Constrained Autonomy

Autonomous software delivery fails in practice less often because models "cannot code" and more often because systems cannot reliably control the propagation of uncertainty. In mission graphs, uncertainty enters through three channels: (i) incomplete or stale context, (ii) unverifiable claims about artifacts, and (iii) unobserved deployment dynamics. Risk and governance therefore cannot be implemented as downstream checklists. They must be expressed as continuous constraints over what the graph is allowed to know, believe, and reuse.

We make a central subclaim: the primary governance boundary in an agentic software system is not the tool boundary, but the context boundary. The system is only as safe as the evidence it allows to influence high-stakes actions (writes, promotions, rollouts). This motivates treating context routing and memory as governed resources, with explicit budgets, permission labels, and revalidation rules.

### 7.1 Proof-Carrying Context

We define proof-carrying context as context that is inseparable from checkable evidence. Formally, a routed context bundle for node $v$ is not just a set of records $c_t^{(v)}$, but a tuple

$$
\tilde{c}_t^{(v)} = (c_t^{(v)}, e_t^{(v)}, \pi_t^{(v)}),
$$

where $e_t^{(v)}$ is an evidence bundle (logs, traces, diffs, test reports, attestations) and $\pi_t^{(v)}$ is a set of machine-checkable discharges for obligations relevant to $v$. A context gate accepts the bundle only if its proofs discharge the obligations required for the decision at hand:

$$
\Gamma_v^{\text{ctx}}(\tilde{c}_t^{(v)}, x_t) = 1
\;\;\Longrightarrow\;\;
\forall \varphi \in \mathcal{O}_v:\; \operatorname{Discharge}(\varphi; e_t^{(v)}, \pi_t^{(v)})=1.
$$

This yields a second subclaim: most "alignment" and "safety" work in delivery settings reduces to ensuring that influential context is proof-carrying. When this holds, the system does not need to trust the narrative; it only needs to verify the evidence.

### 7.2 Provenance Radius: Limiting How Far Beliefs Can Travel

Even with evidence, reusing context too broadly creates correlated failures: the same flawed assumption can contaminate multiple nodes and branches. We introduce provenance radius as a control primitive that bounds the spread of a memory record or context bundle across the graph.

Let $\operatorname{dist}(u, v)$ denote graph distance between nodes. For a memory record $m_i$ with provenance metadata and freshness $f_{i,t}$, define an allowed routing region

$$
\mathcal{N}(m_i) = \{v : \operatorname{dist}(\operatorname{src}(m_i), v) \le r_i\},
$$

where $r_i$ is the provenance radius. Routing must satisfy $m_i \in c_t^{(v)} \Rightarrow v \in \mathcal{N}(m_i)$ unless the record is revalidated by a verifier stage appropriate for $v$.

This yields a third subclaim: provenance radius is a firebreak-friendly alternative to blanket "share memory across all nodes." It preserves reuse where safe (local neighborhoods) while forcing revalidation before context can influence distant, higher-stakes decisions like integration and deploy.

### 7.3 Evidence Exchange Rate and Context Liquidity

Autonomous systems must trade speed for evidence. To make this trade explicit, we introduce two economic quantities.

Evidence exchange rate (EER) measures the cost of converting a claim into promotable context. Let $\Delta R$ denote expected tail-risk reduction attributable to acquiring additional evidence, and let $\operatorname{cost}(e)$ be the cost vector of evidence (compute, time, tokens, human). Then define:

$$
\operatorname{EER}(e) = \frac{\operatorname{cost}(e)}{\Delta R}.
$$

In operational terms: if the next unit of evidence reduces risk only marginally, its exchange rate is poor, and the graph should prefer alternative evidence or route to a different plan.

Context liquidity measures how readily evidence can be transformed into usable context across nodes given budgets and governance constraints. For a context bundle $\tilde{c}$ and a node $v$, define liquidity as the probability of acceptance under the node's context gate and budget:

$$
\operatorname{Liq}(\tilde{c}, v) = \Pr\bigl(\Gamma_v^{\text{ctx}}(\tilde{c}, x_t)=1 \;\wedge\; \operatorname{Tok}(\tilde{c}) \le \kappa_v^{\text{tokens}}\bigr).
$$

Liquidity increases when evidence is standardized (proof-carrying templates), provenance metadata is complete, and permissioning supports safe redaction. Liquidity decreases when evidence is non-reproducible (ad-hoc logs), stale, or constrained by privacy rules that prevent high-fidelity sharing.

These concepts support a fourth subclaim: the performance of a mission-graph system is largely determined by evidence exchange rates and context liquidity, not by raw generation quality. High-liquidity evidence (standardized, provenance-rich, permissioned) composes across nodes and reduces coordination overhead. Low-liquidity evidence forces repeated re-derivations and encourages unsafe "trust me" shortcuts.

### 7.4 Firebreaks: Quarantine, Rollback, and Memory Transactions

Mission graphs require explicit firebreak mechanisms that prevent bad context from propagating and that bound the blast radius of mistakes. We use three complementary firebreaks:

- Context firebreaks: high-stakes nodes (security, deploy, governance) route only from core memory and require proof-carrying context, rejecting branch-local deltas unless explicitly reconciled.
- Memory firebreaks: writes to durable memory are transactional (prepare then commit), and commits require verifier discharge; failed proofs remain quarantined and non-routable.
- Policy firebreaks: learned routing weights and gating thresholds are checkpointed and revertible; incidents trigger rollback to last-known-safe policy parameters and quarantine of implicated provenance chains.

These firebreaks eliminate a common failure mode in agentic systems: the gradual accumulation of unverified "facts" that become de facto policy constraints. With transactional memory and proof-carrying context, unverified artifacts can exist without becoming actionable.

### 7.5 Concrete Examples

Example 1 (Migration risk and provenance radius). A mission proposes a database schema migration with backfill. A builder node produces a migration script and a narrative summary. Under proof-carrying context, the integrator and deployer nodes will not accept the narrative. They require evidence bundles: a reversibility proof (down migration tested), a canary plan, and regression seeds derived from counterexamples in staging. Provenance radius prevents the builder's "seems safe" assessment from reaching deploy without revalidation; the record must be re-attested by migration-specific verifiers at the pre-deploy stage.

Example 2 (Security patch and context liquidity). A mission updates an authentication library to remediate a CVE. The system routes a standardized security evidence bundle (SAST report, dependency diff, exploit repro results) that is permissioned and redacted for broad sharing. Because the evidence is standardized and proof-carrying, it is high-liquidity: the reviewer, governor, and deployer nodes can all consume it under their budgets, and gate composition can reference the same attestation rather than rerunning redundant scans. If an incident occurs post-deploy, the provenance ledger can trace which evidence was used to justify promotion and can quarantine any record that is later contradicted.

## 8. Deployment as Closed-Loop Control (Risk-to-Deploy Interface)

In mission graphs, deployment is not a terminal step. It is the actuation layer of a closed-loop controller. The system continuously chooses how much traffic to expose to new behavior, how strict to make gates, and how much human review to allocate, based on observed health, remaining error budget, and risk estimates derived from verification and monitoring.

The key claim of this section is that deployment decisions are context decisions. Rollout is driven by what evidence is available, how trustworthy it is, and how widely that evidence is allowed to propagate. This is where proof-carrying context, provenance radius, and firebreaks become operational rather than conceptual.

### 8.1 Interface Signals and Proof-Carrying Promotion

We define a standard risk-to-deploy interface that couples verification and governance to rollout. Let $\tau_t$ be rollout fraction, $h_t$ be health, $E_t$ be error budget, and $R_t$ be a tail-risk estimate. A minimal interface is:

$$
\mathcal{I}_{\text{R2D}} = (R_t,\; E_t,\; h_t,\; \hat{c}_t,\; \Delta_t,\; g_t^{\text{gov}}),
$$

where $\hat{c}_t$ is composed verification confidence, $\Delta_t$ is change impact or drift magnitude, and $g_t^{\text{gov}}$ summarizes governance posture.

Critically, each element of $\mathcal{I}_{\text{R2D}}$ must be derivable from proof-carrying context and evidence ledger entries, not from informal observation. For example, $R_t$ should be computed from verifiers with explicit calibration SLOs and from online telemetry with provenance-stamped windows, and $g_t^{\text{gov}}$ must be computed from auditable policy checks (permission adherence, review completion, evidence availability).

This motivates a new subclaim: "promotion to canary" should be treated as a proof obligation, not as a pipeline stage. A deployer node should accept a candidate only if the routed context bundle includes discharges for deploy-specific obligations (rollback plan, guardrails configured, monitoring thresholds, incident playbook). Absent these proofs, the correct action is not to "slow down rollout," but to halt and route to evidence acquisition.

### 8.2 Rollout State Machine With Context-Conditioned Modes

We implement the controller as a state machine with modes $\{\text{ADVANCE}, \text{HOLD}, \text{ROLLBACK}\}$. The novelty is that mode transitions are gated not only by health and risk, but also by context liquidity and provenance.

Let $\tilde{c}_t^{(\text{deploy})}$ be the deployer's proof-carrying context bundle. Define liquidity for deploy as $\operatorname{Liq}(\tilde{c}_t^{(\text{deploy})}, \text{deploy})$. Then:

- ADVANCE requires $h_t \ge h_{\min}$, $R_t \le R_{\text{adv}}$, and $\operatorname{Liq}$ above a threshold (the deployer has sufficient high-quality evidence to justify increasing exposure).
- HOLD is the default when evidence exchange rates are favorable: the system can cheaply buy more certainty by collecting more canary windows or running targeted evals.
- ROLLBACK triggers when health drops, risk spikes, error budget approaches depletion, or when provenance violations occur (e.g., a critical signal lacks proof-carrying provenance).

This yields another new subclaim: low context liquidity is itself a deployment risk signal. When the deployer cannot obtain acceptable evidence under its budgets and permission constraints, advancing rollout is equivalent to acting under partial observability with unknown error bars. The safe response is to hold or rollback and to route to evidence-generation nodes, rather than continuing to actuate.

### 8.3 Provenance Radius as a Deployment Safety Mechanism

Deployment is the point where stale or mis-scoped context is most dangerous. We therefore recommend the smallest provenance radius at the deploy boundary. Concretely:

- Only core memory is routable into deploy decisions.
- Branch-local deltas must be reconciled and re-attested.
- Time-sensitive records (recent incidents, SLO windows, oncall annotations) have aggressively decaying freshness; expired records are non-routable for deploy.

This is a deployment firebreak: even if exploration branches generate plausible narratives, they cannot influence rollout without crossing the revalidation boundary.

### 8.4 Evidence Exchange Rates as Rollout Actuation Knobs

Traditional systems tune rollout by fixed percentages and fixed time windows. Mission graphs can tune rollout by evidence economics. If the marginal evidence exchange rate is low (cheap evidence yields large tail-risk reduction), the controller should prefer HOLD and gather evidence. If the exchange rate is high (evidence is expensive and yields little reduction), the controller should either accept the current risk posture and advance slowly, or stop entirely and replan.

This reframes deployment timing as a rational control problem: rollout is not delayed because "we are cautious," but because evidence is cheap relative to the value of risk reduction.

### 8.5 Concrete Examples

Example 3 (Canary advance blocked by missing provenance). A mission deploys a performance optimization that alters caching semantics. Unit tests and integration tests pass, but the telemetry window used to compute $h_t$ is missing provenance metadata (incorrect service labels; window cannot be reproduced). Under proof-carrying context, the deployer cannot discharge the "health evidence is auditable" obligation. The mode remains HOLD, and the graph routes to an observability repair node to regenerate a provenance-stamped health report. In conventional systems this would proceed as "looks fine"; here it becomes a hard firebreak.

Example 4 (Rollback and memory quarantine). A canary at $\tau_t=0.1$ triggers a latency regression. The controller enters ROLLBACK and writes an incident evidence bundle to the ledger. Critically, it also quarantines the context records that justified the advance (the particular benchmark report and the change-impact estimate) by shrinking their provenance radius to zero until revalidation. Future missions cannot reuse those records as proof-carrying context without running the corresponding verifiers again. The failure mode "ship the same regression twice because the system remembered the wrong lesson" disappears because the memory system is transactionally and causally linked to deploy outcomes.

## 9. Learning and Adaptation

TODO

## 10. System Architecture and Workflows

TODO

## 11. Evaluation Plan and Metrics

TODO

## 12. Failure Modes and Recovery

TODO

## 13. Limitations and Open Problems

TODO

