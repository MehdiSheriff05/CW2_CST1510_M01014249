from __future__ import annotations

# streamlit drives the form rendering and session state
import streamlit as st

# auth manager handles registration and login checks
from services.auth_manager import AuthManager
# helper toggles sidebar visibility until login is done
from services.ui_helpers import set_sidebar_visibility

# configure this page for a centered login/register layout
st.set_page_config(layout="centered", page_title="Login / Register")

# initialise auth helper and ensure built-in admin exists
auth_manager = AuthManager()
auth_manager.ensure_admin_user()


def ensure_session_defaults() -> None:
    # keep predictable session keys for other pages to trust
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("roles", [])


def login_form() -> None:
    # capture login credentials in a form and verify them
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")
    if submitted:
        user = auth_manager.login_user(username, password)
        if user:
            # persist the authenticated identity in session
            st.session_state["logged_in"] = True
            st.session_state["username"] = user.get_username()
            st.session_state["roles"] = user.get_roles()
            st.success("Login successful.")
            st.switch_page("Dashboard.py")
        else:
            st.error("Invalid username or password.")


def registration_form() -> None:
    # collect a username/password pair and attempt to register
    with st.form("registration_form"):
        username = st.text_input("New username", key="register_username")
        password = st.text_input("New password", type="password", key="register_password")
        submitted = st.form_submit_button("Register")
    if submitted:
        success, message = auth_manager.register_user(username, password)
        if success:
            st.success(message)
        else:
            st.error(message)


def main() -> None:
    # main landing logic that toggles between login and register
    ensure_session_defaults()
    set_sidebar_visibility(st.session_state.get("logged_in", False))
    st.title("Login or Register")
    st.write("Use this page to log in or create a regular account.")

    # show who is logged in if someone already authenticated
    if st.session_state.get("logged_in"):
        current_roles = ", ".join(st.session_state.get("roles", [])) or "no roles"
        st.info(
            f"Logged in as {st.session_state['username']} with roles: {current_roles}."
        )

    # segmented control lets user flip between login and register modes
    mode = st.segmented_control("Choose an action", ["Login", "Register"], default="Login")
    if mode == "Login":
        login_form()
        st.caption("Need an account? Switch to Register.")
    else:
        registration_form()
        st.caption("Already registered? Switch to Login.")
    st.caption("New accounts are not assigned roles. Ask the admin user to assign access.")


if __name__ == "__main__":
    main()
