# small shared UI helpers for the dashboards

from __future__ import annotations

import streamlit as st


def set_sidebar_visibility(show: bool) -> None:
    # hide sidebar until login completes
    display_value = "flex" if show else "none"
    toggle_value = "block" if show else "none"
    # inject css so sidebar and toggle follow our desired visibility
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            display: {display_value} !important;
        }}
        button[title="Hide sidebar"] {{
            display: {toggle_value} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_user_box(key_prefix: str) -> None:
    # show info in sidebar only after login
    if not st.session_state.get("logged_in"):
        return
    set_sidebar_visibility(True)
    roles = ", ".join(st.session_state.get("roles", [])) or "no roles"
    with st.sidebar:
        st.caption(
            f"Logged in as {st.session_state.get('username')} ({roles})."
        )
        if st.button("Log out", key=f"{key_prefix}_logout"):
            # reset keys and refresh page
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["roles"] = []
            st.rerun()
