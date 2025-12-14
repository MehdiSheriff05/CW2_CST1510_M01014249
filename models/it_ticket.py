# IT ticket domain model

from __future__ import annotations

from datetime import datetime


class ITTicket:
    # represents an IT service desk ticket

    def __init__(self, **kwargs):
        # keep ticket data stored in a dictionary
        self.data = kwargs

    def assign_to(self, staff_name: str) -> None:
        # update the technician name
        self.data["assigned_staff"] = staff_name

    def close_ticket(self) -> None:
        # close the ticket and record the time
        self.data["status"] = "resolved"
        self.data["resolved_date"] = datetime.utcnow().date().isoformat()

    def __str__(self) -> str:  # pragma: no cover - debug helper
        # show an easy to read ticket summary
        return f"ITTicket(id={self.data.get('id')}, status={self.data.get('status')})"
