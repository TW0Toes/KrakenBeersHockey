import json
import re
import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.hna.com/leagues/schedules.cfm"
    "?clientID=2296&leagueID=5717&teamID=683136&printPage=0"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def clean_team_name(name):
    name = re.sub(r"\bF\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def scrape_schedule():
    schedule = {
        "last_game": None,
        "upcoming_games": []
    }

    response = requests.get(URL, headers=HEADERS, timeout=30)

    print("Status:", response.status_code)
    print("Length:", len(response.text))
    print()
    print(response.text[:5000])

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    print(f"Found {len(rows)} rows")

    game_date = ""

    for row in rows:
        text = row.get_text(" ", strip=True)

        if "Next:" in text:
            match = re.search(
                r"Next:\s*([A-Za-z]{3,4}\.\s*\d{1,2},\s*\d{4})",
                text
            )

            if match:
                game_date = match.group(1)

        cols = [
            td.get_text(" ", strip=True)
            for td in row.find_all(["td", "th"])
        ]

        if cols:
            print(cols)

    for row in rows:
        cols = [
            td.get_text(" ", strip=True)
            for td in row.find_all(["td", "th"])
        ]

        if len(cols) < 7:
            continue

        if cols[0].upper() in ("TIME", "RESULT"):
            continue

        if not re.match(
            r"^\d{1,2}:\d{2}\s*(AM|PM)$",
            cols[0],
            re.IGNORECASE
        ):
            continue

        game = {
            "date": game_date,
            "time": cols[0],
            "away_team": clean_team_name(cols[2]),
            "home_team": clean_team_name(cols[4]),
            "location": cols[6]
        }

        schedule["upcoming_games"].append(game)

    with open("schedule.json", "w") as f:
        json.dump(schedule, f, indent=2)

    print("Saved schedule.json")


if __name__ == "__main__":
    scrape_schedule()
