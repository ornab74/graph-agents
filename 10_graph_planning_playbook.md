# 10_graph_planning_playbook.md

# Graph Planning Playbook

## From concept to executable graph

A mission graph becomes useful when planning stops being an abstract design exercise and turns into a repeatable construction process.

The planner should answer five questions:

- what is the mission objective
- what state must be known before acting
- what can be parallelized safely
- what must be verified before promotion
- what failure paths exist if a step goes wrong

## Graph synthesis

Let the planner emit a graph skeleton

$$
\hat{\mathcal{G}} = (\hat{V}, \hat{E}, \hat{\Pi}, \hat{\Gamma}, \hat{\mathcal{B}}).
$$

The synthesis objective is to maximize expected mission utility while minimizing structural waste:

$$
\max_{\hat{\mathcal{G}}}
\;
\mathbb{E}[J(\hat{\mathcal{G}})]

- \lambda_1 \, |\hat{V}|
- \lambda_2 \, |\hat{E}|
- \lambda_3 \, \operatorname{fragility}(\hat{\mathcal{G}})
$$

This is the formal version of “keep the graph small enough to control, but rich enough to deliver.”

## Planning stages

The planning workflow is naturally staged:

1. **Intent capture** - extract the mission goal and hard constraints.
2. **State census** - inspect repo, tests, history, and environment.
3. **Decomposition** - split the mission into candidate subgoals.
4. **Topology design** - connect nodes with precedence, merge, and gate edges.
5. **Budget assignment** - allocate compute, time, permission, and human-review budget.
6. **Verification design** - attach tests, evals, and approval rules.
7. **Recovery design** - define retries, fallbacks, and rollback edges.

Each stage should output an artifact, not just a conversational summary.

## Candidate node score

For a candidate node $v$, define a planning score

$$
\psi(v)
=
\alpha_1 \, \text{expected\_value}(v)
+ \alpha_2 \, \text{information\_gain}(v)
+ \alpha_3 \, \text{parallelism\_benefit}(v)
- \alpha_4 \, \text{coordination\_cost}(v)
- \alpha_5 \, \text{risk}(v).
$$

Include the node only if

$$
\psi(v) \ge \tau_{\text{plan}}.
$$

This prevents the planner from creating “busywork nodes” that look sophisticated but add little value.

## Edge selection

Edges should encode one of four relationships:

- **precedence**: one node must finish before another starts
- **information flow**: one node informs another
- **verification**: one node validates another node’s output
- **recovery**: one node repairs or replaces a failed path

Let each potential edge $e_{ij}$ have a utility

$$
u(e_{ij})
=
\beta_1 \, \text{dependency\_strength}
- \beta_2 \, \text{latency}
- \beta_3 \, \text{coordination\_overhead}.
$$

Retain the edge only if it improves graph-level utility.

## Fan-out and merge policy

Fan-out should occur when uncertainty is high and branches are cheap relative to the value of exploration.

Let $B$ be the number of branches and $c_B$ the marginal branch cost.  
Then branch if

$$
\operatorname{EVI}_{\text{branch}} > c_B.
$$

Merge should occur only when branch outputs are sufficiently aligned:

$$
\Delta_{\text{branch}} \le \epsilon_{\text{merge}}.
$$

If not, route to a reconciliation node rather than forcing an early merge.

## Budgeted planning

Planning itself consumes budget.  
Let planning cost be $C_{\text{plan}}$ and downstream execution cost be $C_{\text{exec}}$.

The planner should minimize total expected cost:

$$
\min
\;
\mathbb{E}[C_{\text{plan}} + C_{\text{exec}}]
$$

subject to delivery and safety constraints.

If a proposed subplan is expensive to reason about but cheap to execute, it may still be worthwhile.  
If it is cheap to reason about but likely to explode during execution, it should be rejected.

## Planning artifacts

A usable planning artifact should include:

- mission goal
- explicit assumptions
- graph sketch
- node list with responsibilities
- dependency list
- verification gates
- rollback paths
- budget table
- escalation conditions

If any of these are missing, the mission graph is under-specified.

## Planner outputs as contracts

The planner should emit contracts of the form

$$
\mathcal{P}
=
\bigl(
\mathcal{T},
\mathcal{E},
\mathcal{G},
\mathcal{R},
\mathcal{K}
\bigr),
$$

where:

- $\mathcal{T}$ is the task set
- $\mathcal{E}$ is the edge set
- $\mathcal{G}$ is the gate set
- $\mathcal{R}$ is the rollback set
- $\mathcal{K}$ is the set of known assumptions and unknowns

This turns planning into a machine-checkable output rather than a loose strategy note.

## Summary

Planning agent graphs is the act of shaping uncertainty into a controlled execution topology.

The planner should:

- keep the graph small
- branch only when information is worth the cost
- attach gates to every material edge
- budget for retries and human review
- emit artifacts that downstream nodes can execute against

That is how mission graphs stay legible, efficient, and safe enough to run.
