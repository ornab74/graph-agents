# 09_learning_governance.md

# Learning and Governance

## Long-horizon improvement

A mission graph should improve from mission to mission.  
Without learning, the graph is merely repeatable.  
With learning, it becomes compounding infrastructure.

There are two learning loops:

- **inner loop**: adaptation during a mission
- **outer loop**: policy updates across missions

## Meta-objective

Let mission $j$ produce return $G_j$.  
The long-run goal is

$$
\max_{\Theta}
\mathbb{E}_{j \sim \mathcal{M}}
\left[
G_j(\Theta)
\right],
$$

where $\Theta$ parameterizes planners, schedulers, retrievers, verifiers, and deployment controllers.

## Online adaptation

Within a mission, adapt parameters by

$$
\Theta_{t+1} = \Theta_t - \eta_t \nabla_\Theta \ell_t(\Theta_t).
$$

Examples:

- update retrieval weights
- tune verifier thresholds
- change retry policy
- adjust rollout increments

## Policy-gradient framing

If execution is policy-driven, optimize

$$
J(\theta)
=
\mathbb{E}_{\tau \sim \pi_\theta}[G(\tau)].
$$

Then

$$
\nabla_\theta J(\theta)
=
\mathbb{E}_{\tau \sim \pi_\theta}
\left[
\sum_{t}
\nabla_\theta \log \pi_\theta(a_t \mid s_t)\, \hat{A}_t
\right],
$$

where $\hat{A}_t$ is an advantage estimator.

This lets the system learn better graph policies from mission outcomes.

## Regret minimization

Across missions, define regret

$$
\operatorname{Regret}(N)
=
\sum_{j=1}^{N}
\bigl(
G_j^\star - G_j
\bigr),
$$

where $G_j^\star$ is the return of the best policy in hindsight.

A healthy system should aim for sublinear regret:

$$
\operatorname{Regret}(N) = o(N).
$$

That means average per-mission regret tends to zero.

## Governance constraints

Learning cannot override policy.  
Let $\mathcal{C}_{\text{gov}}$ be governance constraints such as permission boundaries, human-approval requirements, or audit obligations.

Then policy updates must satisfy

$$
\pi_{\theta'} \in \mathcal{P}_{\text{safe}}
=
\{\pi : \Pr_\pi(\text{governance violation}) \le \epsilon\}.
$$

One approach is trust-region constrained updates:

$$
\max_{\theta'}
\; J(\theta')
\quad \text{s.t.}\quad
D_{\mathrm{KL}}(\pi_{\theta'} \,\|\, \pi_{\theta}) \le \delta,
\quad
\pi_{\theta'} \in \mathcal{P}_{\text{safe}}.
$$

## Auditability metric

Each mission should emit a complete trace.  
Define audit coverage

$$
A_{\text{cov}}
=
\frac{
N_{\text{decisions with evidence}}
}{
N_{\text{material decisions}}
}.
$$

Target:

$$
A_{\text{cov}} \to 1.
$$

A system that cannot explain why it shipped something is not governance-ready.

## Causal credit assignment

Long-horizon systems need to know which node or policy choice caused outcomes.  
Suppose mission return is $G$ and intervention on component $i$ yields counterfactual $G^{(-i)}$.

Then causal contribution can be approximated by

$$
\Delta_i = G - G^{(-i)}.
$$

This can inform:

- which retriever improved success
- which verifier caused delay with little value
- which deployment controller reduced incidents
- which node template should be retired

## Drift monitoring

Distribution shift matters.  
Let historical feature distribution be $P_t$ and current be $P_{t+1}$.  
Track drift via

$$
D_{\mathrm{KL}}(P_{t+1}\,\|\,P_t)
\quad \text{or} \quad
W_2(P_{t+1},P_t).
$$

If drift exceeds threshold, freeze learning updates or increase human oversight.

## Governance scorecard

A simple scalar governance score:

$$
G_{\text{gov}}
=
\lambda_1 A_{\text{cov}}
+
\lambda_2 (1-\text{violation rate})
+
\lambda_3 (1-\text{unauthorized action rate})
+
\lambda_4 \text{reproducibility}.
$$

This should be reported per mission and over time.

## Human override economics

Human review is expensive but protective.  
Let autonomous decision value be $V_a$ and reviewed decision value be $V_h - C_h$.  
Use human review when

$$
V_h - C_h > V_a.
$$

Equivalently, override where expected risk reduction times incident cost exceeds review cost.

## Summary

Learning and governance are not opposites.  
In a good mission graph they are coupled:

- learn faster where evidence is strong
- constrain updates where risk is high
- maintain audit trails for all material actions
- localize credit and blame
- monitor drift before autonomy silently degrades

That is how mission graphs become an enduring operating system rather than a one-off orchestration trick.
