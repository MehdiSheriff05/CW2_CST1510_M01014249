from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from services.auth_manager import AuthManager
from services.database_manager import DatabaseManager
from services.ui_helpers import sidebar_user_box, set_sidebar_visibility

st.set_page_config(layout="wide")
set_sidebar_visibility(st.session_state.get("logged_in", False))


db_manager = DatabaseManager()
auth_manager = AuthManager()
ALLOWED_ROLES = {"it_ops", "admin"}
CATEGORIES = ["Hardware", "Software", "Network", "Access"]
PRIORITIES = ["low", "medium", "high"]
STATUSES = ["new", "in_progress", "waiting_user", "resolved"]
STATUS_LABELS = {
    "new": "New",
    "in_progress": "In Progress",
    "waiting_user": "Waiting on User",
    "resolved": "Resolved",
}
PRIORITY_COLORS = {"high": "#dc2626", "medium": "#f97316", "low": "#facc15"}


def guard_page() -> None:
    if not st.session_state.get("logged_in"):
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
    roles = st.session_state.get("roles", [])
    if "admin" in roles:
        return
    if not any(role in ALLOWED_ROLES for role in roles):
        st.error("You do not have access to the IT ticketing dashboard.")
        st.stop()


def get_technicians() -> List[str]:
    # gather usernames that hold the it_ops role
    users = auth_manager.get_all_users()
    return [row["username"] for row in users if "it_ops" in row.get("roles", [])]


def fetch_tickets() -> List[Dict]:
    return db_manager.fetch_all("SELECT * FROM it_tickets ORDER BY opened_date DESC, id DESC")


def insert_ticket(payload: Dict) -> None:
    db_manager.execute(
        """
        INSERT INTO it_tickets (
            opened_date, category, priority, status,
            assigned_staff, description, resolved_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("opened_date"),
            payload.get("category"),
            payload.get("priority"),
            payload.get("status"),
            payload.get("assigned_staff"),
            payload.get("description"),
            payload.get("resolved_date"),
        ),
    )


def update_ticket(ticket_id: int, payload: Dict) -> None:
    db_manager.execute(
        """
        UPDATE it_tickets
           SET opened_date = ?, category = ?, priority = ?, status = ?,
               assigned_staff = ?, description = ?, resolved_date = ?
         WHERE id = ?
        """,
        (
            payload.get("opened_date"),
            payload.get("category"),
            payload.get("priority"),
            payload.get("status"),
            payload.get("assigned_staff"),
            payload.get("description"),
            payload.get("resolved_date"),
            ticket_id,
        ),
    )


def delete_ticket(ticket_id: int) -> None:
    db_manager.execute("DELETE FROM it_tickets WHERE id = ?", (ticket_id,))


def safe_date(value: Optional[str]) -> date:
    try:
        return date.fromisoformat(value) if value else date.today()
    except ValueError:
        return date.today()


def load_demo_data() -> None:
    existing = db_manager.fetch_one("SELECT id FROM it_tickets LIMIT 1")
    if existing:
        st.info("Tickets table already has data.")
        return
    csv_path = Path("demo_data/it_tickets.csv")
    if not csv_path.exists():
        st.error(f"Demo file missing at {csv_path}")
        return
    df = pd.read_csv(csv_path)
    for record in df.where(pd.notnull(df), None).to_dict(orient="records"):
        payload = {
            "opened_date": str(record.get("opened_date") or date.today().isoformat()),
            "category": record.get("category") or "Hardware",
            "priority": record.get("priority") or "low",
            "status": record.get("status") or "new",
            "assigned_staff": record.get("assigned_staff"),
            "description": record.get("description") or "No description provided.",
            "resolved_date": str(record.get("resolved_date")) if record.get("resolved_date") else None,
        }
        insert_ticket(payload)
    st.success("Demo tickets loaded from CSV.")


def create_ticket_section() -> None:
    st.subheader("Log ticket")
    technicians = get_technicians()
    with st.form("create_ticket_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            opened_date = st.date_input("Opened date", value=date.today())
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            priority = st.selectbox("Priority", PRIORITIES)
            status = st.selectbox("Status", STATUSES)
        with col3:
            assigned = st.selectbox(
                "Assigned Technician",
                ["Unassigned"] + technicians,
            )
            resolved_date_value = (
                st.date_input("Resolved date", value=date.today())
                if status == "resolved"
                else None
            )
        description = st.text_area("Ticket title / description")
        submitted = st.form_submit_button("Add ticket")
    if submitted:
        payload = {
            "opened_date": opened_date.isoformat(),
            "category": category,
            "priority": priority,
            "status": status,
            "assigned_staff": None if assigned == "Unassigned" else assigned,
            "description": description,
            "resolved_date": resolved_date_value.isoformat() if resolved_date_value else None,
        }
        insert_ticket(payload)
        st.success("Ticket logged.")
        st.rerun()


def render_kanban_board(tickets: List[Dict]) -> None:
    st.subheader("Kanban board")
    st.session_state.setdefault("active_ticket", None)
    st.session_state.setdefault("delete_ticket_pending", None)
    cols = st.columns(len(STATUSES))
    for idx, status in enumerate(STATUSES):
        with cols[idx]:
            st.markdown(f"**{STATUS_LABELS.get(status, status.title())}**")
            matching = [ticket for ticket in tickets if ticket.get("status") == status]
            if not matching:
                st.caption("No tickets yet.")
            for ticket in matching:
                render_ticket_card(ticket)


def render_ticket_card(ticket: Dict) -> None:
    title = ticket.get("description") or f"Ticket #{ticket['id']}"
    with st.container():
        box = st.container()
        with box:
            top_cols = st.columns([5, 1])
            with top_cols[0]:
                st.markdown(f"**{title}**")
            with top_cols[1]:
                if st.button("⋯", key=f"menu_{ticket['id']}"):
                    st.session_state["active_ticket"] = ticket["id"]
            priority_color = PRIORITY_COLORS.get(ticket.get("priority", "low"), "#94a3b8")
            st.markdown(
                f"<span style='color:{priority_color};font-weight:600'>Priority: {ticket.get('priority','n/a').title()}</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"Assigned technician: {ticket.get('assigned_staff') or 'Unassigned'}")
            st.caption(f"Category: {ticket.get('category') or 'N/A'}")
            with st.expander("View details"):
                st.write(f"Opened: {ticket.get('opened_date')}")
                st.write(f"Status: {STATUS_LABELS.get(ticket.get('status'), ticket.get('status'))}")
                st.write(ticket.get("description") or "No additional notes.")

            if st.session_state.get("active_ticket") == ticket["id"]:
                render_ticket_actions(ticket)


def render_ticket_actions(ticket: Dict) -> None:
    st.session_state.setdefault("delete_ticket_pending", None)
    st.info("Edit ticket")
    technicians = get_technicians()
    options = ["Unassigned"] + technicians
    current_assigned = ticket.get("assigned_staff") or "Unassigned"
    if current_assigned not in options:
        options.append(current_assigned)
    with st.form(f"edit_ticket_form_{ticket['id']}"):
        col1, col2, col3 = st.columns(3)
        with col1:
            status = st.selectbox(
                "Status",
                STATUSES,
                index=STATUSES.index(ticket.get("status") or STATUSES[0]),
            )
            priority = st.selectbox(
                "Priority",
                PRIORITIES,
                index=PRIORITIES.index(ticket.get("priority") or PRIORITIES[0]),
            )
        with col2:
            category = st.selectbox(
                "Category",
                CATEGORIES,
                index=CATEGORIES.index(ticket.get("category") or CATEGORIES[0]),
            )
            assigned = st.selectbox(
                "Assigned Technician",
                options,
                index=options.index(current_assigned),
            )
        with col3:
            resolved_date_value = (
                st.date_input(
                    "Resolved date",
                    value=safe_date(ticket.get("resolved_date")),
                )
                if status == "resolved"
                else None
            )
        description = st.text_area("Description", value=ticket.get("description", ""))
        submitted = st.form_submit_button("Save changes")
    if submitted:
        payload = {
            "opened_date": ticket.get("opened_date"),
            "category": category,
            "priority": priority,
            "status": status,
            "assigned_staff": None if assigned == "Unassigned" else assigned,
            "description": description,
            "resolved_date": resolved_date_value.isoformat() if resolved_date_value else None,
        }
        update_ticket(ticket["id"], payload)
        st.success("Ticket updated.")
        st.session_state["active_ticket"] = None
        st.rerun()

    if st.button("Delete ticket", key=f"delete_ticket_{ticket['id']}"):
        st.session_state["delete_ticket_pending"] = ticket["id"]

    if st.session_state.get("delete_ticket_pending") == ticket["id"]:
        st.warning("This will permanently remove the ticket.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm delete", key=f"confirm_delete_{ticket['id']}"):
                delete_ticket(ticket["id"])
                st.success("Ticket deleted.")
                st.session_state["delete_ticket_pending"] = None
                st.session_state["active_ticket"] = None
                st.rerun()
        with col2:
            if st.button("Cancel", key=f"cancel_delete_{ticket['id']}"):
                st.session_state["delete_ticket_pending"] = None


def prepare_dataframe(tickets: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(tickets)
    if df.empty:
        return df
    df["opened_date"] = pd.to_datetime(df["opened_date"], errors="coerce")
    df["resolved_date"] = pd.to_datetime(df["resolved_date"], errors="coerce")
    df["resolution_days"] = (df["resolved_date"] - df["opened_date"]).dt.days
    return df


def analytics_section(tickets: List[Dict]) -> pd.DataFrame:
    st.subheader("Analytics and charts")
    df = prepare_dataframe(tickets)
    if df.empty:
        st.info("Add tickets to view analytics.")
        return df

    cols = st.columns(2)
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "ticket_count"]
    fig_status = px.pie(
        status_counts,
        values="ticket_count",
        names="status",
        title="Tickets by status",
    )
    cols[0].plotly_chart(fig_status, width="stretch")

    resolved = df.dropna(subset=["resolution_days"])
    if not resolved.empty:
        resolved_sorted = resolved.sort_values("opened_date")
        fig_line = px.line(
            resolved_sorted,
            x="opened_date",
            y="resolution_days",
            markers=True,
            title="Resolution days trend",
            labels={"opened_date": "Opened date", "resolution_days": "Resolution days"},
        )
        cols[1].plotly_chart(fig_line, width="stretch")
    else:
        cols[1].info("Resolution timing data will display once tickets are completed.")

    if not resolved.empty:
        resolved_staff = resolved.copy()
        resolved_staff["assigned_staff"] = resolved_staff["assigned_staff"].fillna("Unassigned")
        technician_mix = (
            resolved_staff.groupby(["assigned_staff", "category"])
            .size()
            .reset_index(name="ticket_count")
        )
        fig_mix = px.bar(
            technician_mix,
            x="ticket_count",
            y="assigned_staff",
            color="category",
            orientation="h",
            title="Resolved tickets by technician and category",
            labels={"ticket_count": "Tickets resolved", "assigned_staff": "Technician"},
        )
        st.plotly_chart(fig_mix, width="stretch")
    return df


def insights_section(df: pd.DataFrame) -> None:
    if df.empty:
        return
    backlog = int((df["status"] != "resolved").sum())
    avg_resolution = df["resolution_days"].dropna()
    avg_resolution_value = (
        round(avg_resolution.mean(), 1) if not avg_resolution.empty else "N/A"
    )
    category_counts = df["category"].value_counts()
    busiest_category = category_counts.idxmax() if not category_counts.empty else "n/a"
    st.subheader("Insights and recommendations")
    st.write(
        f"The desk has {backlog} unresolved tickets. Average resolution time is "
        f"{avg_resolution_value} days, with most tickets falling under {busiest_category}. "
        "Consider assigning extra staff to the busiest category and follow up on waiting items."
    )


def main() -> None:
    guard_page()
    sidebar_user_box("it_ops")
    st.title("IT Ticketing Dashboard")
    st.write("Visualize ticket flow, edit work items inline, and monitor analytics.")

    if st.button("Load demo data"):
        load_demo_data()
        st.rerun()

    create_ticket_section()

    tickets = fetch_tickets()
    render_kanban_board(tickets)
    df = analytics_section(tickets)
    if not df.empty:
        insights_section(df)



if __name__ == "__main__":
    main()
