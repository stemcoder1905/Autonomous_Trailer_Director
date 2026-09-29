"""Independent multimodal media validator: video duration, frame extraction, and visual claim verification."""
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from src.media.video_processor import VideoProcessor
from src.media.frame_extractor import FrameExtractor
from src.media.audio_processor import AudioProcessor
from src.models.schemas import (
    TrailerSegment,
    ValidationResultItem,
    SceneMetadata,
    DialogueEvidence,
    SegmentSourceEvidence,
)
from src.models.enums import ValidationStatus, Severity, RepairAction, SourceType
from src.utils.logger import logger


from src.providers.vision import VisionProviderManager, VisionClaimVerificationResult
from src.providers.asr import ASRProviderManager, ASRResult


class MediaValidator:
    """Validates physical video file constraints, extracts visual frames, and checks visual ground-truth claims."""

    def __init__(
        self,
        media_dir: Optional[Union[str, Path]] = None,
        media_path: Optional[Union[str, Path]] = None,
        frames_output_dir: Optional[Union[str, Path]] = None,
        mode: str = "REPLAY",
        execution_mode: Optional[str] = None,
        media_source: Optional[str] = None,
        vision_provider_manager: Optional[VisionProviderManager] = None,
        asr_provider_manager: Optional[ASRProviderManager] = None
    ):
        self.media_dir = Path(media_dir or "sample_data/media")
        self.media_path = Path(media_path) if media_path else None
        self.frames_dir = Path(frames_output_dir or "sample_run/frames")
        
        # Explicit separation: execution_mode vs media_source
        self.execution_mode = (execution_mode or mode).lower()
        if self.execution_mode not in ["replay", "live"]:
            self.execution_mode = "live" if "live" in self.execution_mode else "replay"

        if media_source:
            self.media_source = media_source.lower()
        else:
            is_real = (mode.upper() == "REAL_MEDIA") or (media_path and "sample_data" not in str(media_path).lower())
            self.media_source = "real_media" if is_real else "replay_fixture"

        self.mode = "REAL_MEDIA" if self.media_source == "real_media" else "REPLAY"

        # Vision and ASR providers are chosen by EXECUTION_MODE (live vs replay), NEVER accidentally forced into mock by media_source
        is_live_exec = (self.execution_mode == "live")
        self.vision_mgr = vision_provider_manager or VisionProviderManager(
            preferred_provider="live" if is_live_exec else "mock"
        )
        self.asr_mgr = asr_provider_manager or ASRProviderManager(
            preferred_provider="live" if is_live_exec else "mock"
        )

    def validate_segment_media(
        self,
        segment: TrailerSegment,
        scene: Optional[SceneMetadata] = None,
        video_filename: Optional[str] = None
    ) -> List[ValidationResultItem]:
        """Runs physical media verification: duration boundaries, frame evidence, and visual claim audit."""
        results: List[ValidationResultItem] = []
        target_video = self.media_path if self.media_path else (self.media_dir / (video_filename or "episode_01.mp4"))

        # Determine explicit evidence provenance based on media_source
        source_type = SourceType.REAL_MEDIA if self.media_source == "real_media" else SourceType.REPLAY_FIXTURE

        # Check audio stream existence on physical container
        has_audio, audio_status = AudioProcessor.detect_audio_stream(target_video)

        # Convert segment timecodes to exact physical seconds
        from src.utils.timecode import timecode_to_seconds
        t_in = timecode_to_seconds(segment.source_in)
        t_out = timecode_to_seconds(segment.source_out)

        # Update segment dialogue provenance: ground against real ASR if audio stream exists
        if segment.dialogue or segment.dialogue_id:
            asr_res = self.asr_mgr.transcribe(
                audio_or_video_path=target_video,
                start_seconds=t_in,
                end_seconds=t_out,
                reference_dialogue=segment.dialogue,
                source_type=source_type
            )
            dialogue_source_type = SourceType.METADATA if not asr_res.is_asr_output else SourceType.REAL_MEDIA
            if segment.dialogue_evidence is None:
                segment.dialogue_evidence = DialogueEvidence(
                    source=str(target_video),
                    source_type=dialogue_source_type,
                    verification_method=asr_res.verification_method,
                    verified=asr_res.verified if asr_res.is_asr_output else True,
                    metadata_text=segment.dialogue or "",
                    asr_text=asr_res.transcript_text,
                    asr_engine=asr_res.asr_engine,
                    is_asr_output=asr_res.is_asr_output,
                    audio_status=asr_res.audio_status,
                    dialogue_id=segment.dialogue_id,
                    start_time=segment.source_in,
                    end_time=segment.source_out,
                    match=asr_res.metadata_match,
                    match_confidence=asr_res.average_confidence if asr_res.is_asr_output else 0.0
                )
            else:
                segment.dialogue_evidence.source = str(target_video)
                segment.dialogue_evidence.source_type = dialogue_source_type
                segment.dialogue_evidence.verification_method = asr_res.verification_method
                segment.dialogue_evidence.audio_status = asr_res.audio_status
                segment.dialogue_evidence.asr_engine = asr_res.asr_engine
                segment.dialogue_evidence.is_asr_output = asr_res.is_asr_output
                segment.dialogue_evidence.asr_text = asr_res.transcript_text
                segment.dialogue_evidence.start_time = segment.source_in
                segment.dialogue_evidence.end_time = segment.source_out
                segment.dialogue_evidence.match = asr_res.metadata_match
                segment.dialogue_evidence.verified = asr_res.verified if asr_res.is_asr_output else True
                segment.dialogue_evidence.match_confidence = asr_res.average_confidence if asr_res.is_asr_output else 0.0

        # 1. If physical media file exists, enforce physical media boundary mathematics
        if target_video.exists() and VideoProcessor.is_available():
            meta = VideoProcessor.extract_metadata(target_video)

            # Update segment source provenance
            if segment.source is None:
                segment.source = SegmentSourceEvidence(
                    source=str(target_video),
                    source_type=source_type,
                    verification_method="opencv_inspection",
                    verified=meta.is_valid,
                    timestamp=str(t_in),
                    video=target_video.name,
                    scene_id=segment.scene_id
                )
            else:
                segment.source.source = str(target_video)
                segment.source.source_type = source_type
                segment.source.verification_method = "opencv_inspection"
                segment.source.verified = meta.is_valid
                segment.source.timestamp = str(t_in)

            # Check if cut exceeds physical media duration
            if t_out > meta.duration_seconds:
                results.append(
                    ValidationResultItem(
                        validator="media_validator",
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Media duration violation: Cut end time ({t_out:.2f}s) exceeds physical video duration ({meta.duration_seconds:.2f}s) in '{target_video.name}'.",
                        evidence=[
                            f"segment:{segment.segment_id}",
                            f"video:{target_video.name}",
                            f"cut_in:{t_in}",
                            f"cut_out:{t_out}",
                            f"media_duration:{meta.duration_seconds}",
                            f"source_type:{source_type.value}"
                        ],
                        affected_segments=[segment.segment_id],
                        suggested_action=RepairAction.REPLACE_SEGMENT
                    )
                )

            # Extract actual visual frames for evidence
            frame_res = FrameExtractor.extract_scene_frames(
                video_path=target_video,
                scene_id=segment.scene_id,
                start_seconds=t_in,
                end_seconds=t_out,
                output_dir=self.frames_dir
            )
            segment.frame_evidence = frame_res.get("frames_checked", [])

        # 2. Visual Content & Grounding Claim Verification (Requirement #3 & #16)
        if scene:
            claim_result = self.verify_visual_claim(segment, scene)
            if claim_result.get("status") == "REVIEW":
                results.append(
                    ValidationResultItem(
                        validator="source_accuracy_validator",
                        status=ValidationStatus.PASS_WITH_WARNINGS,
                        severity=Severity.MEDIUM,
                        message=f"Visual claim review recommended for segment '{segment.segment_id}': low vision confidence ({claim_result['confidence']:.2f} < 0.75).",
                        evidence=[
                            f"segment:{segment.segment_id}",
                            f"scene:{segment.scene_id}",
                            f"visual_claim:{claim_result['visual_claim']}",
                            f"confidence:{claim_result['confidence']}",
                            f"observation:{claim_result.get('vision_observation')}"
                        ],
                        affected_segments=[segment.segment_id],
                        suggested_action=RepairAction.NONE
                    )
                )
            elif not claim_result["visual_match"]:
                results.append(
                    ValidationResultItem(
                        validator="source_accuracy_validator",
                        status=ValidationStatus.FAIL,
                        severity=Severity.HIGH,
                        message=f"Visual claim mismatch detected in segment '{segment.segment_id}': metadata claims '{claim_result['visual_claim']}', but frame evidence indicates contradictory content.",
                        evidence=[
                            f"segment:{segment.segment_id}",
                            f"scene:{segment.scene_id}",
                            f"visual_claim:{claim_result['visual_claim']}",
                            f"confidence:{claim_result['confidence']}",
                            f"frames:{claim_result['frames_checked']}"
                        ],
                        affected_segments=[segment.segment_id],
                        suggested_action=RepairAction.REPLACE_SEGMENT
                    )
                )

        return results

    def verify_visual_claim(
        self,
        segment: TrailerSegment,
        scene: SceneMetadata
    ) -> Dict[str, Any]:
        """Compares metadata visual descriptions against frame evidence across sampled frames (start, middle, end)."""
        visual_claim = scene.description
        target_video = self.media_path if self.media_path else (self.media_dir / "episode_01.mp4")

        from src.utils.timecode import timecode_to_seconds
        t_in = timecode_to_seconds(segment.source_in)
        t_out = timecode_to_seconds(segment.source_out)

        # 1. Sample at least start, middle, and end frames for the segment cut
        frame_res = FrameExtractor.extract_scene_frames(
            video_path=target_video,
            scene_id=segment.scene_id,
            start_seconds=t_in,
            end_seconds=t_out,
            output_dir=self.frames_dir
        )
        sampled_frames = frame_res.get("frames_checked", [])
        if not sampled_frames:
            sampled_frames = [
                str(self.frames_dir / f"{segment.scene_id}_start.jpg"),
                str(self.frames_dir / f"{segment.scene_id}_middle.jpg"),
                str(self.frames_dir / f"{segment.scene_id}_end.jpg")
            ]

        source_type = SourceType.REAL_MEDIA if self.media_source == "real_media" else SourceType.REPLAY_FIXTURE
        full_claim = f"{visual_claim}. Segment reason: {segment.reason or ''}"

        observations: List[str] = []
        confidences: List[float] = []
        statuses: List[str] = []
        contradicted_any = False

        for f_path in sampled_frames:
            v_res = self.vision_mgr.verify_frame(
                frame_path=f_path,
                claim=full_claim,
                scene_id=segment.scene_id,
                timestamp=segment.source_in,
                expected_characters=scene.characters,
                source_type=source_type
            )
            observations.append(f"{Path(f_path).name}: {v_res.vision_observation}")
            confidences.append(v_res.confidence)
            statuses.append(v_res.status)
            if v_res.contradicted or v_res.status == "FAIL":
                contradicted_any = True

        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 1.0

        if contradicted_any:
            aggregate_status = "FAIL"
            supported = False
        elif avg_confidence < 0.75 or any(s == "REVIEW" for s in statuses):
            aggregate_status = "REVIEW"
            supported = True
        else:
            aggregate_status = "PASS"
            supported = True

        # Store visual evidence structured on segment
        v_evidence_item = {
            "claim": visual_claim,
            "observations": observations,
            "confidence": avg_confidence,
            "supported": supported,
            "source_type": source_type.value,
            "verification_method": self.vision_mgr.last_provenance.get("verification_method", "VISION_MODEL"),
            "verified": (aggregate_status == "PASS" and source_type == SourceType.REAL_MEDIA and self.execution_mode == "live"),
            "status": aggregate_status,
            "sampled_frames": sampled_frames
        }
        segment.visual_evidence.append(v_evidence_item)
        segment.frame_evidence = sampled_frames
        segment.evidence.append(f"vision_aggregate:{aggregate_status}")
        segment.evidence.append(f"vision_confidence:{avg_confidence}")

        return {
            "scene_id": segment.scene_id,
            "visual_claim": visual_claim,
            "frames_checked": sampled_frames,
            "visual_match": (aggregate_status != "FAIL"),
            "status": aggregate_status,
            "confidence": avg_confidence,
            "observations": observations,
            "mismatch_detail": "; ".join(observations) if aggregate_status == "FAIL" else None,
            "source_type": source_type.value,
            "verification_method": self.vision_mgr.last_provenance.get("verification_method", "VISION_MODEL"),
            "verified": v_evidence_item["verified"],
            "vision_observation": "; ".join(observations)
        }
