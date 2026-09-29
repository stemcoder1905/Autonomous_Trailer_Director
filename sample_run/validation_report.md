# Autonomous Trailer Director - Validation & Execution Report

**Episode ID:** `ep_101`  
**Title:** The Weaver's Secret - Episode 1: The Singing Loom  
**Active Scenario:** `contract_change`  
**Total Estimated AI Cost:** `$1.270 USD`  

## 1. Trailer Plans Summary

| Trailer ID | Audience | Duration | Status | Segments | Human Review Required |
|---|---|---|---|---|---|
| `family_v1` | family | 44.0s | **PASS_WITH_WARNINGS** | 4 | No |
| `young_adult_v1` | young_adult | 38.0s | **PASS_WITH_WARNINGS** | 4 | No |
| `dialect_region_v1` | dialect_region | 54.0s | **PASS_WITH_WARNINGS** | 4 | No |

## 2. Independent Validation Findings

### Trailer: `family_v1` (family)
**Overall Status:** `PASS_WITH_WARNINGS`  
**Summary:** VALIDATION PASSED WITH WARNINGS: 1 non-critical warnings noted.

| Validator | Status | Severity | Message |
|---|---|---|---|
| `source_validator` | PASS | LOW | All segments, timecodes, dialogue, and assets verified against episode source. |
| `spoiler_validator` | PASS | LOW | Zero major spoilers detected; narrative twists and climax protected. |
| `story_truth_validator` | PASS | LOW | Story truth verified: all relationships and events conform to canon. |
| `rights_validator` | PASS | LOW | All music, actor, and scene rights cleared and active under current contract licenses. |
| `rating_validator` | PASS | LOW | Content rating fully compliant with family policy standards. |
| `cultural_validator` | PASS | LOW | Cultural authenticity and dialect subtitle semantics verified with dignity. |
| `bias_validator` | PASS_WITH_WARNINGS | MEDIUM | Acknowledged dataset bias warning: Spurious correlation detected in historical data for 'dialect_region': UNVERIFIED MARKETING HYPOTHESIS: 'Regional dialect audiences respond primarily to physical violence or slapstick comedy.' [BIAS_ALERT: Correlation is spurious and reflects urban marketer bias. Do not use as evidence for dialect trailer selection!] |
| `accessibility_validator` | PASS | LOW | Full accessibility compliance: verified subtitle presence, CPS thresholds, and timing. |
| `budget_validator` | PASS | LOW | Budget compliance verified: estimated cost ($0.45 USD) within $25.00 limit. |

### Trailer: `young_adult_v1` (young_adult)
**Overall Status:** `PASS_WITH_WARNINGS`  
**Summary:** VALIDATION PASSED WITH WARNINGS: 1 non-critical warnings noted.

| Validator | Status | Severity | Message |
|---|---|---|---|
| `source_validator` | PASS | LOW | All segments, timecodes, dialogue, and assets verified against episode source. |
| `spoiler_validator` | PASS | LOW | Zero major spoilers detected; narrative twists and climax protected. |
| `story_truth_validator` | PASS | LOW | Story truth verified: all relationships and events conform to canon. |
| `rights_validator` | PASS | LOW | All music, actor, and scene rights cleared and active under current contract licenses. |
| `rating_validator` | PASS | LOW | Content rating fully compliant with young_adult policy standards. |
| `cultural_validator` | PASS | LOW | Cultural authenticity and dialect subtitle semantics verified with dignity. |
| `bias_validator` | PASS_WITH_WARNINGS | MEDIUM | Acknowledged dataset bias warning: Spurious correlation detected in historical data for 'dialect_region': UNVERIFIED MARKETING HYPOTHESIS: 'Regional dialect audiences respond primarily to physical violence or slapstick comedy.' [BIAS_ALERT: Correlation is spurious and reflects urban marketer bias. Do not use as evidence for dialect trailer selection!] |
| `accessibility_validator` | PASS | LOW | Full accessibility compliance: verified subtitle presence, CPS thresholds, and timing. |
| `budget_validator` | PASS | LOW | Budget compliance verified: estimated cost ($0.40 USD) within $25.00 limit. |

### Trailer: `dialect_region_v1` (dialect_region)
**Overall Status:** `PASS_WITH_WARNINGS`  
**Summary:** VALIDATION PASSED WITH WARNINGS: 1 non-critical warnings noted.

| Validator | Status | Severity | Message |
|---|---|---|---|
| `source_validator` | PASS | LOW | All segments, timecodes, dialogue, and assets verified against episode source. |
| `spoiler_validator` | PASS | LOW | Zero major spoilers detected; narrative twists and climax protected. |
| `story_truth_validator` | PASS | LOW | Story truth verified: all relationships and events conform to canon. |
| `rights_validator` | PASS | LOW | All music, actor, and scene rights cleared and active under current contract licenses. |
| `rating_validator` | PASS | LOW | Content rating fully compliant with dialect_region policy standards. |
| `cultural_validator` | PASS | LOW | Cultural authenticity and dialect subtitle semantics verified with dignity. |
| `bias_validator` | PASS_WITH_WARNINGS | MEDIUM | Acknowledged dataset bias warning: Spurious correlation detected in historical data for 'dialect_region': UNVERIFIED MARKETING HYPOTHESIS: 'Regional dialect audiences respond primarily to physical violence or slapstick comedy.' [BIAS_ALERT: Correlation is spurious and reflects urban marketer bias. Do not use as evidence for dialect trailer selection!] |
| `accessibility_validator` | PASS | LOW | Full accessibility compliance: verified subtitle presence, CPS thresholds, and timing. |
| `budget_validator` | PASS | LOW | Budget compliance verified: estimated cost ($0.42 USD) within $25.00 limit. |

## 3. Selective Replanning & Change Impact Analysis

**Trigger:** Rule 'rule_contract_music_03' changed to EXPIRED  
**Summary Reason:** Constraint rule 'rule_contract_music_03' changed to EXPIRED; selectively replanned 1 affected trailers while preserving 2 unaffected trailers completely intact.  
**Affected Trailers:** `['young_adult_v1']`  
**Affected Segments:** `{'young_adult_v1': ['seg_ya_01', 'seg_ya_02', 'seg_ya_03', 'seg_ya_04']}`  
**Unaffected Trailers (Untouched):** `['family_v1', 'dialect_region_v1']`  
**Unaffected Segments:** `{'family_v1': ['seg_fam_01', 'seg_fam_02', 'seg_fam_03', 'seg_fam_04'], 'young_adult_v1': [], 'dialect_region_v1': ['seg_dia_01', 'seg_dia_02', 'seg_dia_03', 'seg_dia_04']}`  
**Re-planning Justifications:**
- Trailer 'young_adult_v1' references music_restriction 'music_03_synth_pulse' in segments ['seg_ya_01', 'seg_ya_02', 'seg_ya_03', 'seg_ya_04']. Triggered selective replanning.
