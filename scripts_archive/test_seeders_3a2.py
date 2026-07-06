from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("Testing GET /api/v1/users/demo")
    res = client.get("/api/v1/users/demo")
    assert res.status_code == 200
    
    users = ["U00001", "U00002", "U00003"]
    for user_id in users:
        print(f"\nTesting GET /api/v1/users/{user_id}")
        res = client.get(f"/api/v1/users/{user_id}")
        assert res.status_code == 200
        
        print(f"Testing GET /api/v1/users/{user_id}/traveler-profile")
        res = client.get(f"/api/v1/users/{user_id}/traveler-profile")
        assert res.status_code == 200
        data = res.json()["data"]
        print(f"Perfil {user_id} -> Presupuesto: {data['presupuesto']}, Seguridad: {data['peso_seguridad']}")
        
    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    run_tests()
