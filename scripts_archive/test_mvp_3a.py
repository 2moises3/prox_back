import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("Testing GET /api/v1/users/demo")
    res = client.get("/api/v1/users/demo")
    assert res.status_code == 200
    print(res.json()["message"])

    print("\nTesting GET /api/v1/users/U00001")
    res = client.get("/api/v1/users/U00001")
    assert res.status_code == 200
    print(res.json()["data"]["name"])

    print("\nTesting POST /api/v1/users")
    import time
    timestamp = int(time.time())
    test_email = f"test_{timestamp}@proxvel.com"

    print(f"\nTesting POST /api/v1/users with {test_email}")
    new_user_data = {
        "name": "Test User",
        "email": test_email,
        "password": "password123"
    }
    res = client.post("/api/v1/users", json=new_user_data)
    
    assert res.status_code == 201
    new_user_id = res.json()["data"]["user_id"]
    print("Created:", new_user_id)
    assert "password" not in res.json()["data"]
    assert "password_hash" not in res.json()["data"]

    # fetch by email to be sure what ID it is and CHECK hash format
    from app.repositories import db_user_repository
    u = db_user_repository.get_user_by_email(test_email)
    print("Hash format in DB:", u.password_hash)
    assert u.password_hash.startswith("pbkdf2_sha256$100000$")
    new_user_id = u.user_id

    print("\nTesting GET /api/v1/users/{nuevo_user_id}")
    res = client.get(f"/api/v1/users/{new_user_id}")
    assert res.status_code == 200
    print(res.json()["data"]["email"])

    print("\nTesting PATCH /api/v1/users/{nuevo_user_id}")
    res = client.patch(f"/api/v1/users/{new_user_id}", json={"name": "Test User Updated"})
    assert res.status_code == 200
    print(res.json()["data"]["name"])

    print("\nTesting GET traveler-profile (should 404 first time)")
    res = client.get(f"/api/v1/users/{new_user_id}/traveler-profile")
    print(res.status_code, res.json())

    print("\nTesting PUT traveler-profile")
    profile_data = {
        "budget_preference": "Low",
        "peso_clima": 4.5
    }
    res = client.put(f"/api/v1/users/{new_user_id}/traveler-profile", json=profile_data)
    assert res.status_code == 200
    print(res.json()["data"])

    print("\nTesting GET traveler-profile")
    res = client.get(f"/api/v1/users/{new_user_id}/traveler-profile")
    assert res.status_code == 200
    print(res.json()["data"]["peso_clima"])

    print("\nTesting PATCH traveler-profile")
    res = client.patch(f"/api/v1/users/{new_user_id}/traveler-profile", json={"peso_seguridad": 5.0})
    assert res.status_code == 200
    print(res.json()["data"]["peso_seguridad"])

    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    run_tests()
