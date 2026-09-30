from datetime import date
from app.services.auth_service import AuthService
from app.services.address_service import AddressService
from app.services.resolver_service import ResolverService
from app.schemas.auth import UserRegisterRequest
from app.schemas.address import AddressCreate, AddressUpdate


def test_full_acceptance_scenario(client, db_session):
    """
    Acceptance Test Scenario from Requirement 79:
    1. Register user:
       Father: Muhammad, Mother: Ayesha, CNIC ending: 123, DOB: 01-01-1991.
       Generated Edit ID: MA12301011991
    2. Create address in Taunsa Sharif.
       System generates a 6-character Public ID following LLDDYY (e.g. ab1226).
    3. Resolve /a/{public_id} and /api/v1/resolve/{public_id}:
       Verify display text contains:
       'House 25, Street 4, Near Main Market, Taunsa Sharif, Dera Ghazi Khan, Punjab, Pakistan'
    4. Edit address to House 30, Street 7, Near Central Market.
       Verify Public ID remains unchanged.
    5. Resolve the same URL /a/{public_id}:
       Verify display text updates to new address!
    """
    auth_service = AuthService(db_session)
    reg_req = UserRegisterRequest(
        username="bilal_acceptance",
        email="bilal_acceptance@example.com",
        password="ValidPassword123!",
        full_name="Muhammad Bilal",
        father_name="Muhammad",
        mother_name="Ayesha",
        cnic_or_id_card="32203-1234567-123",
        date_of_birth=date(1991, 1, 1)
    )
    user, edit_id = auth_service.register(reg_req)

    # 1. Assert Edit ID matches formula exactly: [PublicID][Father][Mother][CNICLast3][DOBYY]
    assert len(edit_id) == 13
    assert edit_id == f"{user.public_id}MA12391"
    assert edit_id[6:] == "MA12391"

    # 2. Create Address
    address_service = AddressService(db_session)
    addr_data = AddressCreate(
        address_type="DELIVERY",
        location_scope="LOCAL",
        recipient_name="Muhammad Bilal",
        country="Pakistan",
        country_code="PK",
        province_state="Punjab",
        region_division="Dera Ghazi Khan Division",
        district="Dera Ghazi Khan",
        tehsil="Taunsa Sharif",
        city="Taunsa Sharif",
        house_number="25",
        street="Street 4",
        landmark="Near Main Market",
        destination_url="https://maps.google.com",
        redirect_seconds=3
    )
    address = address_service.create_address(user.id, addr_data, year=2026)

    # Assert Public ID is exactly 6 characters following LLDDYY
    public_id = address.public_id
    assert len(public_id) == 6
    assert public_id[0].isalpha()
    assert public_id[1].isalpha()
    assert public_id[2].isdigit()
    assert public_id[3].isdigit()
    assert public_id[4:] == "26"

    # 3. Resolve via Web (both direct /{public_id} and legacy /a/{public_id}) & API
    web_res = client.get(f"/{public_id}")
    assert web_res.status_code == 200
    assert "House 25, Street 4" in web_res.text
    assert "Taunsa Sharif" in web_res.text

    web_res_legacy = client.get(f"/a/{public_id}")
    assert web_res_legacy.status_code == 200
    assert "House 25, Street 4" in web_res_legacy.text
    assert "Taunsa Sharif" in web_res_legacy.text
    assert "Near Main Market" in web_res_legacy.text
    assert "Punjab, Pakistan" in web_res_legacy.text

    api_res = client.get(f"/api/v1/resolve/{public_id}")
    assert api_res.status_code == 200
    res_json = api_res.json()
    assert res_json["public_id"] == public_id
    assert res_json["city"] == "Taunsa Sharif"
    assert res_json["country"] == "Pakistan"
    assert "House 25, Street 4" in res_json["display_text"]

    # 4. Edit Address to House 30, Street 7, Near Central Market
    updated_addr = address_service.update_address(
        public_id=public_id,
        user_id=user.id,
        data=AddressUpdate(
            house_number="30",
            street="Street 7",
            landmark="Near Central Market"
        )
    )

    # CRITICAL: Public ID must remain IDENTICAL!
    assert updated_addr.public_id == public_id

    # 5. Resolve same URL again and verify updated address
    web_res2 = client.get(f"/a/{public_id}")
    assert web_res2.status_code == 200
    assert "House 30, Street 7" in web_res2.text
    assert "Near Central Market" in web_res2.text
    assert "House 25" not in web_res2.text

    api_res2 = client.get(f"/api/v1/resolve/{public_id}")
    assert api_res2.status_code == 200
    assert "House 30, Street 7" in api_res2.json()["display_text"]
