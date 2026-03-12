"""
Session tracker for associating visitor IPs with their search engine referral source.
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SessionTracker:
    """
    Tracks visitor sessions by IP address and stores their first
    external search engine referral (domain + keyword).

    In a real-world scenario, sessions would be identified by cookies
    or visitor IDs. For this exercise, IP address is used as the
    session identifier.
    """

    def __init__(self):
        self._sessions: Dict[str, Tuple[str, str]] = {}
        logger.debug("SessionTracker initialized")

    def track(self, ip: str, search_engine_domain: str, keyword: str) -> None:
        """
        Record the search engine referral for a visitor's session.
        Only the first search engine referral per IP is stored.

        Args:
            ip: Visitor's IP address.
            search_engine_domain: e.g., 'google.com'
            keyword: The search keyword used.
        """
        if ip not in self._sessions:
            self._sessions[ip] = (search_engine_domain, keyword)
            logger.info("New session tracked: ip=%s, engine=%s, keyword='%s'",
                        ip, search_engine_domain, keyword)
        else:
            logger.debug("Session already exists for ip=%s (engine=%s, keyword='%s'). "
                         "Ignoring new referral: engine=%s, keyword='%s'",
                         ip, self._sessions[ip][0], self._sessions[ip][1],
                         search_engine_domain, keyword)

    def get_referral(self, ip: str) -> Optional[Tuple[str, str]]:
        """
        Retrieve the search engine referral for a given IP.

        Args:
            ip: Visitor's IP address.

        Returns:
            Tuple of (search_engine_domain, keyword) or None if the
            visitor did not arrive via a search engine.
        """
        return self._sessions.get(ip)

    def has_referral(self, ip: str) -> bool:
        """Check if an IP has a recorded search engine referral."""
        return ip in self._sessions

    @property
    def total_sessions(self) -> int:
        """Return the total number of tracked sessions."""
        return len(self._sessions)
