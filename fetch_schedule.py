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

# Explicit single-team page query for active season
SCHEDULE_URL = "https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=5717&teamID=683136&printPage=0"


def clean_team_name(name):
  if not name:
    return ""
  # Strip division codes like "KRA F", "VIP F", "REA F" from team names
  cleaned = re.sub(
      r"\s+[A-Z]{2,4}\s+[A-Z0-9]\b", "", name.strip(), flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r"\b[A-Z]{2,5}\s+[A-Z0-9]\b$", "", cleaned, flags=re.IGNORECASE
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
      r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
  ]
  for pat in patterns:
    match = re.search(pat, text, re.IGNORECASE)
    if match:
      return match.group(0).strip()
  return ""


def scrape_schedule():
  print("Fetching HNA schedule for Kraken Beers...")
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

      # Capture date headers (e.g., "Tuesday, Sep 29, 2026" or "Sep 29, 2026")
      found_date = extract_hna_date(raw_row_text)
      if (
          found_date
          and "GAME #" not in row_upper
          and "VISITOR" not in row_upper
      ):
        current_date = found_date

      # Skip table headers, summary rows, and completed games with scores
      if any(
          kw in row_upper
          for kw in ["FINAL", "RESULT", "GAME #", "RECORD:", "CANCELLED"]
      ):
        continue

      if re.search(r"\b\d+\s*-\s*\d+\b", raw_row_text):
        continue

      # Locate time cell/pattern
      time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", row_upper)
      if not time_match:
        continue

      time_str = time_match.group(0)

      # Extract teams and location based on column positions
      visitor_raw = ""
      home_raw = ""

      if len(cols) >= 4:
        # Standard HNA row structure: [Game #, Time, Visitor, Home, Location]
        visitor_raw = cols[2]
        home_raw = cols[3]
      else:
        # Fallback regex split if columns merged
        matchup_cols = [
            c for c in cols if " VS " in c.upper() or " AT " in c.upper()
        ]
        if matchup_cols:
          parts = re.split(
              r"\s+(?:VS|AT)\s+", matchup_cols[0], flags=re.IGNORECASE
          )
          if len(parts) >= 2:
            visitor_raw, home_raw = parts[0], parts[1]

      # Clean team names
      away_clean = clean_team_name(visitor_raw)
      home_clean = clean_team_name(home_raw)

      # Map locations
      location = "Local Rink"
      for col in reversed(cols):
        if any(
            loc_kw in col.upper()
            for loc_kw in ["RINK", "WSA", "PLAYLAND", "ICE", "MAP"]
        ):
          location = col.replace("MAP", "").strip()
          break

      # Ensure team defaults fall back cleanly
      if "KRAKEN" in visitor_raw.upper():
        away_clean = "Kraken Beers"
      elif "KRAKEN" in home_raw.upper():
        home_clean = "Kraken Beers"

      if not home_clean or home_clean.upper() == "OPPONENT":
        home_clean = (
            "Kraken Beers" if away_clean != "Kraken Beers" else "Opponent"
        )
      if not away_clean or away_clean.upper() == "OPPONENT":
        away_clean = (
            "Kraken Beers" if home_clean != "Kraken Beers" else "Opponent"
        )

      game_obj = {
          "date": current_date or "TBD",
          "time": time_str,
          "home_team": home_clean,
          "away_team": away_clean,
          "location": location,
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
