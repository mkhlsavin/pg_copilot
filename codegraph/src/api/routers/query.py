"""
Query Router.

Provides endpoints for executing CPGQL queries directly.
"""

import logging
import time
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User
from src.api.dependencies import get_current_active_user

logger = logging.getLogger("api.routers.query")
router = APIRouter()


# Models
class QueryExecuteRequest(BaseModel):
    """Query execution request model."""
    query: str = Field(..., min_length=1, max_length=10000, description="SQL query string for CPG database")
    timeout: int = Field(default=60, ge=1, le=300, description="Query timeout in seconds")
    limit: int = Field(default=100, ge=1, le=10000, description="Maximum results")
    db_path: Optional[str] = Field(default=None, description="Path to CPG DuckDB database")


class QueryResult(BaseModel):
    """Query result model."""
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    row_count: int
    execution_time_ms: float


class QueryExecuteResponse(BaseModel):
    """Query execution response model."""
    success: bool
    result: Optional[QueryResult] = None
    error: Optional[str] = None
    request_id: str


class QueryValidationResult(BaseModel):
    """Query validation result model."""
    valid: bool
    query: str
    message: str
    warnings: List[str] = Field(default_factory=list)


# SQL Injection prevention patterns
FORBIDDEN_PATTERNS = [
    r'\bDROP\s+',
    r'\bDELETE\s+',
    r'\bTRUNCATE\s+',
    r'\bUPDATE\s+',
    r'\bINSERT\s+',
    r'\bCREATE\s+',
    r'\bALTER\s+',
    r'\bGRANT\s+',
    r'\bREVOKE\s+',
    r'\bATTACH\s+',
    r'\bDETACH\s+',
    r';\s*--',
    r'/\*.*\*/',
]


def validate_query_syntax(query: str) -> tuple[bool, str, List[str]]:
    """
    Validate query syntax and check for dangerous operations.

    Args:
        query: SQL query to validate

    Returns:
        Tuple of (is_valid, message, warnings)
    """
    warnings = []

    # Check for empty query
    if not query or not query.strip():
        return False, "Query cannot be empty", warnings

    # Check for forbidden operations (read-only)
    query_upper = query.upper()
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, query_upper, re.IGNORECASE):
            return False, f"Query contains forbidden operation: {pattern.replace('\\\\b', '').replace('\\\\s+', '')}", warnings

    # Check for SELECT statement
    if not re.search(r'^\s*SELECT\b', query_upper):
        return False, "Only SELECT queries are allowed", warnings

    # Warn about wildcard selects
    if re.search(r'SELECT\s+\*', query_upper):
        warnings.append("Using SELECT * may return large result sets; consider specifying columns")

    # Warn about missing LIMIT
    if not re.search(r'\bLIMIT\b', query_upper):
        warnings.append("Query has no LIMIT clause; results may be truncated")

    return True, "Query syntax is valid", warnings


# Endpoints
@router.post(
    "/execute",
    response_model=QueryExecuteResponse,
    summary="Execute SQL query",
    description="Execute a SQL query against the Code Property Graph database.",
)
async def execute_query(
    request: QueryExecuteRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
) -> QueryExecuteResponse:
    """
    Execute a SQL query against the CPG database.

    Args:
        request: Query execution parameters
        req: FastAPI request
        current_user: Authenticated user

    Returns:
        Query results or error
    """
    request_id = getattr(req.state, "request_id", "unknown")

    # Validate query syntax
    is_valid, message, warnings = validate_query_syntax(request.query)
    if not is_valid:
        logger.warning(f"Invalid query from {current_user.username}: {message}")
        return QueryExecuteResponse(
            success=False,
            result=None,
            error=message,
            request_id=request_id,
        )

    # Try to execute query
    try:
        from src.services.cpg_query_service import CPGQueryService

        # Use provided db_path or default
        db_path = request.db_path or "cpg.duckdb"

        start_time = time.time()

        with CPGQueryService(db_path) as cpg_service:
            # Add LIMIT if not present
            query = request.query.strip()
            if not re.search(r'\bLIMIT\b', query.upper()):
                query = f"{query.rstrip(';')} LIMIT {request.limit}"

            # Execute query
            results = cpg_service.execute_query(query)

            execution_time_ms = (time.time() - start_time) * 1000

            # Extract columns and rows
            if results:
                columns = list(results[0].keys())
                rows = [list(row.values()) for row in results]
            else:
                columns = []
                rows = []

            logger.info(f"Query executed by {current_user.username}: {len(rows)} rows in {execution_time_ms:.2f}ms")

            return QueryExecuteResponse(
                success=True,
                result=QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=execution_time_ms,
                ),
                error=None,
                request_id=request_id,
            )

    except FileNotFoundError as e:
        logger.error(f"Database not found: {e}")
        return QueryExecuteResponse(
            success=False,
            result=None,
            error=f"CPG database not found. Please import a project first.",
            request_id=request_id,
        )
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return QueryExecuteResponse(
            success=False,
            result=None,
            error=f"Query execution failed: {str(e)}",
            request_id=request_id,
        )


@router.post(
    "/validate",
    response_model=QueryValidationResult,
    summary="Validate SQL query",
    description="Validate a SQL query syntax without executing it.",
)
async def validate_query(
    query: str,
    current_user: User = Depends(get_current_active_user),
) -> QueryValidationResult:
    """
    Validate a SQL query syntax.

    Args:
        query: SQL query string

    Returns:
        Validation result with any warnings
    """
    is_valid, message, warnings = validate_query_syntax(query)

    logger.debug(f"Query validation by {current_user.username}: valid={is_valid}")

    return QueryValidationResult(
        valid=is_valid,
        query=query,
        message=message,
        warnings=warnings,
    )
