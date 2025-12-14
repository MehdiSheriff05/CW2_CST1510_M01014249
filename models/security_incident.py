# security incident domain model

from __future__ import annotations

from datetime import datetime


class SecurityIncident:
    # represents a cybersecurity incident record

    SEVERITY_POINTS = {"low": 1, "medium": 2, "high": 3, "critical": 4}

    def __init__(self, **kwargs):
        # store the incident values for later use
        self.data = kwargs

    def get_severity_level(self) -> int:
        # map severity labels to numeric values for analytics
        # convert severity text into a number
        severity = (self.data.get("severity") or "").lower()
        return self.SEVERITY_POINTS.get(severity, 0)

    def update_status(self, new_status: str) -> None:
        # update status and resolved date helper
        # set the new status and auto fill resolved date when required
        self.data["status"] = new_status
        if new_status == "resolved" and not self.data.get("resolved_date"):
            self.data["resolved_date"] = datetime.utcnow().date().isoformat()

    def __str__(self) -> str:  # pragma: no cover - debug helper
        # provide an easy to read text snippet during debugging
        incident_id = self.data.get("id", "?")
        severity = self.data.get("severity", "unknown")
        return f"SecurityIncident(id={incident_id}, severity={severity})"
