"""
CLI commands for Leads management.

Usage:
    python -m src.cli.commands list
    python -m src.cli.commands show <lead_id>
    python -m src.cli.commands export -o leads.csv
    python -m src.cli.commands stats
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

import click
from tabulate import tabulate

# Add parent to path for imports
sys.path.insert(0, ".")


@click.group()
def cli():
    """CodeGraph Leads Management CLI."""
    pass


@cli.command("list")
@click.option("--status", help="Filter by status (new, contacted, qualified, demo_scheduled, converted, closed)")
@click.option("--company", help="Filter by company name")
@click.option("--limit", default=20, help="Number of leads to show")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "csv", "json"]),
    help="Output format",
)
def list_leads(status: Optional[str], company: Optional[str], limit: int, output_format: str):
    """List leads with optional filters."""

    async def _list():
        from src.database.connection import get_db_session
        from src.services.lead_service import LeadService

        async with get_db_session() as session:
            service = LeadService(session)
            leads, total = await service.list_leads(
                status=status,
                company=company,
                limit=limit,
            )

            if not leads:
                click.echo("No leads found.")
                return

            if output_format == "table":
                table_data = [
                    [
                        str(lead.id)[:8],
                        lead.name[:20],
                        lead.email[:25],
                        lead.company[:20],
                        lead.status,
                        lead.created_at.strftime("%Y-%m-%d") if lead.created_at else "",
                    ]
                    for lead in leads
                ]
                click.echo(
                    tabulate(
                        table_data,
                        headers=["ID", "Name", "Email", "Company", "Status", "Created"],
                        tablefmt="simple",
                    )
                )
                click.echo(f"\nShowing {len(leads)} of {total} leads")

            elif output_format == "csv":
                import csv
                import io

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["id", "name", "email", "company", "position", "team_size", "language", "status", "created_at"])
                for lead in leads:
                    writer.writerow([
                        str(lead.id),
                        lead.name,
                        lead.email,
                        lead.company,
                        lead.position or "",
                        lead.team_size or "",
                        lead.language or "",
                        lead.status,
                        lead.created_at.isoformat() if lead.created_at else "",
                    ])
                click.echo(output.getvalue())

            else:  # json
                import json

                data = [lead.to_dict() for lead in leads]
                click.echo(json.dumps(data, indent=2, ensure_ascii=False))

    asyncio.run(_list())


@cli.command("show")
@click.argument("lead_id")
def show_lead(lead_id: str):
    """Show details of a specific lead."""

    async def _show():
        from src.database.connection import get_db_session
        from src.services.lead_service import LeadService

        async with get_db_session() as session:
            service = LeadService(session)
            lead = await service.get_lead(lead_id)

            if not lead:
                click.echo(f"Lead {lead_id} not found", err=True)
                return

            click.echo(f"""
Lead Details
{'=' * 50}
ID:         {lead.id}
Name:       {lead.name}
Email:      {lead.email}
Company:    {lead.company}
Position:   {lead.position or 'N/A'}
Team Size:  {lead.team_size or 'N/A'}
Language:   {lead.language or 'N/A'}
Status:     {lead.status}
Source:     {lead.source}
IP Address: {lead.ip_address or 'N/A'}
Created:    {lead.created_at}
Updated:    {lead.updated_at}
Notes:      {lead.notes or 'N/A'}
            """)

    asyncio.run(_show())


@cli.command("export")
@click.option("--output", "-o", default="leads_export.csv", help="Output file path")
@click.option("--status", help="Filter by status")
@click.option("--from-date", help="Filter from date (YYYY-MM-DD)")
@click.option("--to-date", help="Filter to date (YYYY-MM-DD)")
def export_leads(output: str, status: Optional[str], from_date: Optional[str], to_date: Optional[str]):
    """Export leads to CSV file."""

    async def _export():
        from src.database.connection import get_db_session
        from src.services.export_service import ExportService
        from src.services.lead_service import LeadService

        created_from = datetime.fromisoformat(from_date) if from_date else None
        created_to = datetime.fromisoformat(to_date) if to_date else None

        async with get_db_session() as session:
            service = LeadService(session)
            leads, total = await service.list_leads(
                status=status,
                created_from=created_from,
                created_to=created_to,
                limit=10000,
            )

            if not leads:
                click.echo("No leads found to export.")
                return

            csv_content = ExportService.export_to_csv(leads)

            with open(output, "w", encoding="utf-8") as f:
                f.write(csv_content)

            click.echo(f"Exported {len(leads)} leads to {output}")

    asyncio.run(_export())


@cli.command("stats")
def show_stats():
    """Show leads statistics."""

    async def _stats():
        from src.database.connection import get_db_session
        from src.services.lead_service import LeadService

        async with get_db_session() as session:
            service = LeadService(session)
            stats = await service.get_statistics()

            click.echo(f"""
Leads Statistics
{'=' * 50}
Total Leads:       {stats['total']}

By Status:
  New:             {stats['by_status'].get('new', 0)}
  Contacted:       {stats['by_status'].get('contacted', 0)}
  Qualified:       {stats['by_status'].get('qualified', 0)}
  Demo Scheduled:  {stats['by_status'].get('demo_scheduled', 0)}
  Converted:       {stats['by_status'].get('converted', 0)}
  Closed:          {stats['by_status'].get('closed', 0)}

Time Periods:
  Today:           {stats['today']}
  This Week:       {stats['this_week']}
  This Month:      {stats['this_month']}
            """)

    asyncio.run(_stats())


@cli.command("update")
@click.argument("lead_id")
@click.option("--status", type=click.Choice(["new", "contacted", "qualified", "demo_scheduled", "converted", "closed"]))
@click.option("--notes", help="Add notes to lead")
def update_lead(lead_id: str, status: Optional[str], notes: Optional[str]):
    """Update lead status or notes."""

    async def _update():
        from src.database.connection import get_db_session
        from src.models.lead import LeadStatus, LeadUpdateRequest
        from src.services.lead_service import LeadService

        if not status and notes is None:
            click.echo("Please provide --status or --notes to update", err=True)
            return

        async with get_db_session() as session:
            service = LeadService(session)

            update_data = LeadUpdateRequest(
                status=LeadStatus(status) if status else None,
                notes=notes,
            )

            lead = await service.update_lead(lead_id, update_data)

            if not lead:
                click.echo(f"Lead {lead_id} not found", err=True)
                return

            click.echo(f"Lead {lead_id} updated successfully")
            click.echo(f"  Status: {lead.status}")
            if notes:
                click.echo(f"  Notes: {lead.notes}")

    asyncio.run(_update())


@cli.command("test-notifications")
def test_notifications():
    """Test notification channels (Telegram and Email)."""

    async def _test():
        from src.config import get_settings
        from src.notifications.email import EmailNotifier
        from src.notifications.telegram import TelegramNotifier

        settings = get_settings()

        click.echo("Testing notification channels...\n")

        # Test Telegram
        click.echo("Telegram:")
        if settings.telegram_enabled:
            telegram = TelegramNotifier()
            result = await telegram.test_connection()
            click.echo(f"  Status: {'OK' if result else 'FAILED'}")
        else:
            click.echo("  Status: Not configured")

        # Test Email
        click.echo("\nEmail:")
        if settings.email_enabled:
            email = EmailNotifier()
            result = await email.test_connection()
            click.echo(f"  Status: {'OK' if result else 'FAILED'}")
        else:
            click.echo("  Status: Not configured")

    asyncio.run(_test())


if __name__ == "__main__":
    cli()
