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

SCHEDULE_URL = "https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=5717&teamID=683136&printPage=0"


def clean_team_name(name):
  if not name:
    return ""
  # Remove 'F' division letters and cleanup whitespace
  cleaned = re.sub(r"\bF\b", "", name, flags=re.IGNORECASE)
  cleaned = re.sub(r"\s+", " ", cleaned)
  return cleaned.strip()


def extract_hna_date(text):
  # Matches "Tue Sep 29", "Wed Oct 7", etc., with optional year if present
  match = re.search(
      r"\b(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+[A-Za-z]{3}\s+\d{1,2}(?:,?\s*\d{4})?\b",
      text,
      re.IGNORECASE,
  )
  if match:
    date_str = match.group(0).strip()
    # Append current season year if missing
    if not re.search(r"\d{4}", date_str):
      date_str += ", 2026"
    return date_str
  return ""


def scrape_schedule():
  print("Fetching schedule...")
  schedule_data = {"last_game": None, "upcoming_games": []}
  seen_games = set()

  try:
    res = requests.get(SCHEDULE_URL, headers=HEADERS, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.find_all("tr")
    current_date = ""

    for row in rows:
      tds = row.find_all(["td", "th"])
      cols = [re.sub(r"\s+", " ", td.text).strip() for td in tds]

      if not cols:
        continue

      raw_row_text = " ".join(cols).strip()

      # 1. Capture Date Block Header (e.g. "Tue Sep 29")
      found_date = extract_hna_date(raw_row_text)
      if found_date and len(cols) <= 2:
        current_date = found_date
        continue

      # 2. Skip table column header rows ("Time # Away Home Location")
      if "TIME" in raw_row_text.upper() and "AWAY" in raw_row_text.upper():
        continue

      # 3. Process Game Row (Matches time string like "10:20 PM")
      time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", raw_row_text)
      if time_match:
        time_str = time_match.group(0)

        # Columns align to: [0: Time, 1: #, 2: Away, 3: Home, 4: Location]
        if len(cols) >= 5:
          away_raw = cols[2]
          home_raw = cols[3]
          location_raw = cols[4]

          location_clean = (
              location_raw.replace("Map", "").replace("map", "").strip()
          )

          game_obj = {
              "date": current_date or "Sep. 29, 2026",
              "time": time_str,
              "home_team": clean_team_name(home_raw),
              "away_team": clean_team_name(away_raw),
              "location": location_clean or "Local Rink",
          }

          game_signature = f"{game_obj['date']}_{game_obj['time']}_{game_obj['home_team']}_{game_obj['away_team']}"
          if game_signature not in seen_games:
            seen_games.add(game_signature)
            schedule_data["upcoming_games"].append(game_obj)

  except Exception as e:
    print(f"Error fetching schedule: {e}")

  with open("schedule.json", "w") as f:
    json.dump(schedule_data, f, indent=2)

  print(
      f"Schedule complete! Saved"
      f" {len(schedule_data['upcoming_games'])} upcoming games."
  )


if __name__ == "__main__":
  scrape_schedule()
