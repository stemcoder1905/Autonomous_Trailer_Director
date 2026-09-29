# Known Limitations & Production Constraints

While the **Autonomous Trailer Director** provides an end-to-end, test-verified, and resilient agentic pipeline for editorial trailer planning, real-world deployment across large streaming catalogs introduces specific technical and algorithmic limitations.

---

## 1. Multimodal Grounding vs. Structured Metadata

### Current Architecture
- The system operates primarily on **structured multimodal metadata**: verified scene bounds, character rosters, dialogue transcripts, subtitle alignments, audio stem tags, and emotional tags.
- For local testing and deterministic evaluation, timecode-accurate mock metadata is used.

### Production Limitations
- **Sub-clip Shot Boundary Detection:** In actual video files, a 2-minute scene may contain dozens of camera cuts. Selecting sub-segment cuts (`00:02:14.200` to `00:02:18.600`) requires computer vision tools (e.g. PySceneDetect or OpenCV optical flow) to ensure the cut lands on an exact I-frame or natural shot transition rather than cutting an actor mid-blink or mid-sentence.
- **Audio Stem Layering:** Real trailer rendering requires separate dialogue, music, and Foley effects stems. Our EDL plan specifies the audio intent (e.g., `dialogue_and_acoustic_music`), but full acoustic ducking and cross-fading must be handled by the downstream NLE or FFmpeg engine.

---

## 2. Multi-Clip Combination Spoiler Boundaries

### Current Architecture
- `SpoilerValidator` evaluates both single-clip spoilers and multi-clip combination tuples (e.g., pairing catastrophe scene `scene_08` with instant resolution `scene_09`).

### Algorithmic Limits
- **Combinatorial Explosion:** In an episode with 25 scenes, checking all possible combinations of 4-scene sequences requires evaluating \(\binom{25}{4} = 12,650\) combinations. Checking across an entire 10-episode season becomes computationally intractable without hierarchical graph pruning.
- **Implicit Narrative Deduction:** Some spoilers do not exist in visual elements or dialogue, but are deduced by astute viewers from subtle atmospheric clues (e.g., character wearing a specific ring in scene 3 that only appears in scene 11). Current LLMs cannot reliably predict every human fan-theory deduction.

---

## 3. Cultural & Dialect Nuance

### Current Architecture
- The system checks dialect subtitle semantic alignment and enforces regional dignity policies, blocking crude urban stereotypes.

### Real-World Boundaries
- **Linguistic Ambiguity & Double Entendres:** Regional Indian dialects (e.g. Bhojpuri, Maithili, Magahi) contain rich localized idioms and sarcastic double entendres that standard translation models often misinterpret as offensive or literal.
- **Audience Segmentation Bias:** While the system refuses to equate dialect groups with violent content, personalization based on regional geography always risks subtle echo-chamber bias unless actively diversified by human curators.

---

## 4. Scalability Bottlenecks at Enterprise Scale

1. **State Graph Memory Footprint:** Passing full episode transcript packages and complete video metadata through memory graph state works efficiently for single episodes (~20MB memory), but full multi-season series planning requires distributed state stores (Redis/PostgreSQL) rather than in-memory Pydantic objects.
2. **Re-planning Lock Contention:** If hundreds of legal contracts expire concurrently (e.g. end of calendar year license turnover), triggering selective replanning across thousands of trailers simultaneously requires an asynchronous task queue (Celery/RabbitMQ) with distributed lock management.

---

## 5. Explicit Human Approval Triggers

The system is designed with intentional **Human-in-the-Loop** checkpoints. The autonomous system will refuse to finalize an EDL and will escalate to human editorial review under any of the following conditions:

1. **Automated Repair Exhaustion:** When all available replacement scenes from the canonical pool violate rating or rights policies, the system outputs: `human_approval_requirements: ["Automated repair exhausted"]`.
2. **Legal Rights Ambiguity:** If a contract contains pending or unverified territory clearances (`status: PENDING`).
3. **Severe Dialect Semantic Inversion:** If an external subtitle file has a semantic divergence score above threshold with no canonical source match.
4. **Budget Breach with No Fallback:** When estimated AI processing cost exceeds the `$25.00` budget ceiling and deterministic fallback templates are disabled.
