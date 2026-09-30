from app.services.address_service import AddressService
from app.schemas.address import AddressCreate
from app.models.access_log import AccessLog


def test_public_resolver_case_insensitivity(client, db_session, test_user):
    """
    Acceptance test requirement:
    /a/ab1226, /a/AB1226, /a/Ab1226 must all resolve to the same address!
    """
    service = AddressService(db_session)
    addr = service.create_address(
        test_user.id,
        AddressCreate(
            address_type="DELIVERY",
            location_scope="LOCAL",
            city="Taunsa Sharif",
            country="Pakistan",
            house_number="25",
            street="Street 4",
            landmark="Near Main Market",
            destination_url="https://maps.google.com",
            redirect_seconds=3
        ),
        year=2026
    )
    pid = addr.public_id

    # Test lowercase
    res_lower = client.get(f"/a/{pid.lower()}")
    assert res_lower.status_code == 200
    assert "House 25, Street 4" in res_lower.text

    # Test uppercase
    res_upper = client.get(f"/a/{pid.upper()}")
    assert res_upper.status_code == 200
    assert "House 25, Street 4" in res_upper.text

    # Test mixed case
    res_mixed = client.get(f"/a/{pid.capitalize()}")
    assert res_mixed.status_code == 200
    assert "House 25, Street 4" in res_mixed.text

    # Verify access logs were stored
    logs = db_session.query(AccessLog).filter(AccessLog.public_id == pid).all()
    assert len(logs) == 3


def test_api_resolution_does_not_leak_sensitive_data(client, db_session, test_user):
    """
    Verify /api/v1/resolve/{public_id} returns public address data
    without leaking user ID, CNIC, DOB, Edit ID, password.
    """
    service = AddressService(db_session)
    addr = service.create_address(
        test_user.id,
        AddressCreate(
            address_type="DELIVERY",
            location_scope="LOCAL",
            city="Taunsa Sharif",
            country="Pakistan",
            house_number="25",
            street="Street 4"
        ),
        year=2026
    )

    res = client.get(f"/api/v1/resolve/{addr.public_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["public_id"] == addr.public_id
    assert data["city"] == "Taunsa Sharif"
    assert data["country"] == "Pakistan"
    assert "display_text" in data

    # STRICT CHECK: Sensitive fields must NOT exist in response!
    assert "cnic" not in data
    assert "date_of_birth" not in data
    assert "edit_id" not in data
    assert "password" not in data
    assert "user_id" not in data


def test_inactive_address_returns_410(client, db_session, test_user):
    """Deactivated address returns 410 Unavailable."""
    service = AddressService(db_session)
    addr = service.create_address(
        test_user.id,
        AddressCreate(city="Lahore", country="Pakistan"),
        year=2026
    )
    service.set_active_status(addr.public_id, test_user.id, is_active=False)

    res = client.get(f"/a/{addr.public_id}")
    assert res.status_code == 410
    assert "Address Currently Unavailable" in res.text


def test_nonexistent_address_returns_404(client):
    """Unknown Public ID returns 404 Not Found."""
    res = client.get("/a/zz9926")
    assert res.status_code == 404
    assert "Address Not Found" in res.text
