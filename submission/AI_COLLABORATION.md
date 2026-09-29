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
  Rigorously separated planning from validation. Implemented 9 **deterministic, programmatic validators** (`SourceValidator`, `RightsValidator`, `SpoilerValidator`, etc.) where timecodes, active dates, contract IDs, and relationship graphs are checked with exact Boolean and mathematical logic.

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

## 3. Code Verification Methodology

Every line of code in this repository was verified through a three-stage quality gate:
1. **Automated Unit Testing (`pytest -v`):** 14 specialized unit tests covering boundary conditions, prompt injections, missing scenes, and combination spoilers.
2. **Deterministic Replay Verification (`--mode replay`):** Verifying that identical inputs produce bitwise reproducible outputs without network dependencies.
3. **Adversarial Scenario Injection (`--scenario <name>`):** Manually triggering every adversarial event to confirm that the validator intercepts the failure and the repair agent autonomously remediates it.
