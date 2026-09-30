import random
import re
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.address import Address
from app.core.exceptions import PatternExhaustedError
from app.core.logging import logger


@dataclass
class IdPattern:
    name: str
    pattern: str
    enabled: bool
    priority: int
    description: str

    def calculate_capacity(self) -> int:
        """
        Calculate total possible combinations based on the pattern symbols:
        L = 26 letters (a-z)
        D = 10 digits (0-9)
        YY = constant year suffix (1 combination per year)
        """
        cap = 1
        i = 0
        p = self.pattern
        while i < len(p):
            if p[i:i+2] == "YY":
                i += 2
            elif p[i] == "L":
                cap *= 26
                i += 1
            elif p[i] == "D":
                cap *= 10
                i += 1
            else:
                i += 1
        return cap

    def matches(self, public_id: str, year_suffix: str) -> bool:
        """Test if a 6-character public ID matches this pattern structure for the year."""
        if len(public_id) != 6:
            return False
        if not public_id.endswith(year_suffix):
            return False

        # Build regex for pattern prefix
        regex_parts = []
        i = 0
        p = self.pattern
        while i < len(p):
            if p[i:i+2] == "YY":
                regex_parts.append(re.escape(year_suffix))
                i += 2
            elif p[i] == "L":
                regex_parts.append("[a-z]")
                i += 1
            elif p[i] == "D":
                regex_parts.append("[0-9]")
                i += 1
            else:
                regex_parts.append(re.escape(p[i]))
                i += 1
        regex = f"^{''.join(regex_parts)}$"
        return bool(re.match(regex, public_id))

    def generate_candidate(self, year_suffix: str) -> str:
        """Generate a random candidate following this pattern."""
        chars = []
        i = 0
        p = self.pattern
        while i < len(p):
            if p[i:i+2] == "YY":
                chars.append(year_suffix)
                i += 2
            elif p[i] == "L":
                chars.append(random.choice("abcdefghijklmnopqrstuvwxyz"))
                i += 1
            elif p[i] == "D":
                chars.append(random.choice("0123456789"))
                i += 1
            else:
                chars.append(p[i])
                i += 1
        return "".join(chars).lower()


# Configured Staged Patterns
DEFAULT_PATTERNS: List[IdPattern] = [
    IdPattern(
        name="stage_1",
        pattern="LLDDYY",
        enabled=True,
        priority=1,
        description="Default 2-letter + 2-digit + year (67,600 combinations/yr)"
    ),
    IdPattern(
        name="stage_2",
        pattern="LDDDYY",
        enabled=True,
        priority=2,
        description="Stage 2: 1-letter + 3-digit + year (26,000 combinations/yr)"
    ),
    IdPattern(
        name="stage_3",
        pattern="DLLDYY",
        enabled=True,
        priority=3,
        description="Stage 3: 1-digit + 2-letter + 1-digit + year (67,600 combinations/yr)"
    ),
    IdPattern(
        name="stage_4",
        pattern="DDLLYY",
        enabled=True,
        priority=4,
        description="Stage 4: 2-digit + 2-letter + year (67,600 combinations/yr)"
    ),
    IdPattern(
        name="stage_5",
        pattern="LLLLYY",
        enabled=True,
        priority=5,
        description="Stage 5: 4-letter + year (456,976 combinations/yr)"
    ),
]


class PublicIdGenerator:
    """
    Dedicated generator for 6-character Public Address IDs.
    Enforces staged progression, database uniqueness, lowercase normalization,
    and exhaustion handling.
    """
    def __init__(self, patterns: Optional[List[IdPattern]] = None):
        self.patterns = patterns or DEFAULT_PATTERNS
        self.patterns.sort(key=lambda p: p.priority)

    def get_year_suffix(self, year: Optional[int] = None) -> str:
        """Get 2-digit year suffix e.g. 2026 -> '26'."""
        if year is None:
            year = datetime.now(timezone.utc).year
        return f"{year % 100:02d}"

    def count_used_ids_for_pattern(self, db: Session, pattern: IdPattern, year: int) -> int:
        """Count how many addresses in database currently match this pattern for given year."""
        year_suffix = self.get_year_suffix(year)
        # Fetch all public_ids ending with the year_suffix
        results = db.query(Address.public_id).filter(Address.public_id.like(f"%{year_suffix}")).all()
        count = sum(1 for (pid,) in results if pattern.matches(pid, year_suffix))
        return count

    def get_pattern_statistics(self, db: Session, year: Optional[int] = None) -> List[Dict]:
        """
        Return comprehensive capacity monitoring data for all patterns.
        Used by Admin ID Generator panel.
        """
        if year is None:
            year = datetime.now(timezone.utc).year
        year_suffix = self.get_year_suffix(year)

        # Get all IDs ending in year_suffix
        results = db.query(Address.public_id).filter(Address.public_id.like(f"%{year_suffix}")).all()
        id_list = [pid for (pid,) in results]

        stats = []
        found_active = False

        for pattern in self.patterns:
            capacity = pattern.calculate_capacity()
            used = sum(1 for pid in id_list if pattern.matches(pid, year_suffix))
            remaining = max(0, capacity - used)

            if not pattern.enabled:
                status = "DISABLED"
            elif used >= capacity:
                status = "EXHAUSTED"
            elif not found_active:
                status = "ACTIVE"
                found_active = True
            else:
                status = "STANDBY"

            stats.append({
                "name": pattern.name,
                "pattern": pattern.pattern,
                "priority": pattern.priority,
                "enabled": pattern.enabled,
                "description": pattern.description,
                "capacity": capacity,
                "used": used,
                "remaining": remaining,
                "percentage_used": round((used / capacity) * 100, 2) if capacity > 0 else 0,
                "status": status
            })

        return stats

    def generate(self, db: Session, year: Optional[int] = None, max_attempts_per_pattern: int = 50) -> str:
        """
        Generate next unique 6-character Public Address ID.
        Iterates patterns by priority:
        1. Checks if pattern has remaining capacity.
        2. Tries generating candidates.
        3. Verifies uniqueness against database.
        4. If pattern exhausted, progresses to next pattern.
        5. If all patterns exhausted, raises PatternExhaustedError.
        """
        if year is None:
            year = datetime.now(timezone.utc).year
        year_suffix = self.get_year_suffix(year)

        # Preload existing IDs for this year to avoid repeated DB queries during generation
        existing_ids = {
            pid.lower() for (pid,) in
            db.query(Address.public_id).filter(Address.public_id.like(f"%{year_suffix}")).all()
        }

        for pattern in self.patterns:
            if not pattern.enabled:
                continue

            capacity = pattern.calculate_capacity()
            used_count = sum(1 for pid in existing_ids if pattern.matches(pid, year_suffix))

            if used_count >= capacity:
                logger.info(f"Pattern {pattern.name} ({pattern.pattern}) is exhausted for year {year}. Advancing.")
                continue

            # Attempt random generation within active pattern
            for _ in range(max_attempts_per_pattern):
                candidate = pattern.generate_candidate(year_suffix).lower()
                if candidate not in existing_ids:
                    # Final database check for absolute safety
                    db_exists = db.query(Address.id).filter(Address.public_id == candidate).first()
                    if not db_exists:
                        logger.info(f"Generated Public ID: '{candidate}' using pattern '{pattern.name}'")
                        return candidate
                    else:
                        existing_ids.add(candidate)

            # If repeated random sampling had collisions (high utilization), do sequential scan
            logger.info(f"High utilization for pattern {pattern.name}. Running fallback scan.")
            candidate = self._find_first_available(pattern, year_suffix, existing_ids)
            if candidate:
                return candidate

        # All enabled patterns exhausted!
        logger.error(f"All Public ID patterns exhausted for year {year}!")
        raise PatternExhaustedError(f"No Public Address IDs available for year {year}.")

    def _find_first_available(self, pattern: IdPattern, year_suffix: str, existing_ids: set) -> Optional[str]:
        """Exhaustive search fallback when pattern is >95% full."""
        # For Stage 1: LLDDYY -> 26*26*100
        p = pattern.pattern
        if p == "LLDDYY":
            import itertools
            import string
            for l1 in string.ascii_lowercase:
                for l2 in string.ascii_lowercase:
                    for d in range(100):
                        cand = f"{l1}{l2}{d:02d}{year_suffix}"
                        if cand not in existing_ids:
                            return cand
        elif p == "LDDDYY":
            import string
            for l in string.ascii_lowercase:
                for d in range(1000):
                    cand = f"{l}{d:03d}{year_suffix}"
                    if cand not in existing_ids:
                        return cand
        return None


public_id_generator = PublicIdGenerator()
