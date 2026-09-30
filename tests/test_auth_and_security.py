def test_user_registration_and_login_flow(client):
    """Test full registration and login sequence."""
    reg_payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
        "full_name": "New User",
        "father_name": "Tariq",
        "mother_name": "Maryam",
        "cnic_or_id_card": "456",
        "date_of_birth": "1995-12-25"
    }

    # API Registration
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert "edit_id" in data
    assert len(data["edit_id"]) == 13
    assert data["edit_id"][6:] == "TM45695" # Tariq (T) + Maryam (M) + 456 + 95

    # Login with password
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "newuser", "password": "StrongPassword123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token

    # Check authenticated endpoint /api/v1/auth/me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "newuser"


def test_edit_id_login_flow(client, test_user):
    """Test login via Edit ID."""
    res = client.post(
        "/api/v1/auth/edit-id-login",
        json={"edit_id": "ab1226MA12391"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["username"] == test_user.username


def test_register_redirects_to_edit_id_and_edit_instructions(client):
    """Verify that /register redirects to /address/new, and /edit shows clear instructions."""
    # 1. /register redirects to /address/new
    reg_res = client.get("/register", follow_redirects=False)
    assert reg_res.status_code == 303
    assert "/address/new" in reg_res.headers["Location"]

    # 2. /edit displays comprehensive Edit ID instructions and updated links
    edit_res = client.get("/edit")
    assert edit_res.status_code == 200
    assert "Enter Your 13-Character Edit ID" in edit_res.text
    assert "Suggestion: How to fill your 13-Character Edit ID" in edit_res.text
    assert "Father Initial" in edit_res.text
    assert "Mother Initial" in edit_res.text
    assert "Case-Insensitive" in edit_res.text
    assert "ab1226MA12391" in edit_res.text
    assert "/address/new" in edit_res.text
    assert "/3210325048745" not in edit_res.text  # Secret admin URL is not publicly linked


def test_secret_admin_login_url(client, test_user):
    """Verify that /3210325048745 serves the login page and accepts valid login."""
    # 1. GET /3210325048745
    get_res = client.get("/3210325048745")
    assert get_res.status_code == 200
    assert "Administrator Sign-In" in get_res.text

    # 2. POST /3210325048745
    post_res = client.post(
        "/3210325048745",
        data={"username": "bilal", "password": "UserPass123!"},
        follow_redirects=False
    )
    assert post_res.status_code == 303
    assert "session_token" in post_res.cookies

