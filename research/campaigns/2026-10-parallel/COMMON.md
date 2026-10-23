# Shared protocol: independent SynapticContinuum research

**This is a research campaign, not a predefined architecture or a software delivery sprint.** The instructions apply to all R01–R10 threads.

## Founding research question

Can input observations, internal activation, emitted communication and feedback be events in one persistently evolving neural substrate, with temporally expressive connections, optional fast plasticity, slower learned adapters, and occasional evolutionary selection, without making next-token generation the fundamental computation clock?

This is a hypothesis, not proof of originality, intelligence, consciousness, or advantage over simpler models.

## Required reading

Before research, open the public repository https://github.com/olostan/SynapticContinuum and read from the latest main:
- README.md; FOUNDATIONS.md; ATLAS.md
- RESEARCH_LANDSCAPE.md; SOURCES.md; AGENTS.md
- This campaign's README.md, all track summaries, and your assigned Rxx-PROMPT.md
- The topic-specific files and original papers linked in your own prompt

Treat older references as leads requiring source verification rather than established facts. Read other assignments to understand overlapping questions without presuming the answers those researchers will produce.

## Parallelism without edit conflicts

Each research conversation owns one unique folder:
**research/findings/Rxx-slug/** and, optionally, **prototypes/research-rxx-slug/**.

Write only in your owned folder(s). Existing core files including README.md, FOUNDATIONS.md, ATLAS.md, SOURCES.md, RESEARCH_LANDSCAPE.md, AGENTS.md, experiments/ and ideas/ are read-only for this campaign. Discuss proposed modifications in your report rather than editing shared files.

Create a fresh branch from the current main named research/rxx-slug and an independent PR titled [Rxx] Specific topic, targeting main. Keep the PR open for review. Never force-push, modify another researcher's branch, merge your PR, or directly push your research to main.

To learn about peer work, read the track index and, when useful, inspect **actually open** peer PRs at https://github.com/olostan/SynapticContinuum/pulls . Reference real PR URLs only if they exist. Peer drafts are provisional. You may comment with precise scientific objections, but no cross-thread collaboration is required and no track should wait for another one.

## Scientific standards

- Browse primary papers, original code, official documentation, reproduced results, credible counterevidence and historic precedents. Check author, title, date/version, DOI/arXiv ID and what the results actually show. Do not copy full copyrighted papers.
- Distinguish **Observed locally**, **Published/reported**, **Hypothesized**, **Speculative**, and **Contradicted**. A paper citation does not equal local reproduction.
- Give at least two alternative mechanisms, a simpler strong baseline, and a plausible failure case. Include explicit state/tensor equations or executable pseudocode when appropriate.
- Explain what would falsify the claimed benefit. Carefully control training set, external information access, number of steps, timestamps, FLOPs, latency, trainable parameters, memory, and multiple seeds where relevant.
- Neural state evolution during silence is possible but not automatically beneficial. Complex or chaotic activation is not itself useful reasoning. An internal outgoing-action trace is not proof of external successful delivery.
- Frozen conventional LLMs may help validate suspected semantic regression, but are fallible critics, not teachers whose outputs define correctness.
- Do not invent citations, executed tests, training results, source links or git actions. If code is not run, label it untested. Preserve negative findings.
- The project is public: no credentials, sensitive employer information, unlicensed weights, private data or confidential documents.

## Minimum contribution

In your own folder create REPORT.md containing: research question; closest prior work; precise proposals; technical assumptions; competing explanations; skeptical critique; a decisive experimental protocol with controls; possible next directions; links to primary literature; references to adjacent campaign tracks; what this changes or does not change in the founding vision. Additional source tables and sample code are optional.

If tools allow, actually commit the files and open a distinct PR. The PR body must summarize findings, uncertainties, files, validation performed and 2–4 review questions. Return the real PR URL plus your strongest finding, strongest objection, and next falsification test.

If GitHub write actions are unavailable, produce the full research deliverable and clearly state that no PR was opened. Do not substitute a fabricated URL or claim to have published.

## Synthesis comes later

After useful PRs exist, a separate synthesis agent reviews them together, records contradictions and suggests limited updates to the core documents in its **own PR**. No track agent is authorized to rewrite a shared vision merely because one experiment or source seems persuasive.
