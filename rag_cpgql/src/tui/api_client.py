"""API client for TUI commands.

Provides HTTP and WebSocket communication with the RAG-CPGQL API server.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API client configuration."""

    base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    timeout: float = 30.0
    ws_timeout: float = 300.0  # WebSocket timeout for long operations

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None) -> "APIConfig":
        """
        Load API configuration from config.yaml.

        Args:
            config_path: Path to config.yaml (optional)

        Returns:
            APIConfig instance
        """
        try:
            from src.config.unified_config import UnifiedConfig

            config = UnifiedConfig(config_path)
            api_settings = config.api

            host = getattr(api_settings, "host", "localhost")
            port = getattr(api_settings, "port", 8000)

            # Determine protocol (assume http for local, could be extended)
            protocol = "http"
            if host not in ("localhost", "127.0.0.1", "0.0.0.0"):
                protocol = "https"

            base_url = f"{protocol}://{host}:{port}"
            return cls(base_url=base_url)

        except ImportError:
            logger.warning("UnifiedConfig not available, using defaults")
            return cls()
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            return cls()

    @property
    def full_url(self) -> str:
        """Get full API URL with prefix."""
        return f"{self.base_url}{self.api_prefix}"

    @property
    def ws_url(self) -> str:
        """Get WebSocket URL."""
        base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{base}{self.api_prefix}/ws"


class TUIApiClient:
    """HTTP and WebSocket client for TUI to API communication."""

    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize API client.

        Args:
            config: API configuration (optional, will use defaults)
        """
        self.config = config or APIConfig()
        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @property
    def is_authenticated(self) -> bool:
        """Check if client has authentication token."""
        return self._token is not None

    def set_token(self, token: str, refresh_token: Optional[str] = None):
        """Set authentication tokens."""
        self._token = token
        self._refresh_token = refresh_token

    def clear_token(self):
        """Clear authentication tokens."""
        self._token = None
        self._refresh_token = None

    def _url(self, path: str) -> str:
        """Build full URL for API path."""
        return f"{self.config.full_url}{path}"

    # =========================================================================
    # Authentication API
    # =========================================================================

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login with username and password.

        Args:
            username: User's username
            password: User's password

        Returns:
            Token response with access_token, refresh_token, expires_in
        """
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/auth/token"),
                headers={"Content-Type": "application/json"},
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")
            return data

    async def logout(self) -> bool:
        """
        Logout and invalidate token.

        Returns:
            True if logout was successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    self._url("/auth/logout"),
                    headers=self.headers,
                )
                success = response.status_code == 200
                if success:
                    self.clear_token()
                return success
        except Exception:
            self.clear_token()
            return True

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self._refresh_token:
            raise ValueError("No refresh token available")

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/auth/refresh"),
                headers={"Content-Type": "application/json"},
                json={"refresh_token": self._refresh_token},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("access_token")
            if data.get("refresh_token"):
                self._refresh_token = data["refresh_token"]
            return data

    async def get_current_user(self) -> Dict[str, Any]:
        """Get current authenticated user info."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/auth/me"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_api_keys(self) -> List[Dict[str, Any]]:
        """List user's API keys."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/auth/api-keys"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_api_key(
        self, name: str, expires_days: int = 365, scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new API key."""
        payload = {"name": name, "expires_days": expires_days}
        if scopes:
            payload["scopes"] = scopes

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/auth/api-keys"),
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.delete(
                self._url(f"/auth/api-keys/{key_id}"),
                headers=self.headers,
            )
            return response.status_code in (200, 204)

    # =========================================================================
    # Groups API
    # =========================================================================

    async def list_groups(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List all accessible project groups."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/groups"),
                headers=self.headers,
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            return response.json()

    async def get_group(self, group_id: str) -> Dict[str, Any]:
        """Get group by ID."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url(f"/groups/{group_id}"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_group(
        self, name: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new project group."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/groups"),
                headers=self.headers,
                json={"name": name, "description": description},
            )
            response.raise_for_status()
            return response.json()

    async def update_group(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a project group."""
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.put(
                self._url(f"/groups/{group_id}"),
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def delete_group(self, group_id: str) -> bool:
        """Delete a project group."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.delete(
                self._url(f"/groups/{group_id}"),
                headers=self.headers,
            )
            return response.status_code in (200, 204)

    async def list_group_users(self, group_id: str) -> Dict[str, Any]:
        """List users with access to a group."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url(f"/groups/{group_id}/users"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def add_group_user(
        self, group_id: str, user_id: str, role: str
    ) -> Dict[str, Any]:
        """Add user to group with role."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url(f"/groups/{group_id}/users"),
                headers=self.headers,
                json={"user_id": user_id, "role": role},
            )
            response.raise_for_status()
            return response.json()

    async def remove_group_user(self, group_id: str, user_id: str) -> bool:
        """Remove user from group."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.delete(
                self._url(f"/groups/{group_id}/users/{user_id}"),
                headers=self.headers,
            )
            return response.status_code in (200, 204)

    # =========================================================================
    # Projects API
    # =========================================================================

    async def list_projects(
        self,
        group_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List projects, optionally filtered by group."""
        params = {"limit": limit, "offset": offset}
        if group_id:
            params["group_id"] = group_id

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/projects"),
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url(f"/projects/{project_id}"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_project(
        self,
        name: str,
        group_id: str,
        db_path: Optional[str] = None,
        cpg_path: Optional[str] = None,
        source_path: Optional[str] = None,
        language: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new project in a group."""
        payload = {"name": name, "group_id": group_id}
        if db_path:
            payload["db_path"] = db_path
        if cpg_path:
            payload["cpg_path"] = cpg_path
        if source_path:
            payload["source_path"] = source_path
        if language:
            payload["language"] = language
        if description:
            payload["description"] = description

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/projects"),
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def update_project(
        self, project_id: str, **kwargs
    ) -> Dict[str, Any]:
        """Update project attributes."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.put(
                self._url(f"/projects/{project_id}"),
                headers=self.headers,
                json=kwargs,
            )
            response.raise_for_status()
            return response.json()

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.delete(
                self._url(f"/projects/{project_id}"),
                headers=self.headers,
            )
            return response.status_code in (200, 204)

    async def activate_project(self, project_id: str) -> Dict[str, Any]:
        """Set project as active in its group."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url(f"/projects/{project_id}/activate"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_active_project(self) -> Optional[Dict[str, Any]]:
        """Get currently active project for user."""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(
                    self._url("/projects/active/current"),
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    # =========================================================================
    # Import API
    # =========================================================================

    async def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/import/languages"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_server_status(self) -> Dict[str, Any]:
        """Get Joern server status."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/import/server/status"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def start_import(
        self,
        source: str,
        language: Optional[str] = None,
        group_id: Optional[str] = None,
        project_name: Optional[str] = None,
        mode: str = "FULL",
        **options,
    ) -> Dict[str, Any]:
        """
        Start a project import job.

        Args:
            source: Repository URL or local path
            language: Programming language (auto-detect if None)
            group_id: Target group ID
            project_name: Project name (derived from source if None)
            mode: Import mode (FULL, SELECTIVE, INCREMENTAL)
            **options: Additional import options

        Returns:
            Import job info with job_id
        """
        # Determine if source is URL or path
        if source.startswith(("http://", "https://", "git@")):
            payload = {"repo_url": source}
        else:
            payload = {"local_path": source}

        if language:
            payload["language"] = language
        if group_id:
            payload["group_id"] = group_id
        if project_name:
            payload["project_name"] = project_name
        payload["mode"] = mode
        payload.update(options)

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/import/start"),
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_import_status(self, job_id: str) -> Dict[str, Any]:
        """Get import job status."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url(f"/import/status/{job_id}"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_import_jobs(
        self,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List import jobs."""
        params = {"limit": limit}
        if status:
            params["status"] = status

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/import/jobs"),
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def cancel_import(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running import job."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.delete(
                self._url(f"/import/cancel/{job_id}"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def watch_import_progress(
        self,
        job_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Watch import progress via WebSocket.

        Args:
            job_id: Import job ID
            callback: Function to call with progress updates
        """
        try:
            import websockets
        except ImportError:
            logger.warning("websockets not installed, falling back to polling")
            await self._poll_import_progress(job_id, callback)
            return

        ws_url = f"{self.config.ws_url}/jobs/{job_id}"
        if self._token:
            ws_url += f"?token={self._token}"

        try:
            async with websockets.connect(
                ws_url,
                close_timeout=10,
                ping_interval=30,
            ) as ws:
                async for message in ws:
                    try:
                        data = json.loads(message)
                        callback(data)

                        # Check for terminal states
                        status = data.get("status", "")
                        if status in ("completed", "failed", "cancelled"):
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid WebSocket message: {message}")

        except Exception as e:
            logger.error(f"WebSocket error: {e}, falling back to polling")
            await self._poll_import_progress(job_id, callback)

    async def _poll_import_progress(
        self,
        job_id: str,
        callback: Callable[[Dict[str, Any]], None],
        interval: float = 2.0,
    ) -> None:
        """Poll import progress as fallback."""
        while True:
            try:
                status = await self.get_import_status(job_id)
                callback(status)

                if status.get("status") in ("completed", "failed", "cancelled"):
                    break

                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                break

    # =========================================================================
    # Sessions API
    # =========================================================================

    async def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List chat sessions."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/sessions"),
                headers=self.headers,
                params={"page": page, "page_size": page_size},
            )
            response.raise_for_status()
            return response.json()

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session with dialogue history."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url(f"/sessions/{session_id}"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_session(
        self,
        scenario_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create a new chat session."""
        payload = {}
        if scenario_id:
            payload["scenario_id"] = scenario_id
        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url("/sessions"),
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def update_session(
        self,
        session_id: str,
        scenario_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Update session attributes."""
        payload = {}
        if scenario_id is not None:
            payload["scenario_id"] = scenario_id
        if metadata is not None:
            payload["metadata"] = metadata

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.patch(
                self._url(f"/sessions/{session_id}"),
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.delete(
                self._url(f"/sessions/{session_id}"),
                headers=self.headers,
            )
            return response.status_code in (200, 204)

    async def export_session_history(
        self,
        session_id: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Export session history."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                self._url(f"/history/{session_id}/export"),
                headers=self.headers,
                json={"format": format},
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # Health API
    # =========================================================================

    async def get_health(self) -> Dict[str, Any]:
        """Get system health status."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/health"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_version(self) -> Dict[str, Any]:
        """Get API version info."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/health/version"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # Statistics API
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get general system statistics."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/stats"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_scenario_stats(self) -> Dict[str, Any]:
        """Get scenario usage statistics."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/stats/scenarios"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance metrics."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(
                self._url("/stats/performance"),
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
