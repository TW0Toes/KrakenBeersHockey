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

        print(f"Status Code: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"HTML Length: {len(response.text)}")

        response.raise_for_status()

        # Save raw HTML for inspection
        with open("hna_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        print("Saved hna_debug.html")

        print("\n===== FIRST 5000 CHARACTERS =====\n")
        print(response.text[:5000])
        print("\n===== END HTML =====\n")

        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.find_all("tr")

        print(f"Found {len(rows)} table rows")

        print("\n===== TABLE ROWS =====\n")

        for i, row in enumerate(rows):
            cols = [
                td.get_text(" ", strip=True)
                for td in row.find_all(["td", "th"])
            ]

            if cols:
                print(f"ROW {i}: {cols}")

        print("\n===== END TABLE ROWS =====\n")

        game_date = ""

        # Find "Next: Sep. 29, 2026..."
        for row in rows:
            text = row.get_text(" ", strip=True)

            if "Next:" in text:
                game_date = extract_next_game_date(text)
                print(f"Game Date Found: {game_date}")
                break
