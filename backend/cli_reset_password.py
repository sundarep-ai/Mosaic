#!/usr/bin/env python
"""CLI tool to reset a user's password.

Run this on the host machine when a user cannot log in and cannot answer
their security question either. Requires direct access to the machine.

Usage:
    python cli_reset_password.py
"""

import getpass
import sys

import bcrypt
from sqlmodel import Session, select

from database import engine
from models import User


def main():
    with Session(engine) as session:
        users = list(session.exec(select(User).order_by(User.id)).all())

    if not users:
        print("No user accounts found in the database.")
        sys.exit(1)

    print("Registered accounts:")
    for i, u in enumerate(users, 1):
        print(f"  {i}. {u.username} ({u.display_name})")
    print()

    username = input("Enter username to reset: ").strip()
    if not username:
        print("No username provided.")
        sys.exit(1)

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)

        new_password = getpass.getpass("Enter new password: ")
        if len(new_password) < 6:
            print("Password must be at least 6 characters.")
            sys.exit(1)

        confirm = getpass.getpass("Confirm new password: ")
        if new_password != confirm:
            print("Passwords do not match.")
            sys.exit(1)

        user.password_hash = bcrypt.hashpw(
            new_password.encode(), bcrypt.gensalt()
        ).decode()
        session.add(user)
        session.commit()
        print(f"Password for '{username}' has been reset successfully.")


if __name__ == "__main__":
    main()
