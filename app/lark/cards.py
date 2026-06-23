from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class CardRenderer:
    def __init__(self) -> None:
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def render_diagnosis_approval(
        self,
        incident_id: str,
        severity: str,
        service: str,
        diagnosis_summary: str,
        confidence: float,
        proposals: list[dict],
    ) -> str:
        template = self.env.get_template("diagnosis_approval.j2")
        return template.render(
            incident_id=incident_id,
            severity=severity,
            service=service,
            diagnosis_summary=diagnosis_summary,
            confidence=confidence,
            proposals=proposals,
        )

    def render_diagnosis_confirm(
        self,
        incident_id: str,
        severity: str,
        category: str,
        service: str,
        diagnosis: str,
        confidence: float,
        evidence_text: str = "",
    ) -> str:
        severity_colors = {"p0": "red", "p1": "orange", "p2": "yellow", "p3": "green"}
        template = self.env.get_template("diagnosis_confirm.j2")
        return template.render(
            incident_id=incident_id,
            severity=severity,
            severity_color=severity_colors.get(severity, "blue"),
            category=category,
            service=service,
            diagnosis=diagnosis,
            confidence=confidence * 100,
            evidence_text=evidence_text,
        )

    def render_proposal_confirm(
        self,
        incident_id: str,
        severity: str,
        category: str,
        diagnosis: str,
        confidence: float,
        proposal_text: str,
        high_risk_text: str = "",
    ) -> str:
        severity_colors = {"p0": "red", "p1": "orange", "p2": "yellow", "p3": "green"}
        template = self.env.get_template("proposal_confirm.j2")
        return template.render(
            incident_id=incident_id,
            severity=severity,
            severity_color=severity_colors.get(severity, "blue"),
            category=category,
            diagnosis=diagnosis,
            confidence=confidence * 100,
            proposal_text=proposal_text,
            high_risk_text=high_risk_text,
        )

    def render_execution_result(self, incident_id: str, results: list[dict]) -> str:
        template = self.env.get_template("execution_result.j2")
        return template.render(incident_id=incident_id, results=results)

    def render_no_action(self, incident_id: str, reason: str) -> str:
        template = self.env.get_template("no_action.j2")
        return template.render(incident_id=incident_id, reason=reason)

    def render_escalate(self, incident_id: str, reason: str) -> str:
        template = self.env.get_template("escalate.j2")
        return template.render(incident_id=incident_id, reason=reason)
