"""
Lead service for business logic.

Handles lead CRUD operations and notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Lead
from src.models.lead import LeadCreateRequest, LeadStatus, LeadUpdateRequest
from src.notifications.email import EmailNotifier
from src.notifications.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


class LeadService:
    """Service for lead operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize lead service.

        Args:
            session: Database session
        """
        self.session = session
        self.telegram = TelegramNotifier()
        self.email = EmailNotifier()

    async def create_lead(
        self,
        data: LeadCreateRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Lead:
        """
        Create a new lead and send notifications.

        Args:
            data: Lead creation data
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created Lead object
        """
        lead = Lead(
            name=data.name,
            email=data.email,
            company=data.company,
            position=data.position,
            team_size=data.team_size.value if data.team_size else None,
            language=data.language.value if data.language else None,
            status="new",
            source="landing",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)

        logger.info(f"Lead created: {lead.id} - {lead.email} @ {lead.company}")

        # Send notifications asynchronously (don't block response)
        await self._send_notifications(lead)

        return lead

    async def _send_notifications(self, lead: Lead) -> None:
        """Send notifications for new lead."""
        lead_data = lead.to_dict()

        # Send Telegram notification
        try:
            await self.telegram.send_new_lead_notification(lead_data)
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

        # Send Email notification
        try:
            await self.email.send_new_lead_notification(lead_data)
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    async def get_lead(self, lead_id: UUID | str) -> Optional[Lead]:
        """
        Get lead by ID.

        Args:
            lead_id: Lead UUID

        Returns:
            Lead object or None
        """
        if isinstance(lead_id, str):
            lead_id = UUID(lead_id)

        result = await self.session.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        company: Optional[str] = None,
        language: Optional[str] = None,
        team_size: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> tuple[List[Lead], int]:
        """
        List leads with filters and pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            status: Filter by status
            company: Filter by company (partial match)
            language: Filter by programming language
            team_size: Filter by team size
            created_from: Filter by created date (from)
            created_to: Filter by created date (to)
            search: Search in name, email, company
            limit: Override page_size with specific limit

        Returns:
            Tuple of (leads list, total count)
        """
        # Build base query
        query = select(Lead)
        count_query = select(func.count(Lead.id))

        # Apply filters
        conditions = []

        if status:
            conditions.append(Lead.status == status)

        if company:
            conditions.append(Lead.company.ilike(f"%{company}%"))

        if language:
            conditions.append(Lead.language == language)

        if team_size:
            conditions.append(Lead.team_size == team_size)

        if created_from:
            conditions.append(Lead.created_at >= created_from)

        if created_to:
            conditions.append(Lead.created_at <= created_to)

        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Lead.name.ilike(search_term),
                    Lead.email.ilike(search_term),
                    Lead.company.ilike(search_term),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        actual_limit = limit or page_size
        offset = (page - 1) * page_size if not limit else 0

        query = query.order_by(Lead.created_at.desc())
        query = query.offset(offset).limit(actual_limit)

        # Execute query
        result = await self.session.execute(query)
        leads = list(result.scalars().all())

        return leads, total

    async def update_lead(
        self,
        lead_id: UUID | str,
        data: LeadUpdateRequest,
    ) -> Optional[Lead]:
        """
        Update lead status/notes.

        Args:
            lead_id: Lead UUID
            data: Update data

        Returns:
            Updated Lead object or None
        """
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        if data.status:
            lead.status = data.status.value
        if data.notes is not None:
            lead.notes = data.notes

        await self.session.flush()
        await self.session.refresh(lead)

        logger.info(f"Lead updated: {lead.id} - status={lead.status}")
        return lead

    async def delete_lead(self, lead_id: UUID | str) -> bool:
        """
        Delete lead by ID.

        Args:
            lead_id: Lead UUID

        Returns:
            True if deleted, False if not found
        """
        lead = await self.get_lead(lead_id)
        if not lead:
            return False

        await self.session.delete(lead)
        logger.info(f"Lead deleted: {lead_id}")
        return True

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get lead statistics.

        Returns:
            Statistics dictionary
        """
        # Total count
        total_result = await self.session.execute(
            select(func.count(Lead.id))
        )
        total = total_result.scalar() or 0

        # Count by status
        status_result = await self.session.execute(
            select(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # Today's leads
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await self.session.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= today)
        )
        today_count = today_result.scalar() or 0

        # This week
        week_start = today - timedelta(days=today.weekday())
        week_result = await self.session.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= week_start)
        )
        week_count = week_result.scalar() or 0

        # This month
        month_start = today.replace(day=1)
        month_result = await self.session.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= month_start)
        )
        month_count = month_result.scalar() or 0

        return {
            "total": total,
            "by_status": by_status,
            "today": today_count,
            "this_week": week_count,
            "this_month": month_count,
        }
