"""
Unit Tests for SourcePolicy SSRF Protection and Security Controls
"""

import pytest
from src.collector.policy import (
    SourcePolicy,
    SourcePolicyViolationError,
    UnsafeSourceAddressError,
)


def test_scheme_policy_default_https_only():
    """Test that default SourcePolicy permits HTTPS and rejects HTTP."""
    policy = SourcePolicy()
    parsed = policy.validate_url_scheme_and_domain("https://example.com/page")
    assert parsed.scheme == "https"

    with pytest.raises(SourcePolicyViolationError, match="URL scheme 'http' not allowed"):
        policy.validate_url_scheme_and_domain("http://example.com/page")


def test_ssrf_loopback_ip_blocked():
    """Test that SSRF checks block loopback IPs (127.0.0.1, localhost)."""
    policy = SourcePolicy()
    with pytest.raises(UnsafeSourceAddressError, match="prohibited address"):
        policy.validate_ip_address_safety("127.0.0.1")

    with pytest.raises(UnsafeSourceAddressError, match="prohibited address"):
        policy.validate_ip_address_safety("localhost")


def test_ssrf_aws_metadata_ip_blocked():
    """Test that SSRF checks block AWS metadata IP (169.254.169.254)."""
    policy = SourcePolicy()
    with pytest.raises(UnsafeSourceAddressError, match="prohibited address"):
        policy.validate_ip_address_safety("169.254.169.254")


def test_ssrf_private_ip_ranges_blocked():
    """Test that SSRF checks block private IP ranges (10.0.0.1, 192.168.1.1)."""
    policy = SourcePolicy()
    with pytest.raises(UnsafeSourceAddressError, match="prohibited address"):
        policy.validate_ip_address_safety("10.0.0.1")

    with pytest.raises(UnsafeSourceAddressError, match="prohibited address"):
        policy.validate_ip_address_safety("192.168.1.1")


def test_domain_blacklist():
    """Test domain blacklist enforcement."""
    policy = SourcePolicy(blocked_domains=["malicious-site.com"])
    with pytest.raises(SourcePolicyViolationError, match="explicitly blocked by policy"):
        policy.validate_url_scheme_and_domain("https://malicious-site.com/bad")


def test_content_type_validation():
    """Test response Content-Type header policy validation."""
    policy = SourcePolicy()
    assert policy.validate_content_type("text/html; charset=utf-8") == "text/html"

    with pytest.raises(SourcePolicyViolationError, match="Content-Type 'application/pdf' not permitted"):
        policy.validate_content_type("application/pdf")
