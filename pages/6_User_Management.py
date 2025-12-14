from __future__ import annotations

import streamlit as st
from contextlib import contextmanager

from services.auth_manager import AuthManager, VALID_ROLES
from services.ui_helpers import sidebar_user_box, set_sidebar_visibility

st.set_page_config(layout="wide")
set_sidebar_visibility(st.session_state.get("logged_in", False))

def dialog_container(title: str):
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

# service instance shared by the page
auth_manager = AuthManager()


def guard_page() -> None:
    # stop access for anyone who is not admin
    if not st.session_state.get("logged_in"):
        set_sidebar_visibility(False)
        st.switch_page("pages/Login.py")
        st.stop()
    roles = st.session_state.get("roles", [])
    if "admin" not in roles:
        st.error("Only admin can view this page.")
        st.stop()


def render_user_table(users: list[dict]) -> None:
    # draw a manual table with action buttons per row
    st.subheader("User directory")
    header_cols = st.columns([3, 3, 2, 2])
    header_cols[0].markdown("**Username**")
    header_cols[1].markdown("**Roles**")
    header_cols[2].markdown("**Edit**")
    header_cols[3].markdown("**Delete**")

    if not users:
        st.info("No users found.")
        return

    for row in users:
        cols = st.columns([3, 3, 2, 2])
        roles = ", ".join(row.get("roles", [])) or "none"
        cols[0].write(row["username"])
        cols[1].write(roles)
        if cols[2].button("Edit", key=f"edit_{row['username']}"):
            st.session_state["edit_user"] = row
        disable_delete = row["username"] == "admin"
        if cols[3].button("Delete", disabled=disable_delete, key=f"delete_{row['username']}"):
            st.session_state["delete_user"] = row


def show_create_modal() -> None:
    if not st.session_state.get("show_create_modal"):
        return
    with dialog_container("Create new user"):
        with st.form("create_user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            roles = st.multiselect("Roles", VALID_ROLES)
            submitted = st.form_submit_button("Save user")
        if submitted:
            success, message = auth_manager.create_user(username, password, roles)
            if success:
                st.success(message)
                st.session_state["show_create_modal"] = False
                st.rerun()
            else:
                st.error(message)
        if st.button("Close", key="close_create_modal"):
            st.session_state["show_create_modal"] = False


def show_edit_modal() -> None:
    row = st.session_state.get("edit_user")
    if not row:
        return
    with dialog_container(f"Edit {row['username']}"):
        current_roles = row.get("roles", [])
        with st.form("edit_user_form"):
            roles = st.multiselect("Roles", VALID_ROLES, default=current_roles)
            new_password = st.text_input("New password (optional)", type="password")
            submitted = st.form_submit_button("Update user")
        if submitted:
            saved_roles = auth_manager.update_user_roles(row["username"], roles)
            saved_pw = True
            if new_password:
                saved_pw = auth_manager.update_user_password(row["username"], new_password)
            if saved_roles and saved_pw:
                st.success("User updated.")
                st.session_state["edit_user"] = None
                st.rerun()
            else:
                st.error("Unable to update user.")
        if st.button("Close edit", key="close_edit_modal"):
            st.session_state["edit_user"] = None


def show_delete_modal() -> None:
    row = st.session_state.get("delete_user")
    if not row:
        return
    dialog_fn = getattr(st, "dialog", None)
    if callable(dialog_fn):
        @dialog_fn(f"Delete {row['username']}?")
        def delete_dialog() -> None:
            st.warning(
                "Deleting a user removes their access immediately. This action cannot be undone.",
                icon="⚠️",
            )
            if st.button("Confirm delete", type="primary", key="confirm_delete_user"):
                if auth_manager.delete_user(row["username"]):
                    st.success("User deleted.")
                    st.session_state["delete_user"] = None
                    st.rerun()
                else:
                    st.error("Could not delete user.")
            if st.button("Cancel delete", key="cancel_delete_user"):
                st.session_state["delete_user"] = None

        delete_dialog()
    else:
        with dialog_container(f"Delete {row['username']}?"):
            st.warning(
                "Deleting a user removes their access immediately. This action cannot be undone.",
                icon="⚠️",
            )
            if st.button("Confirm delete", type="primary", key="confirm_delete_user"):
                if auth_manager.delete_user(row["username"]):
                    st.success("User deleted.")
                    st.session_state["delete_user"] = None
                    st.rerun()
                else:
                    st.error("Could not delete user.")
            if st.button("Cancel delete", key="cancel_delete_user"):
                st.session_state["delete_user"] = None


def main() -> None:
    guard_page()
    sidebar_user_box("user_mgmt")
    st.title("User management")
    st.write("View every user, assign roles, and handle support accounts for admins.")

    if st.button("➕ Create new user", type="primary"):
        st.session_state["show_create_modal"] = True

    users = auth_manager.get_all_users()
    render_user_table(users)

    show_create_modal()
    show_edit_modal()
    show_delete_modal()


if __name__ == "__main__":
    main()
