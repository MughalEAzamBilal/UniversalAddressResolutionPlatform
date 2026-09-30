import pytest
from app.services.address_service import AddressService
from app.services.address_formatter import AddressFormatter
from app.schemas.address import AddressCreate, AddressUpdate
from app.core.exceptions import UnsafeDestinationError


def test_create_address_and_formatting(db_session, test_user):
    """Test address creation with clean formatting without empty commas."""
    service = AddressService(db_session)
    data = AddressCreate(
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
    addr = service.create_address(test_user.id, data, year=2026)

    assert len(addr.public_id) == 6
    assert addr.public_id.endswith("26")
    assert ", , " not in addr.address_text
    assert "House 25" in addr.address_text
    assert "Street 4" in addr.address_text
    assert "Taunsa Sharif" in addr.address_text

    # Verify Version 1 snapshot was created
    versions = service.get_versions(addr.public_id, test_user.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1


def test_public_id_stability_across_edits(db_session, test_user):
    """
    Acceptance test requirement:
    Editing House 25, Street 4 to House 30, Street 7
    MUST NOT change Public ID.
    Must archive Version 2.
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
            landmark="Near Main Market"
        ),
        year=2026
    )
    initial_public_id = addr.public_id

    # Edit address to House 30, Street 7
    updated = service.update_address(
        public_id=initial_public_id,
        user_id=test_user.id,
        data=AddressUpdate(
            house_number="30",
            street="Street 7",
            landmark="Near Central Market"
        )
    )

    # CRITICAL ASSERTION: Public ID MUST remain identical!
    assert updated.public_id == initial_public_id
    assert "House 30" in updated.address_text
    assert "Street 7" in updated.address_text

    # Check version history has 2 versions
    versions = service.get_versions(initial_public_id, test_user.id)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert "House 30" in versions[0].address_snapshot
    assert versions[1].version_number == 1
    assert "House 25" in versions[1].address_snapshot


def test_unsafe_destination_rejected():
    """Verify open redirect protection blocks javascript: or data: URIs."""
    from app.core.security import validate_destination_url

    with pytest.raises(UnsafeDestinationError):
        validate_destination_url("javascript:alert(1)")

    with pytest.raises(UnsafeDestinationError):
        validate_destination_url("data:text/html,<script>alert(1)</script>")

    with pytest.raises(UnsafeDestinationError):
        validate_destination_url("file:///etc/passwd")

    # Safe HTTP and HTTPS must pass
    assert validate_destination_url("https://example.com") == "https://example.com"
    assert validate_destination_url("http://maps.google.com") == "http://maps.google.com"


def test_unauthenticated_user_sees_create_edit_id_page(client):
    """Ensure user without login sees the Edit ID creation page with instructions instead of login redirect."""
    response = client.get("/address/new")
    assert response.status_code == 200
    assert "Create Your Edit ID Before Adding an Address" in response.text
    assert "No login, password, or email required!" in response.text
    assert "Why an Edit ID is Required" in response.text
    assert "The Edit ID Formula" in response.text
    assert "Enter Your 13-Character Edit ID" in response.text
    assert "Suggestion: How to fill your 13-Character Edit ID" in response.text


def test_passwordless_direct_address_creation_flow(client):
    """
    End-to-end verification of direct address addition:
    1. User visits /address/new -> generates Edit ID directly without password.
    2. Session is immediately set.
    3. User is directed to create address.
    4. Address is created with stable 6-character Public ID.
    """
    # 1. Submit Edit ID generation form
    edit_id_payload = {
        "full_name": "Tariq Mahmood",
        "father_name": "Mahmood",
        "mother_name": "Zubaida",
        "cnic_or_id_card": "995",
        "date_of_birth": "1995-10-25",
        "phone": "+923001112233",
        "email": "tariq@example.com",
        "public_id": "mz9926"
    }
    res = client.post("/address/create-edit-id", data=edit_id_payload, follow_redirects=False)
    assert res.status_code == 303
    assert "welcome_edit_id=mz9926MZ99595" in res.headers["Location"]
    assert "edit_session_token" in res.cookies

    # 2. Open /address/new with the session cookie
    res_page = client.get(res.headers["Location"], cookies=res.cookies)
    assert res_page.status_code == 200
    assert "Your Edit ID is Ready!" in res_page.text
    assert "mz9926MZ99595" in res_page.text
    assert "Create Smart Address" in res_page.text


def test_alphabet_dropdown_edit_id_without_fullname_or_email(client):
    """
    Verify the updated user requirements:
    1. Only alphabet initials selected for parents (no typing full names).
    2. No full name required.
    3. No email required.
    4. Enable/disable phone toggle supported.
    """
    payload = {
        "father_name": "M",
        "mother_name": "A",
        "cnic_or_id_card": "123",
        "date_of_birth": "1991-01-01",
        "enable_phone": "on",
        "phone": "+923001234567",
        "public_id": "ab1226"
    }
    res = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert res.status_code == 303
    assert "welcome_edit_id=ab1226MA12391" in res.headers["Location"]
    assert "edit_session_token" in res.cookies


    # 3. Create the address directly
    addr_payload = {
        "address_type": "RESIDENTIAL",
        "location_scope": "LOCAL",
        "visibility": "PUBLIC",
        "recipient_name": "Tariq Mahmood",
        "country": "Pakistan",
        "country_code": "PK",
        "province_state": "Punjab",
        "city": "Lahore",
        "house_number": "12-B",
        "street": "Gulberg III",
        "destination_url": "https://google.com/maps",
        "redirect_seconds": 3
    }
    res_addr = client.post("/address/new", data=addr_payload, cookies=res.cookies, follow_redirects=False)
    assert res_addr.status_code == 303
    created_url = res_addr.headers["Location"]
    assert "/view" in created_url


def test_admin_logout_clears_session(client, db_session):
    """Verify that logging out clears session cookies for administrators."""
    from app.services.auth_service import AuthService
    from app.models.user import User, UserRole, AccountStatus
    from datetime import date
    from app.core.security import hash_password, hash_edit_id

    # Create admin
    admin = User(
        username="admin_test",
        email="admintest@test.local",
        full_name="Admin Test",
        father_name="Father",
        mother_name="Mother",
        cnic_or_id_card="123",
        date_of_birth=date(1980, 1, 1),
        password_hash=hash_password("AdminPass123!"),
        edit_id_hash=hash_edit_id("FM12301011980"),
        role=UserRole.ADMIN,
        account_status=AccountStatus.ACTIVE
    )
    db_session.add(admin)
    db_session.commit()

    # Log in
    login_res = client.post("/login", data={"username": "admin_test", "password": "AdminPass123!"}, follow_redirects=False)
    assert login_res.status_code == 303
    assert "session_token" in login_res.cookies

    # Logout
    logout_res = client.get("/logout", cookies=login_res.cookies, follow_redirects=False)
    assert logout_res.status_code == 303
    # Check session cookie deleted or cleared
    assert logout_res.cookies.get("session_token") in (None, "", '""')


def test_cnic_rejects_more_than_three_digits(client):
    """Verify that entering more than 3 digits for CNIC ending is rejected."""
    payload = {
        "father_name": "M",
        "mother_name": "A",
        "cnic_or_id_card": "12345",  # > 3 digits!
        "date_of_birth": "1995-05-15",
    }
    res = client.post("/address/create-edit-id", data=payload)
    assert res.status_code == 400
    assert "CNIC ending must not exceed 3 digit numbers" in res.text


def test_cnic_accepts_valid_three_digits(client):
    """Verify that entering exactly 3 digits for CNIC ending succeeds."""
    payload = {
        "father_name": "M",
        "mother_name": "A",
        "cnic_or_id_card": "786",
        "date_of_birth": "1995-05-15",
    }
    res = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert res.status_code == 303
    assert "/address/new" in res.headers["Location"]
    assert "MA78695" in res.headers["Location"]


def test_address_with_map_pin_coordinates_and_driving_directions(client, db_session, test_user):
    """Verify that an address with pinned GPS coordinates generates Google Maps driving directions."""
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
            latitude=30.7031,
            longitude=70.6500,
            destination_url=None,  # left empty to test auto-default to driving directions
            redirect_seconds=3
        ),
        year=2026
    )

    # Web resolver test
    res = client.get(f"/a/{addr.public_id}")
    assert res.status_code == 200
    assert "Start Driving Directions" in res.text
    assert "30.7031,70.65" in res.text
    assert "travelmode=driving" in res.text

    # API resolver test
    api_res = client.get(f"/api/v1/resolve/{addr.public_id}")
    assert api_res.status_code == 200
    data = api_res.json()
    assert data["latitude"] == 30.7031
    assert data["longitude"] == 70.6500
    assert "driving_directions_url" in data
    assert "destination=30.7031,70.65" in data["driving_directions_url"]
    assert "travelmode=driving" in data["driving_directions_url"]
    # If destination_url was None, it defaults to the driving directions URL
    assert data["destination_url"] == data["driving_directions_url"]


def test_delivery_reach_options_and_no_purpose_in_form(client):
    """Verify that form renders Delivery Reach (Two Options) with high contrast and no Address Purpose."""
    payload = {
        "father_name": "M",
        "mother_name": "A",
        "cnic_or_id_card": "456",
        "date_of_birth": "1992-02-02",
    }
    id_res = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert id_res.status_code == 303
    cookies = id_res.cookies

    res = client.get("/address/new", cookies=cookies)
    assert res.status_code == 200
    assert "Select Delivery Reach (Two Options)" in res.text
    assert "Local City Delivery" in res.text
    assert "Out of City / Worldwide" in res.text
    assert "reach-card-active" in res.text
    assert "reach-card-inactive" in res.text

    # Address Purpose and its obsolete choices must NOT be in the form
    assert "Address Purpose" not in res.text
    assert "RESIDENTIAL" not in res.text
    assert "POSTAL" not in res.text
    assert "TEMPORARY" not in res.text


def test_business_address_creation_and_compulsory_person_name(client):
    """Verify Business Address creation and that person name is compulsory."""
    # 1. Create Edit ID
    payload = {
        "father_name": "T",
        "mother_name": "K",
        "cnic_or_id_card": "789",
        "date_of_birth": "1995-05-15",
    }
    id_res = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert id_res.status_code == 303
    cookies = id_res.cookies

    # 2. Try creating without recipient_name -> rejected
    bad_payload = {
        "address_type": "PERSONAL",
        "location_scope": "LOCAL",
        "city": "Taunsa Sharif",
        "country": "Pakistan",
        "recipient_name": ""
    }
    res_bad = client.post("/address/new", data=bad_payload, cookies=cookies, follow_redirects=False)
    assert res_bad.status_code == 400
    assert "Contact person name is compulsory" in res_bad.text

    # 3. Try creating BUSINESS without business_name -> rejected
    bad_biz_payload = {
        "address_type": "BUSINESS",
        "location_scope": "LOCAL",
        "city": "Taunsa Sharif",
        "country": "Pakistan",
        "recipient_name": "Bilal Ahmad",
        "business_name": ""
    }
    res_bad_biz = client.post("/address/new", data=bad_biz_payload, cookies=cookies, follow_redirects=False)
    assert res_bad_biz.status_code == 400
    assert "Business / Company name is required" in res_bad_biz.text

    # 4. Valid business address creation -> succeeds
    good_biz_payload = {
        "address_type": "BUSINESS",
        "location_scope": "LOCAL",
        "city": "Taunsa Sharif",
        "country": "Pakistan",
        "recipient_name": "Bilal Ahmad",
        "business_name": "Bilal Tech Solutions",
        "house_number": "10-A",
        "street": "College Road"
    }
    res_good = client.post("/address/new", data=good_biz_payload, cookies=cookies, follow_redirects=False)
    assert res_good.status_code == 303
    view_url = res_good.headers["Location"]
    assert "/view" in view_url

    # Check view page renders business info
    res_view = client.get(view_url, cookies=cookies)
    assert res_view.status_code == 200
    assert "Bilal Tech Solutions" in res_view.text
    assert "Bilal Ahmad" in res_view.text
    assert "Business Address" in res_view.text
    assert "Transfer Business Owner" in res_view.text


def test_business_address_owner_transfer_and_edit_id_generation(client):
    """
    Verify that:
    1. Only business address can have ownership transferred.
    2. Generating new owner Edit ID follows [public_id][F][M][CNIC3][YY] (13 chars).
    3. Public ID remains stable.
    4. New owner can authenticate using new Edit ID.
    """
    # 1. Create original owner Edit ID
    payload = {
        "father_name": "M",
        "mother_name": "A",
        "cnic_or_id_card": "111",
        "date_of_birth": "1990-01-01",
        "public_id": "zz9926"
    }
    id_res = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert id_res.status_code == 303
    cookies = id_res.cookies

    # 2. Create Business Address
    biz_payload = {
        "address_type": "BUSINESS",
        "location_scope": "LOCAL",
        "city": "Lahore",
        "country": "Pakistan",
        "recipient_name": "Original Owner",
        "business_name": "Alpha Corp"
    }
    addr_res = client.post("/address/new", data=biz_payload, cookies=cookies, follow_redirects=False)
    assert addr_res.status_code == 303
    pub_id = addr_res.headers["Location"].split("/")[2]

    # 3. Transfer ownership to new owner:
    # New Owner: Father Tariq (T), Mother Fatima (F), CNIC 999, DOB 1998-04-12 (98)
    transfer_payload = {
        "new_owner_name": "Hamza Tariq",
        "father_name": "Tariq",
        "mother_name": "Fatima",
        "cnic_or_id_card": "999",
        "date_of_birth": "1998-04-12"
    }
    transfer_res = client.post(f"/address/{pub_id}/transfer-owner", data=transfer_payload, cookies=cookies, follow_redirects=False)
    assert transfer_res.status_code == 303
    expected_new_edit_id = f"{pub_id}TF99998"
    assert len(expected_new_edit_id) == 13
    assert f"new_edit_id={expected_new_edit_id}" in transfer_res.headers["Location"]
    assert "owner_transferred=true" in transfer_res.headers["Location"]

    # 4. View page with new cookies shows success and new owner
    new_cookies = transfer_res.cookies
    view_res = client.get(transfer_res.headers["Location"], cookies=new_cookies)
    assert view_res.status_code == 200
    assert "Business Ownership Transferred Successfully!" in view_res.text
    assert expected_new_edit_id in view_res.text
    assert "Hamza Tariq" in view_res.text

    # 5. Authenticate directly using the new 13-character Edit ID
    login_res = client.post("/address/use-existing-edit-id", data={"edit_id": expected_new_edit_id}, follow_redirects=False)
    assert login_res.status_code == 303
    assert "edit_session_token" in login_res.cookies


def test_admin_ads_management_system(client, db_session):
    """Verify that administrators can create, list, toggle, and delete ads."""
    from datetime import date
    from app.models.user import User, UserRole, AccountStatus
    from app.core.security import hash_password, hash_edit_id
    from app.services.auth_service import AuthService

    # Create admin user
    admin_user = db_session.query(User).filter(User.username == "ad_manager").first()
    if not admin_user:
        admin_user = User(
            username="ad_manager",
            email="adman@test.local",
            full_name="Ad Manager",
            father_name="Father",
            mother_name="Mother",
            cnic_or_id_card="321",
            date_of_birth=date(1990, 1, 1),
            role=UserRole.ADMIN,
            account_status=AccountStatus.ACTIVE,
            password_hash=hash_password("adminpass123"),
            edit_id_hash=hash_edit_id("ad1226FM32190")
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    # Log in as admin
    login_res = client.post("/login", data={"username": "ad_manager", "password": "adminpass123"}, follow_redirects=False)
    assert login_res.status_code == 303
    cookies = login_res.cookies

    # 1. Admin gets ads page
    res = client.get("/admin/ads", cookies=cookies)
    assert res.status_code == 200
    assert "Ads & Monetization Management" in res.text

    # 2. Admin creates ad
    ad_payload = {
        "title": "Spring Delivery Discount",
        "ad_type": "CUSTOM_HTML",
        "placement": "HOME_CONTENT",
        "code_snippet": "<div id='test-spring-ad'>50% Off Courier Services!</div>",
        "display_order": 10
    }
    create_res = client.post("/admin/ads/create", data=ad_payload, cookies=cookies, follow_redirects=False)
    assert create_res.status_code == 303

    # 3. Ad appears on homepage
    home_res = client.get("/")
    assert home_res.status_code == 200
    assert "test-spring-ad" in home_res.text
    assert "50% Off Courier Services!" in home_res.text

    # 4. Toggle ad inactive
    from app.models.advertisement import Advertisement
    ad = db_session.query(Advertisement).filter(Advertisement.title == "Spring Delivery Discount").first()
    assert ad is not None

    toggle_res = client.post(f"/admin/ads/{ad.id}/toggle", cookies=cookies, follow_redirects=False)
    assert toggle_res.status_code == 303

    # Ad should no longer appear on homepage
    home_res2 = client.get("/")
    assert "test-spring-ad" not in home_res2.text




