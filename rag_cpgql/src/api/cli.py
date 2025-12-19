"""
API Command Line Interface.

Provides CLI commands for running and managing the API server.
"""

import argparse
import logging
import sys
from typing import Optional

import uvicorn


def setup_logging(level: str = "INFO") -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    workers: int = 1,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """
    Run the API server.

    Args:
        host: Host to bind to
        port: Port to bind to
        workers: Number of worker processes
        reload: Enable auto-reload
        log_level: Logging level
    """
    uvicorn.run(
        "src.api.main:create_app",
        factory=True,
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        log_level=log_level,
        access_log=True,
    )


def create_admin_user(username: str, password: str, email: Optional[str] = None) -> None:
    """
    Create an admin user.

    Args:
        username: Admin username
        password: Admin password
        email: Admin email
    """
    import asyncio

    async def _create_admin():
        from src.api.database.connection import get_db_session
        from src.api.database.repositories.user_repo import UserRepository
        from src.api.services.user_service import UserService
        from src.api.database.models import UserRole

        async with get_db_session() as db:
            user_repo = UserRepository(db)
            user_service = UserService(user_repo)

            # Check if user exists
            existing = await user_service.get_by_username(username)
            if existing:
                print(f"User '{username}' already exists")
                return

            # Create admin user
            user = await user_service.create_user(
                username=username,
                password=password,
                email=email,
                role=UserRole.ADMIN,
            )
            await db.commit()

            print(f"Admin user created: {user.username} (ID: {user.id})")

    asyncio.run(_create_admin())


def init_database() -> None:
    """Initialize the database with tables."""
    import asyncio

    async def _init_db():
        from src.api.database.connection import init_db

        await init_db()
        print("Database initialized successfully")

    asyncio.run(_init_db())


def run_migrations(revision: str = "head") -> None:
    """
    Run database migrations.

    Args:
        revision: Migration revision to upgrade to
    """
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, revision)
    print(f"Migrations applied successfully to {revision}")


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CodeGraph API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run server command
    run_parser = subparsers.add_parser("run", help="Run the API server")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    run_parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    run_parser.add_argument("--log-level", default="info", help="Log level")

    # Init database command
    init_parser = subparsers.add_parser("init-db", help="Initialize the database")

    # Run migrations command
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    migrate_parser.add_argument(
        "--revision", default="head", help="Migration revision"
    )

    # Create admin command
    admin_parser = subparsers.add_parser("create-admin", help="Create admin user")
    admin_parser.add_argument("--username", required=True, help="Admin username")
    admin_parser.add_argument("--password", required=True, help="Admin password")
    admin_parser.add_argument("--email", help="Admin email")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging()

    if args.command == "run":
        run_server(
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
            log_level=args.log_level,
        )
    elif args.command == "init-db":
        init_database()
    elif args.command == "migrate":
        run_migrations(args.revision)
    elif args.command == "create-admin":
        create_admin_user(args.username, args.password, args.email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
