from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class CardRenderer:
    def __init__(self) -> None:
        template_dir = Path(__file__).parent / 'templates'
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
        template = self.env.get_template('diagnosis_approval.j2')
        return template.render(
            incident_id=incident_id,
            severity=severity,
            service=service,
            diagnosis_summary=diagnosis_summary,
            confidence=confidence,
            proposals=proposals,
        )

    def render_execution_result(self, incident_id: str, results: list[dict]) -> str:
        template = self.env.get_template('execution_result.j2')
        return template.render(incident_id=incident_id, results=results)

    def render_no_action(self, incident_id: str, reason: str) -> str:
        template = self.env.get_template('no_action.j2')
        return template.render(incident_id=incident_id, reason=reason)

    def render_escalate(self, incident_id: str, reason: str) -> str:
        template = self.env.get_template('escalate.j2')
        return template.render(incident_id=incident_id, reason=reason)
