# Temporal Connection Memory

**Hypothesis** · not yet validated in SynapticContinuum · related [Foundations](../FOUNDATIONS.md)

The proposed primitive is a **temporally expressive connection**. Neuron/region i's incoming signal can depend on j's past *trajectory*, not just j's current activation. This is closer to the user's "previous set of weights" intuition than simply recurrently applying a Transformer layer.

## The naive form

In discrete steps, \`u_i(t) = Σ_j Σ_(k=0..K-1) W[i,j,k] a_j(t-k)\`, followed by a nonlinear recurrent-state update. Equivalently in continuous time, \`u_i(t) = Σ_j ∫ K_ij(τ) a_j(t-τ) dτ\`.

Two distinct mechanisms:
- **Temporal response:** \`W[i,j,k]\` is a learned delay-response kernel, stable during a rollout; past activation changes present influence.
- **Plastic connection:** \`W[i,j,k,t] = W_stable[i,j,k] + P[i,j,k,t]\`; the kernel itself changes through ongoing learning. Do not conflate the two.

This is related to temporal convolution, delay systems, recurrent networks, spiking synaptic filters and state-space models; originality must be sought in the *combined continuous-state/communication/plasticity architecture and empirical performance*, not in the kernel equation alone.

## Scaling

A dense N-node, K-delay kernel costs **O(N²K) parameters**, not exponential growth. Maintaining past activities naively costs O(NK) state; applying dense kernels costs O(N²K) per update. With N=1,000 and K=64 there are 64 million kernel weights before gradients or optimizer states.

Potential reductions, to test rather than presume:
- Sparse E edges: O(EK) kernel weights.
- Shared B exponentially decaying traces per *source*: \`z[j,b](t+1)=λ_b z[j,b](t)+(1-λ_b)a_j(t)\`. Then \`u_i(t)=Σ_j Σ_b C[i,j,b] z[j,b](t)\`; O(NB) trace state and O(EB) sparse coupling.
- Low-rank kernel factors across source/target/time; train on a low-dimensional temporal basis rather than arbitrary K weights.
- A few delays plus optional connection-local state, instead of a dense set of lag taps.
- Event-driven evaluation only for sufficiently changed traces, subject to GPU batching overhead.

**Important:** shared source traces are not the same expressive family as arbitrary connection-local temporal kernels. State the tradeoff; compare capacity fairly.

## Competing designs

A. Instantaneous sparse recurrent connections (control).

B. Fixed temporal kernels, no plasticity.

C. Learned temporal kernels, no plasticity.

D. Shared multiscale traces plus learned couplings.

E. Per-connection local state or fast weights.

F. Any of B–E with reward-modulated, bounded plasticity.

Measure utility separately from state persistence: predictive accuracy vs timed inputs, recovery from pauses/interruptions, long-idle state health, parameter budget, FLOPs and actual runtime.

## Stability

Unbounded positive feedback can amplify tiny disturbances or collapse into repeating patterns. Candidate controls include leaky updates, spectral/gain constraints, normalization, homeostatic activity regulation and plasticity caps. None guarantees semantic correctness.

A useful neural circuit can converge, oscillate or sustain transients. Don't optimize to maximize entropy or chaos. Test robustness to perturbations *and* performance on the actual task.

## Key experiment

[E005](../experiments/E005-temporal-memory-ablation.md) separates timing information from extra time for computation, and compares kernels against simple recurrent memory, equal-parameter trace models and shuffled timestamps.

## Literature entry points

- [S4: Efficiently Modeling Long Sequences with Structured State Spaces](https://arxiv.org/abs/2111.00396)
- [Mamba: Linear-Time Sequence Modeling with Selective State Spaces](https://arxiv.org/abs/2312.00752)
- [Neural Controlled Differential Equations](https://arxiv.org/abs/2005.08926)
- [Continuous Thought Machines](https://arxiv.org/abs/2505.05522)
- [Differentiable Plasticity](https://proceedings.mlr.press/v80/miconi18a.html)

These are architectural precedents, not proof of our claim.
