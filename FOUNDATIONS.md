# SynapticContinuum — Working Foundations

**Living orientation · 2026-10-24 · provisional hypotheses, not a settled architecture**

**Read [VISION.md](VISION.md) first.** It defines the scientific aspiration and operational meaning of our terms. This file defines constraints that should persist as our engineering hypotheses change. The older concept-level atlas is archived separately; [ATLAS.md](ATLAS.md) now maps competing research avenues.

## The research object is an ongoing process, not a response

A candidate system persists as an individual developing dynamical process. External events, internal activity, external actions, and occasional communication are interactions with that process, not compulsory request/response boundaries. It may perform nontrivial internal work, revisit experiences or rest when no event occurs. We test whether that work has later causal consequences rather than praising activity for its own sake.

The desired behavior is **open-ended, probabilistic, revisable exploration of meaningful possibilities**: reconstructing possible pasts, updating uncertain presents, imagining counterfactuals and futures, exploring analogies, interacting with other ongoing processes, and occasionally acting or communicating, without a requested conclusion. There is no promise that we can build this.

## Representational openness

The substrate need not contain labeled entities, symbols or words. Distributed activity, phase/synchrony, temporal histories, embeddings, local connections, episodic patterns, dynamic binding, discrete graph structures or combinations are all open hypotheses. Object identity and role binding cannot simply be ignored: the system must eventually distinguish two similar individuals and the different roles in 'X supports Y' versus 'Y supports X'. That requirement does **not** prescribe one-node-per-object architecture.

A word is an optional observation, action or later probabilistic interpretation of an internal trajectory. A system may learn useful causal consequences before learning the label 'cat'. Adding a category label later can revise confidence about an earlier ambiguous experience, but not make a guess into an observed fact. Use independent diagnostic decoders and test whether they—not the substrate—perform all semantic reasoning.

## Persistent time and epistemic distinctions

Time is a central variable, not necessarily an explicit time-token input. An observation made at t0 remains a valid claim about t0; uncertainty about the world at t1 evolves as unseen changes become possible. Maintain or recover distinction among observed evidence, remembered observation, uncertain current belief, hypothetical past explanation, future prediction, counterfactual imagination and external action. Exact implementation is an open hypothesis.

Past experience may be retrieved through partial temporal activation matching and combined into *new* candidate trajectories. Replaying a stored sequence is different from discovering a transferable causal relationship. A system should transfer 'can fall from height' from vase to cat-like creature without necessarily transferring 'fragile and breaks'.

## Significance and endogenous priority

A candidate internal direction may carry multiple coexisting regulatory dimensions: uncertainty, risk, novelty, relevance, anticipated benefit/harm, reducible surprise, learning progress, urgency, familiarity, habituation and computational cost. These are **proposed control signals**, not proof of emotions or a commitment to a single handcrafted feeling vector. Plausibility of an imagined possibility and priority for further exploration are separate quantities.

Changing internal possibilities can alter significance; significance can alter activity, resource scheduling, plasticity, interest in other possibilities, and optional outward action. Curiosity may favor expected learning progress over irreducible random noise. Fear-like control may increase *internal* study of a danger while inhibiting an unsafe *external* action. Motivation may itself adapt through experience. Rest and silence are valid outcomes.

## Learning and correction

Distinguish ongoing state evolution, durable learning/plasticity, episodic retention/replay, selective inhibition or forgetting, adaptation of the exploration policy, and topology or capacity change. These may have independent timescales and mechanisms.

Negative-only selection, temporary inhibition, gradual weakening, positive stabilization, verified outcome feedback and three-factor eligibility learning are competitors. Blindly eliminating unlikely or surprising trajectories may suppress creativity; blind amplification can produce runaway activity. Unknown, contradicted, improbable, counterfactual and unobserved are not synonyms. Prevent self-confirming fantasy: repeated simulation does not create external evidence.

An external LLM can be a fallible *interpreter/semantic critic* of a bounded causal history, never a hidden author of the student's inner reasoning. A deterministic compact-world oracle supplies ground truth where possible. Validate delayed feedback attribution independently. The student must continue functioning without the critic.

## What 'continually evolving' does and does not require

Always-on computation is not synonymous with always-on firing. It may be useful to let time elapse analytically, consolidate offline, replay selected episodes, allocate work dynamically, or become quiescent. Compare physical/environment time, internal update count and extra compute. Checkpointing and an append-only experimental event ledger improve reproducibility; they do not prove memory or cognition. Recoverable process state must be distinguished from an external narrative context reinserted at each step.

## Our scientific invariants

1. Goal and mechanism stay separate; do not lock into temporal kernels, graphs, explicit concepts, symbolic rules, LLM retrofits or neuron-inspired designs before evidence.
2. No mandatory language tokens inside the operating thought process. Words and communication are optional ports.
3. No task prompt is necessary to *allow* internal evolution; unscripted processes may sometimes form meaningful, testable hypotheses, or remain quiet.
4. World truth, sensory observation, possible state, internal imagination, external validator interpretation and human-readable language must not be conflated.
5. Test **causal effects** of endogenous activity on later belief, action, learning or retention; a pretty trace, apparent association or fluent decoder story is not enough.
6. Preserve uncertainty and diverse alternatives; false, unknown and counterfactual have different meanings.
7. Compare mechanisms against principled baselines and honest resource budgets, including simple probabilistic/symbolic models where they solve the problem.
8. Prior art is a source of mechanisms and critical objections, not a novelty certificate. Negative and null results are first-class.
9. Favor compact discriminating worlds before increasing object count, model size or buying compute.
10. No claims about artificial subjective experience; 'illusion of consciousness' remains a philosophical framing, not experimentally established.
11. Human developmental analogies are inspiration, not medical or neuroscientific claims about a person.
12. Research docs may evolve; older experiment results and unmerged proposals remain intact and properly scoped.

## Minimal illustrative mathematical lens (not a design commitment)

Let latent internal state x(t), learned history/memory parameters m(t), changing modulation or significance g(t), and external observation o(t). A broad candidate transition family is:

- x(t+dt) = F[x(t), m(t), g(t), o(t), randomness; theta]
- m(t+dt) = U[m(t), x history, experience, evidence; theta]
- g(t+dt) = G[g(t), x history, expectation, learning progress; theta]

Internal alternative trajectories can be sampled or distributed, with both calibrated plausibility and distinct exploration-priority weighting. There is no assumption that x contains localized semantic nodes or that g represents literal human feelings. A conventional symbolic belief model may implement analogous functions and is a valuable comparator.

## Research map and historical scope

The [ATLAS](ATLAS.md) lists the open research questions, candidate mechanisms, controls and an evidence status ledger. The 2026-10-22 [historical atlas](archive/ATLAS-2026-10-22.md), existing [idea papers](ideas/), [research findings](research/findings/) and [experiment specifications](experiments/) remain available, without retroactively upgrading their claims. See [EXPERIMENTATION.md](EXPERIMENTATION.md) for preregistration and [AGENTS.md](AGENTS.md) for agent discipline.
