from __future__ import annotations

import streamlit as st

from services import config_manager
from services.ui_helpers import sidebar_user_box, set_sidebar_visibility

st.set_page_config(layout="wide")
set_sidebar_visibility(st.session_state.get("logged_in", False))


def is_logged_in() -> bool:
    return bool(st.session_state.get("logged_in"))


def is_admin() -> bool:
    return "admin" in st.session_state.get("roles", [])


def render_provider_controls(is_admin_user: bool) -> None:
    options = config_manager.get_provider_options()
    current_provider = config_manager.get_current_provider()
    provider = st.selectbox(
        "Provider",
        options,
        index=options.index(current_provider),
        format_func=config_manager.get_provider_label,
        disabled=not is_admin_user,
    )
    if is_admin_user:
        config_manager.set_current_provider(provider)
    else:
        provider = current_provider

    models = config_manager.get_provider_models(provider)
    current_model = config_manager.get_current_model(provider)
    model_index = models.index(current_model) if current_model in models else 0
    model = st.selectbox(
        "Model",
        models,
        index=model_index,
        disabled=not is_admin_user,
    )
    if is_admin_user:
        config_manager.set_current_model(model, provider)

    status = config_manager.get_status(provider)
    st.markdown(
        f"**Status**\n\n- Provider: {status['provider']}\n- Model: {status['model']}\n"
        f"- Key configured: {status['key_present']} (source: {status['key_source']})"
    )


def render_key_inputs(provider: str) -> None:
    st.subheader("API keys")
    if not is_logged_in():
        st.warning("Please log in to configure API keys.")
        return
    if not is_admin():
        st.info("Only Admin can configure API keys.")
        return

    new_key = st.text_input(
        f"{config_manager.get_provider_label(provider)} API key",
        type="password",
        placeholder="Enter new key",
    )

    col1, col2 = st.columns(2)
    if col1.button("Use for this session", disabled=not new_key):
        if config_manager.store_session_key(provider, new_key.strip()):
            st.success("Key stored for this session.")
        else:
            st.error("Please enter a valid key before saving.")

    can_persist = config_manager.can_persist_locally()
    save_disabled = not new_key or not can_persist
    if col2.button("Save locally", disabled=save_disabled):
        if not can_persist:
            st.warning("Local persistence is disabled in hosted environments.")
        elif config_manager.save_key_locally(provider, new_key.strip()):
            st.success("Key saved to .env locally.")
        else:
            st.error("Unable to save the key locally.")

    if not can_persist:
        st.caption("Local saves are unavailable on hosted deployments.")


def main() -> None:
    config_manager.ensure_defaults()
    if not is_logged_in():
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
    sidebar_user_box("settings")

    st.title("Settings")
    st.write("Manage AI provider selection and API keys for the assistant.")

    admin_user = is_admin()
    render_provider_controls(admin_user)
    provider = config_manager.get_current_provider()
    render_key_inputs(provider)


if __name__ == "__main__":
    main()
