from __future__ import annotations

# imports needed for streamlit, auth, and db helpers
import streamlit as st

from services.auth_manager import AuthManager
from services.database_manager import DatabaseManager
from services.ui_helpers import set_sidebar_visibility

# configure the streamlit shell and make sure database is ready
st.set_page_config(page_title="Dashboard", layout="wide")

db_manager = DatabaseManager()
db_manager.create_tables()
AuthManager(db_manager).ensure_admin_user()

# css block to style the dashboard cards
CARD_STYLE = """
<style>
section[data-testid="stMain"] div[data-testid="stButton"] button {
    background-color: #1f1f2e;
    border-radius: 14px;
    border: 1px solid #2f2f40;
    color: #f4f4f7;
    padding: 1.5rem;
    min-height: 180px;
    width: 100%;
    text-align: left;
    font-size: 1rem;
    line-height: 1.4;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
    transition: all 0.2s ease-in-out;
    white-space: normal;
}
section[data-testid="stMain"] div[data-testid="stButton"] button:hover {
    background-color: #2b2b3f;
    border-color: #5c5cff;
    transform: translateY(-2px);
}
section[data-testid="stMain"] div[data-testid="stButton"] button:disabled {
    background-color: #3a3a4a;
    color: #cccccc;
    border-color: #3a3a4a;
    box-shadow: none;
}
</style>
"""

CARDS = [
    {
        "label": "Incident Reporting",
        "description": "Create and analyze cybersecurity incidents for the SOC team.",
        "icon": "🛡️",
        "page": "pages/2_Incident_Reporting.py",
        "roles": {"cybersec_eng", "admin"},
    },
    {
        "label": "Data Analysis",
        "description": "Review cross-domain insights from incidents and tickets.",
        "icon": "📡",
        "page": "pages/3_Data_Analysis.py",
        "roles": {"data_analyst", "admin"},
    },
    {
        "label": "IT Ticketing",
        "description": "Track IT operations tickets and kanban style progress.",
        "icon": "🛠️",
        "page": "pages/4_IT_Ticketing_Dashboard.py",
        "roles": {"it_ops", "admin"},
    },
    {
        "label": "User Management",
        "description": "Assign roles and manage every account in the system.",
        "icon": "👥",
        "page": "pages/6_User_Management.py",
        "roles": {"admin"},
    },
    {
        "label": "Settings",
        "description": "Configure AI provider preferences and API keys.",
        "icon": "⚙️",
        "page": "pages/7_Settings.py",
        "roles": {"admin"},
    },
    {
        "label": "AI Workspace",
        "description": "Launch the AI assistant experience for any domain.",
        "icon": "🤖",
        "page": "pages/8_AI_Assistant.py",
        "roles": {"cybersec_eng", "data_analyst", "it_ops", "admin"},
    },
]


def ensure_session_state() -> None:
# make sure session state always has the keys we need
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("roles", [])


def guard_login() -> None:
# if user is not logged in we send them to the login screen and hide sidebar
    if not st.session_state.get("logged_in"):
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
# once logged in we show the sidebar
    set_sidebar_visibility(True)


def render_cards() -> None:
# render every dashboard card with access rules
    st.markdown(CARD_STYLE, unsafe_allow_html=True)
    roles = set(st.session_state.get("roles", []))
    is_admin = "admin" in roles
    cols_per_row = 3
    for start in range(0, len(CARDS), cols_per_row):
        row = CARDS[start : start + cols_per_row]
        if len(row) < cols_per_row:
            row = row + [None] * (cols_per_row - len(row))
        columns = st.columns(cols_per_row)
        for column, card in zip(columns, row):
            if card is None:
                column.empty()
                continue
            allowed = not card["roles"] or is_admin or bool(roles.intersection(card["roles"]))
            label = f"{card['icon']} {card['label']}\n\n{card['description']}"
            clicked = column.button(
                label,
                key=f"card_{card['label']}",
                disabled=not allowed,
            )
# clicking a card opens the correct page
            if clicked:
                st.switch_page(card["page"])
            if not allowed:
                column.caption("Access restricted for your role.")


def main() -> None:
# overall landing page entry
    ensure_session_state()
    guard_login()
    with st.sidebar:
# provide a single logout button in sidebar
        if st.button("Log out"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["roles"] = []
            st.rerun()
    st.title("Dashboard")
    st.write(
        "Choose a workspace below. Each card mirrors a Streamlit page in this multi-domain platform."
    )
    render_cards()


if __name__ == "__main__":
    main()
