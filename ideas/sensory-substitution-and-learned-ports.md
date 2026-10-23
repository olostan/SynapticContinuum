# Sensory Substitution, Embodiment, and Learned Port Semantics

**Status:** research analogy and experiment proposal (2026-10-23), not evidence of artificial consciousness.

## Motivation

In sensory substitution, humans can learn to use an unfamiliar physical input channel to extract information about the environment. An electrotactile array on the tongue can carry camera-derived image structure; with training, blind participants improve on object/localization and rudimentary visual-information tasks. This does **not** restore ordinary sight or imply arbitrary inputs will become meaningful automatically.

For SynapticContinuum the architectural idea is **ports need not carry fixed human-assigned semantic labels internally**. A continuously operating dynamical substrate might learn sensorimotor contingencies through recurrence, plasticity, correlated observations, and action consequences. External channels can be added gradually while ongoing state and learned structure persist.

## Primary research

- Bach-y-Rita et al., *A Tactile Vision Substitution System* (1969), original historical prototype on the back: https://doi.org/10.1002/j.2330-9474.1969.tb03696.x
- Sampaio, Maris & Bach-y-Rita, *Brain plasticity: 'visual' acuity of blind persons via the tongue* (2001): https://doi.org/10.1016/S0006-8993(01)02667-1
- Nau et al., *Clinical Tests of Ultra-Low Vision Used to Evaluate Rudimentary Visual Perceptions Enabled by the BrainPort Vision Device* (2013): https://pmc.ncbi.nlm.nih.gov/articles/PMC3763892/
- *Successful tactile based visual sensory substitution use functions independently of visual pathway integrity* (2014): https://pmc.ncbi.nlm.nih.gov/articles/PMC4026734/
- Kaspar et al., *The experience of new sensorimotor contingencies by sensory augmentation* (2014), feelSpace belt: https://pubmed.ncbi.nlm.nih.gov/25038534/
- *Learning New Sensorimotor Contingencies: Effects of Long-Term Use of Sensory Augmentation on the Brain and Conscious Perception* (2017): https://pubmed.ncbi.nlm.nih.gov/27959914/

These are analogies and findings about **human biological neuroplasticity**, not a demonstration that a Transformer-derived artificial system will exhibit the same adaptation.

## Research proposal — learned interfaces rather than hardwired meanings

1. Run a small persistent neural substrate with input channels whose event statistics are initially unfamiliar.
2. Present one environment variable through an arbitrary encoding, including intentionally scrambled channel mappings.
3. Allow the system to explore and predict consequences over time. Introduce a simple action port with feedback from the environment; do **not** require correct verbal labeling.
4. Change sensor modality or remap channels while preserving state, and compare adaptation with fresh-state and fresh-weight controls.
5. Evaluate whether representations transfer across channels and support new prediction/action tasks after remapping.
6. Later experiment with a language output port as one more learnable action interface, rather than the core computation clock.

## Discriminating controls

- Fixed feed-forward decoder / supervised mapping.
- Standard recurrent learner with and without continuous idle updates.
- Identical topology but shuffled event-to-environment relationship.
- Frozen plasticity and cleared state at modality switch.
- Input-only learning versus closed-loop action + sensory consequence.

Measure adaptation after port remapping, memory continuity, counterfactual action sensitivity, information transfer and grounded behavioral change. High activation or qualitative descriptions of “seeing” alone cannot establish a new perceptual experience.

## Open questions

- Can a pretrained LM's representations help bootstrap interpretation of arbitrary ports without dictating their semantics?
- Does temporally extended self-observation help integrate new channels beyond ordinary online recurrent learning?
- Is meaningful adaptation primarily driven by temporal correlation or by closed-loop sensorimotor consequences?
- Can spontaneous communication emerge as a learned action channel, with the system retaining autonomy during silence?

**Key distinction:** structural openness to adding ports is a design goal; empirical ability to integrate them is an unsolved learning problem.
