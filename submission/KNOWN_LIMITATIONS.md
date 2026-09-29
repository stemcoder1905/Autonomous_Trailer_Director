# Known Limitations & Production Constraints

While the **Autonomous Trailer Director** provides an end-to-end, test-verified, and resilient agentic pipeline for editorial trailer planning, real-world deployment across production streaming catalogs involves specific technical, algorithmic, and multimodal limitations. The project demonstrates a hardened architectural prototype and quality-gate framework, but should not be claimed as an unattended end-to-end production system without human editorial oversight.

---

## 1. Synthetic / Mock Data & Replay Mode Limitations

- **Synthetic Video Fixture:** The repository includes a deterministic synthetic video (`sample_data/media/episode_01.mp4`). While it has valid MP4 container dimensions, frame rates, and timecodes, it is an illustrative fixture designed for automated offline verification rather than broadcast video evaluation.
- **Absence of Physical Audio Stream:** The replay fixture does not contain an actual audio track. In replay mode, speech recognition explicitly reports `AUDIO_STREAM_NOT_AVAILABLE` and `is_asr_output: False`. The system intentionally refuses to fabricate synthetic ASR transcripts from dialogue metadata.
- **Replay vs. Live Determinism:** In replay mode, LLM and Vision provider responses are simulated using deterministic mock handlers (`MockLLMProvider`, `MockVisionProvider`). While this guarantees 100% reproducible test suites with zero external API costs, it does not evaluate the stochastic variability or latency of live frontier cloud models.

---

## 2. Multimodal Model Inference & Vision/ASR Limits

- **Sub-Clip Shot Boundary Alignment:** Although the system includes OpenCV frame difference analysis (`detect_shot_boundaries`), fine-grained sub-second cuts in live video production require deep boundary models (e.g., TransNetV2, PySceneDetect) to guarantee cuts align with keyframes (I-frames) and avoid clipping actors mid-phoneme or mid-motion.
- **Multimodal Visual Claim Ambiguity:** Vision models evaluate visual grounding from sampled frames (start, middle, end). Subtleties such as micro-expressions, rapid background action, or cinematic lighting shifts can produce low confidence scores ($< 0.75$), triggering mandatory human editorial review rather than autonomous final clearance.
- **Audio Stem Layering & Mixdown:** Trailer delivery requires separate audio stems (dialogue, Foley effects, isolated score). The system generates Edit Decision Lists (EDLs) with audio track directives, but automated acoustic ducking, equalization, and final multi-track stem mixdown must be performed downstream by a professional Digital Audio Workstation (DAW) or FFmpeg rendering pipeline.

---

## 3. Dependency on Supplied Metadata & Ground-Truth Asymmetry

- **Metadata Completeness:** The system relies on structured episode packages (scene boundaries, character lists, dialogue transcripts, subtitle alignments, and contract manifests). If upstream ingestion pipelines provide corrupt or incomplete metadata, validator passes may fail or require manual correction.
- **Ground-Truth Asymmetry:** When external media is ingested without pre-indexed character metadata, face-recognition or speaker-diarization models would be required to independently identify uncredited actors or off-screen dialogue.

---

## 4. Limits of Automated Cultural & Bias Detection

- **Linguistic Ambiguity & Regional Idioms:** Bhojpuri, Maithili, and Purvanchal dialects possess rich colloquial idioms, cultural proverbs, and double entendres. While the regex-based and semantic validators catch explicit sentiment inversions and coarse urban stereotypes (e.g. violent slapstick tropes), subtle sociolinguistic nuances still require verification by native vernacular consultants.
- **Audience Personalization vs. Echo Chambers:** Algorithmic audience tailoring risks inadvertently reinforcing demographic preferences unless curated with intentional diversity. The system guards against negative stereotyping, but cultural resonance requires continual human calibration.

---

## 5. Limits of Spoiler Detection & Implicit Narrative Deduction

- **Combinatorial Spoiler Complexity:** Single-clip spoilers and explicit multi-clip juxtaposition tuples (e.g., disaster scene `scene_08` paired with resolution `scene_09`) are detected deterministically. However, exhaustively evaluating all possible permutations across long series ($>10$ episodes) becomes computationally intensive without domain-specific graph pruning.
- **Implicit Narrative Deduction:** Viewers frequently deduce twists from background props, costume changes, or subtle character glances that automated narrative graphs may classify as benign. Automated systems cannot anticipate every fan-theory deduction.

---

## 6. Mandatory Human Editorial, Legal, and Cultural Approval (Human-in-the-Loop)

The system is deliberately engineered with explicit **Human-in-the-Loop (HITL)** escalation checkpoints. Automated generation halts or flags trailers for sign-off under four structured classes:

1. **`LEGAL` Approval Required**:
   - Contractual sync licenses or talent blackout agreements are unverified, expired, or pending renegotiation without a safe alternative asset.
2. **`CULTURAL` Approval Required**:
   - Dialect subtitle semantic discrepancies or sensitive cultural references that cannot be deterministically resolved against canonical dialogue.
3. **`EDITORIAL` Approval Required**:
   - Multimodal vision confidence falls below the confidence threshold ($< 0.75$), or complex multi-clip pacing tradeoffs require creative human discretion.
4. **`CREATIVE` Approval Required**:
   - All automated candidate arcs fail constraint verification (`NO_SAFE_CANDIDATE`), requiring human editors to re-cut or approve alternative footage.

---

## 7. Production-Scale & Enterprise Infrastructure Boundaries

- **In-Memory State Scaling:** `DirectorState` operates efficiently in-memory for single episodes (~20MB memory). Running continuous operations across large streaming catalogs (hundreds of seasons) will require migrating state to distributed persistence layers (PostgreSQL, Redis) and asynchronous task queues (Celery, Temporal).
- **Concurrent Replanning Throughput:** Mass contract turnover (e.g. dozens of music sync licenses expiring simultaneously at year-end) requires distributed locking and worker pools to replan thousands of promotional assets without database contention.
