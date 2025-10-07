"""
Rate limiting utilities to handle API rate limits and automatic fallback
"""

import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Tuple
import asyncio

logger = logging.getLogger(__name__)


class RateLimitTracker:
    """
    Tracks API usage and manages rate limits with automatic fallback
    """
    
    def __init__(self, max_requests: int = 1500, window_seconds: int = 86400):
        """
        Initialize rate limit tracker
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds (default: 24 hours)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.using_fallback = False
        self.fallback_start_time = None
        self.lock = asyncio.Lock()
    
    async def can_make_request(self) -> Tuple[bool, str]:
        """
        Check if we can make a request to primary API
        
        Returns:
            Tuple of (can_use_primary, recommended_source)
            recommended_source is "primary" or "fallback"
        """
        async with self.lock:
            now = datetime.now()
            
            # Remove old requests outside the window
            cutoff_time = now - timedelta(seconds=self.window_seconds)
            while self.requests and self.requests[0] < cutoff_time:
                self.requests.popleft()
            
            # Check if we're under the limit
            if len(self.requests) < self.max_requests:
                # Record this request
                self.requests.append(now)
                
                # If we were using fallback, check if we can switch back
                if self.using_fallback:
                    # Allow switch back after 1 hour of fallback usage
                    if (self.fallback_start_time and 
                        (now - self.fallback_start_time).total_seconds() > 3600):
                        self.using_fallback = False
                        self.fallback_start_time = None
                        logger.info("Rate limit: Switching back to primary API")
                
                return True, "primary"
            else:
                # Rate limit hit, use fallback
                if not self.using_fallback:
                    self.using_fallback = True
                    self.fallback_start_time = now
                    logger.warning(f"Rate limit reached ({len(self.requests)}/{self.max_requests}). Switching to fallback API")
                
                return False, "fallback"
    
    def record_request(self):
        """Record a request (for fallback API usage tracking)"""
        # For fallback, we don't track against the primary limit
        pass
    
    def force_fallback(self, duration_minutes: int = 60):
        """
        Force using fallback API for a specified duration
        
        Args:
            duration_minutes: How long to use fallback
        """
        self.using_fallback = True
        self.fallback_start_time = datetime.now()
        logger.info(f"Forced fallback mode for {duration_minutes} minutes")
    
    def reset(self):
        """Reset rate limiting (for testing or manual override)"""
        self.requests.clear()
        self.using_fallback = False
        self.fallback_start_time = None
        logger.info("Rate limiter reset")
    
    def get_status(self) -> dict:
        """
        Get current rate limiting status
        
        Returns:
            Dictionary with current status
        """
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        
        # Count requests in current window
        current_requests = sum(1 for req_time in self.requests if req_time > cutoff_time)
        
        status = {
            "current_requests": current_requests,
            "max_requests": self.max_requests,
            "requests_remaining": max(0, self.max_requests - current_requests),
            "using_fallback": self.using_fallback,
            "window_hours": self.window_seconds / 3600
        }
        
        if self.using_fallback and self.fallback_start_time:
            fallback_duration = (now - self.fallback_start_time).total_seconds() / 60
            status["fallback_duration_minutes"] = round(fallback_duration, 1)
        
        return status


class APIRateLimitHandler:
    """
    Handles rate limiting for different APIs
    """
    
    def __init__(self):
        # Configure rate limiters for different APIs
        from config import Config
        
        # Gemini (Google AI Studio) rate limiter
        self.gemini_limiter = RateLimitTracker(
            max_requests=Config.GEMINI_RATE_LIMIT_MAX,
            window_seconds=Config.GEMINI_RATE_LIMIT_WINDOW
        )
        
        # Could add other API rate limiters here
        # self.openrouter_limiter = RateLimitTracker(max_requests=X, window_seconds=Y)
    
    async def get_gemini_api_choice(self) -> Tuple[str, str]:
        """
        Get the recommended API choice for Gemini model
        
        Returns:
            Tuple of (api_source, reason)
            api_source: "google_ai_studio" or "openrouter"
        """
        can_use_primary, source = await self.gemini_limiter.can_make_request()
        
        if source == "primary":
            return "google_ai_studio", "within_rate_limit"
        else:
            return "openrouter", "rate_limit_exceeded"
    
    def record_rate_limit_hit(self, api_source: str, error_details: str = None):
        """
        Record when we hit a rate limit (for future improvements)
        
        Args:
            api_source: Which API hit the rate limit
            error_details: Error message or details
        """
        if api_source == "google_ai_studio":
            self.gemini_limiter.force_fallback(60)  # Force fallback for 1 hour
        
        logger.warning(f"Rate limit hit on {api_source}: {error_details}")
    
    def get_all_status(self) -> dict:
        """Get status of all rate limiters"""
        return {
            "gemini": self.gemini_limiter.get_status()
        }


# Global rate limit handler instance
rate_limit_handler = APIRateLimitHandler()


# Decorator for handling rate limits
def handle_rate_limit(api_source: str):
    """
    Decorator to handle rate limit errors and automatic fallback
    
    Args:
        api_source: Which API this function uses
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limit indicators
                rate_limit_indicators = [
                    "rate limit",
                    "quota exceeded", 
                    "too many requests",
                    "429",
                    "resource exhausted"
                ]
                
                if any(indicator in error_str for indicator in rate_limit_indicators):
                    logger.warning(f"Rate limit detected in {api_source}: {str(e)}")
                    rate_limit_handler.record_rate_limit_hit(api_source, str(e))
                    
                    # Re-raise with clear message
                    raise Exception(f"Rate limit exceeded for {api_source}. Switching to fallback.")
                else:
                    # Re-raise other errors as-is
                    raise
        
        return wrapper
    return decorator