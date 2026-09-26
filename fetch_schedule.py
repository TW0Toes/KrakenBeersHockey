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

# Active 2026-2027 single-team page endpoint
SCHEDULE_URL = "https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=5717&teamID=683136&printPage=0"


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
  print("Fetching team schedule...")
  schedule_data = {"last_game": None, "upcoming_games": []}
  seen_games = set()

  try:
    res = requests.get(SCHEDULE_URL, headers=HEADERS, timeout=15)
    res.raise_for_status()
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

      # Extract date from date headers or rows
      found_date = extract_hna_date(raw_row_text)
      if found_date:
        current_date = found_date

      # Ignore header and summary rows
      if any(
          kw in row_upper
          for kw in ["RESULT", "GAME #", "VISITOR", "FINAL", "RECORD:", "LAST:"]
      ):
        continue

      # Ignore completed/past games with numerical score outputs (e.g. '4 - 2')
      if re.search(r"\b\d+\s*-\s*\d+\b", raw_row_text):
        continue

      # Locate time in row (e.g., '10:20 PM')
      time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", row_upper)
      if not time_match:
        continue

      time_str = time_match.group(0)

      # On HNA single-team pages with >= 4 columns:
      # cols[1] = Time, cols[2] = Visitor, cols[3] = Home, cols[4] = Rink Location
      if len(cols) >= 4:
        visitor_raw = cols[2]
        home_raw = cols[3]
        location_raw = cols[4] if len(cols) > 4 else "Local Rink"
      else:
        # Fallback if text string contains VS/AT
        teams = [c for c in cols if " VS " in c.upper() or " AT " in c.upper()]
        if teams:
          parts = re.split(r"\s+(?:VS|AT)\s+", teams[0], flags=re.IGNORECASE)
          visitor_raw, home_raw = (
              parts[0],
              parts[1] if len(parts) > 1 else "Opponent",
          )
        else:
          visitor_raw, home_raw = "Kraken Beers", "Opponent"
        location_raw = cols[-1] if len(cols) > 3 else "Local Rink"

      home_clean = clean_team_name(home_raw)
      away_clean = clean_team_name(visitor_raw)

      game_obj = {
          "date": current_date or "TBD",
          "time": time_str,
          "home_team": home_clean or "Kraken Beers",
          "away_team": away_clean or "Opponent",
          "location": location_raw,
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
