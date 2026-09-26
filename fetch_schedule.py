import json
import re
import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.hna.com/leagues/schedules.cfm"
    "?clientID=2296"
    "&leagueID=5717"
    "&schedType=main"
    "&printPage=0"
    "&monthID=10"
    "&yearID=2026"
    "&selectedTeamID=683136"
    "&selectedOfficialID=0"
    "&gameType="
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
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

    try:

        session = requests.Session()

        response = session.get(
            URL,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        print(f"Length: {len(response.text)}")

        print("\n===== RESPONSE PREVIEW =====\n")
        print(response.text[:2000])
        print("\n===== END PREVIEW =====\n")

        with open("hna_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        if response.status_code != 200:
            print("Request failed.")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.find_all("tr")

        print(f"Found {len(rows)} rows")

        for i, row in enumerate(rows):
            cols = [
                td.get_text(" ", strip=True)
                for td in row.find_all(["td", "th"])
            ]

            if cols:
                print(f"ROW {i}: {cols}")

        current_date = ""

        for row in rows:

            text = row.get_text(" ", strip=True)

            match = re.search(
                r"Next:\s*([A-Za-z]{3,4}\.\s*\d{1,2},\s*\d{4})",
                text
            )

            if match:
                current_date = match.group(1)

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

            if not re.match(
                r"^\d{1,2}:\d{2}\s*(AM|PM)$",
                cols[0],
                re.IGNORECASE
            ):
                continue

            game = {
                "date": current_date,
                "time": cols[0],
                "away_team": clean_team_name(cols[2]),
                "home_team": clean_team_name(cols[4]),
                "location": cols[6]
            }

            sig = (
                f"{game['date']}|"
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

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    scrape_schedule()
