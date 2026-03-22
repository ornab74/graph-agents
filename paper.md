# paper.md

# Mission Graphs: Persistent, Permissioned, Evaluable Control Systems for Long-Horizon Software Delivery

This draft argues for a systems view of software delivery: not as a chain of prompts or a loose agent swarm, but as a persistent, permissioned control loop over evidence, risk, and rollout.

## 1. Introduction

Long-horizon software work fails when execution is treated as a chat problem. The core difficulties are not linguistic: they are systems failures. Real delivery requires persistence under retries, recoverability under partial progress, measurable gates that prevent unsafe promotion, and explicit privilege boundaries that constrain what can be read, written, and deployed. Existing "agentic" approaches often supply a helpful worker but omit the surrounding control plane. When context is stale, unverifiable, or improperly shared, the system can behave confidently while silently increasing tail risk.

This paper proposes mission graphs as a top-level abstraction for end-to-end delivery. A mission graph is a persistent, permissioned, evaluable execution graph that coordinates planning, context routing, verification, and deployment as a single process with explicit state and constraints. The graph structure is not incidental. It is the mechanism by which work remains stable under delayed feedback (tests, review, telemetry), branch divergence, and escalation.

Our central claim is that software delivery should be modeled as a constrained stochastic control problem over artifacts, memory, verification, and rollout state. Under this view, the system repeatedly observes evidence, selects actions, and updates state while satisfying governance and safety constraints. The result is a delivery system that can justify promotions with checkable evidence rather than narrative, and that can couple risk estimates to rollout actuation rather than treating deployment as a terminal step.

We make two additional subclaims that structure the rest of the paper. First, the primary governance boundary in autonomous delivery is the context boundary: what evidence is allowed to influence high-stakes actions. Second, planning cannot be separated from evidence: the plan must be compiled into a topology of gates, proof obligations, and context-routing requirements, not merely a list of tasks.

Concretely, mission graphs contribute:

- a formal object model for persistent execution with node contracts, budgets, and gates
- a synthesis procedure that compiles intent into an executable topology with recovery paths
- an evidence plane that routes proof-carrying context and records provenance for audit and reuse
- a closed-loop deploy controller that couples verification and governance to rollout decisions

## 2. Mission Graph Formalism

Let the mission graph be

$$
\mathcal{G} = (V, E, \mathcal{S}, \mathcal{A}, \Pi, \Omega, \Gamma, \mathcal{B}, \mathcal{R}),
$$

where:

- $V$ is a set of nodes (execution stages)
- $E \subseteq V \times V$ is a dependency relation (precedence, information flow, promotion)
- $\mathcal{S}$ is the global state space
- $\mathcal{A}$ is the global action space (tool calls, edits, deployments, escalations)
- $\Pi = \{\pi_v\}_{v \in V}$ is a family of node policies
- $\Omega$ is an observation model (what each node can see)
- $\Gamma$ is a set of gates/evaluators controlling transitions and writes
- $\mathcal{B}$ is a set of budgets and constraints
- $\mathcal{R}$ is a utility or reward model

The mission objective is to maximize delivered value while respecting policy, risk, and budget constraints. In practice, that means optimizing not just for correctness, but for the value of shipped outcomes under bounded compute, human attention, and deployment risk.

### 2.1 State, Observations, and Dynamics

We represent mission execution as a controlled stochastic process. Let the global state at time $t$ be decomposed as:

$$
x_t =
\begin{bmatrix}
z_t \\
m_t \\
b_t \\
d_t
\end{bmatrix},
$$

where $z_t$ is artifact/repo state, $m_t$ is memory/context state, $b_t$ is a multi-dimensional budget vector (compute, money, tokens, human review, deploy), and $d_t$ is deployment/environment state (rollout fraction, health, rollback position).

Nodes act under partial observability. Each node $v$ receives an observation $o_t^{(v)} \sim \Omega(\cdot \mid x_t, v)$, which may include working tree diffs, test outcomes, telemetry windows, and prior evidence bundles. The node then chooses an action:

$$
a_t^{(v)} \sim \pi_v(\cdot \mid o_t^{(v)}, m_t, b_t).
$$

State evolves under dynamics:

$$
x_{t+1} = f(x_t, a_t, \xi_t),
$$

where $\xi_t$ captures stochasticity such as flaky tests, delayed CI, human review latency, and production noise. Budgets update as:

$$
b_{t+1} = b_t - c_t(a_t),
$$

and a policy is feasible only if $b_t \succeq 0$ for all $t$.

### 2.2 Node Contracts, Gates, and Recovery

Each node $v$ is specified by a contract:

$$
\mathcal{C}_v = (\mathcal{I}_v,\; \mathcal{O}_v,\; \Theta_v,\; \Gamma_v,\; \kappa_v),
$$

where $\mathcal{I}_v$ and $\mathcal{O}_v$ are input/output contracts, $\Theta_v$ is the permission set (tools, files, deploy scope), $\Gamma_v$ is the set of gates, and $\kappa_v$ is a recovery rule (retry, branch, repair, escalate, terminate).

Gates implement the key idea that promotion is a permissioned transition rather than an informal "looks good". A gate function

$$
\Gamma(x_t, \hat{y}_t, z_t) \in \{0,1\}
$$

must accept before a material transition occurs (promotion to integration, writing durable memory, advancing rollout). Gates may be composed and calibrated, but the defining feature is that they are machine-checkable and produce evidence traces.

Recovery is not a side channel; it is graph structure. For a critical edge $(i \to j)$, there should exist a recovery path to a repair node or rollback node when $\Gamma_{i \to j}=0$, so the graph remains stable under failure rather than degenerating into unstructured retries.

### 2.3 Architecture Layers

A mission graph should expose the following layers:

- semantic layer: goals, assumptions, contracts
- control layer: planning, routing, scheduling, retries
- evidence layer: verifiers, proofs, tests, logs
- delivery layer: rollout, rollback, observability
- learning layer: adaptation, governance, audit

This separation matters because each layer has different failure modes. Planning can be wrong while verification is sound; context can be stale while deployment is healthy; governance can be too loose or too strict. The architecture needs explicit interfaces between these layers.

## 3. Graph Synthesis

Planning is the act of turning intent into an executable topology. In mission graphs, the output of planning is not a narrative plan. It is a graph contract: tasks, edges, context requirements, gates, proof obligations, rollback paths, assumptions, and budget allocations. This is the point where "agent planning" becomes a systems primitive: the planner decides what must be true for downstream nodes to act safely, and encodes those requirements as gates and evidence obligations rather than hope.

We frame synthesis as constructing a candidate graph $\hat{\mathcal{G}}$ that maximizes expected mission utility while minimizing structural fragility:

$$
\max_{\hat{\mathcal{G}}}
\;
\mathbb{E}[J(\hat{\mathcal{G}})]
- \lambda_1 |\hat{V}|
- \lambda_2 |\hat{E}|
- \lambda_3 \operatorname{fragility}(\hat{\mathcal{G}}),
$$

where the penalties capture coordination tax, latency, and failure amplification due to over-branching or missing recovery edges.

### 3.1 Synthesis Pipeline (Intent to Contract)

A practical synthesis procedure is a compilation pipeline:

1. intent capture: extract goal, constraints, and governance requirements
2. state census: produce proof-carrying evidence bundles about repo/tests/environment
3. decomposition: propose candidate subgoals and node templates
4. topology: choose dependencies, promotion edges, merge points, and recovery paths
5. obligations: attach proof obligations to promotion edges (what must be discharged)
6. context routing requirements: attach context gates and budgets (what evidence must be present)
7. budget assignment: allocate compute/tokens/human/deploy budgets and escalation thresholds

The key subclaim is that synthesis must allocate evidence work explicitly. A graph that plans tasks without specifying where evidence comes from is under-specified and will either stall (missing information) or proceed unsafely (acting on narrative).

### 3.2 Decomposition, Branching, and Merge

The planner should keep the graph small enough to control and rich enough to deliver. Over-decomposition creates coordination tax; under-decomposition hides risk. We recommend using value-of-information to decide when to branch. Branching is warranted when the expected value of reducing uncertainty exceeds the cost of running the branch and reconciling its outputs. Conversely, merges should be gated on alignment: if branches disagree materially, the graph should route to a reconciliation node rather than forcing an early merge.

### 3.3 Edge Types and Evidence Attachment

Edges should be typed because different edges imply different evidence requirements:

- precedence edges require readiness and resource feasibility
- information-flow edges require provenance and freshness (to avoid stale propagation)
- promotion edges require proof obligations and verifier discharge
- recovery edges require a bounded rollback or repair procedure

This yields a second synthesis subclaim: the planner should co-design topology and verification. In other words, the "what" (tasks) and the "why safe" (evidence, obligations, gates) must be generated together. Treating verification and context routing as post-hoc additions leads to graphs that are impossible to execute under real budgets and governance constraints.

## 4. Context Routing as a Control Layer

Mission graphs require an evidence plane. Context is not raw text. It is routed evidence under freshness, trust, provenance, and permission constraints. The purpose of the context system is not to make the model "sound informed"; it is to reduce decision uncertainty at the nodes where actions have irreversible or high blast-radius consequences.

We therefore treat context routing as a control law. Let the global mission state be $x_t = (z_t, m_t, b_t, d_t)$, where $z_t$ is artifact state, $m_t$ is memory state, $b_t$ is the remaining budget vector, and $d_t$ is deployment/environment state. Each node $v$ observes $o_t^{(v)}$ and consumes a routed context bundle $c_t^{(v)}$ selected by a router $R_v$:

$$
c_t^{(v)} = R_v(m_t, o_t^{(v)}, b_t, \Theta_v),
$$

where $\Theta_v$ encodes node-local permissions and tool boundaries. A useful abstract routing objective is information gain under cost and staleness penalties:

$$
R_v
=
\arg\max_{c \subseteq m_t}
\Bigl[
I(c; y^{(v)} \mid o_t^{(v)})
-
\lambda_{\text{tok}} |c|
-
\lambda_{\text{stale}} S(c)
\Bigr]
\quad\text{s.t.}\quad
\operatorname{Perm}(c) \subseteq \Theta_v.
$$

Here $y^{(v)}$ is the node output random variable, $S(c)$ is a staleness penalty, and $\operatorname{Perm}(\cdot)$ extracts permission labels. This makes routing explicit: evidence is admitted only if it is both useful and admissible.

Memory should be treated as a typed artifact store: episodic, semantic, artifact, and policy memory all have different routing rules, write policies, and revalidation schedules. The critical point is that routing is safety-critical: it decides which claims are allowed to influence high-stakes actions such as promotion, deployment, or permission escalation.

We make two subclaims.

- Subclaim 4.1: the primary safety boundary in agentic delivery systems is the context boundary. If unverified claims can enter context, they can bypass every other guardrail by becoming "inputs" to otherwise well-behaved policies.
- Subclaim 4.2: routing must be obligation-aware. The router should not retrieve "relevant information" in the abstract; it should retrieve the minimal evidence needed to discharge the obligations required for the next decision.

The strongest design principle here is that context is an execution layer, not a prompt accessory. In the solved system, every context bundle is proof-carrying and provenance-stamped. High-stakes nodes only consume context that can be audited back to primary evidence, and summarization is provenance-aware: summaries retain explicit links to the sources they compress so that downstream gates can renew or reject them.

## 5. Provenance and Evidence Bundles

### 5.1 Proof-Carrying Context

In a solved system, every context bundle is proof-carrying. A bundle includes source hashes, provenance links, obligations, attestations, and redactions. High-stakes nodes consume only context that can be audited back to primary evidence.

Formally, a routed context bundle can be treated as a typed packet:

$$
\tilde{c}_t^{(v)} = (c_t^{(v)}, e_t^{(v)}, \pi_t^{(v)}),
$$

where $e_t^{(v)}$ is the evidence payload (logs, traces, diffs, reports) including provenance metadata (source identities, hashes, freshness, permission scope), and $\pi_t^{(v)}$ is a set of machine-checkable discharge receipts for obligations relevant to $v$. A context gate accepts the packet only if its receipts discharge the obligations required for the decision:

$$
\Gamma_v^{\text{ctx}}(\tilde{c}_t^{(v)}, x_t)=1
\;\Rightarrow\;
\forall \varphi \in \mathcal{O}_v:\; \operatorname{Discharge}(\varphi; e_t^{(v)}, \pi_t^{(v)})=1.
$$

This shifts the epistemic contract: nodes do not "trust" context; they verify that context carries sufficient evidence to justify influence.

### 5.2 Provenance Radius

Provenance radius bounds how far a derived claim may drift from its source roots before it must be renewed. Audit-distance-aware routing prefers primary evidence when provenance radius grows too large.

We treat provenance as a graph over derived claims and their roots. Let $p(u)$ be a provenance pointer from a derived record $u$ to its parent sources. The resulting provenance DAG supports two operations: (i) renewal, which revalidates a claim against its roots and updates freshness, and (ii) restriction, which limits how far a claim may travel across mission-graph distance without renewal.

### 5.3 Evidence Exchange Rate and Context Liquidity

Context should be selected by expected risk reduction per token, latency unit, or verification cost. This turns routing into a portfolio problem. Context liquidity measures how cheaply a claim can be revalidated under drift; low-liquidity claims are risky because they are hard to refresh.

One useful abstraction is the evidence exchange rate: the marginal reduction in tail risk per unit cost of obtaining or renewing evidence. Let $R(x)$ be a tail-risk proxy (e.g., a CVaR estimate of loss) under state $x$. If retrieving or renewing a bundle changes the state from $x$ to $x'$, define:

$$
\operatorname{EER}(\tilde{c}) = \frac{R(x) - R(x')}{\operatorname{cost}(\tilde{c})}.
$$

Liquidity then measures how cheaply acceptable evidence can be repurchased under drift:

$$
\operatorname{Liq}(\tilde{c})
=
\left(\mathbb{E}[\operatorname{cost}(\operatorname{Renew}(\tilde{c}))]\right)^{-1}.
$$

This supports an operational rule: high-stakes nodes should prefer high-liquidity evidence because it can be refreshed cheaply when assumptions shift.

### 5.4 Firebreaks and Contagion Control

If contradictory or low-trust claims begin to spread, the system should enter firebreak mode. High-stakes nodes stop accepting contaminated context, and routing shifts back to source-near bundles. The goal is containment: false or stale claims should not propagate beyond a bounded part of the graph.

We can make contagion concrete by treating "contaminated" context as an epidemic process over nodes. Let $p_t(v)$ be the probability that node $v$'s routed context contains a contaminated claim at time $t$. If routing reuses derived claims without renewal, then contamination can amplify. A simple reproduction number is:

$$
\mathcal{R}_{\text{ctx}}
=
\mathbb{E}\bigl[\#\text{ of downstream nodes influenced by a contaminated claim}\bigr].
$$

Firebreak mode aims to force $\mathcal{R}_{\text{ctx}}<1$ by shrinking provenance radius, requiring renewal before reuse, and restricting high-stakes nodes to core memory plus revalidated primary evidence. This turns contradiction handling from an ad hoc "ignore the bad answer" response into a structural containment policy.

## 6. Verification Orchestration

Verification is a system, not a checkbox. Verifiers form a dependency graph with composed gates, proof obligations, and evidence lineage. The mission graph should treat verification as an orchestrated subsystem that produces promotion certificates: machine-checkable records stating which obligations were discharged, by which evidence, with what calibrated confidence and residual risk.

Promotion should happen only when the required obligations have been discharged by checkable evidence. The system should support hard gates, soft calibrated gates, and disjunctive gates for alternative evidence. Verification should be budgeted, sequential, and adaptive: route cheap high-signal checks first, then expand only if the posterior risk does not clear the threshold.

Verification becomes much more powerful when treated as a graph of obligations rather than a flat suite of tests. Each promotion edge carries proof obligations, and the verifier orchestrator computes a minimal proof boundary instead of rerunning everything. That yields a better abstraction: not “did tests pass,” but “which obligations were discharged, by which evidence, and at what residual risk.”

We formalize this orchestration as follows. Let the verifier graph be $\mathcal{V}=(U,F)$ where $U$ is a set of evals/verifiers and $F$ encodes dependencies (typecheck before unit tests; unit tests before integration). Each verifier $u_m$ produces a signal $v_{m,t}\in[0,1]\cup\{\bot\}$. For a promotion edge $(i\to j)$, define an obligation set $\mathcal{O}_{i\to j}=\{\varphi_1,\dots,\varphi_K\}$ and a discharge predicate $\operatorname{Discharge}(\varphi_k; e_t)\in\{0,1\}$. Promotion is permitted only if all obligations discharge under the evidence bundle $e_t$:

$$
\prod_{k=1}^{K} \operatorname{Discharge}(\varphi_k; e_t) = 1.
$$

Gate composition then reduces multiple verifier signals into a promotion decision. Conservative edges use hard composition (min/AND), while lower-stakes edges can use calibrated aggregation, and some obligations allow disjunctive evidence (one of multiple acceptable proof paths).

We make two further subclaims.

- Subclaim 6.1: verification should minimize proof boundary, not maximize test volume. The orchestrator should seek the smallest evidence portfolio that discharges the active obligations given current budgets and risk posture.
- Subclaim 6.2: verifier health is part of the state. Calibration and flake behavior must feed back into both gate composition and eval routing; otherwise, the evidence layer itself becomes a source of drift.

### 6.1 Proof-Carrying Patches

The builder should not emit only a patch. It should emit a patch plus evidence bundle: test reports, perf deltas, security scans, migration reversibility witnesses, and rollout guardrails. Those artifacts become the machine-checkable proof of promotion.

### 6.2 Calibration SLOs

Verifier confidence is only useful if it is calibrated. Flake rates, Brier score, and ECE should be treated as operational metrics. When calibration degrades, the system should tighten gates or reroute to more discriminative evidence.

### 6.3 Counterexample Reservoirs

Failures should be minimized, canonicalized, and stored as regression seeds. A counterexample reservoir turns incidents into durable verification memory. Future routing can prioritize these seeds so the same failures do not recur.

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

### 7.5 Risk Budgets, Governance Debt, and Safe-Set Projection

Context governance alone is not sufficient. The system must also budget for tail risk, human attention, and deployment exposure, because these are the resources that determine whether a mistake becomes an incident.

We represent feasibility with a multi-dimensional budget vector:

$$
b_t =
\begin{bmatrix}
b_t^{\text{compute}} \\
b_t^{\text{money}} \\
b_t^{\text{tokens}} \\
b_t^{\text{human}} \\
b_t^{\text{deploy}}
\end{bmatrix},
\qquad
b_{t+1}=b_t-c_t(a_t),
\qquad
b_t \succeq 0.
$$

We represent risk as a tail-aware quantity rather than a binary "safe/unsafe" label. A generic objective is:

$$
\max_{\Pi}\ \mathbb{E}[G] - \lambda \operatorname{CVaR}_{\alpha}(L),
$$

with constraints on policy and governance violations. This framing matters because delivery failures are heavy-tailed: rare incidents dominate expected harm.

Governance is a constraint set, but it is also a dynamic state. We introduce governance debt as a scalar (or vector) state variable $D_t$ measuring accumulated "unpaid" governance work (review skipped under low-risk conditions, calibration not refreshed, obligations not yet generalized). A simple dynamics model is:

$$
D_{t+1} = \rho_D D_t + \Delta D_t^{\text{inc}} - \Delta D_t^{\text{pay}},
$$

where $\rho_D \in [0,1]$ captures natural decay, $\Delta D_t^{\text{inc}}$ increases with autonomy under uncertainty, and $\Delta D_t^{\text{pay}}$ increases with audits, reviews, calibration refresh, or obligation discharge.

This motivates a new subclaim: governance debt prevents organizational whiplash. Instead of oscillating between permissive shipping and sudden freezes, the system gradually tightens requirements as debt accumulates, and it explicitly pays debt down when drift or exposure increases.

To operationalize "constraints over actions," we recommend expressing high-stakes decisions as projections into a safe set. Let $a_t$ be a nominal action (e.g., promote, deploy, widen rollout), and let $\mathcal{A}_{\text{safe}}(x_t)$ encode budgets, governance constraints, and risk limits. Then:

$$
a_t^\star = \arg\min_{a \in \mathcal{A}_{\text{safe}}(x_t)} \|a-a_t\|^2.
$$

The system then emits a projection receipt recording active constraints and the applied adjustment. This yields another subclaim: policy enforcement should be auditable as geometry (projection into feasible sets), not as ad hoc exception handling.

Finally, governance debt should influence review allocation and gate strictness. For example, a deploy-specific review intensity $\eta_t^{\text{human}}$ can be coupled to risk and debt:

$$
\eta_t^{\text{human}} = \sigma(\alpha_0 + \alpha_1 R_t + \alpha_2 D_t - \alpha_3 b_t^{\text{human}}),
$$

so that high risk or high debt increases oversight, while scarce human budget forces prioritization.

### 7.6 Concrete Examples

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

### 8.5 Rollback Hedging as a Deploy Resource

Rollout control is only as safe as rollback is cheap. We therefore treat rollback capacity as an explicit state variable and, in high-stakes systems, as a budgeted hedge.

Let $H_t \in [0,1]$ be hedge strength for the current change at rollout fraction $\tau_t$, capturing reversibility (feature flags, backward-compatible reads/writes), time-to-revert, and state safety (migrations/backfills). A simple constraint is:

$$
\text{ADVANCE is admissible only if } H_t \ge H_{\min}(\tau_t).
$$

This yields a new subclaim: rollback is not just a recovery path; it is a control lever that expands the feasible rollout region. Systems with strong hedges can ship faster without increasing tail incident risk.

Hedge strength should itself be evidence-conditioned. For example, $H_t$ should be derived from proof obligations such as: reversible migration witnessed, kill switch verified, and post-rollback correctness checks present. When those obligations cannot be discharged, the correct response is to HOLD and acquire hedge evidence, not to "push carefully" into an unhedged region.

### 8.6 Risk-Limit Order Books and Partial Fills

In production, multiple changes compete for the same error budget and the same deployment channels. A robust deployment controller therefore needs a concurrency-aware allocation mechanism rather than a single change-at-a-time heuristic.

We propose treating rollout increments as risk-limited orders. Let each change $i$ submit an intent to increase rollout by $\Delta\tau_i$. Associate with that intent a marginal tail-risk consumption $\Delta \operatorname{CVaR}_{\alpha}^{(i)}(\Delta\tau_i)$ and an expected value gain $\Delta V_i(\Delta\tau_i)$. Under shared limits, the controller solves an allocation problem:

$$
\max_{\Delta\tau_i \in [0, \bar{\tau}_i]}
\sum_i \Delta V_i(\Delta\tau_i)
\quad\text{s.t.}\quad
\sum_i \Delta \operatorname{CVaR}_{\alpha}^{(i)}(\Delta\tau_i) \le R_{\text{limit}},
\;\; E_t \ge E_{\min}.
$$

When constraints bind, the system can partially fill orders: advance only a smaller $\Delta\tau_i$ while emitting a receipt describing which constraint blocked full fill (risk limit, error budget, missing proofs, low liquidity). This avoids a common failure mode: independent teams "each shipping safely" while collectively exhausting error budget.

### 8.7 Dual-Control Separation at Canary Time

Evidence gathered during canary is only valid if the decision policy is approximately stationary while the evidence is collected. If the system changes its rollout policy or its evaluation routing mid-canary (e.g., via online learning), then the observed canary outcomes no longer correspond to the policy used to justify the rollout decision.

We therefore recommend dual-control separation at deployment time. Let $\pi_{\text{ship}}$ be the ship-time controller producing mode and rollout actions, and let $\pi_{\text{learn}}$ be the learning-time controller updating routing weights, thresholds, and models. During active rollout (i.e., while $\tau_t$ is in an advancing trajectory), learning updates must be frozen or restricted to a trust region:

$$
D_{\mathrm{KL}}(\pi_{\text{ship},t+1}\,\|\,\pi_{\text{ship},t}) \le \delta_{\text{ship}}
\quad\text{and}\quad
\mathbf{1}\{\text{learn enabled}\} = \mathbf{1}\{\Delta_t \le \Delta_{\max}\}\cdot \mathbf{1}\{g_t^{\text{gov}} \ge g_{\min}\}.
$$

This yields a new subclaim: ship-vs-learn separation is not an implementation detail; it is a prerequisite for making canary evidence interpretable and for preserving governance guarantees under drift.

### 8.8 Concrete Examples

Example 3 (Canary advance blocked by missing provenance). A mission deploys a performance optimization that alters caching semantics. Unit tests and integration tests pass, but the telemetry window used to compute $h_t$ is missing provenance metadata (incorrect service labels; window cannot be reproduced). Under proof-carrying context, the deployer cannot discharge the "health evidence is auditable" obligation. The mode remains HOLD, and the graph routes to an observability repair node to regenerate a provenance-stamped health report. In conventional systems this would proceed as "looks fine"; here it becomes a hard firebreak.

Example 4 (Rollback and memory quarantine). A canary at $\tau_t=0.1$ triggers a latency regression. The controller enters ROLLBACK and writes an incident evidence bundle to the ledger. Critically, it also quarantines the context records that justified the advance (the particular benchmark report and the change-impact estimate) by shrinking their provenance radius to zero until revalidation. Future missions cannot reuse those records as proof-carrying context without running the corresponding verifiers again. The failure mode "ship the same regression twice because the system remembered the wrong lesson" disappears because the memory system is transactionally and causally linked to deploy outcomes.

## 9. Learning and Adaptation

Learning is useful only if it preserves control. The core requirement is *control-preserving adaptation*: the system must improve from mission to mission while maintaining bounded policy violation probability and bounded tail risk at ship time. This forces a separation of concerns:

- a ship-time controller that is conservative, stable, and rollbackable
- a learning-time controller that proposes updates, but cannot silently change the ship-time operating envelope

Formally, let the system have parameters $\Theta$ that govern planning, routing, verification, and rollout. A single mission produces a trace $\tau = (x_{0:T}, a_{0:T}, o_{0:T})$ and a realized return $G(\tau)$ computed from shipped outcomes, incident costs, and budget usage. The outer-loop objective is

$$
\max_{\Theta}
\;\mathbb{E}[G(\tau;\Theta)]
\quad\text{s.t.}\quad
\Pr(\text{governance violation}) \le \epsilon_{\text{gov}},
\;\Pr(\text{SLO breach}) \le \epsilon_{\text{slo}}.
$$

### 9.1 Quarantined Learning Lanes

We propose a concrete separation: maintain two parameter sets, $\Theta^{\text{ship}}$ and $\Theta^{\text{learn}}$. Ship-time execution uses $\Theta^{\text{ship}}$ exclusively. Learning proposes $\Theta^{\text{cand}}$ in a quarantined lane, and promotion to $\Theta^{\text{ship}}$ occurs only after the candidate has discharged explicit obligations (offline replay, counterfactual checks, and governance approvals).

This yields a new subclaim: **learning should be gated by proof obligations just like code promotion**. In particular, changes to context routing policy (provenance caps, firebreak thresholds, evidence exchange rate floors) must be promoted only if they come with evidence that they do not worsen containment or auditability under distribution shift.

One practical mechanism is a trust-region constrained update:

$$
\max_{\Theta'}
\; J(\Theta')
\quad \text{s.t.}\quad
D_{\mathrm{KL}}(\pi_{\Theta'} \,\|\, \pi_{\Theta^{\text{ship}}}) \le \delta,
\quad
\Theta' \in \mathcal{P}_{\text{safe}},
$$

where $\mathcal{P}_{\text{safe}}$ encodes governance constraints and rollout safety constraints. This formalizes "improve, but do not jump outside the operating envelope."

### 9.2 Evidence-Conditioned Adaptation

Mission graphs have an advantage over ad-hoc agent systems: they already maintain an evidence ledger and a provenance graph. That makes learning *evidence-conditioned* rather than purely outcome-conditioned.

Let $\mathcal{L}$ be the evidence ledger and $\mathcal{P}$ the provenance graph over memory records and bundles. For a learning update to be admissible, the causal chain from decision to outcome must be auditable:

$$
\operatorname{AuditOK}(\tau)
=
\mathbf{1}\{\text{material decisions in } \tau \text{ have proof-carrying context receipts}\}.
$$

Then enforce a minimum audit coverage requirement before incorporating a mission into policy updates:

$$
\mathbb{E}[\operatorname{AuditOK}(\tau)] \ge a_{\min}.
$$

This yields a second new subclaim: **mission graphs should refuse to learn from unauditable successes**. If the system cannot explain why it shipped something safely, it cannot safely generalize that behavior.

### 9.3 Learning the Evidence Plane

In addition to learning "what code changes work," mission graphs can learn better evidence routing and containment policies. Concretely, treat the following as learnable, versioned parameters:

- provenance radius caps $\kappa_v^{\text{prov}}$ per node class
- context shock thresholding and firebreak activation policies (when to quarantine derived memory)
- evidence exchange rate thresholds $\tau_{\text{eer}}^{(v)}$ and liquidity penalties for low-revalidatable claims
- verifier routing priors (which evals provide high signal for which change profiles)

The system should optimize these parameters under an explicit auditability constraint: gains in speed are not allowed to come from routing farther from source roots or from weakening proof-carrying context requirements for high-stakes nodes.

### 9.4 Governance as Safe-Set Projection

Governance is not a separate queue; it is a continuous constraint set on action selection, evidence routing, and policy updates. The solved-world picture makes governance feel less like paperwork and more like projection.

Let a node propose a nominal action $\tilde{a}_t$ (advance rollout, promote an artifact, commit a memory record). Let the active constraint set at time $t$ be $\mathcal{C}_t$ (permissions, required approvals, provenance caps, obligation discharges). Define the executed action as a projection:

$$
a_t
=
\arg\min_{a \in \mathcal{A}}
\|a - \tilde{a}_t\|^2
\quad \text{s.t.}\quad
a \in \mathcal{A}_{\text{safe}}(\mathcal{C}_t).
$$

The system emits a signed receipt containing $(\tilde{a}_t, a_t, \mathcal{C}_t, \text{evidence IDs})$. This receipt is the artifact humans audit: it shows which constraints were active, what adjustment was applied, and which proof-carrying bundles justified the decision.

Learning and governance therefore remain coupled but separated: ship controllers can tighten gates and roll back, while learning controllers propose updates inside quarantined lanes. This separation prevents mid-rollout behavior drift and allows improvement without silently changing the system's risk posture.

## 10. System Architecture and Workflows

The solved world changes the shape of teamwork because it changes what "work" is made of. A mission graph is not an agent chat transcript; it is a persistent object with a topology, a budget vector, and explicit evidence obligations. The paper's abstract control loop becomes an operating environment: context, verification, deployment, and governance stop being separate disciplines and start behaving like one machine.

### 10.1 Core Components

A production mission-graph system can be expressed as a small set of services and stores with crisp interfaces:

- **Graph registry**: stores $\mathcal{G}=(V,E,\Pi,\Gamma,\mathcal{B},\kappa)$ and versioned graph contracts.
- **Artifact store**: code diffs, tests, build logs, deployments, and checkpoints indexed by content hash.
- **Evidence ledger**: append-only log of verifier results, telemetry windows, approvals, and obligation discharges.
- **Provenance service**: maintains $\mathcal{P}_t$, linking derived records to source roots and computing provenance radius.
- **Context router**: produces proof-carrying context packets under budgets, provenance caps, and permission constraints.
- **Verifier orchestrator**: schedules evals, composes gates, and discharges proof obligations with attestation lineage.
- **Scheduler/executor**: admits nodes under resource constraints, retries, and escalation rules.
- **Risk-to-deploy controller**: actuates rollout, tightens gates, and triggers human review based on health and evidence integrity.
- **Governor**: enforces permissions, approvals, and policy constraints; can freeze learning and force rollback.
- **Learning lane**: proposes updates to $\Theta$ under quarantine, with offline replay and promotion gates.

The architecture enforces an important invariance: *every material decision must be replayable from artifacts and evidence*. If a decision cannot be replayed, it is not eligible to influence high-stakes actions or learning updates.

### 10.2 Proof-Carrying Workflows

The basic workflow resembles modern PR-based development, but with evidence and context as first-class artifacts.

1. **Mission open**: a mission is created with an explicit goal, budgets, and policy constraints. The planner emits a graph contract, including required obligations per promotion edge.
2. **Scout and census**: the system generates a repo census and dependency snapshots as source-root evidence bundles, establishing a low-provenance-radius core.
3. **Build and verify**: builders attach proof-carrying context to patches. Memory writes are prepared but not committed until verification discharges the relevant obligations.
4. **Integrate**: integration is a certification step, not a merge-by-default step: it requires branch alignment under core-delta leases and reconciliation of conflicting evidence.
5. **Deploy**: deployment is a controlled actuation step: rollout advances only if deploy-time obligations are discharged and telemetry evidence is provenance-stamped.
6. **Postmortem to policy**: incidents and near-misses update the evidence ledger and can quarantine memory. Learning proposals are evaluated in the quarantined lane and promoted only when their own obligations are discharged.

This produces a new subclaim: **review becomes evidence review**. Humans review proof receipts and obligation discharge artifacts rather than reading long narratives. The unit of inspection is: what claims were used, what evidence supported them, what provenance radius bounds were enforced, and what firebreaks or leases were active.

### 10.3 Firebreaks as Operational Workflow

Containment is not merely a theory section; it becomes an everyday operational workflow. When contradictions appear (context shock), the system:

- marks suspected derived records as non-routable into high-stakes nodes
- tightens provenance caps for deployment, security, and governance decisions
- schedules renewal actions (fresh tests, telemetry windows, policy re-attestations)
- emits a visible mode change with a receipt: "firebreak active" and the set of blocked claims

This eliminates a common failure mode in autonomous systems: quiet contamination of the evidence plane. Instead, contradiction becomes a control signal with explicit, auditable system behavior.

### 10.4 Interfaces and Artifacts

The architecture succeeds or fails on interfaces. We recommend treating the following as explicit, typed artifacts:

- **Context packet**: a minimal proof-carrying bundle with IDs/hashes, provenance links, obligations referenced, attestations, and redactions.
- **Promotion receipt**: the gate composition and the discharged obligations for a promotion edge.
- **Governance receipt**: a safe-set projection record showing constraints and the executed action.
- **Lease certificate**: a time-bounded core memory certificate and renewal evidence.

These artifacts unify runtime control and post-hoc audit. They also make cross-team workflows smoother: oncall sees the same evidence receipts that the builder and deployer used, and compliance teams inspect receipts rather than reverse-engineering behavior from logs.

## 11. Evaluation Plan and Metrics

A mission-graph system should be evaluated with graph-native metrics, not just end-task success. The core object being optimized is not a single output artifact, but an evidence-conditioned trajectory through graph state. Evaluation must therefore measure: (i) whether promotions are justified by auditable evidence, (ii) whether the evidence system stays calibrated under drift, and (iii) whether the control loop remains stable under adversarial or noisy conditions.

Two subclaims guide the evaluation design.

First, mission-graph performance should be measured as a joint efficiency-safety outcome: the system can "succeed" at producing patches while becoming more brittle if it accumulates calibration debt, forgets counterexamples, or routes stale context. Second, evaluation must instrument the intermediate artifacts (obligations, certificates, counterexamples, provenance ledgers) because these artifacts are the mechanism that makes long-horizon autonomy governable; without them, "success rate" collapses to an uninformative, easily Goodharted metric.

### 11.1 Promotion and Evidence Metrics

We treat every promotion edge as producing a promotion certificate with obligation discharge evidence. Define obligation completeness for a promotion edge $(i \to j)$ as:

$$
\operatorname{Comp}(\mathcal{O}_{i\to j})
=
\frac{
\left|\{\varphi \in \mathcal{O}_{i\to j} : \text{evidence lineage present}\}\right|
}{
|\mathcal{O}_{i\to j}|
}.
$$

In a correct implementation, promotion should enforce $\operatorname{Comp}=1$ by construction; empirically, violations measure governance bugs, not "model quality."

Define time-to-safe-promotion (certificate latency) as:

$$
T_{\text{cert}} = t_{\text{promote}} - t_{\text{proposal}},
$$

and report its distribution (p50/p95) conditioned on change impact $\Delta(z)$ and obligation frontier cost. A solved-world system reduces $T_{\text{cert}}$ by routing evidence sequentially rather than running fixed suites, while holding post-promotion incident probability constant or lower.

Define evidence reuse rate as:

$$
R_{\text{reuse}}
=
\frac{\#\{\text{eval results reused via dependency-closure caching}\}}{\#\{\text{eval results consumed}\}}.
$$

High $R_{\text{reuse}}$ is not inherently good; it must be paired with freshness/invalidations, so we also track stale-evidence violations:

$$
V_{\text{stale}} = \Pr(\text{promotion consumes evidence with freshness } f < f_{\min}).
$$

### 11.2 Verifier Calibration SLOs and Debt Metrics

Soft gate composition is only safe when verifier scores are calibrated. We impose calibration SLOs at the verifier and gate levels.

Let $v_{m,t}$ be a verifier score and $y_t \in \{0,1\}$ denote eventual correctness with respect to the obligation(s) the verifier is intended to support (measured by regressions, incidents, or audit replay). Define per-verifier rolling Brier score:

$$
\operatorname{BS}_t(u_m) = \mathbb{E}\left[(v_{m,t} - y_t)^2\right].
$$

An SLO requires $\operatorname{BS}_t(u_m) \le \epsilon_{\text{cal}}$ over a window, and violations must trigger deterministic policy changes: harden gate composition, require disjunctive evidence, or schedule verifier repair.

We also track calibration debt and its service level analogue. Let $D_t(u_m)$ be calibration debt as defined in the verification plane. The solved-world target is not $D_t \to 0$ (systems drift), but bounded debt with bounded "interest": the rate at which debt rises under drift injections.

### 11.3 Counterexample Reservoir and Market Metrics

Counterexample reservoirs are evaluated as an evidence memory, not as a bug list. Useful measures include:

$$
H_{\text{res}} = \Pr(\text{a new change triggers an existing reservoir counterexample} \mid \Delta(z) > 0),
$$

which measures whether the reservoir is exercising meaningful regressions, and a portfolio efficiency score:

$$
\operatorname{ROI}_{\text{res}}
=
\frac{\text{estimated tail-risk reduction attributable to reservoir tests}}{\text{reservoir maintenance cost}}.
$$

If counterexamples are priced (a counterexample market), we additionally evaluate market efficiency by correlating counterexample prices with realized incident reduction after the system buys evidence according to those prices. Mispricing is a first-class failure mode because it can distort sequential evaluation routing.

### 11.4 Control and Containment Metrics

Because mission graphs are control systems, evaluation must include stability and containment.

Define contradiction containment under provenance radius as the expected spread of a false claim before quarantine:

$$
\mathbb{E}[\text{spread distance}] \le r_{\text{prov}},
$$

and report violations as a safety regression. For deployment coupling, track rollback latency (time to return to a safe rollout fraction) and rollout oscillation (number of mode flips ADVANCE/HOLD/ROLLBACK per release).

### 11.5 Experimental Protocols

We recommend three evaluation regimes:

- Offline replay: replay historical changes and incidents under mission-graph policies, measuring certificate latency, completeness, and counterfactual incident avoidance.
- Stress injection: inject drift, verifier flakiness, and contradictory context bundles; measure calibration SLO compliance, quarantine behavior, and promotion safety.
- Online canary comparison: compare against a baseline CI/CD pipeline on matched change sets, reporting $T_{\text{cert}}$, incident rates, and human review load under fixed budgets.

The key solved-world claim is that autonomy improves along multiple axes simultaneously: shorter time-to-safe-promotion, stable or lower incident probability, and increasing audit coverage, because evidence becomes the primary optimization target.

## 12. Failure Modes and Recovery

Mission graphs change failure modes in two ways. They eliminate several common "invisible" failures by making evidence explicit, and they surface new meta-failures in the evidence plane itself (miscalibration, mispricing, obligation mismatch). Recovery therefore must be modeled as a controlled process: detect, contain, correct, and update policy without violating governance constraints.

Two subclaims organize this section. First, the dominant failures in mission-graph systems shift from "bad outputs" to "bad evidence": a promotion is unsafe primarily when an obligation is discharged by stale, miscalibrated, or contaminated evidence. Second, recovery should be minimal-intervention and reversible: prefer actions that restore evidence integrity (quarantine, reroute, recalibrate) before actions that expand autonomy (replanning, branching), because evidence failures are often systemic.

### 12.1 Evidence-Plane Failure Modes

Silent context contamination becomes rare when proof-carrying context is enforced, but related failures remain:

- Provenance gap: evidence exists but cannot be traced to reproducible sources (missing lineage).
- Staleness leak: cached evidence is reused beyond its dependency closure or freshness bounds.
- Permission leak: disallowed evidence is routed across privilege boundaries (governance violation).

The first-line recovery action is containment: shrink provenance radius, quarantine the suspect bundles, and route execution into information-gathering nodes that regenerate provenance-stamped evidence. Transactional memory writes prevent the system from "learning the wrong lesson" by committing unverified narratives as durable memory.

### 12.2 Verifier-Plane Failure Modes

Verifier graphs introduce their own operational incidents:

- Flake amplification: a flaky verifier sits on a verification cut and blocks promotions.
- Calibration collapse: a verifier remains stable syntactically but becomes semantically miscalibrated under drift.
- Obligation misbinding: a verifier is treated as evidence for an obligation it does not actually support.

Recovery is policy-driven. Flake amplification triggers reliability quarantine and disjunctive routing around the cut; calibration collapse triggers gate hardening and a recalibration mission; obligation misbinding triggers obligation-lattice correction (repair implication edges or discharge mappings) and certificate invalidation for affected promotions.

### 12.3 Counterexample and Market Failures

Counterexample reservoirs reduce repeat regressions, but they introduce selection and pricing risks:

- Reservoir myopia: the portfolio overfits to a narrow region of failure space, missing new modes.
- Counterexample poisoning: adversarial or low-quality counterexamples enter the reservoir and distort routing.
- Market mispricing: counterexample prices do not reflect realized tail-risk reduction, biasing sequential evaluation.

Recovery relies on diversity constraints (coverage geometry), admission controls (trust and provenance scoring), and post-hoc auditing: when an incident occurs, the system must explain which obligations were believed discharged, which evidence paths were purchased, and whether mispricing or miscalibration caused under-verification.

### 12.4 Deployment-Coupled Recovery

The deploy controller provides a strong actuator for recovery, but it must be evidence-conditioned. Rollback is always permitted when health drops or tail risk spikes, but memory and evidence must also be quarantined: the system should not continue to reuse the same context that justified a failed advance. In solved-world operation, this coupling eliminates "mystery incidents with no causal chain" because every rollback event produces an evidence bundle and certificate delta that can be replayed.

### 12.5 What Disappears, What Remains

Compared to conventional pipelines, the following failure modes become rare or bounded:

- promotions without traceable evidence (certificate completeness enforces this)
- repeat regressions from forgotten counterexamples (reservoir memory)
- verification thrash on trivial edits (dependency-closure caching + sequential routing)
- governance bypass through informal exceptions (permissioned routing + certificate enforcement)

What remains are primarily meta-failures that are observable and correctable: calibration drift, obligation specification errors, and market or reservoir portfolio pathologies. The paper’s claim is not that failures vanish, but that they become legible, localized, and policy-controllable.

## 13. Limitations and Open Problems

Mission graphs are an engineering and research program, not a single algorithm. Several limitations are structural and must be addressed explicitly for the approach to be robust.

Two subclaims matter here. First, the hardest open problems are specification problems (what should be proven, under what semantics), not orchestration problems (how to run more tasks). Second, the evaluation artifacts that make mission graphs compelling (provenance, certificates, ledgers) create privacy and scale constraints that must be engineered, not wished away.

Several open problems stand out:

- how to specify obligations cleanly in novel domains
- how to calibrate verifiers under distribution shift and adversarial pressure
- how to preserve privacy while retaining auditable provenance
- how to compose many obligations without creating excessive overhead
- how to maintain strong autonomy when evidence is scarce

These are solvable research problems, but they require treating mission graphs as an engineered control system rather than a prompt trick.

## 14. Related Work and Positioning

Mission graphs sit at the intersection of several existing traditions, but they are not identical to any of them.

- Classical workflow engines provide orchestration, but they usually stop at task ordering and do not model evidence, confidence, or governed memory.
- CI/CD systems provide deployment automation, but they generally treat verification as a fixed stage rather than an adaptive control problem.
- Safe reinforcement learning and constrained optimization provide useful math for budgets and hazards, but they rarely model provenance, auditability, or artifact-level recovery.
- Proof-carrying code suggests that safety properties can be attached to artifacts, and mission graphs generalize that intuition from code to context, rollout, and governance.
- Multi-agent systems provide delegation, but delegation alone does not guarantee stable long-horizon execution or recoverable decision traces.

The key contribution of mission graphs is to bind these strands into one execution model. A mission graph is not just a scheduler, not just a memory system, not just a verifier, and not just a deploy controller. It is the coupling of all of those components through explicit state, evidence, and policy.

## 15. Formal Properties and Propositions

The paper’s thesis can be made more precise through a few useful propositions.

### Proposition 1: Evidence-Conditioned Promotion

If every promotion edge is guarded by a proof obligation set $\mathcal{O}_{i \to j}$ and every obligation must be discharged by a proof-carrying context bundle, then promotions are evidence-conditioned rather than narrative-conditioned.

This matters because it shifts the source of authority from conversational confidence to auditable artifacts.

### Proposition 2: Containment Under Provenance Radius

If context routing respects a bounded provenance radius and high-stakes nodes accept only core memory or revalidated bundles, then the spread of a false claim is structurally bounded by graph distance and revalidation cost.

This does not eliminate mistakes, but it limits how far a mistake can propagate before the system is forced to renew its evidence.

### Proposition 3: Tail-Risk Governance

If rollout control uses a tail-risk objective and treats error budget, governance, and human attention as explicit constraints, then rollout behavior becomes sensitive to rare but expensive incidents rather than only to average metrics.

This is the reason the risk-to-deploy interface is useful: average-success systems often fail precisely where long-horizon delivery is most costly.

### Proposition 4: Calibration-Coupled Verification

If verifier calibration SLOs are part of the control loop, then low-calibration verifiers can be downweighted, quarantined, or replaced before they distort promotion decisions.

This makes verification robust to drift in the evidence machinery itself.

## 16. End-to-End Case Study

Consider a realistic mission: shipping a latency optimization that also changes cache invalidation rules.

The mission begins with planning. The planner identifies that the change touches runtime behavior, observability, rollback, and perhaps a schema or configuration surface. It emits a graph contract with the following nodes: repo census, implementation, targeted unit tests, load replay, canary deployment, and post-deploy monitoring. The planner also attaches assumptions: the cache semantics are backward compatible, rollback is reversible, and the health metrics are reproducible under the current observability setup.

Context routing then gathers a proof-carrying bundle for the builder. The bundle includes the latest dependency graph, the affected runtime code, prior incident summaries, and a provenance-stamped performance baseline. Because the change affects a high-stakes surface, the context gate refuses any stale or low-liquidity summary. The builder therefore works against primary evidence rather than a vague architectural recollection.

Verification orchestration composes the necessary obligations. Unit tests cover functional correctness. A targeted replay suite covers representative request patterns. A small load test checks the expected latency envelope. The verifier orchestrator does not run every possible test; it chooses the minimal obligation discharge path with the highest risk reduction per cost. When one verifier is flaky, it is downweighted and another evidence route is chosen.

The patch is promoted only when the evidence ledger can produce a promotion certificate. That certificate records which obligations were discharged, which counterexamples were seen, which verifiers were trusted, and what the residual risk estimate was at the moment of promotion.

Deployment then runs the canary as an online evaluation. If the canary window stays healthy and the error budget remains stable, rollout advances in small increments. If provenance for the health window is missing, rollout holds until observability evidence is repaired. If the canary regresses, the system rolls back and quarantines the specific evidence that supported the prior promotion so that stale assumptions do not re-enter the core memory unchallenged.

This case study illustrates the paper’s central claim: the graph is not merely a coordination tool. It is a control system for moving from intent to production under bounded uncertainty.

## 17. Implementation Sketch

A prototype mission graph runtime would likely need the following components:

- a graph compiler that turns mission intent into nodes, edges, and gates
- a context router with provenance-aware retrieval and transactional writes
- a verifier orchestrator that schedules proof obligations and caches evidence
- a deployment controller that exposes rollout, hold, and rollback actuators
- an evidence ledger that stores certificates, traces, and counterexamples
- a governance engine that enforces permissions, review requirements, and rollback rules

The interface between these components should be artifact-centric. The compiler should emit machine-readable mission specs. The router should emit proof-carrying context packets. The verifier should emit promotion certificates. The deploy controller should emit projection receipts. The ledger should make all of these artifacts replayable.

This suggests two implementation subclaims. First, the ledger is the integration boundary: everything important should be keyed and replayable there. Second, projection receipts are the governance primitive that lets humans audit the system without reconstructing its internal state from logs.

## 18. Conclusion

Mission graphs are persistent, evaluable, permissioned systems for long-horizon software delivery. Their core contribution is to unify planning, context routing, verification, deployment, and governance into one control loop with explicit evidence, budgets, and rollback paths.

The practical significance of that unification is simple: software work becomes more legible, more auditable, and more recoverable. In the solved world, the organization no longer depends on memory, optimism, or informal process to ship safely. It depends on a graph that can explain itself.

Two final subclaims summarize the paper. First, legibility is not cosmetic; it is a performance property because it reduces wasted motion, repeated failure, and governance shock. Second, recovery should be the default mode of a mature mission graph, not an exceptional path.

## 19. Appendix: Quantum-Inspired Swarm Search

This appendix is speculative. It explores how a mission graph might use quantum-inspired variational search as a substrate for solving hard binary synthesis problems inside the planner or builder layer. The point is not to claim physical quantum advantage. The point is to give the graph a principled optimization primitive for search spaces that look like QUBOs: instruction selection, register allocation, scheduling, cache layout, and other binary combinatorial subproblems.

### 19.1 Binary Synthesis as an Energy Landscape

Suppose a synthesis task can be written as binary decision variables $\mathbf{x} \in \{0,1\}^n$ with objective:

$$
C(\mathbf{x}) = \sum_i a_i x_i + \sum_{i<j} b_{ij} x_i x_j + \text{constraint penalties}.
$$

This can be mapped to an Ising-style energy function:

$$
H = \sum_i h_i Z_i + \sum_{i<j} J_{ij} Z_i Z_j,
$$

where low-energy states correspond to good synthesis choices. In mission-graph terms, the planner can interpret this as a route-selection or layout-selection problem over a large binary design space.

### 19.2 Variational Swarm Update

Rather than committing to a single greedy choice, a swarm of agents can maintain distributions over candidate synthesis states. Let each agent carry a state vector $|\psi_t^{(i)}\rangle$ and evolve it by a parameterized unitary:

$$
|\psi\rangle_{t+1}^{(i)} = U(\theta_t^*) |\psi\rangle_t^{(i)},
\qquad
\theta_t^* = \arg\min_\theta \langle \psi_t^{(i)} | U^\dagger(\theta) H U(\theta) | \psi_t^{(i)} \rangle.
$$

This is best understood as a quantum-inspired search policy: it preserves broad exploration while gradually biasing the swarm toward low-energy, high-quality synthesis states.

### 19.3 Mission-Graph Interpretation

In a mission graph, this search primitive can play three roles:

- planner augmentation: propose compact graph topologies under combinatorial constraints
- builder augmentation: choose low-level synthesis parameters under size and speed tradeoffs
- verifier augmentation: search for counterexamples or minimal failing configurations under obligation constraints

The key subclaim is that an explicitly variational search primitive may outperform brittle greedy search when the underlying design space has many interacting binary constraints. That does not require literal quantum hardware; it requires a better stateful search policy.

### 19.4 Swarm Coupling and Counterexample Memory

A swarm search layer becomes more interesting when coupled to the mission graph’s evidence plane. Counterexamples discovered by one agent should not vanish; they should be written into the shared reservoir and used to reshape the search energy landscape for future agents. That turns failure into a persistent prior.

In this framing, the "best" synthesis state is not just the one with the lowest local cost. It is the state that minimizes cost while remaining compatible with provenance, recovery, verification, and deployment constraints.

### 19.5 Caveat

This appendix should be read as an advanced optimization metaphor and a possible implementation direction, not as a claim that the mission graph depends on quantum hardware. Its value is in suggesting how a swarm of agents could maintain global exploration while still converging on a low-energy synthesis policy.


### 13.1 Obligation Specification and Semantics

Obligations must be expressible in a form that is both meaningful to humans and dischargeable by machines. In novel domains, there may be no stable obligation vocabulary, and implication relationships in the obligation lattice may be unknown or unstable. Open problems include:

- obligation DSL design that supports implication, disjunction, and staged discharge without becoming a full theorem prover
- methods to learn or propose implication edges from evidence lineage without introducing unsoundness
- mechanisms to represent "soft obligations" (preferences) separately from "hard obligations" (constraints), avoiding accidental policy escalation

### 13.2 Calibration Under Shift

Verifier calibration SLOs require ground truth streams and stable semantics for "eventual correctness." Under distribution shift, the meaning of a verifier score can change, and counterexample markets can amplify miscalibration by buying the wrong evidence. Open problems include robust calibration under covariate shift, principled SLO thresholds for heterogeneous obligations, and adversarial calibration attacks that exploit soft gate composition.

### 13.3 Provenance, Privacy, and Governance

Proof-carrying context implies storing evidence lineage, which can leak sensitive information. There is a tension between auditability and privacy. Promising directions include:

- tiered provenance with redaction that preserves dischargeability
- cryptographic commitments to evidence (hashes/attestations) that allow verification without revealing raw payloads
- permission-aware summarization that is itself proof-carrying

### 13.4 Computational Overhead and Graph Scale

Mission graphs add overhead: more gates, more artifacts, more bookkeeping. The practical challenge is to keep the system net-positive by exploiting obligation lattices, sequential verification cascades, and reuse. Open problems include scaling the evidence ledger, avoiding lineage DAG blowup, and preventing verifier graphs from becoming a second unmaintainable build system.

### 13.5 Evidence Scarcity and Human Factors

When evidence is scarce (no tests, little telemetry, ambiguous specs), mission graphs must fall back to human review. A key open problem is designing policies that degrade gracefully: tighten gates and reduce autonomy without halting progress entirely. Another is incentive alignment: if teams optimize for certificate speed instead of safety, they may Goodhart obligations and markets. This motivates explicit metrics (Section 11) and governance constraints (Sections 7–9) as non-negotiable components of the system.

These limitations are solvable, but only if mission graphs are treated as engineered control systems with explicit state, constraints, and failure recovery, rather than as prompt tricks or ad hoc multi-agent workflows.

## 14. Related Work and Positioning

Mission graphs sit at the intersection of several existing traditions, but they are not identical to any of them.

Classical workflow engines and DAG orchestrators provide robust task ordering, retries, and operational visibility. They are strong at moving work through a topology, but they typically do not (i) treat *evidence* as a first-class object with provenance and calibration, (ii) treat *memory* as a governed, permissioned artifact store, or (iii) treat *promotion* as an evidence-conditioned decision with explicit obligations.

CI/CD systems provide deployment automation and a practical discipline around gating, but they often implement verification as a fixed stage sequence rather than an adaptive policy. In practice, CI/CD pipelines are mostly "run this suite, then deploy," whereas mission graphs propose an eval router that chooses checks dynamically under risk and budget constraints and records which proof obligations were discharged.

SRE practice around error budgets and progressive delivery adds crucial operational ideas: coupling shipping velocity to reliability and using canaries, holds, and rollbacks to protect users. Mission graphs treat these ideas not only as heuristics but as a controllable stochastic process with an explicit actuator (rollout fraction), sensors (health and verifier evidence), and an objective that prices tail risk.

Safe reinforcement learning, constrained optimization, and control theory provide formal tools for action selection under constraints and hazards. Mission graphs adopt this framing but extend the state and constraint sets to include provenance, auditability, and permission boundaries. In other words, the "safe set" is not merely physical safety or average performance; it also includes governance feasibility and evidence sufficiency.

Formal methods and proof-carrying code suggest that artifacts can carry proofs of properties, and that trust can be shifted from informal review to checkable evidence. Mission graphs generalize this: not only code artifacts but also *context bundles*, *promotion edges*, and *deployment health windows* are treated as proof-carrying objects that must discharge explicit obligations before affecting high-stakes actions.

Multi-agent systems, agentic tool use, and delegation frameworks emphasize decomposition and parallel work. Mission graphs are compatible with delegation but argue that delegation is not the primary abstraction. Without persistent state, gates, evidence ledgers, and rollback semantics, multi-agent execution remains brittle under delay, drift, and hidden coupling.

Two additional contrasts matter for positioning:

First, mission graphs treat governance as *projection*, not as a separate queue. Rather than "get approvals at the end," governance-projected control ensures that every nominal action is mapped into a feasible safe set and yields a receipt describing which constraints were active. This changes the operating model: governance becomes a continuous constraint, not a periodic ceremony.

Second, mission graphs treat "why did we do that?" as a system output, not as post-hoc explanation. Evidence ledgers, promotion certificates, and projection receipts make end-to-end behavior replayable and auditable by construction.

The key contribution is therefore the coupling: a mission graph is not just a scheduler, not just memory, not just verification, and not just deploy control. It is a single execution model in which these components interact through shared state, explicit obligations, and constraint-aware control.

## 15. Formal Properties and Propositions

The paper’s thesis can be made more precise through a few useful propositions.

### Proposition 1: Evidence-Conditioned Promotion

If every promotion edge is guarded by a proof obligation set $\mathcal{O}_{i \to j}$ and every obligation must be discharged by a proof-carrying context bundle, then promotions are evidence-conditioned rather than narrative-conditioned.

This matters because it shifts the source of authority from conversational confidence to auditable artifacts.

### Proposition 2: Containment Under Provenance Radius

If context routing respects a bounded provenance radius and high-stakes nodes accept only core memory or revalidated bundles, then the spread of a false claim is structurally bounded by graph distance and revalidation cost.

This does not eliminate mistakes, but it limits how far a mistake can propagate before the system is forced to renew its evidence.

### Proposition 3: Tail-Risk Governance

If rollout control uses a tail-risk objective and treats error budget, governance, and human attention as explicit constraints, then rollout behavior becomes sensitive to rare but expensive incidents rather than only to average metrics.

This is the reason the risk-to-deploy interface is useful: average-success systems often fail precisely where long-horizon delivery is most costly.

### Proposition 4: Calibration-Coupled Verification

If verifier calibration SLOs are part of the control loop, then low-calibration verifiers can be downweighted, quarantined, or replaced before they distort promotion decisions.

This makes verification robust to drift in the evidence machinery itself.

### Proposition 5: Governance-Projected Feasibility

Let $y_t$ denote the coupled rollout-governance state and let $\mathcal{A}_{\text{safe}}(y_t)$ denote the set of control actions satisfying:

- hard rollout constraints ($0 \le \tau_t + u_t \le 1$)
- budget feasibility ($b_{t+1} \succeq 0$)
- governance feasibility (permissions and required approvals satisfied)
- safety barriers (e.g., error budget invariance)

Define a governance-projected controller as:

$$
a_t^{\star}
=
\arg\min_{a \in \mathcal{A}_{\text{safe}}(y_t)}
\|a - a_t^{(0)}\|_W^2.
$$

If $\mathcal{A}_{\text{safe}}(y_t)$ is nonempty for all relevant $t$, then the controller produces feasible actions by construction, and the probability of violating any *explicitly encoded* constraint is zero under perfect enforcement.

This proposition clarifies a practical claim: governance should be expressed as constraints in the safe set, not as post-hoc review of actions already taken.

### Proposition 6: Hysteresis Bounds Chattering

Let $\text{mode}_t \in \{\text{ADVANCE},\text{HOLD},\text{ROLLBACK}\}$ be selected by threshold guards. If guards use symmetric thresholds, then bounded-noise observations can cause frequent mode flips (chattering), which in turn burns deploy budget and human attention.

If mode selection is defined by a rollback hysteresis envelope with separated thresholds and a minimum HOLD dwell time $\Delta_{\text{hold}}$, then the number of mode switches in any time window is bounded by the dwell-time budget and the envelope geometry. In particular, absent sustained constraint violations, the system cannot switch from HOLD to ADVANCE faster than once per $\Delta_{\text{hold}}$.

This makes stability an explicit policy object rather than an emergent property of metric noise.

### Proposition 7: Elastance-Optimal Review Allocation (Sketch)

Let $\eta$ denote review intensity and let $R(\eta)$ be the residual risk estimate after review. Define review elastance $\mathcal{E}_H(\eta) = -\frac{d}{d\eta}R(\eta)$ and let $c_H(\eta)$ be the cost of review.

Under mild regularity assumptions (e.g., $R$ is decreasing and convex in $\eta$ and $c_H$ is increasing and convex), the optimal $\eta^\star$ for a one-step controller satisfies a marginal condition of the form:

$$
\mathcal{E}_H(\eta^\star)
=
\lambda_H \frac{d}{d\eta} c_H(\eta^\star).
$$

This justifies a concrete operating rule: allocate review where marginal risk reduction per unit marginal cost is highest, and stop buying review when elastance collapses under overload.

## 16. End-to-End Case Study

Consider a realistic mission: shipping a latency optimization that also changes cache invalidation rules.

The mission begins with planning, but planning is already coupled to delivery constraints. The planner identifies that the change touches runtime behavior, observability, rollback, and configuration. It emits a graph contract that includes:

- a repo census node producing a proof-carrying dependency and ownership map
- an implementation node bounded by write permissions and a rollback contract
- a verification bundle: targeted unit tests, a request replay suite, and a latency envelope check
- a canary deployment node with a rollback hysteresis envelope tuned for latency noise
- a post-deploy monitoring node that emits provenance-stamped health evidence

Crucially, the planner also attaches explicit assumptions and obligations: cache semantics are backward compatible, rollback is reversible, health metrics are reproducible, and the SLO barrier must remain invariant during rollout.

Context routing gathers a proof-carrying bundle for the builder: affected modules, prior incidents involving cache invalidation, the baseline performance profile, and a provenance-stamped trace of the current cache behavior. Because the change is high impact, the context gate refuses stale or low-liquidity summaries and routes only primary-evidence-near bundles. The builder therefore works against verifiable references rather than architectural folklore.

Verification orchestration then constructs an obligation boundary for the promotion edge. Unit tests discharge functional obligations; replay discharges "representative workload" obligations; the latency envelope check discharges performance obligations. The orchestrator chooses checks adaptively under budget: cheap high-signal checks first; expand only if posterior tail risk remains high. If a performance check is flaky, calibration SLOs downweight it and trigger an alternative evidence route (additional replay windows or a different benchmark harness).

The patch is promoted only when the ledger can produce a promotion certificate: a structured object that records (i) obligations discharged, (ii) verifier signals and calibration status, (iii) counterexamples encountered and resolved, and (iv) a residual tail-risk estimate.

Deployment then turns into online evaluation and control. The controller observes verifier outputs $v_t$, health $h_t$, drift $\Delta_t$, and incident indicators. It proposes a nominal action (advance rollout by a fixed increment) and then applies governance-projected control: the action is projected into the safe set defined by budget feasibility, governance feasibility, and an error budget barrier constraint.

At this point, the solved-world operating model changes the experience of shipping. The deploy dashboard prominently displays shadow prices:

- if the error-budget shadow price spikes ($\pi_E \uparrow$), rollout increments collapse automatically and the system enters HOLD, gathering additional performance evidence rather than "pushing through"
- if the governance shadow price spikes ($\pi_G \uparrow$) due to missing provenance on a health window, the controller refuses to advance rollout and routes to observability repair

Rollback hysteresis envelopes prevent chattering. A transient health blip does not cause a rollback; instead the system holds for the minimum dwell time and requests additional evidence. Only sustained degradation crossing the rollback thresholds triggers rollback.

Finally, human review is purchased as an actuator, not as a ritual. If the system estimates high review elastance for concurrency-related changes in the caching layer (historically under-tested failure mode), it allocates targeted expert review; if elastance is low, it prefers additional machine evidence and smaller rollout steps.

This case study illustrates the paper’s central claim: the mission graph is a control system for moving from intent to production under bounded uncertainty, with explicit evidence and explicit constraints at every promotion and deployment decision.

## 17. Implementation Sketch

A prototype mission graph runtime would likely need the following components:

- a graph compiler that turns mission intent into nodes, edges, and gates
- a context router with provenance-aware retrieval and transactional writes
- a verifier orchestrator that schedules proof obligations and caches evidence
- a deployment controller that exposes rollout, hold, and rollback actuators
- an evidence ledger that stores certificates, traces, and counterexamples
- a governance engine that enforces permissions, review requirements, and rollback rules

The interface between these components should be artifact-centric. The compiler should emit machine-readable mission specs. The router should emit proof-carrying context packets. The verifier should emit promotion certificates. The deploy controller should emit projection receipts. The ledger should make all of these artifacts replayable.

To make this concrete, a minimal implementation can be structured as an event-driven runtime with an append-only log:

- **Mission spec**: a machine-readable graph contract with nodes, edges, budgets, and obligations.
- **Artifacts**: content-addressed objects (diffs, reports, traces) stored with hashes and permission labels.
- **Evidence ledger**: an append-only sequence of certificates (promotion certificates, projection receipts, counterexample bundles) referencing content-addressed artifacts.
- **Controllers**: policies that read the ledger and current signals and emit actions (route context, run evals, adjust rollout, request review).

Two practical subclaims follow from this structure:

First, the evidence ledger is the primary integration boundary. Existing CI systems can be adapted by having jobs emit structured evidence bundles and certificates into the ledger, without requiring a full rewrite of tooling.

Second, the projection receipt is a practical governance primitive. It is small, versionable, and reviewable. It allows a controller to justify actions in a form that security, compliance, and SRE teams can audit without reading code.

At the API level, the most important standardization is the risk-to-deploy interface:

$$
\mathcal{I}_{\text{R2D}}
=
(R_t,\; E_t,\; g_t^{\text{gov}},\; \hat{c}_t,\; h_t,\; \Delta_t),
\qquad
\mathcal{O}_{\text{R2D}}
=
(\text{mode}_t,\; u_t,\; \tau_t^{\text{gate}},\; \eta_t^{\text{human}},\; \kappa_t).
$$

This gives implementers a stable seam: verification and telemetry provide the inputs; deployment automation consumes the outputs. Governance-projected control can then be implemented as a projection module around existing rollout tooling rather than as an end-to-end replacement.

Security boundaries can be enforced by construction: each node runs with explicit permissions, every ledger write is signed, and high-stakes controllers accept only core memory or revalidated evidence bundles. This makes "permissioned over unconstrained" an engineering property rather than a best-effort guideline.

## 18. Conclusion

Mission graphs are persistent, evaluable, permissioned systems for long-horizon software delivery. Their core contribution is to unify planning, context routing, verification, deployment, and governance into one control loop with explicit evidence, budgets, and rollback paths.

The practical significance of that unification is that delivery becomes a controlled process with stable artifacts:

- promotions are conditioned on discharged obligations rather than informal confidence
- rollout is actuated and stabilized (advance/hold/rollback) under explicit risk and error-budget constraints
- governance is enforced continuously through feasibility projection, not episodically through exception handling

Two further subclaims become visible in the solved-world operating model.

First, legibility is a performance feature. Shadow prices, projection receipts, and promotion certificates reduce coordination cost and incident time-to-diagnosis. "Why did we slow rollout?" becomes answerable by reading the active constraints rather than reconstructing human intent after the fact.

Second, recovery becomes a default path rather than an emergency improvisation. Counterexample bundles, transactional memory writes, and quarantine rules prevent repeat regressions by making negative evidence durable and routable. The graph does not merely ship; it remembers what went wrong in a way that changes future control actions.

In the solved world, the organization no longer depends on memory, optimism, or informal process to ship safely. It depends on a graph that can explain itself, constrain itself, and recover itself.
