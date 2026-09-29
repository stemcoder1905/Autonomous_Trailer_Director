"""Graph-based workflow engine for Autonomous Trailer Director."""
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.state import DirectorState
from src.models.enums import AudienceType, ValidationStatus, ConstraintStatus
from src.models.schemas import EpisodePackage, ConstraintRule
from src.ingestion.episode_loader import EpisodePackageLoader
from src.agents.story_agent import StoryUnderstandingAgent
from src.agents.constraint_agent import ConstraintAnalysisAgent
from src.agents.audience_agent import AudienceStrategyAgent
from src.agents.planner_agent import CreativeTrailerPlannerAgent
from src.agents.validator_agent import IndependentValidationAgent
from src.agents.repair_agent import RepairAgent
from src.agents.impact_agent import ChangeImpactAgent
from src.providers.llm import ProviderManager
from src.utils.logger import logger, DecisionLogger


class TrailerDirectorWorkflow:
    """State graph orchestrating the multi-agent lifecycle from ingestion to repair."""

    def __init__(
        self,
        base_dir: Path,
        provider_manager: Optional[ProviderManager] = None,
        decision_logger: Optional[DecisionLogger] = None,
        reference_date: Optional[str] = "2026-04-15",
        media_path: Optional[Path] = None,
        media_mode: str = "REPLAY"
    ):
        self.base_dir = Path(base_dir)
        self.decision_logger = decision_logger or DecisionLogger()
        self.provider_manager = provider_manager or ProviderManager()
        self.reference_date = reference_date
        self.media_path = media_path
        self.media_mode = media_mode

        # Instantiate specialized agents
        from src.media.media_validator import MediaValidator
        self.media_validator = MediaValidator(media_path=self.media_path, mode=self.media_mode)
        self.loader = EpisodePackageLoader(self.base_dir)
        self.story_agent = StoryUnderstandingAgent(self.decision_logger)
        self.constraint_agent = ConstraintAnalysisAgent(self.decision_logger)
        self.audience_agent = AudienceStrategyAgent(self.decision_logger)
        self.planner_agent = CreativeTrailerPlannerAgent(self.provider_manager, self.decision_logger)
        self.validator_agent = IndependentValidationAgent(
            reference_date=self.reference_date,
            decision_logger=self.decision_logger,
            media_validator=self.media_validator
        )
        self.repair_agent = RepairAgent(self.validator_agent, self.decision_logger)
        self.impact_agent = ChangeImpactAgent(self.validator_agent, self.repair_agent, self.decision_logger)

    def run(
        self,
        selected_audiences: Optional[List[AudienceType]] = None,
        scenario: Optional[str] = None
    ) -> DirectorState:
        """Execute the end-to-end multi-agent graph workflow."""
        state = DirectorState(active_scenario=scenario)
        audiences = selected_audiences or [
            AudienceType.FAMILY,
            AudienceType.YOUNG_ADULT,
            AudienceType.DIALECT_REGION,
        ]

        logger.info(f"=== Starting Trailer Director Workflow (Scenario: {scenario or 'NORMAL'}) ===")

        # Node 1: INGESTION
        state.current_node = "INGESTION"
        state.execution_history.append("INGESTION")
        state.episode_package = self.loader.load_package()

        # Node 2: STORY_ANALYSIS
        state.current_node = "STORY_ANALYSIS"
        state.execution_history.append("STORY_ANALYSIS")
        state.story_map = self.story_agent.analyze_story(state.episode_package)
        state.spoiler_map = self.story_agent.generate_spoiler_map(state.story_map)

        # Node 3: CONSTRAINT_ANALYSIS
        state.current_node = "CONSTRAINT_ANALYSIS"
        state.execution_history.append("CONSTRAINT_ANALYSIS")
        state.constraint_map = self.constraint_agent.analyze_constraints(
            state.episode_package, reference_date=self.reference_date
        )

        # Node 4: AUDIENCE_STRATEGY & CREATIVE_PLANNING
        state.current_node = "CREATIVE_PLANNING"
        state.execution_history.append("CREATIVE_PLANNING")
        for aud in audiences:
            brief = self.audience_agent.create_strategy(
                aud, state.episode_package, state.story_map, state.constraint_map
            )
            plan = self.planner_agent.plan_trailer(
                brief,
                state.episode_package,
                state.story_map,
                state.constraint_map,
                adversarial_scenario=scenario
            )
            state.trailer_plans[aud.value] = plan

        # Node 5: INDEPENDENT_VALIDATION
        state.current_node = "INDEPENDENT_VALIDATION"
        state.execution_history.append("INDEPENDENT_VALIDATION")
        for aud_key, plan in state.trailer_plans.items():
            report = self.validator_agent.validate_plan(
                plan, state.episode_package, state.story_map, state.constraint_map
            )
            state.validation_reports[aud_key] = report

        # Node 6: CONDITIONAL REPAIR / REJECTION
        state.current_node = "REPAIR_OR_REJECT"
        state.execution_history.append("REPAIR_OR_REJECT")
        for aud_key, plan in list(state.trailer_plans.items()):
            if plan.validation.status == ValidationStatus.FAIL:
                logger.info(f"[Workflow] Trailer '{aud_key}' failed initial validation. Invoking RepairAgent.")
                repaired_plan, pass_ok = self.repair_agent.attempt_repair(
                    plan, state.episode_package, state.story_map, state.constraint_map
                )
                state.trailer_plans[aud_key] = repaired_plan
                state.validation_reports[aud_key] = repaired_plan.validation

        # Node 7: FINALIZE
        state.current_node = "COMPLETED"
        state.execution_history.append("COMPLETED")
        state.total_cost_usd = round(sum(p.estimated_cost for p in state.trailer_plans.values()), 3)
        logger.info(f"=== Workflow Execution Completed. Total Trailers: {len(state.trailer_plans)} ===")

        return state

    def trigger_contract_modification(
        self,
        state: DirectorState,
        changed_rule: ConstraintRule
    ) -> DirectorState:
        """Selectively replans only affected trailers and segments when a contract rule changes."""
        logger.info(f"=== Triggering Selective Replanning for changed rule '{changed_rule.rule_id}' ===")
        # Update rule in state constraint_map
        updated_rules = []
        for r in state.constraint_map.rules:
            if r.rule_id == changed_rule.rule_id:
                updated_rules.append(changed_rule)
            else:
                updated_rules.append(r)
        state.constraint_map.rules = updated_rules

        # Run impact agent
        impact_report = self.impact_agent.analyze_and_replan(
            list(state.trailer_plans.values()),
            changed_rule,
            state.constraint_map,
            state.episode_package,
            state.story_map
        )
        state.change_impact_reports.append(impact_report)
        return state
