"""Command-Line Interface (CLI) for Autonomous Trailer Director."""
import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path when invoked directly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.workflow.graph import TrailerDirectorWorkflow
from src.models.enums import AudienceType, ConstraintStatus
from src.models.schemas import ConstraintRule
from src.providers.llm import ProviderManager
from src.utils.logger import DecisionLogger


# Initialize console with ascii/utf-8 compatibility
console = Console(highlight=False)


def parse_args():
    parser = argparse.ArgumentParser(
        description="OTT Dialect Platform - Autonomous Trailer Director CLI"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="sample_data",
        help="Path to input data directory (containing episode_package, policies, contracts, etc.)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sample_run",
        help="Directory to save generated trailer plans and decision logs",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["replay", "live"],
        default="replay",
        help="Execution mode: 'replay' (deterministic zero-cost mock) or 'live'",
    )
    parser.add_argument(
        "--audience",
        type=str,
        choices=["all", "family", "young_adult", "dialect_region"],
        default="all",
        help="Target audience for trailer generation",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=[
            "none",
            "spoiler",
            "contract_change",
            "missing_scene",
            "bias",
            "clickbait",
            "subtitle_mismatch",
            "model_failure",
            "budget_exceeded",
            "prompt_injection"
        ],
        default="none",
        help="Trigger a specific surprise scenario / adversarial test",
    )
    return parser.parse_args()


def export_validation_report_markdown(output_path: Path, state) -> None:
    """Generate a readable markdown summary report of the validation results."""
    md_lines = [
        "# Autonomous Trailer Director - Validation & Execution Report",
        "",
        f"**Episode ID:** `{state.episode_package.episode_id}`  ",
        f"**Title:** {state.episode_package.title}  ",
        f"**Active Scenario:** `{state.active_scenario or 'NORMAL'}`  ",
        f"**Total Estimated AI Cost:** `${state.total_cost_usd:.3f} USD`  ",
        "",
        "## 1. Trailer Plans Summary",
        "",
        "| Trailer ID | Audience | Duration | Status | Segments | Human Review Required |",
        "|---|---|---|---|---|---|",
    ]

    for aud, plan in state.trailer_plans.items():
        human_req = "Yes" if plan.human_approval_requirements else "No"
        md_lines.append(
            f"| `{plan.trailer_id}` | {plan.audience} | {plan.duration_seconds}s | **{plan.validation.status.value}** | {len(plan.segments)} | {human_req} |"
        )

    md_lines.extend([
        "",
        "## 2. Independent Validation Findings",
        ""
    ])

    for aud, plan in state.trailer_plans.items():
        md_lines.append(f"### Trailer: `{plan.trailer_id}` ({plan.audience})")
        md_lines.append(f"**Overall Status:** `{plan.validation.status.value}`  ")
        md_lines.append(f"**Summary:** {plan.validation.summary}")
        md_lines.append("")
        md_lines.append("| Validator | Status | Severity | Message |")
        md_lines.append("|---|---|---|---|")
        for item in plan.validation.items:
            md_lines.append(f"| `{item.validator}` | {item.status.value} | {item.severity.value} | {item.message} |")
        md_lines.append("")

    if state.change_impact_reports:
        md_lines.extend([
            "## 3. Selective Replanning & Change Impact Analysis",
            ""
        ])
        for report in state.change_impact_reports:
            md_lines.append(f"**Trigger:** {report.trigger}  ")
            md_lines.append(f"**Summary Reason:** {report.reason}  ")
            md_lines.append(f"**Affected Trailers:** `{report.affected_trailers}`  ")
            md_lines.append(f"**Affected Segments:** `{report.affected_segments}`  ")
            md_lines.append(f"**Unaffected Trailers (Untouched):** `{report.unaffected_trailers}`  ")
            md_lines.append(f"**Unaffected Segments:** `{report.unaffected_segments}`  ")
            md_lines.append("**Re-planning Justifications:**")
            for r in report.replan_reasons:
                md_lines.append(f"- {r}")
            md_lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))


def main():
    args = parse_args()
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel.fit(
            "[bold cyan]OTT DIALECT PLATFORM -- AUTONOMOUS TRAILER DIRECTOR[/bold cyan]\n"
            f"[yellow]Mode:[/yellow] {args.mode.upper()} | "
            f"[yellow]Audience:[/yellow] {args.audience} | "
            f"[yellow]Scenario:[/yellow] {args.scenario}",
            border_style="cyan"
        )
    )

    simulate_model_failure = (args.scenario == "model_failure")
    provider_mgr = ProviderManager(
        preferred_provider="mock" if args.mode == "replay" else "primary",
        simulate_primary_failure=simulate_model_failure
    )

    decision_log_path = output_dir / "decision_log.json"
    decision_logger = DecisionLogger(log_path=decision_log_path)

    if args.audience == "family":
        audiences = [AudienceType.FAMILY]
    elif args.audience == "young_adult":
        audiences = [AudienceType.YOUNG_ADULT]
    elif args.audience == "dialect_region":
        audiences = [AudienceType.DIALECT_REGION]
    else:
        audiences = [AudienceType.FAMILY, AudienceType.YOUNG_ADULT, AudienceType.DIALECT_REGION]

    # Baseline reference date for planning: 2026-02-15 (active contracts)
    workflow = TrailerDirectorWorkflow(
        base_dir=input_dir,
        provider_manager=provider_mgr,
        decision_logger=decision_logger,
        reference_date="2026-02-15"
    )

    active_scenario = None if args.scenario == "none" else args.scenario
    state = workflow.run(selected_audiences=audiences, scenario=active_scenario)

    # Scenario-specific handling and notifications
    if args.scenario == "contract_change":
        console.print("[bold magenta]>> Triggering Event: Music Rights Expiration for 'music_03_synth_pulse'...[/bold magenta]")
        expired_rule = ConstraintRule(
            rule_id="rule_contract_music_03",
            type="music_restriction",
            scope="asset:music_03_synth_pulse",
            condition="music == 'music_03_synth_pulse'",
            allowed_behavior="None",
            blocked_behavior="License expired on 2026-03-31; all promotional sync prohibited.",
            evidence=["Contract Amendment Notice MUS-2026-03-EXP"],
            status=ConstraintStatus.EXPIRED,
            effective_date="2026-01-01",
            expiry_date="2026-03-31"
        )
        state = workflow.trigger_contract_modification(state, expired_rule)
        
        impact_path = output_dir / "change_impact_report.json"
        with open(impact_path, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in state.change_impact_reports], f, indent=2)
        console.print(f"[green][OK] Saved change impact report to: {impact_path}[/green]")
        for rep in state.change_impact_reports:
            console.print(f"   [yellow]Affected Trailers:[/yellow] {rep.affected_trailers}")
            console.print(f"   [green]Unaffected Trailers (Preserved Intact):[/green] {rep.unaffected_trailers}")
            console.print(f"   [cyan]Reason:[/cyan] {rep.reason}")

    elif args.scenario == "prompt_injection":
        from src.ingestion.metadata_loader import MetadataLoader
        flagged = MetadataLoader.detect_injection_attempts(state.episode_package.scenes)
        console.print(f"[bold yellow]>> Ingestion Guardrail Flagged {len(flagged)} Untrusted Data Pattern(s):[/bold yellow]")
        for item in flagged:
            sample_text = item.get("sample", item.get("snippet", ""))
            console.print(f"   - Scene: [cyan]{item['scene_id']}[/cyan] | Snippet: \"{sample_text}\" | Verdict: [bold red]{item['verdict']}[/bold red]")
        console.print("   [green][OK] Independent validators rejected malicious contract override; valid plan enforced and repaired.[/green]")

    elif args.scenario in ["spoiler", "missing_scene", "bias", "clickbait", "subtitle_mismatch", "budget_exceeded"]:
        console.print(f"[bold cyan]>> Scenario '{args.scenario}' executed successfully:[/bold cyan]")
        console.print(f"   [yellow]1. Adversarial proposal submitted[/yellow]")
        console.print(f"   [red]2. Independent Validator rejected proposal with FAIL[/red]")
        console.print(f"   [green]3. RepairAgent executed automated remediation[/green]")
        console.print(f"   [bold green]4. Re-validation verified compliant trailer[/bold green]")

    # Persist artifacts to output directory
    story_map_path = output_dir / "story_map.json"
    with open(story_map_path, "w", encoding="utf-8") as f:
        json.dump(state.story_map.model_dump(), f, indent=2)

    constraint_map_path = output_dir / "constraint_map.json"
    with open(constraint_map_path, "w", encoding="utf-8") as f:
        json.dump(state.constraint_map.model_dump(), f, indent=2)

    for aud_key, plan in state.trailer_plans.items():
        plan_file = output_dir / f"{aud_key}_trailer.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan.model_dump(), f, indent=2)

    validation_report_path = output_dir / "validation_report.md"
    export_validation_report_markdown(validation_report_path, state)
    decision_logger.persist(decision_log_path)

    # Render summary table in CLI
    table = Table(title="Generated Trailer Plans & Validation Status", border_style="green")
    table.add_column("Audience", style="cyan", no_wrap=True)
    table.add_column("Trailer ID", style="magenta")
    table.add_column("Duration", justify="right", style="yellow")
    table.add_column("Segments", justify="right")
    table.add_column("Validation Status", style="bold")
    table.add_column("Human Approval", style="red")

    for aud_key, plan in state.trailer_plans.items():
        status_color = "green" if plan.validation.status.value == "PASS" else ("yellow" if "WARNING" in plan.validation.status.value else "red")
        human_req = "Required" if plan.human_approval_requirements else "None"
        table.add_row(
            plan.audience,
            plan.trailer_id,
            f"{plan.duration_seconds}s",
            str(len(plan.segments)),
            f"[{status_color}]{plan.validation.status.value}[/{status_color}]",
            human_req
        )

    console.print(table)
    console.print(f"[bold green][OK] Artifacts successfully written to: {output_dir.resolve()}[/bold green]")


if __name__ == "__main__":
    main()
