"""Dynamic user resolution — replaces the old hardcoded USER_A/USER_B config constants."""

from sqlalchemy import func
from sqlmodel import Session, select

from models import User


def get_all_users(session: Session) -> list[User]:
    """Return all registered users ordered by id (first-created first)."""
    return list(session.exec(select(User).order_by(User.id)).all())


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def get_user_by_display_name(session: Session, display_name: str) -> User | None:
    return session.exec(
        select(User).where(User.display_name == display_name)
    ).first()


def get_user_count(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User)).one()


def get_display_names(session: Session) -> tuple[str, str]:
    """Return (first_user_display, second_user_display). Empty strings for missing users."""
    users = get_all_users(session)
    a = users[0].display_name if len(users) > 0 else ""
    b = users[1].display_name if len(users) > 1 else ""
    return a, b


def resolve_names(session: Session, current_username: str) -> tuple[str, str]:
    """Return (my_display_name, other_display_name) for the logged-in user."""
    users = get_all_users(session)
    me_user = next((u for u in users if u.username == current_username), None)
    if not me_user:
        return current_username, ""
    me = me_user.display_name
    other = next(
        (u.display_name for u in users if u.username != current_username), ""
    )
    return me, other


def build_user_map(session: Session) -> dict[str, str]:
    """Return {login_username: display_name} for all registered users."""
    return {u.username: u.display_name for u in get_all_users(session)}


def is_primary_user(session: Session, username: str) -> bool:
    """Check if the given username is the first-created user (solo-mode eligible)."""
    users = get_all_users(session)
    return len(users) > 0 and users[0].username == username
