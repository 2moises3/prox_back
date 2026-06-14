import urllib.request, json, time
time.sleep(2) # Wait for backend to be ready

uid = 'U00008'

# POST USER FIRST
user_payload = {
  'name': 'Usuario Fase3A3',
  'email': 'fase3a3@test.com',
  'password': 'Test1234!'
}
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/users', data=json.dumps(user_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print('POST USER:', response.status)
        res = json.loads(response.read().decode('utf-8'))
        uid = res['data']['user_id']
except urllib.error.HTTPError as e:
    print('POST USER Error:', e.code, e.read().decode('utf-8'))

# PUT PROFILE
profile_payload = {
  'presupuesto': 'medio',
  'dias_viaje': 3,
  'clima_preferido': 'templado',
  'tipo_interes': 'mixto',
  'intereses': ['naturaleza', 'gastronomico'],
  'tolerancia_multitudes': 'moderado'
}
req_put = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{uid}/traveler-profile', data=json.dumps(profile_payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='PUT')
try:
    with urllib.request.urlopen(req_put) as response:
        print('\n--- PUT PROFILE ---', response.status)
        print(json.dumps(json.loads(response.read().decode('utf-8')), indent=2))
except Exception as e:
    print('PUT Error', e)

# GET PROFILE
req_get_p = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/users/{uid}/traveler-profile')
try:
    with urllib.request.urlopen(req_get_p) as response:
        print('\n--- GET PROFILE ---', response.status)
        print(json.dumps(json.loads(response.read().decode('utf-8')), indent=2))
except Exception as e:
    print('GET Profile Error', e)
