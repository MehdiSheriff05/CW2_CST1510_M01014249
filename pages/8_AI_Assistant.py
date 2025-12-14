from __future__ import annotations

# streamlit powers rendering and chat widgets
import streamlit as st

# assistant service wraps the provider logic
from services.ai_assistant import AIAssistant
from services.ui_helpers import sidebar_user_box, set_sidebar_visibility

# configure page for a wide chat experience
st.set_page_config(layout="wide")
set_sidebar_visibility(st.session_state.get("logged_in", False))

# allowed roles include every domain plus admin
ALLOWED_ROLES = {"cybersec_eng", "data_analyst", "it_ops", "admin"}
# default summaries help provide context to the assistant
DEFAULT_SUMMARIES = {
    "Incident Reporting": "SOC analysts are reviewing phishing, malware, and other alerts. Focus on response speed and case triage.",
    "Data Analysis": "Data analysts monitor dataset health, storage usage, and model-ready quality metrics across departments.",
    "IT Ticketing": "IT operations coordinate tickets, track technician workload, and aim for faster resolution times.",
}


def guard_page() -> None:
    # ensure only logged in users with correct roles reach this page
    if not st.session_state.get("logged_in"):
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
    roles = set(st.session_state.get("roles", []))
    if "admin" in roles:
        return
    if not roles.intersection(ALLOWED_ROLES):
        st.error("You do not have access to the AI workspace.")
        st.stop()


def init_chat_state() -> None:
    # seed default chat history and context values
    st.session_state.setdefault("ai_chat_history", [])
    st.session_state.setdefault("ai_summary_domain", "Incident Reporting")
    st.session_state.setdefault("ai_summary_text_value", DEFAULT_SUMMARIES["Incident Reporting"])


def render_chat_history() -> None:
    # replay stored conversation messages
    for message in st.session_state.get("ai_chat_history", []):
        with st.chat_message(message["role"]):
            st.write(message["content"])


def handle_user_message(domain: str, summary_text: str, assistant: AIAssistant) -> None:
    # capture chat input and call the ai assistant service
    prompt = st.chat_input("Ask the assistant about your dashboard work")
    if not prompt:
        return
    st.session_state["ai_chat_history"].append({"role": "user", "content": prompt})
    response = assistant.get_response(domain, summary_text, prompt)
    st.session_state["ai_chat_history"].append({"role": "assistant", "content": response})
    st.rerun()


def main() -> None:
    # primary entry point for the ai workspace
    guard_page()
    init_chat_state()
    sidebar_user_box("ai_page")
    st.title("AI Workspace")
    st.write("Chat with the coursework assistant about any domain. Update the summary text to give more context.")

    assistant = AIAssistant()
    # domain selector lets students toggle context quickly
    domain = st.selectbox(
        "Choose domain context",
        list(DEFAULT_SUMMARIES.keys()),
        index=list(DEFAULT_SUMMARIES.keys()).index(st.session_state["ai_summary_domain"]),
    )
    if domain != st.session_state["ai_summary_domain"]:
        st.session_state["ai_summary_domain"] = domain
        st.session_state["ai_summary_text_value"] = DEFAULT_SUMMARIES[domain]
        st.rerun()
    # summary is editable so students can pass custom context to the ai
    summary_text = st.text_area(
        "Domain summary shared with the assistant",
        value=st.session_state["ai_summary_text_value"],
        key="ai_summary_text_value",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Reset summary to default"):
            st.session_state["ai_summary_text_value"] = DEFAULT_SUMMARIES[domain]
            st.rerun()
    with col2:
        if st.button("Clear chat history"):
            st.session_state["ai_chat_history"] = []
            st.rerun()

    # show previous chat bubbles and listen for new prompts
    render_chat_history()
    handle_user_message(domain, summary_text, assistant)


if __name__ == "__main__":
    main()
