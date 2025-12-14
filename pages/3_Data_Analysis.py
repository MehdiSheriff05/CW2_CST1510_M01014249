from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from services.database_manager import DatabaseManager
from services.ui_helpers import sidebar_user_box, set_sidebar_visibility

st.set_page_config(layout="wide")
set_sidebar_visibility(st.session_state.get("logged_in", False))

db_manager = DatabaseManager()
ALLOWED_ROLES = {"data_analyst", "admin"}


def guard_page() -> None:
    if not st.session_state.get("logged_in"):
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
    roles = set(st.session_state.get("roles", []))
    if "admin" in roles:
        return
    if not roles.intersection(ALLOWED_ROLES):
        st.error("You do not have access to this analytics view.")
        st.stop()


def to_dataframe(records: list[dict], date_columns: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return df
    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
    if {"created_date", "resolved_date"}.issubset(df.columns):
        df["incident_resolution_days"] = (df["resolved_date"] - df["created_date"]).dt.days
    if {"opened_date", "resolved_date"}.issubset(df.columns):
        df["ticket_resolution_days"] = (df["resolved_date"] - df["opened_date"]).dt.days
    return df


def monthly_counts(df: pd.DataFrame, date_column: str, label: str) -> pd.DataFrame:
    if df.empty or date_column not in df.columns:
        return pd.DataFrame(columns=["month", "count", "source"])
    monthly = (
        df.groupby(df[date_column].dt.to_period("M"))
        .size()
        .reset_index(name="count")
    )
    monthly["month"] = monthly[date_column].dt.to_timestamp()
    monthly["source"] = label
    return monthly[["month", "count", "source"]]


def resolution_summary(incident_df: pd.DataFrame, ticket_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    if "incident_resolution_days" in incident_df:
        valid = incident_df["incident_resolution_days"].dropna()
        if not valid.empty:
            records.append({"dataset": "Incidents", "avg_days": valid.mean()})
    if "ticket_resolution_days" in ticket_df:
        valid = ticket_df["ticket_resolution_days"].dropna()
        if not valid.empty:
            records.append({"dataset": "Tickets", "avg_days": valid.mean()})
    return pd.DataFrame(records)


def backlog_table(incident_df: pd.DataFrame, ticket_df: pd.DataFrame) -> pd.DataFrame:
    incident_open = (
        incident_df[incident_df["status"].isin(["open", "in_progress"])]
        if "status" in incident_df
        else pd.DataFrame()
    )
    ticket_open = (
        ticket_df[ticket_df["status"].isin(["new", "in_progress", "waiting_user"])]
        if "status" in ticket_df
        else pd.DataFrame()
    )
    rows = [
        {
            "Workstream": "Incidents",
            "Open items": len(incident_open),
            "Most common severity": (
                incident_open["severity"].mode().iloc[0]
                if "severity" in incident_open and not incident_open["severity"].dropna().empty
                else "n/a"
            ),
        },
        {
            "Workstream": "Tickets",
            "Open items": len(ticket_open),
            "Most common priority": (
                ticket_open["priority"].mode().iloc[0]
                if "priority" in ticket_open and not ticket_open["priority"].dropna().empty
                else "n/a"
            ),
        },
    ]
    return pd.DataFrame(rows)


def main() -> None:
    guard_page()
    sidebar_user_box("data_analyst")
    st.title("Data Analysis")
    st.write(
        "This page aggregates cybersecurity incidents and IT ticketing data so the analytics team "
        "can review trends across both departments."
    )

    incidents = db_manager.fetch_all("SELECT * FROM security_incidents")
    tickets = db_manager.fetch_all("SELECT * FROM it_tickets")

    incident_df = to_dataframe(incidents, ["created_date", "resolved_date"])
    ticket_df = to_dataframe(tickets, ["opened_date", "resolved_date"])

    if incident_df.empty and ticket_df.empty:
        st.info("No incidents or tickets available yet. Load demo data on the other dashboards first.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total incidents", len(incident_df))
    col2.metric(
        "Open incidents",
        int((incident_df["status"].isin(["open", "in_progress"])).sum())
        if "status" in incident_df
        else 0,
    )
    col3.metric("Total tickets", len(ticket_df))
    col4.metric(
        "Active tickets",
        int(
            ticket_df["status"]
            .isin(["new", "in_progress", "waiting_user"])
            .sum()
        )
        if "status" in ticket_df
        else 0,
    )

    monthly_incidents = monthly_counts(incident_df, "created_date", "Incidents")
    monthly_tickets = monthly_counts(ticket_df, "opened_date", "Tickets")
    combined = pd.concat([monthly_incidents, monthly_tickets], ignore_index=True)
    if not combined.empty:
        fig_line = px.line(
            combined,
            x="month",
            y="count",
            color="source",
            markers=True,
            title="Monthly volume comparison",
            labels={"count": "Records", "month": "Month", "source": "Dataset"},
        )
        st.plotly_chart(fig_line, width="stretch")

    severity_counts = (
        incident_df["severity"].value_counts().reset_index(name="count").rename(columns={"index": "severity"})
        if "severity" in incident_df
        else pd.DataFrame()
    )
    priority_counts = (
        ticket_df["priority"].value_counts().reset_index(name="count").rename(columns={"index": "priority"})
        if "priority" in ticket_df
        else pd.DataFrame()
    )
    if not severity_counts.empty or not priority_counts.empty:
        bar_cols = st.columns(2)
        if not severity_counts.empty:
            bar_cols[0].plotly_chart(
                px.bar(
                    severity_counts,
                    x="severity",
                    y="count",
                    color="severity",
                    title="Incidents by severity",
                    labels={"severity": "Severity", "count": "Count"},
                ),
                width="stretch",
            )
        if not priority_counts.empty:
            bar_cols[1].plotly_chart(
                px.bar(
                    priority_counts,
                    x="priority",
                    y="count",
                    color="priority",
                    title="Tickets by priority",
                    labels={"priority": "Priority", "count": "Count"},
                ),
                width="stretch",
            )

    resolution_df = resolution_summary(incident_df, ticket_df)
    if not resolution_df.empty:
        fig_resolution = px.bar(
            resolution_df,
            x="dataset",
            y="avg_days",
            title="Average resolution days comparison",
            labels={"dataset": "Dataset", "avg_days": "Avg days"},
            color="dataset",
        )
        st.plotly_chart(fig_resolution, width="stretch")

    ticket_status_counts = (
        ticket_df["status"].value_counts().reset_index(name="count").rename(columns={"index": "status"})
        if "status" in ticket_df
        else pd.DataFrame()
    )
    if not ticket_status_counts.empty:
        st.plotly_chart(
            px.pie(
                ticket_status_counts,
                names="status",
                values="count",
                title="Ticket status distribution",
            ),
            width="stretch",
        )

    incident_owner_counts = (
        incident_df["assigned_to"]
        .fillna("Unassigned")
        .value_counts()
        .reset_index(name="count")
        .rename(columns={"index": "assigned", "assigned_to": "assigned"})
        if "assigned_to" in incident_df
        else pd.DataFrame()
    )
    if not incident_owner_counts.empty:
        st.plotly_chart(
            px.bar(
                incident_owner_counts,
                x="count",
                y="assigned",
                orientation="h",
                title="Incident volume by assignee",
                labels={"assigned": "Analyst", "count": "Incidents"},
            ),
            width="stretch",
        )

    resolution_trend = []
    if "incident_resolution_days" in incident_df and not incident_df["incident_resolution_days"].dropna().empty:
        inc_monthly = (
            incident_df.dropna(subset=["incident_resolution_days"])
            .groupby(incident_df["created_date"].dt.to_period("M"))["incident_resolution_days"]
            .mean()
            .reset_index(name="avg_days")
        )
        inc_monthly["month"] = inc_monthly["created_date"].dt.to_timestamp()
        inc_monthly["dataset"] = "Incidents"
        resolution_trend.append(inc_monthly[["month", "avg_days", "dataset"]])
    if "ticket_resolution_days" in ticket_df and not ticket_df["ticket_resolution_days"].dropna().empty:
        tic_monthly = (
            ticket_df.dropna(subset=["ticket_resolution_days"])
            .groupby(ticket_df["opened_date"].dt.to_period("M"))["ticket_resolution_days"]
            .mean()
            .reset_index(name="avg_days")
        )
        tic_monthly["month"] = tic_monthly["opened_date"].dt.to_timestamp()
        tic_monthly["dataset"] = "Tickets"
        resolution_trend.append(tic_monthly[["month", "avg_days", "dataset"]])
    if resolution_trend:
        trend_df = pd.concat(resolution_trend, ignore_index=True)
        st.plotly_chart(
            px.line(
                trend_df,
                x="month",
                y="avg_days",
                color="dataset",
                markers=True,
                title="Average resolution days trend",
                labels={"month": "Month", "avg_days": "Avg days"},
            ),
            width="stretch",
        )

    backlog_df = backlog_table(incident_df, ticket_df)
    st.subheader("Backlog snapshot")
    st.dataframe(backlog_df, width="stretch")


if __name__ == "__main__":
    main()
