from __future__ import annotations

# standard libs help with dates, files, typing, and modal fallbacks
from datetime import date, datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

# pandas and plotly power the analytics sections, streamlit renders everything
import pandas as pd
import plotly.express as px
import streamlit as st

# local helpers for incident domain
from models.security_incident import SecurityIncident
from services.database_manager import DatabaseManager
from services.ui_helpers import sidebar_user_box, set_sidebar_visibility

# configure a wide layout since this dashboard has multiple columns
st.set_page_config(layout="wide")
set_sidebar_visibility(st.session_state.get("logged_in", False))


# simple constants for dropdown choices across the page
db_manager = DatabaseManager()
ALLOWED_ROLES = {"cybersec_eng", "admin"}
INCIDENT_TYPES = ["phishing", "malware", "other"]
SEVERITIES = ["low", "medium", "high", "critical"]
STATUSES = ["open", "in_progress", "resolved"]


def guard_page() -> None:
    # block users without matching roles and hide sidebar when redirecting
    if not st.session_state.get("logged_in"):
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
    roles = st.session_state.get("roles", [])
    if "admin" in roles:
        return
    if not any(role in ALLOWED_ROLES for role in roles):
        st.error("You do not have access to the cybersecurity dashboard.")
        st.stop()


def fetch_incidents() -> List[Dict]:
    # read records sorted by most recent first
    return db_manager.fetch_all(
        "SELECT * FROM security_incidents ORDER BY created_date DESC, id DESC"
    )


def insert_incident(payload: Dict) -> None:
    # add a record into the database
    db_manager.execute(
        """
        INSERT INTO security_incidents (
            created_date, incident_type, severity, status,
            description, assigned_to, resolved_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("created_date"),
            payload.get("incident_type"),
            payload.get("severity"),
            payload.get("status"),
            payload.get("description"),
            payload.get("assigned_to"),
            payload.get("resolved_date"),
        ),
    )


def update_incident(incident_id: int, payload: Dict) -> None:
    # update an existing record
    db_manager.execute(
        """
        UPDATE security_incidents
           SET created_date = ?, incident_type = ?, severity = ?, status = ?,
               description = ?, assigned_to = ?, resolved_date = ?
         WHERE id = ?
        """,
        (
            payload.get("created_date"),
            payload.get("incident_type"),
            payload.get("severity"),
            payload.get("status"),
            payload.get("description"),
            payload.get("assigned_to"),
            payload.get("resolved_date"),
            incident_id,
        ),
    )


def delete_incident(incident_id: int) -> None:
    # delete the selected incident
    db_manager.execute("DELETE FROM security_incidents WHERE id = ?", (incident_id,))


def parse_date(date_str: Optional[str]) -> date:
    # safely parse date strings or return today
    if not date_str:
        return date.today()
    try:
        return datetime.fromisoformat(date_str).date()
    except ValueError:
        return date.today()


def load_demo_data() -> None:
    # insert two example incidents for grading
    existing = db_manager.fetch_one("SELECT id FROM security_incidents LIMIT 1")
    if existing:
        st.info("Security incident table already has data.")
        return
    csv_path = Path("demo_data/security_incidents.csv")
    if not csv_path.exists():
        st.error(f"Demo file missing at {csv_path}")
        return
    df = pd.read_csv(csv_path)
    for record in df.where(pd.notnull(df), None).to_dict(orient="records"):
        payload = {
            "created_date": str(record.get("created_date") or date.today().isoformat()),
            "incident_type": record.get("incident_type") or "other",
            "severity": record.get("severity") or "medium",
            "status": record.get("status") or "open",
            "description": record.get("description") or "No description provided.",
            "assigned_to": record.get("assigned_to"),
            "resolved_date": str(record.get("resolved_date")) if record.get("resolved_date") else None,
        }
        insert_incident(payload)
    st.success("Demo incidents loaded from CSV.")


def create_incident_section() -> None:
    # show the creation form with three-column layout
    st.subheader("Create new incident")
    with st.form("create_incident_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            created_date = st.date_input("Created date", value=date.today())
            incident_type = st.selectbox("Incident type", INCIDENT_TYPES)
        with col2:
            severity = st.selectbox("Severity", SEVERITIES)
            status = st.selectbox("Status", STATUSES)
        with col3:
            assigned_to = st.text_input("Assigned to")
            include_resolved = st.checkbox("Include resolved date")

        resolved_date_value = None
        if include_resolved:
            resolved_date_value = st.date_input("Resolved date", value=date.today())

        description = st.text_area("Description")

        if st.form_submit_button("Add incident"):
            insert_incident(
                {
                    "created_date": created_date.isoformat(),
                    "incident_type": incident_type,
                    "severity": severity,
                    "status": status,
                    "description": description,
                    "assigned_to": assigned_to,
                    "resolved_date": resolved_date_value.isoformat()
                    if resolved_date_value
                    else None,
                }
            )
            st.success("Incident added successfully.")
            st.rerun()


def incident_dialog(title: str):
    dialog_fn = getattr(st, "dialog", None)
    if callable(dialog_fn):
        try:
            context = dialog_fn(title)
            if hasattr(context, "__enter__") and hasattr(context, "__exit__"):
                return context
        except TypeError:
            pass

    @contextmanager
    def fallback():
        st.write(f"### {title}")
        yield

    return fallback()


def show_edit_modal() -> None:
    # modal edit UI triggered from the table buttons
    record = st.session_state.get("incident_to_edit")
    if not record:
        return
    with incident_dialog(f"Edit incident #{record['id']}"):
        default_created = parse_date(record.get("created_date"))
        with st.form(f"edit_incident_form_{record['id']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                created_date = st.date_input("Created date", value=default_created, key=f"edit_created_{record['id']}")
                incident_type_value = record.get("incident_type", INCIDENT_TYPES[0])
                incident_type = st.selectbox(
                    "Incident type",
                    INCIDENT_TYPES,
                    index=INCIDENT_TYPES.index(incident_type_value) if incident_type_value in INCIDENT_TYPES else 0,
                    key=f"edit_type_{record['id']}",
                )
            with col2:
                severity_value = record.get("severity", SEVERITIES[0])
                severity = st.selectbox(
                    "Severity",
                    SEVERITIES,
                    index=SEVERITIES.index(severity_value) if severity_value in SEVERITIES else 0,
                    key=f"edit_severity_{record['id']}",
                )
                status_value = record.get("status", STATUSES[0])
                status = st.selectbox(
                    "Status",
                    STATUSES,
                    index=STATUSES.index(status_value) if status_value in STATUSES else 0,
                    key=f"edit_status_{record['id']}",
                )
            with col3:
                assigned_to = st.text_input(
                    "Assigned to",
                    value=record.get("assigned_to", ""),
                    key=f"edit_assigned_{record['id']}",
                )
                has_resolved = st.checkbox(
                    "Has resolved date",
                    value=bool(record.get("resolved_date")),
                    key=f"edit_resolved_toggle_{record['id']}",
                )
                resolved_date_value = None
                if has_resolved:
                    resolved_value = record.get("resolved_date")
                    resolved_date_value = st.date_input(
                        "Resolved date",
                        value=parse_date(resolved_value) if resolved_value else date.today(),
                        key=f"edit_resolved_{record['id']}",
                    )

            description = st.text_area(
                "Description",
                value=record.get("description", ""),
                key=f"edit_description_{record['id']}",
            )
            submitted = st.form_submit_button("Update incident")

        if submitted:
            payload = {
                "created_date": created_date.isoformat(),
                "incident_type": incident_type,
                "severity": severity,
                "status": status,
                "description": description,
                "assigned_to": assigned_to,
                "resolved_date": resolved_date_value.isoformat() if isinstance(resolved_date_value, date) else None,
            }
            update_incident(record["id"], payload)
            st.success("Incident updated.")
            st.session_state["incident_to_edit"] = None
            st.rerun()
        if st.button("Close edit", key=f"close_edit_{record['id']}"):
            st.session_state["incident_to_edit"] = None


def show_delete_modal() -> None:
    record = st.session_state.get("incident_to_delete")
    if not record:
        return
    with incident_dialog(f"Delete incident #{record['id']}?"):
        st.warning(
            "Deleting an incident removes it permanently from this dashboard.",
            icon="⚠️",
        )
        if st.button("Confirm delete", type="primary", key=f"confirm_delete_{record['id']}"):
            delete_incident(record["id"])
            st.success("Incident deleted.")
            st.session_state["incident_to_delete"] = None
            st.rerun()
        if st.button("Cancel", key=f"cancel_delete_{record['id']}"):
            st.session_state["incident_to_delete"] = None


def incidents_table_section(incidents: List[Dict]) -> None:
    # render main table of incidents
    st.subheader("Current incidents")
    if not incidents:
        st.info("No incident data to display yet.")
        return
    df_view = pd.DataFrame(incidents)[
        ["id", "created_date", "incident_type", "severity", "status", "assigned_to"]
    ].rename(
        columns={
            "id": "ID",
            "created_date": "Created",
            "incident_type": "Type",
            "severity": "Severity",
            "status": "Status",
            "assigned_to": "Assigned",
        }
    )
    st.dataframe(df_view, width="stretch")
    st.caption("Sort or filter the table above, then trigger quick actions below.")
    st.write("**Row actions**")
    for row in incidents:
        cols = st.columns([5, 2, 2])
        cols[0].write(f"#{row['id']} - {row.get('incident_type')} ({row.get('status')})")
        cols[1].write(row.get("assigned_to") or "Unassigned")
        action_cols = cols[2].columns(2)
        if action_cols[0].button("Edit", key=f"edit_incident_{row['id']}"):
            st.session_state["incident_to_edit"] = row
        if action_cols[1].button("Delete", key=f"delete_incident_{row['id']}"):
            st.session_state["incident_to_delete"] = row

    highest_level = max((SecurityIncident(**row).get_severity_level() for row in incidents), default=0)
    st.caption(f"Highest severity level score recorded: {highest_level}")


def prepare_dataframe(incidents: List[Dict]) -> pd.DataFrame:
    # convert records into a dataframe with derived values
    df = pd.DataFrame(incidents)
    if df.empty:
        return df
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["resolved_date"] = pd.to_datetime(df["resolved_date"], errors="coerce")
    df["resolution_days"] = (df["resolved_date"] - df["created_date"]).dt.days
    return df


def analytics_section(incidents: List[Dict]):
    # build the plotly figures
    df = prepare_dataframe(incidents)
    if df.empty:
        st.info("Add incidents to view analytics.")
        return df, None, None

    weekly = (
        df.groupby(pd.Grouper(key="created_date", freq="W"))
        .size()
        .reset_index(name="incident_count")
    )
    fig_weekly = px.line(
        weekly,
        x="created_date",
        y="incident_count",
        title="Incidents logged per week",
        labels={"created_date": "Week", "incident_count": "Incidents"},
    )

    resolved = df.dropna(subset=["resolution_days"])
    if not resolved.empty:
        severity_resolution = (
            resolved.groupby("severity")["resolution_days"]
            .mean()
            .reset_index(name="avg_resolution_days")
        )
        fig_resolution = px.bar(
            severity_resolution,
            x="severity",
            y="avg_resolution_days",
            title="Average resolution days by severity",
            labels={"severity": "Severity", "avg_resolution_days": "Avg days"},
            color="severity",
        )
    else:
        fig_resolution = None
        st.info("Resolution timing data will appear after incidents are closed.")
    return df, fig_weekly, fig_resolution


def insights_section(df: pd.DataFrame) -> None:
    # write short text guidance based on metrics
    if df.empty:
        return
    open_incidents = int((df["status"] == "open").sum())
    avg_resolution = df["resolution_days"].dropna()
    avg_resolution_value = round(avg_resolution.mean(), 1) if not avg_resolution.empty else "N/A"
    severity_counts = df["severity"].value_counts()
    severe_focus = severity_counts.idxmax() if not severity_counts.empty else "n/a"

    st.subheader("Insights and recommendations")
    st.write(
        f"There are {open_incidents} open incidents. Focus on '{severe_focus}' severity cases first "
        f"and aim for an average closure time below {avg_resolution_value} days. "
        "Review the weekly volume chart to plan analyst capacity."
    )


def main() -> None:
    guard_page()
    sidebar_user_box("cyber")
    st.title("Incident Reporting")

    st.write("Track, update, and monitor incident response tasks.")

    if st.button("Load demo data"):
        load_demo_data()
        st.rerun()

    incidents = fetch_incidents()
    incidents_table_section(incidents)
    show_edit_modal()
    show_delete_modal()

    df, line_fig, bar_fig = analytics_section(incidents)
    if line_fig or bar_fig:
        st.subheader("Analytics and charts")
        chart_cols = st.columns(2)
        if line_fig:
            chart_cols[0].plotly_chart(line_fig, width="stretch")
        if bar_fig:
            chart_cols[1].plotly_chart(bar_fig, width="stretch")
    if not df.empty:
        insights_section(df)

    create_incident_section()


if __name__ == "__main__":
    main()
