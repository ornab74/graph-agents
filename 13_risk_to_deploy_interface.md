# 13_risk_to_deploy_interface.md

# Risk-to-Deploy Interface

## Why this interface matters

Risk budgeting (Chapter 07), deployment rollout (Chapter 08), and governance (Chapter 09) are often designed as separate systems.

In a mission graph, they must form a single closed-loop controller:

- verifiers and monitoring estimate risk
- risk consumes budget and triggers governance requirements
- rollout is the actuator that turns code into production behavior
- governance is the constraint set that risk-aware autonomy cannot violate

## Coupled control state

Define the deployment state from Chapter 08:

$$
d_t = (\tau_t, e_t, s_t, \kappa_t),
$$

and budget state from Chapter 07:

$$
b_t =
\begin{bmatrix}
b_t^{\text{compute}} \\
b_t^{\text{money}} \\
b_t^{\text{tokens}} \\
b_t^{\text{human}} \\
b_t^{\text{deploy}}
\end{bmatrix}.
$$

Let governance scorecard state from Chapter 09 be summarized as $g_t^{\text{gov}}$ (higher is better).

A practical closed-loop state is

$$
y_t
=
\bigl(
d_t,\,
b_t,\,
R_t,\,
E_t,\,
g_t^{\text{gov}}
\bigr),
$$

where:

- $R_t$ is a scalar risk estimate (aggregated from $\rho_t^{(j)}$)
- $E_t$ is the service error budget (or reliability slack)

## Observable signals

Let the system observe

$$
o_t
=
\bigl(
v_t,\,
h_t,\,
\Delta_t,\,
\text{incidents}_t
\bigr),
$$

where:

- $v_t$ are verifier outputs (tests, security scans, contract checks)
- $h_t$ is a health score (latency, error rate, saturation)
- $\Delta_t$ is drift or change magnitude since last stable state
- $\text{incidents}_t$ are production incident indicators

These are the measurements the controller can use to steer rollout.

## Control actions

The controller has three types of actuators:

1. **Rollout control**: choose rollout increment $u_t$ so $\tau_{t+1} = \tau_t + u_t$.
2. **Gate tightening**: increase thresholds $\tau_i$ in verifiers / gates, or add additional evals.
3. **Governance escalation**: consume human budget to require review, approvals, or freeze learning updates.

Collect actions as

$$
a_t^{\text{ctrl}} = (u_t,\; \theta_t^{\text{gate}},\; \eta_t^{\text{human}}),
$$

where $\theta_t^{\text{gate}}$ parameterizes gate strictness and $\eta_t^{\text{human}}$ parameterizes review intensity.

## Risk estimate as a filtered posterior

Let $\theta_t$ denote latent defect probability under current rollout.
Using a Beta-Binomial update as in Chapters 06 and 08:

$$
\theta_t \mid k,n \sim \operatorname{Beta}(\alpha + k,\; \beta + n - k).
$$

Define a scalar risk estimate as a tail probability:

$$
R_t
=
\Pr(\theta_t \ge \theta_{\max} \mid k,n).
$$

This makes risk actionable: it is a directly thresholdable quantity.

## Error-budget coupling

Let $E_t$ evolve as in Chapter 08:

$$
E_{t+1} = E_t - \max(0, S^\star - S_t),
$$

where $S_t$ is observed SLO performance.

Risk control should incorporate $E_t$ explicitly because low error budget makes every marginal rollout step more expensive.

## Governance constraint set

Let $\mathcal{C}_{\text{gov}}$ denote governance constraints (approval rules, permission boundaries, auditability requirements).

Express them as feasibility constraints on the controller:

$$
a_t^{\text{ctrl}} \in \mathcal{A}_{\text{safe}}(y_t)
\quad\text{and}\quad
\Pr(\text{gov violation} \mid y_t, a_t^{\text{ctrl}}) \le \epsilon_{\text{gov}}.
$$

In words: rollout advances are disallowed if they would predictably violate governance.

## The closed-loop objective

The rollout controller should optimize value subject to safety:

$$
\max_{\{a_t^{\text{ctrl}}\}}
\;
\mathbb{E}\left[
\sum_{t=0}^{T}
\gamma^t
\left(
V(\tau_t)
- \lambda_R R_t
- \lambda_E \max(0, E_{\min} - E_t)
- \lambda_H \eta_t^{\text{human}}
\right)
\right]
$$

subject to:

$$
0 \le \tau_t \le 1,\quad
b_t \succeq 0,\quad
g_t^{\text{gov}} \ge g_{\min}.
$$

Interpretation:

- $V(\tau_t)$ is delivered feature value increasing in rollout fraction
- $R_t$ penalizes tail risk of defects
- the $E_t$ term penalizes approaching or crossing error budget limits
- the human term prices review load explicitly

## New concept: governance-projected control

Operationally, teams often pick a nominal rollout plan (a canary schedule) and then layer governance and safety as post-hoc stop conditions.
That architecture causes two predictable failures:

- the nominal plan keeps pushing even when constraints are tight, creating repeated stop-start oscillations
- constraint handling is implicit and difficult to audit ("we rolled back because vibes")

In a mission graph, governance is better treated as part of the controller.

Let the controller first propose a nominal action $a_t^{(0)} = (u_t^{(0)}, \theta_t^{(0)}, \eta_t^{(0)})$ and then project it into the feasible set.

Define the safe action set $\mathcal{A}_{\text{safe}}(y_t)$ to include:

- hard rollout constraints: $0 \le \tau_t + u_t \le 1$
- budget feasibility: $b_{t+1} = b_t - c_t(a_t^{\text{ctrl}}) \succeq 0$
- governance feasibility: required approvals and permission boundaries satisfied
- safety constraints derived from SLO and risk bounds

Define the **governance-projected controller (GPC)**:

$$
a_t^{\star}
=
\arg\min_{a \in \mathcal{A}_{\text{safe}}(y_t)}
\;
\|a - a_t^{(0)}\|_{W}^2,
$$

where $W \succeq 0$ weights deviation costs (for example, rolling back is often expensive and should not occur unless constraints demand it).

The GPC turns governance from a separate pipeline into an explicit projection operator that shapes every rollout step.

## New concept: risk-to-deploy dual variables

Risk-to-deploy decisions sit at the intersection of multiple constraints.
A useful controller should make those constraints legible.

Introduce a one-step constrained objective:

$$
\max_{a \in \mathcal{A}_{\text{safe}}(y_t)}
\;
\widehat{V}(\tau_t + u)
- \lambda_R R_t
- \lambda_H \eta,
$$

where $\widehat{V}$ is predicted value delivered by increasing rollout fraction.

The KKT multipliers for the constraints are interpretable shadow prices.
In particular, let $\pi_E(t)$ be the multiplier on the error-budget constraint $E_t \ge E_{\min}$ and let $\pi_G(t)$ be the multiplier on governance feasibility (for example, missing evidence or approvals).

Interpretation:

- $\pi_E(t)$ is the **error-budget shadow price**: it rises sharply when reliability slack is scarce, and it should slow rollout mechanically
- $\pi_G(t)$ is the **governance shadow price**: it rises when auditability or permission constraints are tight, and it should increase review and evidence collection

These dual variables are not just math artifacts.
They provide human-comprehensible explanations and a stable interface for debugging deployment behavior across missions.

## Error-budget economics (elastic rollout)

The linear "shrink rollout increment when $E_t$ is low" rule is a good baseline.
However, near the safety boundary, controllers typically need to be superlinear conservative to avoid repeated threshold crossings.

Define error-budget pressure:

$$
p_E(t) = \max\left(0, \frac{E_{\min} - E_t}{E_{\min}}\right).
$$

Define an **elastic rollout law**:

$$
u_t
=
\bar{u}
\cdot
\exp(-\zeta_E p_E(t))
\cdot
\mathbf{1}\{h_t \ge h_{\min}\}
\cdot
\mathbf{1}\{R_t \le R_{\max}\}.
$$

This yields:

- rapid progress when slack is plentiful
- steep slowdown as the controller approaches the SLO boundary

The dual view connects this to $\pi_E(t)$: high $\pi_E$ implies high $p_E$, which implies small $u_t$.

## Safety barrier constraints (SLO invariance)

Expected-value control is not enough if "never violate an SLO boundary" is the actual requirement.
To express that requirement, enforce invariance of a safe set.

Let the safe set be:

$$
\mathcal{S} = \{y: E(y) \ge E_{\min}\}.
$$

Define a discrete-time barrier function:

$$
B(y_t) = E_t - E_{\min}.
$$

Enforce a barrier constraint:

$$
B(y_{t+1}) \ge (1-\alpha_B) B(y_t),
$$

with $\alpha_B \in (0,1]$ controlling how quickly the controller may spend slack.
In practice, implement this inside $\mathcal{A}_{\text{safe}}(y_t)$ using a one-step prediction $\widehat{E}_{t+1}(a)$ derived from telemetry.

This is a clean way to turn "error budget coupling" into a checkable control invariant.

## Safe rollout policy as a state machine

For operational clarity, implement the optimal policy as a state machine driven by risk and health:

- **ADVANCE**: increase $\tau$ if gates pass, health is stable, and risk is low
- **HOLD**: keep $\tau$ fixed while gathering evidence (more canary windows, more evals)
- **ROLLBACK**: decrease $\tau$ if health drops, risk spikes, or incidents appear

Formally, define:

$$
\text{mode}_t \in \{\text{ADVANCE},\text{HOLD},\text{ROLLBACK}\}.
$$

One simple guard condition is:

$$
\text{mode}_t=
\begin{cases}
\text{ROLLBACK} & \text{if } h_t < h_{\min} \;\text{or}\; R_t > R_{\max}\;\text{or}\; E_t < E_{\min},\\
\text{ADVANCE} & \text{if } h_t \ge h_{\min} \;\text{and}\; R_t \le R_{\text{adv}}\;\text{and}\; g_t^{\text{gov}} \ge g_{\min},\\
\text{HOLD} & \text{otherwise.}
\end{cases}
$$

This is the practical interface between the math and real deployment pipelines.

## New concept: rollback hysteresis envelopes

Threshold-based mode switching can oscillate under noisy health metrics and sparse canary windows.
Oscillation is expensive: it burns deploy budget, triggers repeated human pages, and makes postmortems harder.

Introduce hysteresis and dwell time.

Let $R_{\text{rb}} > R_{\text{adv}}$ and let $h_{\text{adv}} > h_{\text{rb}}$ be distinct thresholds for entering and leaving rollback.
Let $\Delta_{\text{hold}}$ be a minimum time spent collecting evidence in HOLD before advancing.

Define:

$$
\text{mode}_t=
\begin{cases}
\text{ROLLBACK} & \text{if } R_t \ge R_{\text{rb}} \;\text{or}\; h_t \le h_{\text{rb}} \;\text{or}\; E_t \le E_{\min},\\
\text{ADVANCE} & \text{if } R_t \le R_{\text{adv}} \;\text{and}\; h_t \ge h_{\text{adv}} \;\text{and}\; \operatorname{dwell}(\text{HOLD}) \ge \Delta_{\text{hold}},\\
\text{HOLD} & \text{otherwise.}
\end{cases}
$$

Call $(R_{\text{adv}}, R_{\text{rb}}, h_{\text{adv}}, h_{\text{rb}}, \Delta_{\text{hold}})$ a **rollback hysteresis envelope (RHE)**.

RHEs are small objects that can be reviewed, versioned, and learned across missions, and they make rollout behavior far less sensitive to measurement noise.

## Gate tightening as risk feedback

When risk increases, the controller should raise gate strictness or route to additional verifiers.

Let composite confidence from Chapter 06 be $\hat{c}_t \in [0,1]$.
Define adaptive gate threshold:

$$
\tau^{\text{gate}}_t
=
\tau_0
+ \xi_1 R_t
+ \xi_2 \max(0, E_{\min}-E_t).
$$

Then require:

$$
\hat{c}_t \ge \tau^{\text{gate}}_t.
$$

This links "risk is high" to a concrete behavior change: gates get stricter.

## Human review as a budgeted actuator

Human oversight is not binary; it is a resource to be allocated.

Let $\eta_t^{\text{human}} \in [0,1]$ be the fraction of outputs requiring review.
Consume human budget:

$$
b_{t+1}^{\text{human}} = b_t^{\text{human}} - c_H(\eta_t^{\text{human}}).
$$

Choose human review when it reduces tail risk enough to justify the cost:

$$
\Delta \operatorname{CVaR}_\alpha(L \mid \eta_t^{\text{human}})
>
\frac{c_H(\eta_t^{\text{human}})}{\lambda}.
$$

This turns "escalate to a human" into an explicit control action with economics.

## New concept: human review elastance

Review does not convert into safety linearly.
Most teams experience three regimes:

- high-yield: a small amount of review catches many high-severity issues
- diminishing returns: additional review yields smaller incremental risk reduction
- overload: review quality drops when attention is scarce and queues are long

To model this, treat review as an actuator with a response curve.

Let $R(\eta)$ be the risk estimate after applying review intensity $\eta \in [0,1]$.
Define **review elastance**:

$$
\mathcal{E}_H(\eta)
=
-\frac{d}{d\eta} R(\eta).
$$

Define a reviewer quality factor $q_H \in (0,1]$:

$$
q_H
=
\sigma\!\left(\omega_0 + \omega_1 b_t^{\text{human}} - \omega_2 \cdot \text{queue\_load}_t\right).
$$

Then realized elastance is:

$$
\widetilde{\mathcal{E}}_H(\eta) = q_H \cdot \mathcal{E}_H(\eta).
$$

Allocate review where it is most effective given current human capacity:

$$
\eta_t^{\star}
=
\arg\max_{\eta \in [0,1]}
\left[
\widetilde{\mathcal{E}}_H(\eta)
- \lambda_H \frac{d}{d\eta} c_H(\eta)
\right].
$$

This turns human review from a static policy into a measurable, optimizable part of the control loop.

## Freezing learning under drift

When drift is large, learned policies can silently degrade.
Use a governance-driven freeze rule:

$$
\mathbf{1}\{\text{learning enabled}\}
=
\mathbf{1}\{\Delta_t \le \Delta_{\max}\}
\cdot
\mathbf{1}\{g_t^{\text{gov}} \ge g_{\min}\}.
$$

In words: high drift or poor governance scores disable outer-loop updates during rollout.

## The interface contract

To connect the systems cleanly, define a standard interface between risk, deploy, and governance:

$$
\mathcal{I}_{\text{R2D}}
=
(R_t,\; E_t,\; g_t^{\text{gov}},\; \hat{c}_t,\; h_t,\; \Delta_t).
$$

And a standard controller output:

$$
\mathcal{O}_{\text{R2D}}
=
(\text{mode}_t,\; u_t,\; \tau_t^{\text{gate}},\; \eta_t^{\text{human}},\; \kappa_t).
$$

If teams can only standardize one thing, standardize these signals.

## Summary (what this adds)

This chapter couples three previously separate pieces into one loop:

- risk estimates and budgets become inputs that actively shape rollout speed and gating strictness
- deployment rollout becomes a controllable actuator rather than a linear "ship it" step
- governance becomes a constraint set that is checked continuously, not only at the end

That interface is what makes mission graphs deployable at scale without losing safety or auditability.

## Summary (new concepts introduced)

- **Governance-projected controller (GPC)**: project nominal rollout actions onto a governance- and safety-feasible set before acting.
- **Risk-to-deploy dual variables**: shadow prices (especially an error-budget shadow price) that quantify why rollout slows, gates tighten, or review increases.
- **Rollback hysteresis envelopes (RHEs)**: hysteresis and dwell-time parameters that prevent advance/rollback oscillation under noisy telemetry.
- **Human review elastance**: a marginal-effectiveness curve for review under overload, enabling principled allocation of scarce human oversight.
