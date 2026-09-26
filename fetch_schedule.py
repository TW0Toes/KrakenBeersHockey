import requests
from bs4 import BeautifulSoup

URL = "https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=5717&teamID=683136&printPage=0"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

res = requests.get(URL, headers=HEADERS, timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')

rows = soup.find_all('tr')
print(f"Total rows: {len(rows)}\n")

for i, row in enumerate(rows):
    cells = [f"Col {idx}: '{td.text.strip()}'" for idx, td in enumerate(row.find_all(['td', 'th']))]
    if cells:
        print(f"Row {i:02d} -> " + " | ".join(cells))
