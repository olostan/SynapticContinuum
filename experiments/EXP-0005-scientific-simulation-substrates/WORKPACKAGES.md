# EXP-0005 bounded implementation campaign

**No execution authorized by this design PR.** Approval gate G0 in SPEC.md applies. Work packages are independent adapter PRs, not one monolithic 'install all and benchmark' campaign. Each asks the laborant to submit an implementation PLAN and unresolved assumptions first; Principal Researcher reviews architecture before expensive work.

| Order | Work package | Purpose | Input dependency | Recommended review boundary |
| --- | --- | --- | --- | --- |
| 0 | [WP-00](work-packages/WP-00-contracts-oracle.md) | Fixture byte identity, independent oracle, schema v2, pilot harness | EXP-0004 read-only | independent contract/oracle PR |
| 1 | [WP-01](work-packages/WP-01-nest.md) | NEST native hybrid spike/clock baseline | WP-00 accepted | NEST-native PR |
| 2 | [WP-02](work-packages/WP-02-brian2.md) | Brian2 runtime vs generated standalone C++ | WP-00 accepted | Brian2-native PR |
| 3 | [WP-03](work-packages/WP-03-arbor.md) | Arbor LIF and then its native cable cell | WP-00; preferably aligned NEST/Brian semantics | Arbor-native PR |
| 4 | [WP-04](work-packages/WP-04-ross.md) | Genuinely optimistic ROSS with rollback/GVT proof | WP-00 + independent causality design gate | ROSS prototype PR before any optimization |
| 5 | [WP-05](work-packages/WP-05-synthesis.md) | Adversarial validation, atlas extension, future architecture | at least 2 independently audited adapters | synthesis PR |

**Ordering:** WP-01 and WP-02 can be implemented on separate branches after WP-00 and may be parallel ONLY if laborant coordination avoids shared files. WP-03 then WP-04 sequential on resource-constrained Linux; WP-05 starts after two valid adapters, may continue after later reports. One framework per agent/PR. Each work package owns only its adapter subtree, package-specific tests/configs and compact runs; all shared oracle/schema changes belong to WP-00 or separately reviewed additive revision.

**Checkpoints each WP:** (1) short written assumptions/requirements digest, (2) minimal native working spike example committed, (3) reference tests and trace parity or tolerance committed, (4) review of actual native code/algorithm and attribution, (5) small measured cells, (6) explicit scale permission, (7) independent review and GO / CHANGES REQUESTED / NO-GO. Each stage uses separate commit(s), not an opaque final report. No broad autonomy to silently substitute approximations.

**Campaign stop:** Failing a framework installation, semantic parity or reversibility is a useful outcome. Record failure and re-scope; do not skip to another framework or commit fake data. Keep one small Linux runtime safe (<60% available RAM, max incremental RSS 6GiB, <=5 min pilot); owner explicitly authorizes longer >5-min cells and any hour-long test. Other processes must be accounted for.

See [PROMPT.md](PROMPT.md) for orchestrator handoff, [LINUX-LABORANT-PROMPT.md](LINUX-LABORANT-PROMPT.md) for copy-paste execution handoff, and [RESEARCH-AGENTS-PROMPTS.md](RESEARCH-AGENTS-PROMPTS.md) for independent specialists.
