"""
Export service for leads data.

Handles CSV export functionality.
"""

import csv
import io
import logging
from datetime import datetime
from typing import List, Optional

from src.database.models import Lead

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting leads data."""

    # CSV column headers
    HEADERS = [
        "ID",
        "Name",
        "Email",
        "Company",
        "Position",
        "Team Size",
        "Language",
        "Status",
        "Source",
        "IP Address",
        "Created At",
        "Updated At",
        "Notes",
    ]

    # Language display names
    LANGUAGE_NAMES = {
        "c-cpp": "C/C++",
        "java": "Java",
        "python": "Python",
        "go": "Go",
        "javascript": "JavaScript/TypeScript",
        "csharp": "C#",
        "other": "Other",
    }

    @classmethod
    def export_to_csv(cls, leads: List[Lead]) -> str:
        """
        Export leads to CSV string.

        Args:
            leads: List of Lead objects

        Returns:
            CSV content as string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write header
        writer.writerow(cls.HEADERS)

        # Write data rows
        for lead in leads:
            writer.writerow(cls._lead_to_row(lead))

        return output.getvalue()

    @classmethod
    def _lead_to_row(cls, lead: Lead) -> list:
        """Convert lead to CSV row."""
        language_display = cls.LANGUAGE_NAMES.get(lead.language, lead.language) if lead.language else ""

        return [
            str(lead.id),
            lead.name,
            lead.email,
            lead.company,
            lead.position or "",
            lead.team_size or "",
            language_display,
            lead.status,
            lead.source,
            str(lead.ip_address) if lead.ip_address else "",
            lead.created_at.isoformat() if lead.created_at else "",
            lead.updated_at.isoformat() if lead.updated_at else "",
            lead.notes or "",
        ]

    @classmethod
    def generate_filename(
        cls,
        prefix: str = "leads",
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ) -> str:
        """
        Generate export filename.

        Args:
            prefix: Filename prefix
            created_from: Filter start date
            created_to: Filter end date

        Returns:
            Generated filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if created_from and created_to:
            date_range = f"_{created_from.strftime('%Y%m%d')}-{created_to.strftime('%Y%m%d')}"
        elif created_from:
            date_range = f"_from_{created_from.strftime('%Y%m%d')}"
        elif created_to:
            date_range = f"_to_{created_to.strftime('%Y%m%d')}"
        else:
            date_range = ""

        return f"{prefix}{date_range}_{timestamp}.csv"
