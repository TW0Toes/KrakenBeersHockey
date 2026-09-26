import json
import re
import requests
from bs4 import BeautifulSoup

SCHEDULE_URL = (
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
    if not name:
        return ""

    name = re.sub(r"\bF\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def extract_next_game_date(text):
    """
    Extract:
    Next: Sep. 29, 2026 at 10:20 PM
    """

    match = re.search(
        r"Next:\s*([A-Za-z]{3,4}\.\s*\d{1,2},\s*\d{4})",
        text
    )

    if match:
        return match.group(1).strip()

    return ""


def scrape_schedule():
    print("Fetching schedule...")

    schedule_data = {
        "last_game": None,
        "upcoming_games": []
    }

    try:
        response = requests.get(
            SCHEDULE_URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        rows = soup.find_all("tr")

        game_date = ""

        #
        # Get date from summary row
        #
        for row in rows:
            text = row.get_text(" ", strip=True)

            if "Next:" in text:
                game_date = extract_next_game_date(text)
                break

        seen = set()

        for row in rows:

            cols = [
                re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip()
                for td in row.find_all(["td", "th"])
            ]

            if len(cols) < 7:
                continue

            #
            # Skip headers
            #
            if cols[0].upper() in ["TIME", "RESULT"\]:
                continue

            #
            # Find rows beginning with a time
            #
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

            signature = (
                f"{game['date']}|"
                f"{game['time']}|"
                f"{game['away_team']}|"
                f"{game['home_team']}"
            )

            if signature not in seen:
                seen.add(signature)
                schedule_data["upcoming_games"].append(game)

        with open("schedule.json", "w") as f:
            json.dump(
                schedule_data,
                f,
                indent=2
           )

        print(
            f"Saved {len(schedule_data['upcoming_games'])} games"
        )

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    scrape_schedule()
