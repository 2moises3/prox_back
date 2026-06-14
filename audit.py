import urllib.request, json, sys

print('--- SWAGGER ENDPOINTS ---')
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/openapi.json') as response:
        openapi = json.loads(response.read().decode('utf-8'))
        for path in openapi.get('paths', {}):
            print(path)
except Exception as e:
    print('Error fetching OpenAPI spec:', e)

print('\n--- 1. POST USER ---')
user_payload = {
  'name': 'Usuario Auditoria',
  'email': 'usuario.auditoria.final@test.com',
  'password': 'Test1234!'
}
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/users', data=json.dumps(user_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
uid = None
try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode('utf-8'))
        print('Status:', response.status)
        print(json.dumps(res, indent=2))
        uid = res['data']['user_id']
except urllib.error.HTTPError as e:
    print('Error:', e.code)
    print(e.read().decode('utf-8'))

print('\n--- 6. DUPLICATE POST USER ---')
try:
    with urllib.request.urlopen(req) as response:
        pass
except urllib.error.HTTPError as e:
    print('Error:', e.code)
    print(e.read().decode('utf-8'))

if uid:
    print('\n--- 2. GET USER ---')
    req_get = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{uid}')
    try:
        with urllib.request.urlopen(req_get) as response:
            print('Status:', response.status)
            print(json.dumps(json.loads(response.read().decode('utf-8')), indent=2))
    except Exception as e:
        print('GET Error', e)

    print('\n--- 3. PUT PROFILE ---')
    profile_payload = {
      'budget_preference': 'medio',
      'climate_preference': 'templado',
      'crowd_preference': 'moderado',
      'peso_accesibilidad': 3.0,
      'peso_aforo_multitudes': 3.0,
      'peso_alojamiento': 3.0,
      'peso_atencion_servicio': 4.0,
      'peso_atractivos': 5.0,
      'peso_clima': 4.0,
      'peso_costos': 3.0,
      'peso_gastronomia': 4.0,
      'peso_limpieza': 4.0,
      'peso_seguridad': 4.0
    }
    req_put = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{uid}/traveler-profile', data=json.dumps(profile_payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='PUT')
    try:
        with urllib.request.urlopen(req_put) as response:
            print('Status:', response.status)
            print(json.dumps(json.loads(response.read().decode('utf-8')), indent=2))
    except Exception as e:
        print('PUT Error', e)

    print('\n--- 4. GET PROFILE ---')
    req_get_p = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{uid}/traveler-profile')
    try:
        with urllib.request.urlopen(req_get_p) as response:
            print('Status:', response.status)
            print(json.dumps(json.loads(response.read().decode('utf-8')), indent=2))
    except Exception as e:
        print('GET Profile Error', e)

    print('\n--- 7. INVALID WEIGHT ---')
    profile_payload_inv = profile_payload.copy()
    profile_payload_inv['peso_seguridad'] = 99.0
    req_put_inv = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{uid}/traveler-profile', data=json.dumps(profile_payload_inv).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='PUT')
    try:
        with urllib.request.urlopen(req_put_inv) as response:
            print('Status:', response.status)
    except urllib.error.HTTPError as e:
        print('Error:', e.code)
        print(e.read().decode('utf-8'))

print('\n--- 5. GET DEMO USERS PROFILES ---')
for d_uid in ['U00001', 'U00002', 'U00003']:
    req_demo = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{d_uid}/traveler-profile')
    try:
        with urllib.request.urlopen(req_demo) as response:
            print(f'DEMO {d_uid} Status:', response.status)
    except urllib.error.HTTPError as e:
        print(f'DEMO {d_uid} Error:', e.code)
