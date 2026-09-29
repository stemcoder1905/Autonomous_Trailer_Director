"""Constraint Analysis Agent for translating contracts and policies into executable rules."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.models.schemas import (
    EpisodePackage,
    ConstraintMap,
    ConstraintRule,
    ConstraintType,
    ConstraintStatus,
)
from src.utils.logger import logger, DecisionLogger


class ConstraintAnalysisAgent:
    """Parses, verifies, and indexes contractual, rating, accessibility, and budgetary constraints."""

    def __init__(self, decision_logger: Optional[DecisionLogger] = None):
        self.decision_logger = decision_logger

    def analyze_constraints(
        self,
        package: EpisodePackage,
        reference_date: Optional[str] = "2026-04-15"
    ) -> ConstraintMap:
        """Compile contracts and policies into an authoritative, executable ConstraintMap."""
        logger.info(f"[ConstraintAgent] Compiling constraint rules for '{package.episode_id}'")

        compiled_rules: List[ConstraintRule] = []
        for contract in package.contracts:
            rule = contract.model_copy()
            # Evaluate expiry dynamically if expiry_date is provided
            if rule.expiry_date and reference_date:
                if reference_date > rule.expiry_date:
                    rule.status = ConstraintStatus.EXPIRED
                    logger.warning(
                        f"[ConstraintAgent] Rule '{rule.rule_id}' ({rule.scope}) is EXPIRED "
                        f"(expiry: {rule.expiry_date}, ref_date: {reference_date})"
                    )
                else:
                    rule.status = ConstraintStatus.ACTIVE
            compiled_rules.append(rule)

        rating_rules = package.policies.get("rating_guidelines", {})
        accessibility_reqs = package.policies.get("accessibility_standards", {})
        budget_limit = package.cost_sheet.max_total_budget_usd

        constraint_map = ConstraintMap(
            episode_id=package.episode_id,
            rules=compiled_rules,
            rating_rules=rating_rules,
            budget_limit_usd=budget_limit,
            accessibility_requirements=accessibility_reqs
        )

        if self.decision_logger:
            self.decision_logger.log_decision(
                agent="ConstraintAnalysisAgent",
                action="COMPILE_CONSTRAINTS",
                reason=f"Compiled {len(compiled_rules)} operational rules for {package.episode_id}",
                input_evidence=[f"contract_count:{len(package.contracts)}", f"ref_date:{reference_date}"],
                selected_decision={"rules_count": len(compiled_rules), "budget_usd": budget_limit},
                risk="LOW"
            )

        return constraint_map
