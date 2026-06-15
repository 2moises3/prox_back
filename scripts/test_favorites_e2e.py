import urllib.request
import json
import urllib.error

base_url = "http://localhost:8000/api/v1"

def api_request(endpoint, token=None, method="GET", data=None):
    url = f"{base_url}/{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req_data = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, {"detail": body}

def get_token(email, name):
    status, res = api_request("auth/login", method="POST", data={"email": email, "password": "password123"})
    if status == 200:
        return res["data"]["access_token"]
    
    # Register
    api_request("users", method="POST", data={"name": name, "email": email, "password": "password123"})
    status, res = api_request("auth/login", method="POST", data={"email": email, "password": "password123"})
    return res["data"]["access_token"]

print("=== STARTING FAVORITES VALIDATION ===")

# 1. GET /favorites sin token -> 401
s, r = api_request("favorites")
print(f"1. Sin token -> Status: {s} (Expected: 401)")
assert s == 401

# Get tokens for A and B
token_a = get_token("user_a_fav@example.com", "User A Fav")
token_b = get_token("user_b_fav@example.com", "User B Fav")

# 2. GET /favorites con token válido -> 200
s, r = api_request("favorites", token=token_a)
print(f"2. Con token -> Status: {s} (Expected: 200)")
assert s == 200

destination_test = "machu-picchu"

# 3. POST /favorites/{destination_id} -> agrega favorito
s, r = api_request(f"favorites/{destination_test}", token=token_a, method="POST")
print(f"3. Agregar favorito -> Status: {s} (Expected: 200), Response: {r}")
assert s == 200

# 4. Repetir POST mismo destino -> no duplica (devuelve 200 con mensaje)
s, r = api_request(f"favorites/{destination_test}", token=token_a, method="POST")
print(f"4. Repetir POST -> Status: {s} (Expected: 200), Message: {r['message']}")
assert s == 200
assert "ya está en favoritos" in r['message']

# 5. GET /favorites -> muestra el favorito agregado
s, r = api_request("favorites", token=token_a)
print(f"5. Listar favoritos Usuario A -> Status: {s}, Cantidad: {len(r['data'])}")
assert any(d["destination_id"] == destination_test for d in r["data"])

# 6. DELETE /favorites/{destination_id} -> elimina favorito
s, r = api_request(f"favorites/{destination_test}", token=token_a, method="DELETE")
print(f"6. Eliminar favorito -> Status: {s} (Expected: 200), Response: {r}")
assert s == 200

# 7. GET /favorites -> ya no aparece
s, r = api_request("favorites", token=token_a)
print(f"7. Listar tras eliminar -> Status: {s}, Cantidad: {len(r['data'])}")
assert not any(d["destination_id"] == destination_test for d in r["data"])

# 8. Usuario A agrega favorito
s, r = api_request(f"favorites/{destination_test}", token=token_a, method="POST")
print(f"8. Usuario A agrega favorito de nuevo -> Status: {s}")

# 9. Usuario B consulta favoritos
s, r = api_request("favorites", token=token_b)
print(f"9. Usuario B consulta -> Status: {s}, Cantidad: {len(r['data'])}")

# 10. Confirmar que Usuario B NO ve favoritos de Usuario A
assert not any(d["destination_id"] == destination_test for d in r["data"])
print("10. Confirmado: Aislamiento correcto entre usuarios.")
print("=== END OF VALIDATION ===")
