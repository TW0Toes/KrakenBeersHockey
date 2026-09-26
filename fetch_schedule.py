import json
import datetime
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

CLIENT_ID = "2296"
LEAGUE_ID = "5717"
TEAM_ID = "683136"

YEARS = [2026, 2027]
MONTHS = list(range(1, 13))


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
  seen_games = set()

  # Cutoff logic: current date for filtering completed games
  today = datetime.datetime.now()

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

          # Check for date block headers
          found_date = extract_hna_date(raw_row_text)
          if found_date:
            current_date = found_date
            continue

          # Skip table headers, summary rows, or completed games with score indicators
          if any(
              kw in row_upper
              for kw in [
                  "GAME #",
                  "VISITOR",
                  "HOME",
                  "RECORD:",
                  "LAST:",
                  "FINAL",
                  "CANCELLED",
                  "POSTPONED",
              ]
          ):
            continue

          # Ignore completed games (rows showing numerical scores like '4 - 2' or '3-1')
          if re.search(r"\b\d+\s*-\s*\d+\b", raw_row_text):
            continue

          # Check if time column exists (e.g., '10:20 PM')
          time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", row_upper)
          if not time_match or not current_date:
            continue

          time_str = time_match.group(0)

          # Parse column elements when available
          visitor_team = clean_team_name(cols[2]) if len(cols) > 2 else ""
          home_team = clean_team_name(cols[3]) if len(cols) > 3 else ""
          location = cols[4] if len(cols) > 4 else "Local Rink"

          # Fallbacks if column indexes shift
          if not visitor_team or not home_team:
            teams = [
                c for c in cols if " VS " in c.upper() or " AT " in c.upper()
            ]
            if teams:
              parts = re.split(
                  r"\s+(?:VS|AT)\s+", teams[0], flags=re.IGNORECASE
              )
              if len(parts) >= 2:
                visitor_team, home_team = clean_team_name(
                    parts[0]
                ), clean_team_name(parts[1])

          # Validate team relevance
          if "KRAKEN" not in (
              visitor_team + home_team + raw_row_text
          ).upper():
            continue

          game_obj = {
              "date": current_date,
              "time": time_str,
              "home_team": home_team or "Kraken Beers",
              "away_team": visitor_team or "Opponent",
              "location": location,
          }

          game_signature = f"{game_obj['date']}_{game_obj['time']}_{game_obj['home_team']}_{game_obj['away_team']}"
          if game_signature not in seen_games:
            seen_games.add(game_signature)
            schedule_data["upcoming_games"].append(game_obj)

      except Exception as e:
        print(f"Skipping month {month}/{year}: {e}")

  with open("schedule.json", "w") as f:
    json.dump(schedule_data, f, indent=2)

  print(
      f"Schedule complete! Saved"
      f" {len(schedule_data['upcoming_games'])} upcoming games."
  )


if __name__ == "__main__":
  scrape_schedule()
