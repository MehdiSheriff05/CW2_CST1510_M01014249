# user domain model

from __future__ import annotations


class User:
    # represents an authenticated user record

    def __init__(self, username: str, roles: list[str]) -> None:
        # store username text
        self.username = username
        # store every role value as a list
        self.roles = roles

    def get_username(self) -> str:
        # return the saved username
        return self.username

    def get_roles(self) -> list[str]:
        # return a list of role labels
        return self.roles

    def get_primary_role(self) -> str:
        # return first role or none
        return self.roles[0] if self.roles else "none"

    def __str__(self) -> str:  # pragma: no cover - simple data method
        # quick readable text for debugging
        return f"User(username={self.username}, roles={self.roles})"
