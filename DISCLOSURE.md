# Pre-existing work disclosure

This project is an entry to Google's **All Things Agentic** hackathon
(submission window 3–31 August 2026).

## What is new

All source in this repository was written on or after 27 August 2026 on
the mandatory stack:

- Gemini 3.5+ via Vertex AI
- Google Agent Development Kit (ADK) via `agents-cli`
- Google Cloud Run, Firestore, Pub/Sub, Cloud Trace

Scaffolding produced by `agents-cli scaffold create` (Apache-2.0,
Google LLC) is included and attributed in file headers.

## What is not copied

An earlier public prototype, [vn-envy/Leadsy](https://github.com/vn-envy/Leadsy),
explored the same *product idea* on a different stack (OpenAI, Cloudflare
Workers, Convex). **No application code, prompts, schemas, or assets were
copied from that repository.** Brand art will be regenerated with Gemini
image generation. The brand name "Leadsy" and the flock personas are
retained as concept lineage, which the rules allow.

## Open source used (licenses honored)

| Dependency | License | How |
|---|---|---|
| Google ADK + agents-cli templates | Apache-2.0 | scaffold |
| CopilotKit / AG-UI (Mission Control) | MIT | frontend path |
| Stagehand (later) | MIT | Scout browser evidence |
| emilkowalski/skills (later) | MIT | build-time UI taste |
| last30days-skill (later) | MIT | Scout crowd lens, zero-key mode |
| Remotion (later) | Remotion (free ≤3-person co.) | Ad Kit + film |

AGPL repositories were studied for *ideas only* (`signal`, `OpenMontage`).
No AGPL code or skill files are present in this repo.
