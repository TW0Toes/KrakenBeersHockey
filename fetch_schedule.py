import json
import requests
from bs4 import BeautifulSoup

HNA_URL = "https://www.hna.com/leagues/schedules.cfm?leagueID=25148&clientID=2296"
TARGET_TEAM = "KRAKEN BEERS"

def scrape_hna_schedule():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(HNA_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    games = []

    rows = soup.find_all("tr")
    for row in rows:
        text = row.get_text(" ", strip=True)
        if TARGET_TEAM.lower() in text.lower():
            cols = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
            if len(cols) >= 4:
                games.append({
                    "date_time": cols[0],
                    "home_team": cols[1],
                    "away_team": cols[2],
                    "location": cols[3] if len(cols) > 3 else "TBD",
                    "status": cols[4] if len(cols) > 4 else "Scheduled"
                })

    with open("schedule.json", "w") as f:
        json.dump(games, f, indent=2)

    print(f"Successfully scraped {len(games)} games.")

if __name__ == "__main__":
    scrape_hna_schedule()
