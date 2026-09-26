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

    cleaned = re.sub(r"\bF\b", "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


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

        with open("hna_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        print("Saved hna_debug.html")

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        print("\n========================")
        print("ALL TABLE ROWS")
        print("========================\n")

        rows = soup.find_all("tr")

        for i, row in enumerate(rows):
            cols = [
                td.get_text(" ", strip=True)
                for td in row.find_all(["td", "th"])
            ]

            if cols:
                print(f"ROW {i}: {cols}")

        print("\n========================")
        print("END TABLE ROWS")
        print("========================\n")

        current_date = ""

        for row in rows:

            cols = [
                re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip()
                for td in row.find_all(["td", "th"])
            ]

            if not cols:
                continue

            row_text = " ".join(cols)

            date_match = re.search(
                r"(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+"
                r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                r"\s+\d{1,2}",
                row_text,
                re.IGNORECASE
            )

            if date_match:
                current_date = date_match.group(0)
                continue

            time_match = re.search(
                r"\b\d{1,2}:\d{2}\s*(AM|PM)\b",
                row_text,
                re.IGNORECASE
            )

            if not time_match:
                continue

            print(f"GAME ROW FOUND: {cols}")

            game = {
                "date": current_date,
                "time": time_match.group(0),
                "raw_columns": cols
            }

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
        print(f"ERROR: {e}")


if __name__ == "__main__":
    scrape_schedule()
