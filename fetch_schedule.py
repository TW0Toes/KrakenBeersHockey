import requests
from bs4 import BeautifulSoup

URL = "https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=5717&teamID=683136&printPage=0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

res = requests.get(URL, headers=HEADERS, timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')

print(f"HTTP Status: {res.status_code}")
rows = soup.find_all('tr')
print(f"Total TR rows found: {len(rows)}\n")

for idx, row in enumerate(rows[:25]):  # Print first 25 rows
    cols = [td.text.strip() for td in row.find_all(['td', 'th']) if td.text.strip()]
    if cols:
        print(f"Row {idx}: {cols}")
