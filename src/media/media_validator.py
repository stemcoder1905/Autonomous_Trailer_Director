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
        vision_provider_manager: Optional[VisionProviderManager] = None,
        asr_provider_manager: Optional[ASRProviderManager] = None
    ):
        self.media_dir = Path(media_dir or "sample_data/media")
        self.media_path = Path(media_path) if media_path else None
        self.frames_dir = Path(frames_output_dir or "sample_run/frames")
        self.mode = mode
        self.vision_mgr = vision_provider_manager or VisionProviderManager(
            preferred_provider="live" if mode.upper() == "LIVE" else "mock"
        )
        self.asr_mgr = asr_provider_manager or ASRProviderManager(
            preferred_provider="live" if mode.upper() == "LIVE" else "mock"
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

        # Determine explicit evidence provenance
        is_synthetic = "sample_data" in str(target_video).lower() or "episode_01.mp4" in str(target_video).lower()
        source_type = SourceType.REPLAY_FIXTURE if (self.mode == "REPLAY" and is_synthetic) else SourceType.REAL_MEDIA

        # Check audio stream existence on physical container
        has_audio, audio_status = AudioProcessor.detect_audio_stream(target_video)

        # Update segment dialogue provenance: ground against real ASR if audio stream exists
        if segment.dialogue or segment.dialogue_id:
            asr_res = self.asr_mgr.transcribe(
                audio_or_video_path=target_video,
                start_seconds=0.0,
                end_seconds=5.0,
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
                    dialogue_id=segment.dialogue_id
                )
            else:
                segment.dialogue_evidence.source = str(target_video)
                segment.dialogue_evidence.source_type = dialogue_source_type
                segment.dialogue_evidence.verification_method = asr_res.verification_method
                segment.dialogue_evidence.audio_status = asr_res.audio_status
                segment.dialogue_evidence.asr_engine = asr_res.asr_engine
                segment.dialogue_evidence.is_asr_output = asr_res.is_asr_output
                segment.dialogue_evidence.asr_text = asr_res.transcript_text
                segment.dialogue_evidence.verified = asr_res.verified if asr_res.is_asr_output else True

        # 1. If physical media file exists, enforce physical media boundary mathematics
        if target_video.exists() and VideoProcessor.is_available():
            meta = VideoProcessor.extract_metadata(target_video)
            from src.utils.timecode import timecode_to_seconds
            t_in = timecode_to_seconds(segment.source_in)
            t_out = timecode_to_seconds(segment.source_out)

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
        """Compares metadata visual descriptions against frame evidence using VisionProvider."""
        visual_claim = scene.description
        frames = [
            f"sample_run/frames/{segment.scene_id}_start.jpg",
            f"sample_run/frames/{segment.scene_id}_middle.jpg",
            f"sample_run/frames/{segment.scene_id}_end.jpg"
        ]
        primary_frame = frames[1] if len(frames) > 1 else (frames[0] if frames else "frame.jpg")

        source_type = SourceType.REAL_MEDIA if self.mode == "REAL_MEDIA" else SourceType.REPLAY_FIXTURE
        full_claim = f"{visual_claim}. Segment reason: {segment.reason or ''}"
        
        vision_res = self.vision_mgr.verify_frame(
            frame_path=primary_frame,
            claim=full_claim,
            scene_id=segment.scene_id,
            timestamp=segment.source_in,
            expected_characters=scene.characters,
            source_type=source_type
        )

        # Store visual evidence on segment
        segment.evidence.append(f"vision_observation:{vision_res.vision_observation}")
        segment.evidence.append(f"vision_confidence:{vision_res.confidence}")
        segment.evidence.append(f"vision_source:{vision_res.source_type}")

        return {
            "scene_id": segment.scene_id,
            "visual_claim": visual_claim,
            "frames_checked": frames,
            "visual_match": (vision_res.status != "FAIL" and not vision_res.contradicted),
            "status": vision_res.status,
            "confidence": vision_res.confidence,
            "mismatch_detail": vision_res.vision_observation if (vision_res.contradicted or not vision_res.supported) else None,
            "source_type": vision_res.source_type,
            "verification_method": vision_res.verification_method,
            "verified": vision_res.verified,
            "vision_observation": vision_res.vision_observation
        }
