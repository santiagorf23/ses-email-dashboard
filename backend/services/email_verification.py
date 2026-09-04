import logging
import re
import dns.resolver
import socket
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Known disposable email domains (top 100+)
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.net", "tempmail.com",
    "throwaway.email", "temp-mail.org", "fakeinbox.com", "sharklasers.com",
    "guerrillamailblock.com", "grr.la", "dispostable.com", "yopmail.com",
    "yopmail.fr", "trashmail.com", "maildrop.cc", "tempail.com",
    "tempr.email", "temp-mail.io", "mohmal.com", "getnada.com",
    "emailondeck.com", "33mail.com", "mytemp.email", "burnermail.io",
    "harakirimail.com", "tmail.ws", "tmpmail.net", "tmpmail.org",
    "mailnesia.com", "tempm.com", "tempinbox.com", "discard.email",
    "discardmail.com", "discardmail.de", "mailcatch.com", "mailexpire.com",
    "mailnull.com", "spambox.us", "spamgourmet.com", "spamherelots.com",
    "spamhereplease.com", "spamhole.com", "spamify.com", "spaminator.de",
    "spamkill.info", "spaml.com", "spaml.de", "spammotel.com",
    "spamobox.com", "spamoff.de", "speed.1s.fr", "superrito.com",
    "teleworm.us", "tempalias.com", "tempemail.biz", "tempemail.co.za",
    "tempemail.com", "tempemail.net", "tempinbox.co.uk", "tempmail.eu",
    "tempmail.it", "tempmail2.com", "tempmaildemo.com", "tempmailer.com",
    "tempmailer.de", "tempomail.fr", "temporarily.de", "tempthe.net",
    "thankyou2010.com", "thisisnotmyrealemail.com", "throwam.com",
    "tittbit.in", "tizi.com", "tmailinator.com", "toiea.com",
    "toomail.biz", "topranklist.com", "tradermail.info", "trash-destination.com",
    "trashdevil.com", "trashemail.de", "trashmail.at", "trashmail.me",
    "trashmail.net", "trashmail.org", "trashmail.ws", "trashmailer.com",
    "trashymail.com", "trashymail.net", "trialmail.de", "trbvm.com",
    "trbvo.com", "trbvn.com", "turbopostage.com", "tuts4you.com",
    "tvnet.com.au", "tvscreencast.com", "twltter.com", "tyldd.com",
    "uggsrock.com", "umail.net", "upliftnet.com", "venompen.com",
    "veryrealliemail.com", "viditag.com", "viewcastmedia.com",
    "viewcastmedia.net", "viewcastmedia.org", "vomoto.com", "vpn021.com",
    "wetrainbayarea.com", "wetrainbayarea.org", "wh4f.org", "whatiaas.com",
    "whatpaas.com", "whyspam.me", "wickmail.net", "wilemail.com",
    "willhackforfood.biz", "willselfdestruct.com", "winemaven.info",
    "wronghead.com", "wuzup.net", "wuzupmail.net", "wwwnew.eu",
    "xagloo.com", "xemaps.com", "xents.com", "xjoi.com",
    "xmaily.com", "xoxy.net", "yapped.net", "yeah.net",
    "yep.it", "yogamaven.com", "yomail.info", "yopmail.gq",
    "yopmail.info", "yopmail.org", "yourdomain.com", "ypmail.webarnak.fr",
    "yuurok.com", "zehnminutenmail.de", "10minutemail.com",
    "10minutemail.co.za", "guerrillamail.com", "guerrillamail.net",
    "maildrop.cc", "mailinator.com", "tempmail.com", "throwaway.email"
}


class VerificationResult(BaseModel):
    """Result of email verification."""
    email: str
    is_valid_format: bool
    domain_exists: bool
    mx_records: list[str]
    is_disposable: bool
    is_free_provider: bool
    suggestion: Optional[str] = None
    score: int  # 0-100
    status: str  # valid, risky, invalid


class BulkVerificationResult(BaseModel):
    """Result of bulk email verification."""
    total: int
    valid: int
    risky: int
    invalid: int
    results: list[VerificationResult]


# Free email providers
FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com",
    "aol.com", "icloud.com", "mail.com", "protonmail.com", "proton.me",
    "zoho.com", "yandex.com", "gmx.com", "fastmail.com", "tutanota.com",
    "163.com", "126.com", "qq.com", "sina.com", "sohu.com",
    "terra.com.br", "bol.com.br", "uol.com.br", "r7.com", "ig.com.br",
    "hotmail.fr", "hotmail.be", "hotmail.de", "hotmail.it", "hotmail.es",
    "live.fr", "live.de", "live.it", "live.es", "live.nl",
    "outlook.fr", "outlook.de", "outlook.it", "outlook.es", "outlook.nl",
    "yahoo.co.jp", "yahoo.co.uk", "yahoo.co.in", "yahoo.ca", "yahoo.com.au",
    "yahoo.com.br", "yahoo.com.mx", "yahoo.com.ar"
}


def verify_email(email: str) -> VerificationResult:
    """
    Verify a single email address.
    
    Checks:
    1. Format validation
    2. Domain existence
    3. MX records
    4. Disposable domain detection
    5. Free provider detection
    """
    email = email.strip().lower()
    
    # 1. Format validation
    is_valid_format = _is_valid_email_format(email)
    
    if not is_valid_format:
        return VerificationResult(
            email=email,
            is_valid_format=False,
            domain_exists=False,
            mx_records=[],
            is_disposable=False,
            is_free_provider=False,
            score=0,
            status="invalid"
        )
    
    # Extract domain
    domain = email.split("@")[1]
    
    # 2. Domain existence
    domain_exists = _check_domain_exists(domain)
    
    # 3. MX records
    mx_records = _get_mx_records(domain)
    
    # 4. Disposable detection
    is_disposable = domain in DISPOSABLE_DOMAINS
    
    # 5. Free provider detection
    is_free_provider = domain in FREE_PROVIDERS
    
    # Calculate score
    score = _calculate_verification_score(
        is_valid_format, domain_exists, mx_records, is_disposable, is_free_provider
    )
    
    # Determine status
    if score >= 80:
        status = "valid"
    elif score >= 50:
        status = "risky"
    else:
        status = "invalid"
    
    # Generate suggestion if needed
    suggestion = None
    if not domain_exists and mx_records:
        suggestion = f"El dominio {domain} tiene registros MX pero no existe"
    elif is_disposable:
        suggestion = "Este es un servicio de email desechable"
    
    return VerificationResult(
        email=email,
        is_valid_format=is_valid_format,
        domain_exists=domain_exists,
        mx_records=mx_records,
        is_disposable=is_disposable,
        is_free_provider=is_free_provider,
        suggestion=suggestion,
        score=score,
        status=status
    )


def verify_bulk_emails(emails: list[str]) -> BulkVerificationResult:
    """Verify a list of email addresses."""
    results = [verify_email(email) for email in emails]
    
    valid = sum(1 for r in results if r.status == "valid")
    risky = sum(1 for r in results if r.status == "risky")
    invalid = sum(1 for r in results if r.status == "invalid")
    
    return BulkVerificationResult(
        total=len(results),
        valid=valid,
        risky=risky,
        invalid=invalid,
        results=results
    )


def _is_valid_email_format(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _check_domain_exists(domain: str) -> bool:
    """Check if domain exists via DNS."""
    try:
        dns.resolver.resolve(domain, 'A')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return False
    except Exception as e:
        logger.warning(f"DNS lookup failed for {domain}: {e}")
        return False


def _get_mx_records(domain: str) -> list[str]:
    """Get MX records for domain."""
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return [str(record.exchange).rstrip('.') for record in mx_records]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return []
    except Exception as e:
        logger.warning(f"MX lookup failed for {domain}: {e}")
        return []


def _calculate_verification_score(
    is_valid_format: bool,
    domain_exists: bool,
    mx_records: list[str],
    is_disposable: bool,
    is_free_provider: bool
) -> int:
    """Calculate verification score (0-100)."""
    score = 0
    
    # Format validation (30 points)
    if is_valid_format:
        score += 30
    
    # Domain exists (30 points)
    if domain_exists:
        score += 30
    
    # MX records (25 points)
    if mx_records:
        score += 25
    
    # Disposable penalty (-40 points)
    if is_disposable:
        score -= 40
    
    # Free provider penalty (-10 points)
    if is_free_provider:
        score -= 10
    
    return max(0, min(100, score))


def check_disposable_domain(domain: str) -> bool:
    """Check if a domain is a disposable email provider."""
    return domain.lower() in DISPOSABLE_DOMAINS


def add_disposable_domain(domain: str) -> None:
    """Add a domain to the disposable list."""
    DISPOSABLE_DOMAINS.add(domain.lower())


def remove_disposable_domain(domain: str) -> None:
    """Remove a domain from the disposable list."""
    DISPOSABLE_DOMAINS.discard(domain.lower())
