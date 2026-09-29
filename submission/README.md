# Autonomous Trailer Director — Submission Package Overview

This submission package provides the architecture specifications, design rationales, AI collaboration notes, known limitations, compliance audit, and interview preparation for the **OTT Dialect Platform — Autonomous Trailer Director**.

---

## Submission Package Contents

1. [ARCHITECTURE.md](ARCHITECTURE.md)
   - Deep dive into state-graph multi-agent architecture, state transitions, memory boundaries, and dependency tracking.
   - Decoupled validation design and why self-evaluating LLMs fail.
   - Multimodal grounding and timecode math.
   - Cost guardrails and resilience fallback architecture.

2. [AI_COLLABORATION.md](AI_COLLABORATION.md)
   - Detailed disclosure of AI-assisted coding tools used.
   - Verification methodology and regression guards.
   - Concrete examples of plausible-but-wrong suggestions intercepted and corrected during development.

3. [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)
   - Real-world production constraints: video/audio multimodal frame analysis limits.
   - Multi-clip combination spoiler boundaries and combinatorial explosion.
   - Nuanced cultural idiom translation edge cases.
   - Explicit triggers where human editorial approval is strictly required.

4. [INTERVIEW_PREP.md](INTERVIEW_PREP.md)
   - Comprehensive answers to all required hiring manager technical questions:
     1. How does the system define and detect a spoiler?
     2. How do creative generation and validation remain meaningfully independent?
     3. What happens when a music contract changes after planning?
     4. How do you personalize for a dialect audience without stereotyping it?
     5. Which part of the system would fail first at large scale?
     6. What did the AI coding assistant suggest that looked plausible but was wrong?

5. [ASSIGNMENT_COMPLIANCE.md](ASSIGNMENT_COMPLIANCE.md)
   - Rigorous self-audit against every single requirement in the take-home specification.
   - Real status declarations: implemented, partially implemented, mocked, or not implemented.
