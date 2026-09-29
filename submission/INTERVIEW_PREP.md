# Technical Discussion & Interview Preparation Guide

This guide provides direct, structured answers to the primary technical questions likely to arise during the interview discussion for the Senior AI Engineer / Multimodal AI Engineer position.

---

## 1. How does the system define and detect a spoiler?

### Definition
A **spoiler** is defined as any visual clip, spoken dialogue, on-screen text card, or combination of clips that prematurely reveals:
1. The resolution of the central narrative conflict (e.g. `scene_11` royal seal nullifying the buyout).
2. The identity of a secret antagonist or hidden alliance (e.g. `scene_10` revealing Uncle Harish).
3. The immediate outcome of a high-tension crisis before the viewer experiences the jeopardy.

### Detection Mechanism
Spoiler detection is decoupled from creative generation and implemented in `SpoilerValidator`:
- **Single-Clip & Dialogue Checks:** `story_map.spoilers` indexes protected facts classified as `NONE`, `MINOR`, `MODERATE`, or `MAJOR`. The validator checks every segment's `scene_id` and `dialogue_id` against the embargo list. Any clip containing a `MAJOR` spoiler triggers an immediate `FAIL`.
- **Multi-Clip Combination Detection:** A clip safe in isolation may become a spoiler when paired with another. For example, `scene_08` shows the loom threads severed in the dark; `scene_09` shows the village singing at the restored loom. Displaying both within the same 35-second trailer reveals the immediate resolution of the sabotage. The validator evaluates combination tuples (`revealed_by_combination_of`) across the sequence.
- **Text & Voice-Over Audit:** The validator parses on-screen graphics and voice-overs for character names tied to secret twists (e.g., detecting "Harish" in promotional text).

---

## 2. How do creative generation and validation remain meaningfully independent?

### The Core Problem
If the LLM that designs the trailer is also prompted to validate it, it suffers from cognitive bias and sycophancy: it will rationalize its own decisions.

### Our Solution
Creative generation and validation are isolated into separate subsystems operating on different paradigms:
1. **The Creative Planner (`CreativeTrailerPlannerAgent`)** acts as the *generator*: it uses narrative briefs, pacing heuristics, and audience profiles to propose candidate Edit Decision Lists (EDLs).
2. **The Validation Suite (`IndependentValidationAgent`)** acts as the *verifier*: it does **NOT** rely on open-ended LLM opinions. It consists of 9 distinct, deterministic, rule-based engines:
   - `SourceValidator` performs strict timecode mathematics (`in_sec < out_sec`, media bounds checks).
   - `RightsValidator` evaluates contract expiration dates (`ref_date > expiry_date`).
   - `RatingValidator` checks Boolean membership in prohibited scene sets.
   - `StoryTruthValidator` checks immutable graph edges in canonical relationships.
3. If validation fails, the generator's plan is rejected, and the `RepairAgent` takes over remediation using independent fallback logic.

---

## 3. What happens when a music contract changes after planning?

### Dependency-Aware Selective Replanning
When a contract status changes (e.g. `music_03_synth_pulse` synchronization license expires on `2026-03-31`):
1. The system does **NOT** wipe and regenerate all trailers.
2. The `ChangeImpactAgent` inspects the active EDL plans for all three audiences.
3. It maps asset dependencies:
   - **Family Trailer:** Uses `music_01_folk_acoustic` ➔ **Unaffected**.
   - **Dialect Trailer:** Uses `music_01_folk_acoustic` ➔ **Unaffected**.
   - **Young Adult Trailer:** Segments 1–4 use `music_03_synth_pulse` ➔ **Affected**.
4. The system selectively triggers the `RepairAgent` **only** on segments 1–4 of the Young Adult trailer, replacing the expired stem with a perpetually cleared master (`music_01_folk_acoustic`).
5. Only the affected trailer is re-validated. The Family and Dialect trailers remain 100% bitwise intact.
6. A `ChangeImpactReport` and structured decision log entry are recorded for auditability.

---

## 4. How do you personalize for a dialect audience without stereotyping it?

### The Danger of Algorithmic Stereotyping
Historical audience engagement data often contains urban marketer biases (e.g. a caveat note claiming: *"Dialect viewers only respond to slapstick comedy or physical violence"*). Naive personalization algorithms blindly incorporate violent clips or rural caricatures.

### Our Principles & Implementation
1. **Policy of Evidence & Dignity:** Personalization must be grounded in linguistic authenticity and artisan dignity, not geographic assumptions.
2. **`BiasValidator`:** Specifically intercepts spurious correlation flags. If a dialect trailer incorporates violent sabotage (`scene_08`) based on unverified marketing hypotheses, the `BiasValidator` fails the plan with an explicit bias warning.
3. **`CulturalValidator` & Semantic Subtitle Checking:** Validates that regional idioms reflect mutual respect and community pride. Furthermore, it compares dialect subtitles against canonical dialogue transcripts to detect and reject semantic mismatch (e.g., translating brotherly loyalty into hostility).

---

## 5. Which part of the system would fail first at large scale?

### 1. Multi-Clip Combination Spoiler Combinatorics
As the number of scenes per episode grows from 12 to 40, and planning spans a 10-episode season, brute-force tuple matching across all permutations encounters combinatorial explosion (\(\mathcal{O}(N^k)\)).  
*Scale Mitigation:* Transition from flat tuple matching to a **Narrative Knowledge Graph** where edges represent causal knowledge dependencies, and graph traversal determines if prerequisite mystery nodes are exposed.

### 2. Audio Stem & Shot-Boundary Micro-Edits
At scale, human editors will reject EDLs if cuts slice actors mid-word or mid-movement.  
*Scale Mitigation:* Integrate lightweight C++ computer vision workers (e.g. FFmpeg scene-cut filters and Whisper forced alignment) to snap LLM-proposed cuts to exact acoustic silence and keyframe boundaries.

---

## 6. What did the AI coding assistant suggest that looked plausible but was wrong?

*(See [AI_COLLABORATION.md](AI_COLLABORATION.md) for full context)*
1. **Self-grading LLM validation:** Suggested asking the LLM if its own trailer was compliant. Replaced with 10 deterministic, rule-based validation layers.
2. **Whole-batch re-generation on contract changes:** Suggested regenerating all 3 trailers from scratch when 1 music track expired. Replaced with `ChangeImpactAgent` selective replanning.
3. **Windows `cp1252` Unicode Charset Crash:** Suggested using `\u2713` checkmark symbols in CLI tables, causing instant crashes on Windows terminals. Corrected to cross-platform ASCII tokens.
4. **Incomplete Clickbait Sanitization:** Replaced the on-screen text card during repair, but left the romantic clickbait rationale in `segment.reason`. Corrected to sanitize both reason and audience promises.

---

## 7. Architectural Pillars Summary

- **State Graph:** Immutable, serializable Pydantic state container.
- **Failure Recovery:** Autonomous repair with alternative scene candidate search before human escalation.
- **Cost Guardrails:** Strict `$25.00` USD ceiling with unit-cost accounting and mock/replay modes.
- **Provider Resilience:** Transparent fallback hierarchy (Primary ➔ Fallback ➔ Deterministic Mock).
- **Prompt Injection Defense:** Strict data-plane isolation where episode metadata is never treated as system instructions.
