# authentication manager with bcrypt helpers

from __future__ import annotations

from typing import List, Optional, Tuple

import bcrypt

from models.user import User
from services.database_manager import DatabaseManager

# sentinel is stored when a user has no roles yet
DEFAULT_ROLE_SENTINEL = "none"
VALID_ROLES = ["cybersec_eng", "data_analyst", "it_ops", "admin"]
# simple remap supports older role names if they appear in the database
ROLE_REMAP = {
    "cyber_analyst": "cybersec_eng",
    "cyber": "cybersec_eng",
    "data_scientist": "data_analyst",
}


class AuthManager:
    # simple registration and login handler

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        # keep a shared database helper ready
        self.db_manager = db_manager or DatabaseManager()

    def _hash_password(self, password: str) -> bytes:
        # hash the password for safe storage
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    def _verify_password(self, password: str, password_hash: str) -> bool:
        # check a login password against stored hash
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False

    def _serialise_roles(self, roles: List[str]) -> str:
        # join roles into a comma separated string
        cleaned = [role for role in roles if role in VALID_ROLES]
        return ",".join(cleaned) if cleaned else DEFAULT_ROLE_SENTINEL

    def _parse_roles(self, raw_roles: str) -> List[str]:
        # convert saved string back to a validated role list
        if not raw_roles or raw_roles == DEFAULT_ROLE_SENTINEL:
            return []
        cleaned = [role.strip() for role in raw_roles.split(",") if role.strip()]
        mapped = [ROLE_REMAP.get(role, role) for role in cleaned]
        return [role for role in mapped if role in VALID_ROLES]

    def register_user(self, username: str, password: str) -> Tuple[bool, str]:
        # create a new user record with no roles
        username = username.strip()
        if not username or not password:
            return False, "Username and password are required."

        # make sure username is not already taken
        existing = self.db_manager.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        )
        if existing:
            return False, "Username already exists."

        password_hash = self._hash_password(password).decode("utf-8")
        self.db_manager.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, DEFAULT_ROLE_SENTINEL),
        )
        return True, "Registration successful. Ask an admin to assign roles."

    def create_user(self, username: str, password: str, roles: Optional[List[str]] = None) -> Tuple[bool, str]:
        # admin helper to create a user with optional roles
        username = username.strip()
        if not username or not password:
            return False, "Username and password are required."
        # this path is similar but allows admins to assign roles directly
        existing = self.db_manager.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        )
        if existing:
            return False, "Username already exists."
        password_hash = self._hash_password(password).decode("utf-8")
        stored_roles = self._serialise_roles(roles or [])
        self.db_manager.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, stored_roles),
        )
        return True, "User created."

    def login_user(self, username: str, password: str) -> Optional[User]:
        # load a user from the database when credentials pass
        username = username.strip()
        if not username or not password:
            return None

        # pull the user row from sqlite for validation
        row = self.db_manager.fetch_one(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            (username,),
        )
        if not row:
            return None

        if self._verify_password(password, row["password_hash"]):
            roles = self._parse_roles(row["role"])
            return User(row["username"], roles)
        return None

    def get_all_users(self) -> List[dict]:
        # return every user for admin tools
        rows = self.db_manager.fetch_all(
            "SELECT id, username, role FROM users ORDER BY username"
        )
        for row in rows:
            row["roles"] = self._parse_roles(row.get("role", ""))
        return rows

    def update_user_roles(self, username: str, roles: List[str]) -> bool:
        # update which roles belong to a username
        serialised = self._serialise_roles(roles)
        result = self.db_manager.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            (serialised, username),
        )
        return result is not None

    def update_user_password(self, username: str, new_password: str) -> bool:
        # change the stored password hash
        if not new_password:
            return False
        new_hash = self._hash_password(new_password).decode("utf-8")
        result = self.db_manager.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
        return result is not None

    def delete_user(self, username: str) -> bool:
        # remove a user except the built in admin
        if username == "admin":
            return False
        result = self.db_manager.execute(
            "DELETE FROM users WHERE username = ?",
            (username,),
        )
        return result is not None

    def ensure_admin_user(self) -> None:
        # add a default admin account if missing
        existing = self.db_manager.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            ("admin",),
        )
        if existing:
            return
        password_hash = self._hash_password("admin").decode("utf-8")
        self.db_manager.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", password_hash, "admin"),
        )
