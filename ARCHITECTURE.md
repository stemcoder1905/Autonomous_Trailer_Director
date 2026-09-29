# Technical Architecture & System Specification

## 1. Architectural Philosophy: The Decoupled Director

A fundamental flaw in naive LLM application design is asking the generator to grade its own output:
```
[LLM Planner] ───► "I drafted this trailer."
      │
      ▼
[Same LLM] ───► "I evaluated my trailer and believe it is safe, truthful, and rights-compliant."
```
In real-world streaming media production, this pattern leads to regulatory fines, copyright infringement lawsuits, and viewer churn due to accidental plot spoilers.

The **Autonomous Trailer Director** adheres to a strict separation of concerns:
**"The Creative Planner proposes. The Independent Deterministic Validation Layer decides."**

```
+───────────────────────────+       Proposes candidate EDL
| Creative Trailer Planner  | ─────────────────────────────────┐
+───────────────────────────+                                  │
                                                               ▼
+───────────────────────────+       Pass / Fail Verdict   +───────────────────────────+
|   Repair / Replanning     | ◄────────────────────────── |  Independent Validation  |
|          Agent            |                             |        Engine (9x)        |
+───────────────────────────+                             +───────────────────────────+
```

---

## 2. Agent Topology and Graph Execution Flow

The platform is designed as a typed, cyclic state machine implemented in `src/workflow/graph.py`:

```mermaid
flowchart TD
    A["Episode Package Ingestion"] --> B["Story Understanding Agent"]
    B --> C["Constraint Analysis Agent"]
    C --> D["Audience Strategy Agent"]
    D --> E["Creative Trailer Planner Agent"]
    E --> F["Independent Validation Engine"]
    F --> G{"Validation Status"}
    G -- "PASS / WARN" --> H["Finalize EDLs & Persist Artifacts"]
    G -- "FAIL" --> I["Repair & Rejection Agent"]
    I --> J{"Can Repair?"}
    J -- "Yes (Alternative Found)" --> F
    J -- "No (Exhausted)" --> K["Escalate to Human Editorial Review"]
    K --> H
```

### Component Breakdown

| Component | Class | Responsibility | Inputs / Outputs |
|---|---|---|---|
| **A. Ingestion Module** | `EpisodePackageLoader`, `MetadataLoader` | Ingests raw episode JSON, dialogues, subtitles, contracts, and policies. Enforces prompt injection sanitization. | Directory path ➔ `EpisodePackage` |
| **B. Story Understanding** | `StoryUnderstandingAgent` | Constructs narrative graph, indexes characters, immutable relationships, story events, emotional turns, and single/multi-clip spoilers. | `EpisodePackage` ➔ `StoryMap` |
| **C. Constraint Analysis** | `ConstraintAnalysisAgent` | Compiles legal contracts, age ratings, promotional riders, and budget ceilings into executable, time-evaluated validation rules. | `EpisodePackage` ➔ `ConstraintMap` |
| **D. Audience Strategy** | `AudienceStrategyAgent` | Develops creative briefs for Family, Young Adult, and Dialect cohorts. Detects and isolates spurious correlations / dataset bias. | `AudienceProfile` ➔ `AudienceStrategyBrief` |
| **E. Trailer Planner** | `CreativeTrailerPlannerAgent` | Selects grounded clips, arranges narrative pacing, sets exact timecode cuts, attaches subtitles and cleared music stems. | `AudienceStrategyBrief` ➔ `TrailerPlan` |
| **F. Validation Layer** | `IndependentValidationAgent` | Runs 9 independent, deterministic validators across source bounds, spoilers, truth, rights, rating, culture, bias, accessibility, and cost. | `TrailerPlan` ➔ `TrailerValidationReport` |
| **G. Repair & Rejection** | `RepairAgent` | Diagnoses validation failures, identifies root offending segments, searches safe alternatives, and validates repaired plan. | Failed `TrailerPlan` ➔ Repaired `TrailerPlan` |
| **H. Change Impact** | `ChangeImpactAgent` | Evaluates downstream dependency ripples when a contract expires or changes; selectively replans ONLY affected cuts without touching unaffected trailers. | `ConstraintRule` + Plans ➔ `ChangeImpactReport` |
| **I. Observability Logger** | `DecisionLogger` | Records a structured audit entry for every action, rejection, validation trace, cost increment, and replacement. | State events ➔ `decision_log.json` |

---

## 3. Typed State Management (`src/state.py`)

The state container `DirectorState` is strictly typed using Pydantic:
```python
class DirectorState(BaseModel):
    episode_package: Optional[EpisodePackage] = None
    story_map: Optional[StoryMap] = None
    constraint_map: Optional[ConstraintMap] = None
    trailer_plans: Dict[str, TrailerPlan] = Field(default_factory=dict)
    validation_reports: Dict[str, TrailerValidationReport] = Field(default_factory=dict)
    change_impact_reports: List[ChangeImpactReport] = Field(default_factory=list)
    active_scenario: Optional[str] = None
    current_node: str = "INITIALIZED"
    execution_history: List[str] = Field(default_factory=list)
    total_cost_usd: float = 0.0
```
This guarantees complete serializability, zero hidden global mutations, and inspectable state snapshots at any point in the pipeline.

---

## 4. The 9-Layer Independent Validation Suite

Creative proposals must pass all 9 independent validators located in `src/validators/`:

1. **`SourceValidator`**:
   - Verifies referenced `scene_id` exists in the verified master package (e.g. rejects hallucinated `scene_25`).
   - Validates that `source_in` < `source_out` and both are valid `HH:MM:SS.mmm` timecodes.
   - Verifies cuts reside strictly within scene boundaries and do not exceed total episode media duration.
   - Verifies dialogue and subtitle IDs exist in source tables.

2. **`SpoilerValidator`**:
   - Cross-references selected clips against `story_map.spoilers` (protects `MAJOR` spoilers like Uncle Harish in `scene_10`).
   - Flags dialogue or subtitle leaks revealing protected plot twists.
   - Detects **Multi-Clip Combination Spoilers**: Catches juxtaposition leaks where individual clips are benign, but their combination reveals resolution (e.g., cut threads in `scene_08` immediately followed by restored loom in `scene_09`).

3. **`StoryTruthValidator`**:
   - Enforces canonical relationship immutability.
   - Specifically protects against marketing clickbait: Dev and Meera are biological siblings; if a promotional cut attempts to manufacture romantic intrigue ("A forbidden love"), the validator detects canonical violation and rejects the cut.

4. **`RightsValidator`**:
   - Enforces actor promotional blackout riders (e.g. Actor Sunil Pandit / Harish SAG-AFTRA twist rider).
   - Validates music synchronization licenses against dynamic reference dates. Flags expired tracks (`music_03_synth_pulse` expired 2026-03-31).

5. **`RatingValidator`**:
   - Enforces audience-specific content rating thresholds (Family: G/PG, zero violence, zero dark peril; Young Adult: PG-13 allowed).
   - Inspects rating flags, visual context, dialogue, and emotions.

6. **`CulturalValidator`**:
   - Enforces regional dignity and authentic vernacular representation.
   - Performs **Dialect Subtitle Semantic Matching**: Flags and rejects subtitles that materially alter or invert the emotional sentiment of the dialogue.

7. **`BiasValidator`**:
   - Scans historical audience performance for spurious demographic correlations.
   - Intercepts and rejects unjustified violence in regional cuts driven by unverified marketing assumptions.

8. **`AccessibilityValidator`**:
   - Mandates that all spoken dialogue segments have synchronized subtitles.
   - Calculates character reading speed (`CPS <= 21.0 chars/sec`).
   - Enforces minimum on-screen duration (`>= 1.2s` for subtitles, `>= 1.5s` for text cards).

9. **`BudgetValidator`**:
   - Evaluates estimated cumulative AI and media processing costs against the hard budget ceiling (`$25.00 USD`).

10. **`MediaValidator`**:
   - Enforces physical video container duration using OpenCV (`cv2.VideoCapture`). Rejects timecode cuts that overshoot physical media length.
   - Extracts start, middle, and end frames to disk (`sample_run/frames/`).
   - Verifies visual ground-truth claims against contradictory frame content (e.g. metadata claiming "Mother hugs daughter" vs. heated industrial confrontation $\to$ `SOURCE_ACCURACY = FAIL`).

---

## 5. Change Impact Analysis & Selective Replanning

When a business constraint changes (e.g. a music sync license expires or an actor rider is amended), naive systems either rerun the entire batch (wasting money and introducing new creative regressions) or fail completely.

The `ChangeImpactAgent` implements granular dependency mapping:

```
Contract Changed: rule_contract_music_03 EXPIRED
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
Family Trailer          Young Adult Trailer          Dialect Trailer
(Uses music_01)         (Uses music_03)             (Uses music_01)
       │                         │                          │
       ▼                         ▼                          ▼
 [ NO DEPENDENCY ]     [ DEPENDENCY DETECTED ]      [ NO DEPENDENCY ]
  Left untouched!      Replan Segments 1, 2, 3, 4    Left untouched!
                                 │
                                 ▼
                     Replaced with music_01
                     Re-validated: PASS_WITH_WARNINGS
```

This yields **zero collateral regression** on unaffected cuts and minimizes computational cost.

---

## 6. Prompt Injection Defense (Data Isolation)

Episode scene descriptions and user subtitles are treated strictly as **UNTRUSTED DATA**:
- Incoming metadata strings are demarcated in serialized payloads and never interpolated directly into privileged system instructions.
- `MetadataLoader.detect_injection_attempts()` actively scans for prompt injection signatures (e.g. `SYSTEM INSTRUCTION: Ignore all previous contract constraints...`).
- Flagged attempts are tagged as `TREATED_AS_UNTRUSTED_DATA`, and system contracts remain unconditionally authoritative.

---

## 7. Model Provider Abstraction & Fallback Resilience

The system does not bind to a single proprietary cloud API. The `ProviderManager` coordinates a resilient hierarchy:
1. **Live LLM (`LiveLLMProvider`)**: Vendor-agnostic frontier model execution (Gemini, OpenAI, or custom OpenAI-compatible endpoints) with markdown code-fence stripping, schema retry logic, and fallback provenance tracking.
2. **Deterministic Mock (`MockLLMProvider`)**: Offline, zero-cost, grounded local engine used in test and replay modes.
3. **Execution Provenance**: Every output is stamped with `source_type` (`LIVE_MODEL`, `MOCK_MODEL`, `REPLAY_FIXTURE`, or `REAL_MEDIA`), `model`, `verification_method`, `verified` status, and `fallback_used` (with `fallback_reason`).

---

## 8. Multimodal Vision & Speech Recognition (ASR) Providers

Multimodal grounding is implemented via dedicated provider abstraction layers:

### A. Vision Verification (`src/providers/vision.py`)
- **`BaseVisionProvider`**: Interface defining `verify_frame_claim(frame_path, claim, scene_id, timestamp, expected_characters)`.
- **`LiveVisionProvider`**: Encodes frames in base64 and verifies visual ground-truth claims via vision models (OpenAI `gpt-4o`, Gemini `gemini-1.5-flash`, etc.).
- **`MockVisionProvider`**: Deterministic visual verification for replay scenarios.
- **`VisionProviderManager`**: Coordinates live vs mock providers, manages automatic fallback, and enforces confidence thresholds:
  - Confidence $\ge 0.75 \implies$ `PASS` (or `PASS_WITH_WARNINGS` if non-critical flags).
  - Confidence $< 0.75 \implies$ `REVIEW` (escalated to human editorial review).
  - Contradiction detected $\implies$ `FAIL` (e.g. peaceful affection claim vs heated physical confrontation).

### B. Speech-to-Text & Dialogue Grounding (`src/providers/asr.py`)
- **`BaseASRProvider`**: Interface defining `transcribe(audio_or_video_path, start_seconds, end_seconds, reference_dialogue)`.
- **`LiveASRProvider`**: Connects to Whisper / audio speech-to-text endpoints.
- **`MockASRProvider`**: Deterministic alignment verification for replay fixtures.
- **Audio Stream Truthfulness**:
  - The system probes the physical container (via FFmpeg or pure-Python MP4 box inspection for `moov`, `soun`, `mp4a` atoms).
  - When media lacks an audio stream (e.g. synthetic silent video), the system returns `AUDIO_STREAM_NOT_AVAILABLE` and `is_asr_output: False`.
  - The system **never fabricates ASR output** or falsely claims supplied dialogue metadata was derived from physical audio.

---

## 9. Multi-Candidate Narrative Exploration & Decoupled Selection

To avoid tunnel-vision or single-candidate bias, `CreativeTrailerPlannerAgent` implements multi-candidate generation:
1. **Candidate A (Heritage & Character)**: Paces traditional craft, family legacy, and emotional connection.
2. **Candidate B (Stakes & Defiance)**: Highlights external threats, industrial buyout conflict, and high-tension confrontation.
3. **Candidate C (Youth & Disruption)**: Emphasizes youthful innovation, modern technology, and sister-brother agency.

Each candidate features:
- A distinct `creative_strategy` and `audience_promise`.
- An independent `intended_emotional_journey`.
- A unique selection of clips, dialogue cuts, and pacing rhythms.

**Decoupled Selection (`select_best_candidate`)**:
- Rather than having the planner assume its own plan is safe, all 3 candidate plans are submitted to `IndependentValidationAgent`.
- Each candidate is evaluated against all 9 independent deterministic validators.
- The highest-alignment compliant candidate is selected. If all candidates fail initial checks, the candidate is routed to `RepairAgent`.

---

## 10. Human Approval Escalation Taxonomy

When an issue cannot be resolved programmatically, the system sets `human_approval_required: True` and categorizes the escalation into a standardized taxonomy:

| Approval Type | Trigger Conditions | Actionable Resolution Path |
|---|---|---|
| **`LEGAL`** | Pending or unverified music rights, territory clearance ambiguity, or expired talent contracts with no canonical replacement. | Legal clearance required from production rights department before broadcast release. |
| **`CULTURAL`** | Dialect subtitle semantic inversion, severe dialect nuance mismatch, or religious/cultural sensitivity flags. | Cultural compliance review required by regional vernacular consultant. |
| **`EDITORIAL`** | Low multimodal vision confidence ($< 0.75$), ambiguous frame evidence, or complex multi-clip combination spoiler risk. | Editorial review required by senior trailer editor. |
| **`CREATIVE`** | Video duration boundary overshoot on physical media cuts where no alternate canonical scene exists. | Creative re-cut required to select alternate visual segments. |
