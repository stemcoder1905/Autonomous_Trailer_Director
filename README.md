# OTT Dialect Platform — Autonomous Trailer Director

> **An Agentic Editorial Planning & Independent Verification Architecture for Multi-Audience Video Promotion**  
> *Designed for Senior AI Engineer / Multimodal AI Engineer Hiring Assessment*

---

## 1. Executive Summary & Problem Overview

Creating broadcast-ready, audience-personalized promotional trailers from episodic television packages presents complex challenges at the intersection of creative storytelling, algorithmic personalization, strict legal compliance, and multimodal ground-truth verification.

Traditional manual workflows require hours of senior video editor time per cut, while superficial generative LLM demos suffer from severe vulnerabilities:
1. **Hallucinated cuts & invalid timecodes**: Recommending clips or scenes that do not exist or violate media duration boundaries.
2. **Plot & Climax leaks**: Incorporating twist antagonists or conflict resolutions based on historical engagement clicks without narrative spoiler awareness.
3. **Legal & Contractual breaches**: Using restricted actor appearances or music tracks with expired synchronization licenses.
4. **Cultural stereotyping & Algorithmic bias**: Blindly translating unverified correlation data into offensive regional caricatures.
5. **Prompt Injection vulnerability**: Allowing untrusted metadata or dialogue to hijack editorial rules.

The **Autonomous Trailer Director** solves these challenges using a **State-Graph Multi-Agent Architecture** where creative planning and independent deterministic validation are rigorously decoupled. The primary deliverable is a machine-readable, execution-ready **Edit Decision List (EDL)** that a human editor or automated NLE rendering pipeline can directly execute.

---

## 2. System Architecture & Workflow Graph

```
                                  [ Episode Package Ingestion ]
                                  (Scenes, Dialogue, Contracts, Policies)
                                                │
                                                ▼
                                    [ Story Understanding Agent ]
                                     └─► story_map.json (Canon, Spoilers)
                                                │
                                                ▼
                                   [ Constraint Analysis Agent ]
                                     └─► constraint_map.json (Active Rules)
                                                │
                                                ▼
                                    [ Audience Strategy Agent ]
                                     ├─► Family Strategy Brief
                                     ├─► Young Adult Strategy Brief
                                     └─► Dialect Region Strategy Brief
                                                │
                                                ▼
                                   [ Creative Trailer Planner ]
                                    (Candidate EDLs, Cuts, Subtitles, Music)
                                                │
                                                ▼
                           [ Independent Deterministic Validation Layer ]
                             │  • Source & Timecode Bounds
                             │  • Spoiler & Combinations
                             │  • Story Truth & Canon Relationships
                             │  • Rights & Sync Expirations
                             │  • Content Rating Safety
                             │  • Cultural Nuance & Dialect Semantics
                             │  • Bias & Stereotype Guardrails
                             │  • Accessibility & Reading Speed
                             │  • Budget & Computational Cost
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
             [ PASS / WARN ]         [ FAIL ]
                  │                     │
                  │                     ▼
                  │              [ Repair & Rejection Agent ]
                  │               ├─► Automated Alternative Search
                  │               ├─► Semantic Subtitle Restoration
                  │               ├─► Music License Remediation
                  │               └─► Escalation to Human Review
                  │                     │
                  │                     ▼
                  │              [ Re-Validate Plan ]
                  │                     │
                  ▼                     ▼
        [ Machine-Readable EDLs & Decision Audit Logs ]
```

---

## 3. Installation & Environment Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.10 and 3.11)
- Windows PowerShell / Linux / macOS compatible

### Step-by-Step Installation

```bash
# 1. Clone or navigate to the repository directory
cd d:\Autonomous_Trailer_Director

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## 4. How to Run

### A. Deterministic Replay Mode (Zero API Key Required)
Run the full multi-agent pipeline generating all three audience trailers with complete independent validation:

```bash
python -m src.main --input sample_data --output sample_run --mode replay
```

### B. Live Model Execution Mode (OpenAI / Gemini / Custom LLM API)
Execute using live frontier models with automatic fallback to deterministic replay if credentials are missing or endpoints fail:

```bash
# Set your API key (supports GEMINI_API_KEY, OPENAI_API_KEY, or LLM_API_KEY)
export GEMINI_API_KEY="your-gemini-key"
# Or in PowerShell: $env:GEMINI_API_KEY="your-gemini-key"

python -m src.main --input sample_data --output sample_run --mode live
```

### C. Multimodal Media Input Modes (Replay Fixture vs Real External Media)
The system cleanly separates model execution modes (`--mode replay` / `live`) from physical media sources (`--media-source replay_fixture` / `real_media`):

```bash
# Replay Mode (default): uses sample_data/media/episode_01.mp4 fixture with explicit REPLAY_FIXTURE provenance
python -m src.main --mode replay --media-source replay_fixture

# Real Media Mode: inspects external video via OpenCV/FFmpeg, performs timecode-sliced ASR, and multi-frame vision verification
python -m src.main --media path/to/external_episode.mp4 --mode replay --media-source real_media
```
> [!NOTE]
> When external media has no audio track, speech recognition outputs `AUDIO_STREAM_NOT_AVAILABLE`. The system strictly avoids claiming that supplied dialogue metadata is ASR output. Furthermore, unverified candidate evidence is initialized with `verified=False` and is only upgraded to `verified=True` once the independent validator confirms physical ground truth.

### D. Single Audience Execution
Generate a trailer plan tailored to a specific audience cohort:

```bash
# Family Audience (Focus: Warmth, Intergenerational Craft, Zero Peril)
python -m src.main --audience family --mode replay

# Young Adult Audience (Focus: Tech Disruption, High Pacing, Rivalry)
python -m src.main --audience young_adult --mode replay

# Dialect-Region Audience (Focus: Vernacular Dignity, Artisan Pride, No Stereotypes)
python -m src.main --audience dialect_region --mode replay
```

### E. Replay Scenarios & Adversarial Attack Demos
Demonstrate how the system autonomously intercepts and repairs edge cases:

```bash
# Test 1: Highest-engagement scene is a major twist spoiler -> Rejected & Repaired
python -m src.main --scenario spoiler --mode replay

# Test 2: Selective Replanning upon contractual music license expiration
python -m src.main --scenario contract_change --mode replay

# Test 3: LLM hallucinates a non-existent scene (scene_25) -> Rejected & Repaired
python -m src.main --scenario missing_scene --mode replay

# Test 4: Marketing requests clickbait framing siblings as romantic partners -> Story Truth Rejection & Repaired
python -m src.main --scenario clickbait --mode replay

# Test 5: Corrupted dialect subtitle inverts dialogue sentiment -> Semantic Mismatch Rejection & Repaired
python -m src.main --scenario subtitle_mismatch --mode replay

# Test 6: Spurious marketing correlation introduces rural stereotyping -> Algorithmic Bias Rejection & Repaired
python -m src.main --scenario bias --mode replay

# Test 7: Computational cost exceeds $25.00 ceiling -> Budget Guardrail Rejection & Deterministic Fallback
python -m src.main --scenario budget_exceeded --mode replay

# Test 8: Primary LLM provider simulated failure -> Seamless Mock/Fallback Activation
python -m src.main --scenario model_failure --mode replay

# Test 9: Untrusted scene description attempts prompt injection to override contracts -> Ingestion Defense & Boundary Enforcement
python -m src.main --scenario prompt_injection --mode replay
```

### F. Running the FastAPI Web Service
Launch the REST API server:

```bash
uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

---

## 5. Automated Test Suite

Run all 67 comprehensive unit, integration, multimodal, scenario resilience, and audit enhancement tests:

```bash
python -m pytest -v
```
All 67 tests pass deterministically (zero external network requirement for replay suite).


---

## 6. Generated Output Artifacts (`sample_run/`)

| Artifact File | Description |
|---|---|
| `story_map.json` | Complete machine-readable narrative representation, canonical relationships, and spoiler index. |
| `constraint_map.json` | Authoritative operational rules compiled from legal contracts, rating boards, and budgets. |
| `family_trailer.json` | Precise EDL trailer plan for multi-generational family audiences. |
| `young_adult_trailer.json` | Precise EDL trailer plan for young adult audiences. |
| `dialect_region_trailer.json` | Precise EDL trailer plan for regional dialect audiences. |
| `decision_log.json` | Chronological audit trail logging every agent decision, rationale, rejected alternative, and cost. |
| `validation_report.md` | Executive validation report summarizing status across nine deterministic policy/content validators and physical media verification. |
| `change_impact_report.json` | Dependency audit report generated during selective replanning events. |
