import re
from app.services.public_id_generator import PublicIdGenerator, IdPattern
from app.models.address import Address, AddressType, LocationScope, AddressVisibility


def test_stage_1_pattern_format(db_session):
    """Test that default Stage 1 produces exact 6-character LLDDYY IDs."""
    gen = PublicIdGenerator()
    public_id = gen.generate(db_session, year=2026)

    assert len(public_id) == 6
    assert public_id == public_id.lower()
    # Check LLDDYY regex for 2026 -> 2 letters, 2 digits, ending in '26'
    assert re.match(r"^[a-z]{2}[0-9]{2}26$", public_id), f"Invalid ID generated: {public_id}"


def test_permanent_year_suffix(db_session):
    """Test year suffix calculation for different years."""
    gen = PublicIdGenerator()
    id_2026 = gen.generate(db_session, year=2026)
    assert id_2026.endswith("26")

    id_2030 = gen.generate(db_session, year=2030)
    assert id_2030.endswith("30")


def test_uniqueness_and_collision_handling(db_session, test_user):
    """Verify generator generates unique IDs and never duplicates existing database entries."""
    gen = PublicIdGenerator()
    generated = set()

    for _ in range(25):
        pid = gen.generate(db_session, year=2026)
        assert pid not in generated
        generated.add(pid)

        # Insert into DB
        addr = Address(
            public_id=pid,
            user_id=test_user.id,
            address_type=AddressType.DELIVERY,
            location_scope=LocationScope.LOCAL,
            visibility=AddressVisibility.PUBLIC,
            city="Taunsa Sharif",
            country="Pakistan",
            address_text="Sample address",
            is_active=True
        )
        db_session.add(addr)
        db_session.commit()


def test_no_premature_mixing_and_stage_exhaustion_transition(db_session):
    """
    Test that generator stays strictly on Stage 1 while it has capacity,
    and transitions to Stage 2 ONLY when Stage 1 is exhausted.
    """
    # Create test pattern generator with miniature capacity for testing
    mini_stage1 = IdPattern(
        name="test_stage_1",
        pattern="LDYY", # capacity = 26 * 10 = 260
        enabled=True,
        priority=1,
        description="Test Stage 1"
    )
    mini_stage2 = IdPattern(
        name="test_stage_2",
        pattern="DDYY", # capacity = 10 * 10 = 100
        enabled=True,
        priority=2,
        description="Test Stage 2"
    )

    custom_gen = PublicIdGenerator(patterns=[mini_stage1, mini_stage2])

    # First generation must strictly follow stage 1 (starts with letter)
    id1 = custom_gen.generate(db_session, year=2026)
    assert id1[0].isalpha()

    # Pre-populate all available stage 1 combinations for year 26 in DB
    year_suffix = "26"
    import string
    for l in string.ascii_lowercase:
        for d in range(10):
            pid = f"{l}{d}{year_suffix}"
            addr = Address(
                public_id=pid,
                user_id=1,
                address_type=AddressType.DELIVERY,
                location_scope=LocationScope.LOCAL,
                visibility=AddressVisibility.PUBLIC,
                city="Test",
                country="Pakistan",
                address_text="Test",
                is_active=True
            )
            db_session.add(addr)
    db_session.commit()

    # Now Stage 1 is 100% full! The generator MUST advance to Stage 2 (DDYY)
    next_id = custom_gen.generate(db_session, year=2026)
    assert next_id[0].isdigit() # Stage 2 starts with a digit!
    assert next_id.endswith("26")
