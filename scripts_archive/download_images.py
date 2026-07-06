import os
import urllib.request
import urllib.parse
import csv

os.makedirs('temp_images', exist_ok=True)
req = urllib.request.Request(
    'https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu.png',
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req) as response, open('temp_images/machu-picchu.png', 'wb') as out_file:
    out_file.write(response.read())

req2 = urllib.request.Request(
    urllib.parse.quote('https://commons.wikimedia.org/wiki/Special:FilePath/Lago_Titicaca,_Puno,_Perú,_2015-08-01,_DD_13.JPG', safe=':/'),
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req2) as response, open('temp_images/lago-titicaca.jpg', 'wb') as out_file:
    out_file.write(response.read())

req3 = urllib.request.Request(
    urllib.parse.quote('https://commons.wikimedia.org/wiki/Special:FilePath/CIRCUITO_MÁGICO_DEL_AGUA_-_Lima.jpg', safe=':/'),
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req3) as response, open('temp_images/circuito-magico.jpg', 'wb') as out_file:
    out_file.write(response.read())

print("Images downloaded.")
