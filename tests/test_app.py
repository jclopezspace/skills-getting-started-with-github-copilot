import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to original state before each test."""
    original = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original)


@pytest.fixture
def client():
    return TestClient(app)


# --- GET / ---

def test_root_redirects_to_static(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


# --- GET /activities ---

def test_get_activities_returns_all(client):
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "Chess Club" in data
    assert "Programming Class" in data


def test_activity_has_expected_fields(client):
    response = client.get("/activities")
    data = response.json()
    activity = data["Chess Club"]
    assert "description" in activity
    assert "schedule" in activity
    assert "max_participants" in activity
    assert "participants" in activity
    assert isinstance(activity["participants"], list)


# --- POST /activities/{name}/signup ---

def test_signup_success(client):
    response = client.post(
        "/activities/Chess Club/signup?email=newstudent@mergington.edu"
    )
    assert response.status_code == 200
    assert "newstudent@mergington.edu" in response.json()["message"]

    # Verify participant was added
    act = client.get("/activities").json()
    assert "newstudent@mergington.edu" in act["Chess Club"]["participants"]


def test_signup_duplicate_returns_400(client):
    response = client.post(
        "/activities/Chess Club/signup?email=michael@mergington.edu"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up"


def test_signup_nonexistent_activity_returns_404(client):
    response = client.post(
        "/activities/Nonexistent Club/signup?email=test@mergington.edu"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


# --- DELETE /activities/{name}/signup ---

def test_unregister_success(client):
    response = client.delete(
        "/activities/Chess Club/signup?email=michael@mergington.edu"
    )
    assert response.status_code == 200
    assert "michael@mergington.edu" in response.json()["message"]

    # Verify participant was removed
    act = client.get("/activities").json()
    assert "michael@mergington.edu" not in act["Chess Club"]["participants"]


def test_unregister_not_signed_up_returns_400(client):
    response = client.delete(
        "/activities/Chess Club/signup?email=unknown@mergington.edu"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregister_nonexistent_activity_returns_404(client):
    response = client.delete(
        "/activities/Nonexistent Club/signup?email=test@mergington.edu"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


# --- Signup + Unregister round-trip ---

def test_signup_then_unregister(client):
    email = "roundtrip@mergington.edu"
    # Sign up
    resp = client.post(f"/activities/Art Club/signup?email={email}")
    assert resp.status_code == 200
    # Unregister
    resp = client.delete(f"/activities/Art Club/signup?email={email}")
    assert resp.status_code == 200
    # Confirm removed
    act = client.get("/activities").json()
    assert email not in act["Art Club"]["participants"]
