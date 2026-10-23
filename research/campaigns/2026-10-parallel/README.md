# Parallel research campaign — 2026-10

**Repository:** https://github.com/olostan/SynapticContinuum

This map gives ten independent ChatGPT conversations a shared understanding of the other investigations while preserving freedom to disagree. Open **one PR per track**, don't merge or require early consensus. The full instructions live in [COMMON.md](COMMON.md). Copy-paste launchers are in [LAUNCHERS.md](LAUNCHERS.md).

## Track and file ownership

| Track | Topic | Exclusive output folder | Adjacent tracks |
|---|---|---|---|
| [R01](R01-PROMPT.md) | Literature, prior art and citation audit | research/findings/R01-literature-novelty/ | R02 R03 R07 R08 |
| [R02](R02-PROMPT.md) | Temporal kernels and synaptic memory | research/findings/R02-temporal-connections/ | R10 R03 R09 R08 |
| [R03](R03-PROMPT.md) | Communication as live neural activity | research/findings/R03-streaming-communication/ | R02 R04 R05 R09 |
| [R04](R04-PROMPT.md) | Online plasticity and grounded reinforcement | research/findings/R04-online-plasticity/ | R03 R05 R06 R10 |
| [R05](R05-PROMPT.md) | Frozen LLM as validator, not teacher | research/findings/R05-llm-guardrails/ | R03 R04 R06 R08 |
| [R06](R06-PROMPT.md) | Evolution, LoRA and durable consolidation | research/findings/R06-evolution-consolidation/ | R04 R05 R07 R10 |
| [R07](R07-PROMPT.md) | Retrofitting pretrained LLMs | research/findings/R07-pretrained-retrofit/ | R01 R02 R06 R09 |
| [R08](R08-PROMPT.md) | Skeptical review and falsification | research/findings/R08-skeptical-falsification/ | R01 R02 R05 R09 |
| [R09](R09-PROMPT.md) | Controlled greeting prototype experiments | research/findings/R09-greeting-prototype/ | R02 R03 R04 R08 |
| [R10](R10-PROMPT.md) | Dynamical systems, stability and asynchronous updates | research/findings/R10-dynamics-stability/ | R02 R04 R08 R09 |

The current repository foundations, research atlas, landscape, existing idea papers and experiment proposals remain read-only for individual track agents. Each agent may discover peer PRs during its work but should **not** wait for them. Missing peer results are unknown, not an invitation to invent citations.

## Run sequence

1. Launch all ten threads with the individual text from [LAUNCHERS.md](LAUNCHERS.md) (or your own short message pointing to the track's prompt).
2. Each thread reads this campaign map and [COMMON.md](COMMON.md), does external research, writes only its assigned files and opens a review PR to main.
3. Examine cross-track disagreement rather than forcing consensus. Strong negative results are valuable contributions.
4. Only after some PRs are open, run [SYNTHESIS-PROMPT.md](SYNTHESIS-PROMPT.md) in a separate thread.

## Guiding idea

A sequence of sensory events, an internal trajectory of activations, and outgoing communicative acts may be different interfaces on the same persistent dynamical substrate, with time-sensitive connections and multi-timescale learning. All advantages remain unverified and must be measured against ordinary recurrent/state-space approaches.
