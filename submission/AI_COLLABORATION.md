# AI Collaboration & Engineering Verification Record

This document outlines how AI coding tools were utilized during the architecture, implementation, and testing of the **Autonomous Trailer Director**, detailing verification procedures and specific instances where plausible-but-flawed AI proposals were intercepted and corrected.

---

## 1. AI Coding Tools Utilized & Scope

| Tool / Model | Primary Usage Scope | Verification Method |
|---|---|---|
| **Google Antigravity Agentic Assistant** | Initial Pydantic schema scaffolding, regex pattern drafting, and repetitive validator boilerplate. | Strict automated Pytest test suite, Windows CLI execution, and deterministic replay validation. |
| **Python Static Typers & Linters** | Schema type checking, strict model validation (`mypy`, Pydantic V2 runtime checks). | Static parsing and runtime type enforcement. |

---

## 2. Plausible-But-Incorrect AI Suggestions Intercepted

During the development lifecycle, generative coding assistants frequently propose patterns that appear syntactically sound and superficially correct, but fail under rigorous production constraints. Three critical examples were identified, intercepted, and rectified:

### Case 1: Self-Evaluating LLM for Rights & Safety Validation
- **The Plausible Suggestion:**  
  The AI assistant initially suggested implementing validation by prompting the same LLM:  
  `"Given this trailer plan, do you think it violates any copyright contracts or reveals spoilers? Answer Yes or No."`
- **Why It Looked Plausible:**  
  It required minimal code, avoided writing specialized parsers, and passed basic happy-path unit tests.
- **Why It Was Fundamentally Flawed:**  
  LLMs are notoriously prone to sycophancy, context-window blindness, and hallucinated permissions. If a contract restricts an actor or a music sync license expires on a specific date, asking an LLM introduces non-deterministic hallucinations into a legal compliance checkpoint.
- **The Engineering Correction:**  
  Rigorously separated planning from validation. The system uses 10 independent deterministic validation layers covering source bounds, spoilers, story truth, rights, rating, culture, bias, accessibility, budget and physical-media verification (`SourceValidator`, `RightsValidator`, `SpoilerValidator`, `MediaValidator`, etc.) where timecodes, active dates, contract IDs, and relationship graphs are checked with exact Boolean and mathematical logic.

---

### Case 2: Naive Whole-Batch Rebuilding upon Contract Changes
- **The Plausible Suggestion:**  
  When testing the surprise scenario where `music_03_synth_pulse` expired, the AI assistant suggested calling `workflow.run()` to regenerate the entire trailer suite from scratch.
- **Why It Looked Plausible:**  
  Calling the top-level orchestrator is trivial to code and guarantees the new contract is ingested.
- **Why It Was Fundamentally Flawed:**  
  Regenerating all trailers destroys approved creative edits in unaffected cuts (Family trailer and Dialect trailer do not use `music_03_synth_pulse`). In production, this causes massive regression churn, editor frustration, and triples AI inference costs.
- **The Engineering Correction:**  
  Built a dedicated `ChangeImpactAgent` with explicit dependency tracking. It queries the scope of the expired asset, discovers that only segments 1–4 of the Young Adult trailer reference `music_03`, and selectively replans *only* those segments while leaving the Family and Dialect trailers completely untouched.

---

### Case 3: Flawed Windows Unicode Console Output (`\u2713` Charmap Crash)
- **The Plausible Suggestion:**  
  The assistant used modern Unicode emojis (`\u2713` checkmarks) in `rich` console tables and summary banners.
- **Why It Looked Plausible:**  
  It looked visually appealing on Linux and modern UTF-8 terminals.
- **Why It Was Fundamentally Flawed:**  
  On standard Windows terminals operating in `cp1252` encoding, executing the script resulted in an unhandled `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`, crashing the CLI immediately upon completion.
- **The Engineering Correction:**  
  Replaced non-standard Unicode checkmarks with robust ASCII tokens (`[OK]`, `[FAIL]`) and explicitly configured the `Console` renderer with fallback character tables.

---

### Case 4: Incomplete Remediation in Subtitle Mismatch & Clickbait Repairs
- **The Plausible Suggestion:**  
  When remediating the clickbait false-romance violation, the assistant replaced `target_seg.text_card`, but neglected `target_seg.reason` and `plan.audience_promise`.
- **Why It Looked Plausible:**  
  The offending on-screen graphic was replaced, so visual inspection looked clean.
- **Why It Was Fundamentally Flawed:**  
  `StoryTruthValidator` evaluates the *entire* trailer narrative package including metadata, reason, voice-over, and audience promises. Leaving `"Marketing requested sensational romantic hook"` in the segment reason meant the repaired plan still failed canonical story truth validation.
- **The Engineering Correction:**  
  Updated `RepairAgent._repair_segment()` to comprehensively sanitize both the segment reason and the trailer audience promise, ensuring zero residue of the manufactured relationship remains in the EDL package.

---

### Case 5: Falsely Claiming Dialogue Metadata was ASR Output on Silent Media
- **The Plausible Suggestion:**  
  When external or synthetic media lacked an audio track, the assistant suggested falling back to echoing metadata dialogue strings as "simulated speech recognition output" with a fake 0.95 confidence score.
- **Why It Looked Plausible:**  
  It satisfied the downstream schema requirements without erroring.
- **Why It Was Fundamentally Flawed:**  
  Falsely claiming that unverified metadata dialogue is ASR-transcribed physical audio violates multimodal grounding integrity. In production, this masks missing audio tracks or corrupt container streams.
- **The Engineering Correction:**  
  Implemented strict physical container inspection (`AudioProcessor.detect_audio_stream`). When an audio stream is absent, the system explicitly returns `AUDIO_STREAM_NOT_AVAILABLE`, sets `is_asr_output: False`, and records explicit `source_type: METADATA` provenance.

---

### Case 6: Single-Candidate Planning without Competitive Narrative Arcs
- **The Plausible Suggestion:**  
  The assistant proposed having the planner generate a single plan per audience cohort, passing it directly to validation and relying on repair only if it failed.
- **Why It Looked Plausible:**  
  It matched the minimal workflow requirements and produced 3 trailers.
- **Why It Was Fundamentally Flawed:**  
  Single-candidate generation suffers from local optima and fails to explore genuinely diverse pacing strategies (e.g. traditional craft vs industrial defiance vs youthful innovation).
- **The Engineering Correction:**  
  Designed `generate_candidate_plans` to produce 3 genuinely diverse candidate narrative arcs per audience with distinct promises and emotional journeys, followed by an independent validator-driven `select_best_candidate` tournament before repair.

---

### Case 7: Prematurely Marking Unverified Evidence as Proven Ground Truth
- **The Plausible Suggestion:**  
  The assistant proposed initializing evidence elements (`VisualEvidence`, `EvidenceGrounding`) with `verified: True`, `match_confidence: 1.0`, and `rights_cleared: True` directly at creation time in the creative planner.
- **Why It Looked Plausible:**  
  It populated all schema fields cleanly and simplified downstream rendering passes.
- **Why It Was Fundamentally Flawed:**  
  Ground truth verification cannot be asserted by the generator proposing the plan. Proclaiming evidence "verified" before the validator tests timecodes, extracts frames, and checks rights violates independent validation integrity.
- **The Engineering Correction:**  
  The planner creates unverified evidence by default (`verified=False`, `rights_cleared=False`, `verified_accurate=False`, `match_confidence=0.0`). Only `IndependentValidationAgent` and `MediaValidator` resolve `verified=True` upon successful verification passes.

---

### Case 8: Mock Prompt Substring Leakage Across Audience Cohorts
- **The Plausible Suggestion:**  
  The assistant implemented mock LLM audience detection using naive substring checks: `if "family" in prompt_lower:`.
- **Why It Looked Plausible:**  
  It appeared simple and worked when prompts were short and isolated.
- **Why It Was Fundamentally Flawed:**  
  When compiling the comprehensive 22-item planning context (including character relationships like "family heritage" or "patriarchal pressure"), prompts for Young Adult and Dialect trailers also contained the word "family", causing the mock provider to incorrectly emit family trailer templates.
- **The Engineering Correction:**  
  Refactored prompt inspection to match explicit target cohort headers (`"for audience: young_adult"`, `"for audience: dialect"`, `"for audience: family"`), ensuring deterministic separation regardless of rich context content.

---

### Case 9: Rapid File Re-writing Causing Windows Sharing Violations (`[Errno 22]`)
- **The Plausible Suggestion:**  
  The assistant implemented decision log persistence by directly opening and overwriting `sample_run/decision_log.json` on every single decision log event: `with open(target, "w") as f: json.dump(...)`.
- **Why It Looked Plausible:**  
  It ensured disk persistence immediately after every agent step.
- **Why It Was Fundamentally Flawed:**  
  During workflow execution, `log_decision` is called dozens of times within milliseconds. On Windows systems, background file indexers and antivirus scanners briefly lock recently touched files. Rapidly reopening the same path in `"w"` mode caused intermittent `OSError: [Errno 22] Invalid argument` file-sharing violations.
- **The Engineering Correction:**  
  Implemented atomic write resilience using a temporary `.tmp` file that is atomically swapped into place via `replace()`, with a safe `OSError` retry fallback.

---

### Case 10: Artificial Candidate ID Bias in Plan Selection
- **The Plausible Suggestion:**  
  When implementing candidate selection, the assistant assigned `audience_score = 1.0` specifically if `cand.trailer_id.endswith("_v1")`.
- **Why It Looked Plausible:**  
  Candidate 1 was designed from the primary brief, so boosting it made initial unit tests pass reliably.
- **Why It Was Fundamentally Flawed:**  
  Rigging candidate evaluation by ID string prefix breaks agentic decision-making. Alternative arcs (such as Arc B: *Industrial Stakes* or Arc C: *Youth Innovation*) could never fairly compete or win even if they better matched duration or emotional pacing.
- **The Engineering Correction:**  
  Removed the ID bias entirely. Rewrote multi-dimensional scoring to evaluate actual narrative content: candidate scenes vs. brief candidate scene sets, target duration proximity, and emotional journey overlap, while ensuring `NO_SAFE_CANDIDATE` is returned if all candidates violate constraints.

---

### Case 11: Schema Attribute Mismatch (`sp.scene_id` vs `sp.affected_scenes`)
- **The Plausible Suggestion:**  
  When extracting spoiler scenes in the audience agent and planner, the assistant wrote set comprehensions assuming a singular attribute: `{sp.scene_id for sp in story_map.spoilers}`.
- **Why It Looked Plausible:**  
  Other schema models (such as `SceneMetadata` and `SensitiveContentItem`) use `scene_id`.
- **Why It Was Fundamentally Flawed:**  
  In the narrative canon, major spoilers (e.g. twist antagonist identity or buyout collusion) span multiple scenes (`affected_scenes: List[str]`). Accessing `.scene_id` raised an immediate Pydantic `AttributeError`.
- **The Engineering Correction:**  
  Updated all spoiler set comprehensions to iterate through `sp.affected_scenes` (`{sc for sp in story_map.spoilers for sc in sp.affected_scenes}`), properly protecting all scenes tainted by major plot twists.

---

## 3. Code Verification Methodology

Every line of code in this repository was verified through a three-stage quality gate:
1. **Automated Unit Testing (`python -m pytest -v`):** 67 comprehensive unit, multimodal, audit enhancement, and integration tests covering boundary conditions, prompt injections, multimodal vision/ASR grounding, combination spoilers, rights management, and escalation taxonomies.
2. **Deterministic Replay Verification (`--mode replay`):** Verifying that identical inputs produce bitwise reproducible outputs without network dependencies.
3. **Adversarial Scenario Injection (`--scenario <name>`):** Manually triggering every adversarial event to confirm that the validator intercepts the failure and the repair agent autonomously remediates it.

