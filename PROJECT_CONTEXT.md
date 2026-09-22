# Scryx — Project Context

> Persistent development context and source of truth for long-running work on Scryx.
> Read this file before proposing features, changing direction, or starting a new development session.

## Project purpose

Scryx is a focused web reconnaissance CLI for authorized security work.

Its purpose is to take a starting URL and make the researcher's initial web-mapping workflow faster, clearer, safer, and less manual. Scryx should combine the most useful early reconnaissance steps into one understandable workflow rather than forcing the researcher to manually collect, classify, check, and organize URLs.

The product advantage is **workflow efficiency and clarity**, not trying to outperform every specialist security tool at its own specialty.

## Product boundaries

Scryx should remain a focused Web Recon tool.

It is **not** intended to become:
- a vulnerability exploitation framework;
- a brute-force tool;
- a fuzzing platform;
- a port scanner;
- a subdomain-enumeration replacement;
- a CVE/Nuclei-style vulnerability scanner;
- a collection of many unrelated third-party tools.

A new feature belongs in Scryx only when it clearly reduces useful manual reconnaissance work while preserving bounded, understandable behavior.

## Current stable baseline

Current stable release: **v1.1.2**

The v1.1.x baseline includes:
- installable Python CLI;
- quick, recon, and deep presets;
- bounded same-host crawling;
- scope controls;
- URL analysis and classification;
- parameterized/dynamic URL identification;
- HTTP checks;
- redirect and scope handling;
- Recon Map;
- Recon Intelligence;
- structured report output;
- restrained semantic terminal colors;
- documented CLI help and User Guide.

v1.1.2 is the stable baseline. Do not change existing reconnaissance behavior casually.

## Design principles

1. **Researcher time first** — prefer features that remove repetitive manual work.
2. **Focused over bloated** — do not add a feature merely because another security tool has it.
3. **Observed facts over aggressive guessing** — map what the application exposes before adding active testing.
4. **Readable output** — important findings should be easy to identify without visual noise.
5. **Bounded behavior** — scope, crawl depth, request limits, and redirects must remain explicit and predictable.
6. **Authorized use** — design and documentation assume systems owned by the user or explicitly authorized for testing.
7. **Validate before expanding** — real usage should reveal the next problem before a feature is promoted into the roadmap.

## Competitive position

Scryx exists alongside specialist tools rather than trying to replace all of them.

Examples of adjacent categories:
- crawlers and endpoint discovery tools;
- HTTP probing tools;
- subdomain discovery tools;
- vulnerability-template scanners;
- passive URL collectors;
- recon orchestration frameworks.

Before implementing a major feature, compare the proposed workflow with mature tools in the relevant category. The question is not "Can Scryx also do this?" but "Does adding this make the Scryx reconnaissance workflow materially simpler or more useful?"

## Roadmap

### v1.1.2 — Stable baseline

Status: **completed and validated**

Release, installation, version output, CLI help, documentation, Recon Intelligence, Recon Map, HTTP checks, reports, and terminal color hierarchy have been validated.

### v1.2 — Recon Workflow Efficiency

Status: **research before implementation**

Goal: reduce additional manual work during initial application-surface mapping without changing Scryx into a vulnerability scanner.

Primary research candidate:
- **Forms / Input Mapping** — identify observed forms, methods, actions, and input names and organize them for the researcher.

This is a candidate, not automatic approval to implement. Compare it with existing tools and validate that it saves meaningful work first.

### v1.3 — JavaScript Endpoint Discovery

Status: **future research candidate**

Investigate whether lightweight static JavaScript endpoint discovery adds meaningful value to the Scryx workflow.

Do not implement merely to duplicate mature endpoint-extraction/crawling tools. Research the gap first.

## Separate-project candidate

A future reconnaissance orchestration tool may be considered as a **separate project**, not as uncontrolled expansion of Scryx.

Possible purpose: accept a domain/target and coordinate selected existing reconnaissance tools into a simpler workflow. Before building it, study existing orchestration projects and identify a concrete usability gap.

## Change-control rule

Before adding a major Scryx feature:

1. State the researcher problem it solves.
2. Compare how existing tools solve the same problem.
3. Explain what manual work Scryx would remove.
4. Confirm that the feature fits the project purpose and boundaries above.
5. Only then design or implement it.

Ideas that fail this test stay outside Scryx.

## Continuity protocol

This file is the persistent project memory.

At the beginning of a new Scryx chat/session:
1. Read this file.
2. Check the current repository state and CHANGELOG.
3. Treat the latest verified repository state as authoritative.
4. Continue from the current roadmap rather than reconstructing the project from chat memory.

After a meaningful milestone or decision:
- update this file;
- replace stale current-state information instead of accumulating chat transcripts;
- use Git history/CHANGELOG for historical detail.

Do **not** store passwords, tokens, API keys, account credentials, or other secrets here.

## Current next step

Do not add another feature immediately after v1.1.2.

The next development task is to research **Forms / Input Mapping** against existing reconnaissance tools and decide whether it provides enough workflow value to become the v1.2 implementation target.
