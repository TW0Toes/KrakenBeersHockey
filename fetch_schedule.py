import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Base parameters for Kraken Beers schedule querying
CLIENT_ID = "2296"
LEAGUE_ID = "5717"
TEAM_ID = "683136"

YEARS = [2026, 2027]
MONTHS = list(range(1, 13))  # Months 1 through 12


def clean_team_name(name):
  if not name:
    return ""
  cleaned = re.sub(
      r"\b[A-Z]{2,5}\s+[A-Z0-9]\b$", "", name.strip(), flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r"\b[A-Z]{3,5}\b$", "", cleaned.strip(), flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r"^\d+\s*(vs\.?|at|@)?\s*", "", cleaned, flags=re.IGNORECASE
  )
  return re.sub(r"\s+", " ", cleaned).strip()


def extract_hna_date(text):
  patterns = [
      (
          r"\b(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,?\s+[A-Za-z]{3,4}\.?\s+\d{1,2}(?:,?\s*\d{4})?\b"
      ),
      r"\b[A-Za-z]{3,4}\.?\s+\d{1,2},?\s+\d{4}\b",
  ]
  for pat in patterns:
    match = re.search(pat, text, re.IGNORECASE)
    if match:
      return match.group(0).strip()
  return ""


def scrape_schedule():
  print("Fetching schedule across 2026 and 2027...")
  schedule_data = {"last_game": None, "upcoming_games": []}
  seen_games = set()  # Deduplication set

  for year in YEARS:
    for month in MONTHS:
      url = f"https://www.hna.com/leagues/schedules.cfm?clientID={CLIENT_ID}&leagueID={LEAGUE_ID}&schedType=main&printPage=0&monthID={month}&yearID={year}&selectedTeamID={TEAM_ID}&selectedOfficialID=0&gameType="

      try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
          continue

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")
        current_date = ""

        for row in rows:
          cols = [
              re.sub(r"\s+", " ", td.text).strip()
              for td in row.find_all(["td", "th"])
          ]
          if not cols:
            continue

          raw_row_text = " ".join(cols).strip()
          row_upper = raw_row_text.upper()

          found_date = extract_hna_date(raw_row_text)
          if found_date:
            current_date = found_date

          # Filter out header/summary noise
          if any(
              kw in row_upper
              for kw in [
                  "RESULT",
                  "GAME #",
                  "VISITOR",
                  "FINAL",
                  "RECORD:",
                  "LAST:",
              ]
          ):
            continue

          # Match game rows
          if "KRAKEN" in row_upper or "VS" in row_upper or "AT" in row_upper:
            time_str = next(
                (c for c in cols if "PM" in c.upper() or "AM" in c.upper()), ""
            )
            teams = [
                c for c in cols if " VS " in c.upper() or " AT " in c.upper()
            ]

            matchup = teams[0] if teams else "Kraken Beers vs Opponent"
            location = cols[-1] if len(cols) > 3 else "Local Rink"

            if " VS " in matchup.upper():
              parts = re.split(r"\s+VS\s+", matchup, flags=re.IGNORECASE)
              home, away = parts[0], parts[1]
            elif " AT " in matchup.upper():
              parts = re.split(r"\s+AT\s+", matchup, flags=re.IGNORECASE)
              away, home = parts[0], parts[1]
            else:
              home, away = "Kraken Beers", "Opponent"

            game_obj = {
                "date": current_date or "TBD",
                "time": time_str,
                "home_team": clean_team_name(home),
                "away_team": clean_team_name(away),
                "location": location,
            }

            # Create unique fingerprint to prevent duplicates across month queries
            game_signature = (
                f"{game_obj['date']}_{game_obj['time']}_{game_obj['home_team']}"
            )
            if game_signature not in seen_games:
              seen_games.add(game_signature)
              schedule_data["upcoming_games"].append(game_obj)

      except Exception as e:
        print(f"Skipping month {month}/{year} due to error: {e}")

  with open("schedule.json", "w") as f:
    json.dump(schedule_data, f, indent=2)

  print(
      f"Schedule complete! Total unique games saved:"
      f" {len(schedule_data['upcoming_games'])}"
  )


if __name__ == "__main__":
  scrape_schedule()
