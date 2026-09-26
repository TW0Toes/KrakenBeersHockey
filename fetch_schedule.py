import json
import re
import requests
from bs4 import BeautifulSoup

MONTH = 10
YEAR = 2026

URL = (
    "https://www.hna.com/leagues/schedules.cfm"
    f"?clientID=2296"
    f"&leagueID=5717"
    f"&schedType=main"
    f"&printPage=0"
    f"&monthID={MONTH}"
    f"&yearID={YEAR}"
    f"&selectedTeamID=683136"
    f"&selectedOfficialID=0"
    f"&gameType="
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.hna.com/",
}


def clean_team_name(name):
    name = re.sub(r"\bF\b", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def scrape_schedule():
    schedule = {
        "last_game": None,
        "upcoming_games": []
    }

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    print("Status:", response.status_code)
    print("URL:", response.url)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    print("\n===== ROW DEBUG =====\n")

for i, row in enumerate(rows):
    cols = [
        td.get_text(" ", strip=True)
        for td in row.find_all(["td", "th"])
    ]

    if cols:
        print(f"ROW {i}: {cols}")

print("\n===== END DEBUG =====\n")

    print(f"Found {len(rows)} rows")

    seen = set()

    for row in rows:

        cols = [
            td.get_text(" ", strip=True)
            for td in row.find_all(["td", "th"])
        ]

        if len(cols) < 7:
            continue

        if cols[0].upper() in ("TIME", "RESULT"):
            continue

        time_match = re.match(
            r"^\d{1,2}:\d{2}\s*(AM|PM)$",
            cols[0],
            re.IGNORECASE
        )

        if not time_match:
            continue

        game = {
            "date": f"{YEAR}-{MONTH:02d}",
            "time": cols[0],
            "away_team": clean_team_name(cols[2]),
            "home_team": clean_team_name(cols[4]),
            "location": cols[6]
        }

        sig = (
            f"{game['time']}|"
            f"{game['away_team']}|"
            f"{game['home_team']}"
        )

        if sig not in seen:
            seen.add(sig)
            schedule["upcoming_games"].append(game)

    with open("schedule.json", "w") as f:
        json.dump(schedule, f, indent=2)

    print(
        f"Saved {len(schedule['upcoming_games'])} games"
    )


if __name__ == "__main__":
    scrape_schedule()
