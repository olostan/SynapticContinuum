# EXP-0006 — From tiny world to open-ended real-world potential

**Purpose:** We are not making a miniature real world. We are identifying a transferable **mechanism** for persistent neural development. A toy experiment is scientifically meaningful only if it constrains what might happen when experience becomes larger, noisier, more compositional and lifelong. This document records prerequisites and failure modes; it does not claim extrapolation is validated.

## Four distinct generalization claims — never conflate
1. **Compositional transfer:** same model withholds combinations of already known relation rules and succeeds on disjoint test compositions; a simple memorized transition table should fail.
2. **Vocabulary/identity expansion:** a new opaque entity ID can be encoded through shared parameters without adding a fixed per-ID learned embedding. The number of active memory slots may grow; quantify bytes and lookup/update cost.
3. **Continual conceptual development:** an unfamiliar relation/rule can be acquired through observations and bounded teacher assistance, then retained without overwriting unrelated prior knowledge; later learns further rules faster than an equally prepared GRU/SSM baseline.
4. **Horizon/interaction growth:** longer silence, delayed feedback, more uncertain observations, and extended living history do not cause resource blowup or catastrophic prediction drift. Report how workload / memory grows, not just end score.

## Controlled extrapolation ladder
L0: 3–5 objects, 1-level containment, 8-tick gaps, unambiguous appearances, known deterministic rules; prove learnability and honest oracle.
L1: 5–8 objects, 2 nested containment levels, 32–128 tick gaps, 25% observation dropout; teacher-free holdout and intervention.
L2: 12–24 objects, depth 3, rare hidden events, 50% dropout and a new causal exception; **same learned parameterization** and same observation protocol; document actual new allocation needs.
L3 (not part of initial run): variable-length sensory streams from pretrained perception/semantic encoder, small changing environments; investigate representation mismatch, uncertainty and concept grounding.
L4 (outside experiment): genuinely open-ended lifelong world; no prediction that L0 success ensures L4.

At every ladder step evaluate cross-scale transfer **without resetting** training state and with a from-scratch control trained at that scale to distinguish transfer from general scalability. Record number of distinct observations and concepts, time since learning each, memory resident bytes per entity/relation, inference compute per encountered event, and forgetting of earliest knowledge.

## Hard limits / anti-shortcuts
- If trained on fixed object slots and tested with new object slots, architectural growth claim FAILS.
- If adding a relation requires editing source code or mapping an explicit node for every new fact, spontaneous representation growth claim FAILS.
- If all facts are reconstructed from a serialized text database at every step, endogenous-state hypothesis is untested; explicit symbolic memory is a respectable baseline instead.
- If teacher continually participates in held-out probes or supplies hidden target labels, autonomous student capability claim FAILS.
- If fixed-size recurrent state loses old knowledge as rules grow, report capacity/forgetting limits. An expandable explicit episodic cache may be necessary and does not automatically invalidate neural learning, but its complexity/memory must be tracked and compared fairly.
- Simulator rules may be exact, but new real-world inputs are noisy and ambiguous; transfer demands calibration and causal grounding, not just matching symbol vectors.
- Constant spontaneous activity is not required. Efficient silence/memory consolidation may be an advantage if it preserves useful representations and predicts when updates matter.

## Future interface to large pretrained models
Potential staged bridge: pretrained image/text/audio encoder supplies partial *observations* or initial semantic embeddings; small persistent student maintains and continually updates h/m/W; occasional local or cloud teacher produces validated feedback or curriculum; optional behavior actuator reads student predictions. Never assume static LLM weights or latent vectors transfer meaning automatically across architectures. A separate alignment/probe experiment must verify encoding, stable entity binding, distribution shift and knowledge preservation. No natural-language token decoding inside the core is required.

## Scientific investment decisions
- Stop after L1 if strong GRU/explicit-memory controls match all effects of endogenous dynamics.
- Study online plasticity/slow memory if useful autonomous dynamics exist but oldest facts are lost on L2.
- Explore EXP-0003/4/5 scheduling/fast kernels only if actual observed adaptation dynamics hit capacity/runtime limits.
- Introduce pretrained feature encoders only if student shows robust unknown-ID and heldout composition transfer; otherwise high-dimensional input conceals the central mechanism.
- No new GPU/hardware assumption or purchase on the basis of neural-state animations.
