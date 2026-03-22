# context.md

# Codex Mission Graphs — Context Pack

This pack reframes **subagents** as a weaker primitive inside a larger system: a **mission graph**.  
A mission graph is a persistent, evaluable, permissioned execution graph for long-horizon software work.

Instead of thinking in terms of “spawn a helper,” think in terms of:

- **graph structure**: nodes, edges, dependencies, and gates
- **persistent state**: memory, artifacts, checkpoints, and audit logs
- **execution policy**: planning, scheduling, retries, and escalation
- **verification**: tests, proofs, evals, and approval rules
- **deployment**: progressive delivery, rollback, and recovery
- **learning**: post-task updating, policy adaptation, and budget optimization

## Core thesis

A subagent is a delegated worker.  
A mission graph is a **stateful computational process** that can plan, branch, verify, and ship.

## Canonical object

We define a mission graph as:

$$
\mathcal{G} = (V, E, \mathcal{S}, \mathcal{A}, \Pi, \Omega, \Gamma, \mathcal{B}, \mathcal{R})
$$

where:

- $V$ is the set of execution nodes
- $E \subseteq V \times V$ is the dependency relation
- $\mathcal{S}$ is the global state space
- $\mathcal{A}$ is the action space across all nodes
- $\Pi$ is the collection of node policies
- $\Omega$ is the observation model
- $\Gamma$ is the set of gates and evaluators
- $\mathcal{B}$ is the set of budgets and constraints
- $\mathcal{R}$ is the reward or utility model

## Master objective

The system should maximize delivered value while respecting risk, budget, and policy constraints:

$$
\max_{\Pi, \sigma, \kappa}
\;\;
J
=
\mathbb{E}\left[
\sum_{t=0}^{T}
\gamma^t
\left(
U_t - \lambda_c C_t - \lambda_r R_t - \lambda_d D_t
\right)
\right]
$$

subject to:

$$
\Pr(\text{policy violation}) \le \varepsilon_p,\qquad
\Pr(\text{SLO breach}) \le \varepsilon_s,\qquad
\sum_{t=0}^{T} C_t \le B.
$$

Interpretation:

- $U_t$ = mission utility at step $t$
- $C_t$ = compute or financial cost
- $R_t$ = operational or model risk
- $D_t$ = delivery delay
- $B$ = budget ceiling
- $\gamma$ = temporal discount factor
- $\sigma$ = scheduler
- $\kappa$ = checkpoint / rollback policy

## Design principles

1. **Persistent over ephemeral**  
   The state of work must survive retries, handoffs, and failures.

2. **Evaluable over impressionistic**  
   Every important node should emit measurable success criteria.

3. **Permissioned over unconstrained**  
   Tool use, network access, deployment scope, and write privileges are explicit.

4. **Artifact-first over chat-first**  
   Outputs are code, specs, tests, patches, dashboards, and deployment records.

5. **Rollbackable over brittle**  
   Every critical edge has a recovery path.

6. **Learned over static**  
   The graph updates future behavior using the outcomes of prior missions.

## Recommended node taxonomy

A practical first taxonomy:

- **Scout** — inspect repo, incidents, docs, telemetry
- **Planner** — form plan, DAG, milestone ordering
- **Builder** — implement code changes
- **Tester** — run unit, integration, and regression checks
- **Reviewer** — security, correctness, architecture checks
- **Integrator** — merge artifacts and resolve conflicts
- **Deployer** — canary, staged rollout, rollback
- **Historian** — maintain decision log and memory index
- **Governor** — enforce policy and human approval rules

## Shared notation

Throughout these files:

- $x_t$ = global mission state at time $t$
- $o_t$ = observation available to a node
- $a_t$ = action taken by a node
- $m_t$ = memory state
- $b_t$ = remaining budget vector
- $r_t$ = reward or utility signal
- $\ell_t$ = loss
- $\mathcal{C}$ = set of constraints
- $\tau$ = rollout or canary parameter
- $\rho$ = risk measure
- $\hat{y}$ = prediction, estimate, or verifier output

## File map

1. **01_mission_graphs_overview.md**  
   Product framing, formal object, and high-level architecture.

2. **02_graph_dynamics.md**  
   State evolution, dependency structure, and graph-theoretic control.

3. **03_context_memory.md**  
   Context routing, retrieval, summarization, and memory compression.

4. **04_planning_decomposition.md**  
   Hierarchical planning, decomposition, and decision-theoretic control.

5. **05_execution_scheduling.md**  
   Resource allocation, scheduling, concurrency, retries, and throughput.

6. **06_verification_evals.md**  
   Test gates, statistical validation, proof obligations, and confidence scoring.

7. **07_risk_budgeting.md**  
   Risk-sensitive utility, cost management, budget enforcement, and escalation.

8. **08_deployment_rollout.md**  
   Progressive delivery, canaries, SLO protection, and rollback dynamics.

9. **09_learning_governance.md**  
   Meta-learning, governance, auditability, and long-horizon adaptation.

10. **10_graph_planning_playbook.md**  
    Practical graph synthesis, node selection, edge design, and planning artifacts.

## Suggested reading order

Use the pack in this order:

1. Overview
2. Graph dynamics
3. Context + memory
4. Planning
5. Scheduling
6. Verification
7. Risk + budgeting
8. Deployment
9. Learning + governance
10. Graph planning playbook

## Operating assumption

This material is intended for designing a **Codex-native mission execution layer**:

- graph-native
- artifact-centric
- equation-backed
- suitable for implementation specs, research notes, or investor-facing architecture docs

## One-line positioning

> Not subagents. Mission graphs: persistent, evaluable, permissioned systems for long-horizon software execution.
