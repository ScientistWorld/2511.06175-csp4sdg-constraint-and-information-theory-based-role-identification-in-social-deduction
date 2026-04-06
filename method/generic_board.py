"""
Generic board utilities for dynamically-constructed Avalon role schemas.
Used for the AvalonLogs dataset which has variable player counts (5-10).
"""

from method.sdg_framework import RoleSchema


def build_schema(schema_dict: dict) -> RoleSchema:
    """
    Create RoleSchema from dictionary:
      - role_counts: dict of role_key -> count
      - good_roles: list of role_key that are good
    """
    return RoleSchema(schema_dict["role_counts"], good_roles=schema_dict["good_roles"])


def role_is(player: str, role: str):
    """Predicate: world[player] == role."""
    return lambda world: world[player] == role


def role_not(player: str, role: str):
    """Predicate: world[player] != role."""
    return lambda world: world[player] != role


def evil_at_least(schema: RoleSchema, team: list, min_fail: int):
    """Return a predicate checking at least min_fail members of team are evil."""
    def predicate(world: dict):
        bad_count = sum(1 for p in team if not schema.is_good(world[p]))
        return bad_count >= min_fail
    return predicate


def team_all_good(schema: RoleSchema, team: list):
    """Predicate ensuring every member of `team` is on the good side."""
    def predicate(world: dict):
        return all(schema.is_good(world[p]) for p in team)
    return predicate
