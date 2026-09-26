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

# Current season months
YEARS = [2026, 2027]
MONTHS = [9, 10, 11, 12, 1, 2, 3, 4]  # Sep through Apr


def clean_team_name(name):
  if not name:
    return ""
  # Strip division codes like "KRA F", "WHI F", "REA F" from team names
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
  print("Fetching monthly schedules...")
  schedule_data = {"last_game": None, "upcoming_games": []}
  seen_games = set()

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

          # Check for date block headers (e.g. "Wednesday, Oct 14, 2026")
          found_date = extract_hna_date(raw_row_text)
          if found_date:
            current_date = found_date
            continue

          # Skip table header/footer noise
          if any(
              kw in row_upper
              for kw in [
                  "GAME #",
                  "VISITOR",
                  "HOME",
                  "RECORD:",
                  "LAST:",
                  "CANCELLED",
                  "POSTPONED",
              ]
          ):
            continue

          # Ignore completed games with scores (e.g., '4 - 2')
          if re.search(r"\b\d+\s*-\s*\d+\b", raw_row_text) or "FINAL" in row_upper:
            continue

          # Only process rows where Kraken is playing
          if "KRAKEN" not in row_upper:
            continue

          # Ensure we have enough table columns to map visitor, home, location
          if len(cols) >= 5:
            # Monthly schedule table cell structure:
            # cols[1] = Time, cols[2] = Visitor, cols[3] = Home, cols[4] = Location
            time_str = cols[1] if ("AM" in cols[1].upper() or "PM" in cols[1].upper()) else ""
            visitor_raw = cols[2]
            home_raw = cols[3]
            location_raw = cols[4]

            # If time wasn't in cell 1, try regex search across row
            if not time_str:
              time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", row_upper)
              time_str = time_match.group(0) if time_match else ""

            away_team = clean_team_name(visitor_raw)
            home_team = clean_team_name(home_raw)

            # Skip if parsing failed to extract valid team names
            if not away_team or not home_team:
              continue

            game_obj = {
                "date": current_date or "TBD",
                "time": time_str,
                "home_team": home_team,
                "away_team": away_team,
                "location": location_raw or "Local Rink",
            }

            # Deduplicate across month fetches
            game_signature = f"{game_obj['date']}_{game_obj['time']}_{game_obj['home_team']}_{game_obj['away_team']}"
            if game_signature not in seen_games:
              seen_games.add(game_signature)
              schedule_data["upcoming_games"].append(game_obj)

      except Exception as e:
        print(f"Skipping month {month}/{year}: {e}")

  with open("schedule.json", "w") as f:
    json.dump(schedule_data, f, indent=2)

  print(f"Schedule complete! Saved {len(schedule_data['upcoming_games'])} games.")


if __name__ == "__main__":
  scrape_schedule()
