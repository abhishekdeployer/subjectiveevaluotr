"""
Session management for handling concurrent users with isolation
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
from schemas import SessionInfo, FileType

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions for concurrent evaluation processing
    Ensures complete isolation between users
    """
    
    def __init__(self, max_sessions: int = 1000, session_timeout_minutes: int = 30):
        """
        Initialize session manager
        
        Args:
            max_sessions: Maximum concurrent sessions
            session_timeout_minutes: Session timeout in minutes
        """
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.active_sessions: Dict[str, SessionInfo] = {}
        self.session_data: Dict[str, dict] = {}  # Stores temporary session data
        self.lock = asyncio.Lock()
    
    async def create_session(self, question: str, file_data: bytes, file_type: str) -> str:
        """
        Create a new isolated session for a user
        
        Args:
            question: User's question
            file_data: Answer file content
            file_type: "image" or "pdf"
            
        Returns:
            session_id: Unique session identifier
            
        Raises:
            Exception: If max sessions exceeded
        """
        async with self.lock:
            # Check session limits
            if len(self.active_sessions) >= self.max_sessions:
                # Try to clean up expired sessions first
                await self._cleanup_expired_sessions()
                
                if len(self.active_sessions) >= self.max_sessions:
                    raise Exception(f"Maximum concurrent sessions ({self.max_sessions}) exceeded. Please try again later.")
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create session info
            session_info = SessionInfo(
                session_id=session_id,
                created_at=datetime.now(),
                question=question,
                file_size_kb=round(len(file_data) / 1024, 2),
                file_type=FileType(file_type),
                status="active"
            )
            
            # Store session
            self.active_sessions[session_id] = session_info
            self.session_data[session_id] = {
                "question": question,
                "file_data": file_data,
                "file_type": file_type,
                "created_at": datetime.now(),
                "last_accessed": datetime.now()
            }
            
            logger.info(f"Session {session_id}: Created (total active: {len(self.active_sessions)})")
            return session_id
    
    async def get_session_data(self, session_id: str) -> Optional[dict]:
        """
        Get session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dictionary or None if not found
        """
        async with self.lock:
            if session_id not in self.session_data:
                logger.warning(f"Session {session_id}: Not found")
                return None
            
            # Update last accessed time
            self.session_data[session_id]["last_accessed"] = datetime.now()
            return self.session_data[session_id].copy()
    
    async def update_session_status(self, session_id: str, status: str):
        """
        Update session status
        
        Args:
            session_id: Session identifier
            status: New status
        """
        async with self.lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id].status = status
                logger.debug(f"Session {session_id}: Status updated to {status}")
    
    async def cleanup_session(self, session_id: str):
        """
        Clean up a specific session
        
        Args:
            session_id: Session to clean up
        """
        async with self.lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            if session_id in self.session_data:
                # Clear sensitive data
                self.session_data[session_id].clear()
                del self.session_data[session_id]
            
            logger.info(f"Session {session_id}: Cleaned up")
    
    async def _cleanup_expired_sessions(self):
        """
        Clean up expired sessions (internal method)
        """
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session_info in self.active_sessions.items():
            if now - session_info.created_at > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.cleanup_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def periodic_cleanup(self):
        """
        Periodic cleanup task (should be run in background)
        """
        while True:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Session cleanup error: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def get_session_stats(self) -> dict:
        """
        Get session statistics
        
        Returns:
            Dictionary with session stats
        """
        now = datetime.now()
        total_sessions = len(self.active_sessions)
        
        # Count sessions by age
        session_ages = []
        for session_info in self.active_sessions.values():
            age_minutes = (now - session_info.created_at).total_seconds() / 60
            session_ages.append(age_minutes)
        
        stats = {
            "total_active_sessions": total_sessions,
            "max_sessions": self.max_sessions,
            "session_utilization_percent": round((total_sessions / self.max_sessions) * 100, 1),
            "average_session_age_minutes": round(sum(session_ages) / len(session_ages), 1) if session_ages else 0,
            "timeout_minutes": self.session_timeout.total_seconds() / 60
        }
        
        return stats
    
    async def force_cleanup_all(self):
        """
        Force cleanup all sessions (for testing or emergency)
        """
        async with self.lock:
            session_count = len(self.active_sessions)
            self.active_sessions.clear()
            self.session_data.clear()
            logger.warning(f"Force cleaned up all {session_count} sessions")


class SessionStateManager:
    """
    Manages state for individual sessions during evaluation workflow
    """
    
    def __init__(self):
        self.session_states: Dict[str, dict] = {}
        self.lock = asyncio.Lock()
    
    async def init_session_state(self, session_id: str, initial_state: dict):
        """
        Initialize state for a session
        
        Args:
            session_id: Session identifier
            initial_state: Initial state dictionary
        """
        async with self.lock:
            self.session_states[session_id] = initial_state.copy()
    
    async def update_session_state(self, session_id: str, updates: dict):
        """
        Update session state
        
        Args:
            session_id: Session identifier
            updates: Dictionary of updates to apply
        """
        async with self.lock:
            if session_id not in self.session_states:
                self.session_states[session_id] = {}
            
            self.session_states[session_id].update(updates)
    
    async def get_session_state(self, session_id: str) -> dict:
        """
        Get current session state
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current state dictionary
        """
        async with self.lock:
            return self.session_states.get(session_id, {}).copy()
    
    async def clear_session_state(self, session_id: str):
        """
        Clear session state
        
        Args:
            session_id: Session identifier
        """
        async with self.lock:
            if session_id in self.session_states:
                del self.session_states[session_id]


# Global session manager instances
session_manager = SessionManager()
session_state_manager = SessionStateManager()


# Convenience functions
async def create_user_session(question: str, file_data: bytes, file_type: str) -> str:
    """
    Convenience function to create a new user session
    
    Returns:
        session_id: New session ID
    """
    return await session_manager.create_session(question, file_data, file_type)


async def get_user_session(session_id: str) -> Optional[dict]:
    """
    Convenience function to get session data
    
    Returns:
        Session data or None
    """
    return await session_manager.get_session_data(session_id)


async def cleanup_user_session(session_id: str):
    """
    Convenience function to cleanup session
    """
    await session_manager.cleanup_session(session_id)
    await session_state_manager.clear_session_state(session_id)