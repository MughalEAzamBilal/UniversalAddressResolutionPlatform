import pytest
from datetime import date
from app.services.edit_id_service import EditIdService
from app.core.exceptions import InvalidEditIdError, AccountLockedError


def test_edit_id_generation():
    """Verify Edit ID formula: PublicID + Father[0] + Mother[0] + CNIC[-3:] + DOB_YY."""
    dob = date(1991, 1, 1)
    edit_id = EditIdService.generate_edit_id(
        public_id="ab1226",
        father_name="Muhammad",
        mother_name="Ayesha",
        cnic_or_id_card="32203-1234567-123",
        date_of_birth=dob
    )
    assert edit_id == "ab1226MA12391"
    assert len(edit_id) == 13


def test_case_insensitive_edit_id_verification(db_session, test_user):
    """Verify Edit ID is strictly case-insensitive."""
    # Test uppercase
    u1 = EditIdService.verify_and_authenticate(db_session, "AB1226MA12391")
    assert u1.id == test_user.id

    # Test lowercase
    u2 = EditIdService.verify_and_authenticate(db_session, "ab1226ma12391")
    assert u2.id == test_user.id

    # Test mixed case
    u3 = EditIdService.verify_and_authenticate(db_session, "ab1226MA12391")
    assert u3.id == test_user.id


def test_invalid_edit_id_rejected(db_session, test_user):
    """Invalid Edit ID raises InvalidEditIdError."""
    with pytest.raises(InvalidEditIdError):
        EditIdService.verify_and_authenticate(db_session, "WRONGID1230101")


def test_temporary_lockout_on_failed_attempts(db_session, test_user):
    """Verify user gets locked after max failed attempts."""
    for _ in range(5):
        EditIdService.record_failed_attempt(db_session, test_user)

    assert test_user.is_locked()
    with pytest.raises(AccountLockedError):
        EditIdService.verify_and_authenticate(db_session, "ab1226MA12391")


def test_edit_ids_cannot_be_identical_or_same(db_session):
    """
    Verify requirement: 'Edit IDs cannt be identical or same'.
    When multiple users share the same public ID, father initial, mother initial,
    CNIC last 3 digits, and DOB year, each user MUST receive a unique Edit ID.
    No two Edit IDs can be identical or same.
    """
    from app.services.auth_service import AuthService
    dob = date(1991, 1, 1)

    auth = AuthService(db_session)

    # User 1 registers with public_id ab1226 and M, A, 123, 1991
    user1, edit_id_1 = auth.register_or_get_by_edit_id(
        full_name="User One",
        father_name="Muhammad",
        mother_name="Ayesha",
        cnic_or_id_card="123",
        date_of_birth=dob,
        public_id="ab1226"
    )
    assert edit_id_1 == "ab1226MA12391"

    # User 2 registers with identical public_id, initials, CNIC ending, and DOB
    user2, edit_id_2 = auth.register_or_get_by_edit_id(
        full_name="User Two",
        father_name="Mansoor",
        mother_name="Amina",
        cnic_or_id_card="123",
        date_of_birth=dob,
        public_id="ab1226"
    )
    # MUST NOT be identical!
    assert edit_id_2 != edit_id_1
    assert edit_id_2 == "ab1226MA12391-2"

    # User 3 registers with identical inputs again
    user3, edit_id_3 = auth.register_or_get_by_edit_id(
        full_name="User Three",
        father_name="Mustafa",
        mother_name="Asma",
        cnic_or_id_card="123",
        date_of_birth=dob,
        public_id="ab1226"
    )
    # MUST NOT be identical to either user 1 or user 2!
    assert edit_id_3 != edit_id_1
    assert edit_id_3 != edit_id_2
    assert edit_id_3 == "ab1226MA12391-3"

    # Verify each user authenticates strictly to their own account
    auth_u1 = EditIdService.verify_and_authenticate(db_session, edit_id_1)
    auth_u2 = EditIdService.verify_and_authenticate(db_session, edit_id_2)
    auth_u3 = EditIdService.verify_and_authenticate(db_session, edit_id_3)

    assert auth_u1.id == user1.id
    assert auth_u2.id == user2.id
    assert auth_u3.id == user3.id

    # Verify case-insensitivity on suffixed Edit ID
    auth_u2_lower = EditIdService.verify_and_authenticate(db_session, "ab1226ma12391-2")
    assert auth_u2_lower.id == user2.id


def test_web_create_edit_id_endpoint_assigns_unique_edit_ids(client):
    """
    Verify web endpoint /address/create-edit-id generates non-identical Edit IDs
    when two users submit matching initials and date of birth.
    """
    payload = {
        "father_name": "M",
        "mother_name": "A",
        "cnic_or_id_card": "786",
        "date_of_birth": "1993-05-15",
        "public_id": "cd3426"
    }

    # First user
    res1 = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert res1.status_code == 303
    assert "welcome_edit_id=cd3426MA78693" in res1.headers["Location"]

    # Second user with same parameters and same public_id
    res2 = client.post("/address/create-edit-id", data=payload, follow_redirects=False)
    assert res2.status_code == 303
    # Second user MUST NOT receive cd3426MA78693
    assert "welcome_edit_id=cd3426MA78693-2" in res2.headers["Location"]
