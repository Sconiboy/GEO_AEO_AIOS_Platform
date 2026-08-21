"""
Source Policy & SSRF Security Controls for Live Content Collection
"""

import ipaddress
import socket
import urllib.parse
from typing import List, Optional, Set
from pydantic import BaseModel, Field


class SourcePolicyViolationError(Exception):
    """Raised when a URL violates the strict SourcePolicy rules."""
    pass


class UnsafeSourceAddressError(SourcePolicyViolationError):
    """Raised when a URL resolves to a loopback, private, or link-local IP address (SSRF Protection)."""
    pass


class SourcePolicy(BaseModel):
    """
    Enforces security, network transport, and content safety rules for web source collection.
    """

    allowed_schemes: Set[str] = Field(
        default_factory=lambda: {"https"},
        description="Allowed URI schemes (default: https only)",
    )
    max_redirects: int = Field(default=3, ge=0, le=10)
    max_response_bytes: int = Field(
        default=5 * 1024 * 1024, ge=1024, description="Maximum allowed response payload (default: 5MB)"
    )
    allowed_content_types: List[str] = Field(
        default_factory=lambda: [
            "text/html",
            "text/plain",
            "application/xhtml+xml",
            "application/json",
        ]
    )
    timeout_seconds: float = Field(default=10.0, ge=0.5, le=60.0)
    block_private_ips: bool = Field(
        default=True,
        description="Block loopback, private, link-local (e.g. 169.254.169.254), and reserved IP ranges",
    )
    allowed_domains: Optional[List[str]] = Field(
        default=None, description="Optional domain whitelist"
    )
    blocked_domains: List[str] = Field(
        default_factory=list, description="Optional domain blacklist"
    )

    def validate_url_scheme_and_domain(self, url: str) -> urllib.parse.ParseResult:
        """Validates URI scheme and domain rules."""
        parsed = urllib.parse.urlparse(url)

        if not parsed.scheme or parsed.scheme.lower() not in self.allowed_schemes:
            raise SourcePolicyViolationError(
                f"URL scheme '{parsed.scheme}' not allowed. Permitted: {sorted(list(self.allowed_schemes))}"
            )

        hostname = parsed.hostname
        if not hostname:
            raise SourcePolicyViolationError(f"URL '{url}' missing valid hostname.")

        clean_hostname = hostname.lower()

        if self.blocked_domains and any(
            clean_hostname == d.lower() or clean_hostname.endswith(f".{d.lower()}")
            for d in self.blocked_domains
        ):
            raise SourcePolicyViolationError(f"Domain '{clean_hostname}' is explicitly blocked by policy.")

        if self.allowed_domains and not any(
            clean_hostname == d.lower() or clean_hostname.endswith(f".{d.lower()}")
            for d in self.allowed_domains
        ):
            raise SourcePolicyViolationError(f"Domain '{clean_hostname}' is not in allowed domain whitelist.")

        return parsed

    def validate_ip_address_safety(self, hostname: str) -> str:
        """
        Resolves hostname to IP addresses and enforces SSRF protection.
        Blocks loopback, private, link-local (169.254.169.254), and reserved IPs.
        """
        if not self.block_private_ips:
            return hostname

        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise SourcePolicyViolationError(f"DNS resolution failed for hostname '{hostname}': {e}")

        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_loopback
                    or ip_obj.is_private
                    or ip_obj.is_link_local
                    or ip_obj.is_reserved
                    or ip_obj.is_multicast
                    or ip_obj.is_unspecified
                ):
                    raise UnsafeSourceAddressError(
                        f"SSRF Protection: Hostname '{hostname}' resolved to prohibited address {ip_str}"
                    )
            except ValueError:
                continue

        return hostname

    def validate_content_type(self, content_type_header: str) -> str:
        """Validates response Content-Type header against allowed policy types."""
        clean_type = content_type_header.split(";")[0].strip().lower()
        if not any(clean_type == act for act in self.allowed_content_types):
            raise SourcePolicyViolationError(
                f"Content-Type '{clean_type}' not permitted by policy. Allowed: {self.allowed_content_types}"
            )
        return clean_type
