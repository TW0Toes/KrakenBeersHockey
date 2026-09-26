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
  # Strip division codes (e.g., KRA F, REA F, VIP F, etc.)
  cleaned = re.sub(
      r"\s+[A-Z]{2,4}\s+[A-Z0-9]\b", "", name.strip(), flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r"\b[A-Z]{2,5}\s+[A-Z0-9]\b$", "", cleaned, flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r"^\d+\s*(vs\.?|at|@)?\s*", "", cleaned, flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r"\b(MAP|DIRECTIONS)\b", "", cleaned, flags=re.IGNORECASE
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
  print("Fetching Kraken Beers schedule...")
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
          if td.text.strip()
      ]
      if not cols:
        continue

      raw_row_text = " ".join(cols).strip()
      row_upper = raw_row_text.upper()

      # Extract Date Header
      found_date = extract_hna_date(raw_row_text)
      if (
          found_date
          and "GAME #" not in row_upper
          and "VISITOR" not in row_upper
      ):
        current_date = found_date
        continue

      # Skip headers, cancelled games, and completed game scores
      if any(
          kw in row_upper
          for kw in ["FINAL", "RESULT", "GAME #", "RECORD:", "CANCELLED"]
      ):
        continue
      if re.search(r"\b\d+\s*-\s*\d+\b", raw_row_text):
        continue

      # Check for time format
      time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", row_upper)
      if not time_match:
        continue

      time_str = time_match.group(0)

      # Extract Location
      location = "Local Rink"
      location_cols = []
      for col in cols:
        if any(
            loc_kw in col.upper()
            for loc_kw in [
                "RINK",
                "WSA",
                "PLAYLAND",
                "ICE",
                "CENTER",
                "ARENA",
            ]
        ):
          location_cols.append(col.replace("Map", "").strip())

      if location_cols:
        location = location_cols[0]

      # Extract Teams dynamically across all columns
      candidate_teams = []
      for col in cols:
        col_cleaned = clean_team_name(col)
        # Skip time, location strings, and game numbers
        if (
            col_cleaned
            and not re.search(r"\b\d{1,2}:\d{2}\b", col_cleaned)
            and not any(
                loc_kw in col_cleaned.upper()
                for loc_kw in ["RINK", "WSA", "PLAYLAND", "ICE", "MAP"]
            )
            and not col_cleaned.isdigit()
        ):
          candidate_teams.append(col_cleaned)

      # Determine Home vs Away
      home_team = "Kraken Beers"
      away_team = "Kraken Beers"

      non_kraken = [
          t for t in candidate_teams if "KRAKEN" not in t.upper()
      ]
      opponent = non_kraken[0] if non_kraken else "Opponent"

      # Check if Kraken is Visitor or Home in raw row text
      # Standard HNA ordering: Visitor @ Home or Visitor vs Home
      kraken_pos = row_upper.find("KRAKEN")
      opp_pos = row_upper.find(opponent.upper()) if opponent != "Opponent" else -1

      if opp_pos != -1 and opp_pos < kraken_pos:
        # Opponent appears first -> Opponent is Away, Kraken is Home
        away_team = opponent
        home_team = "Kraken Beers"
      else:
        # Kraken appears first -> Kraken is Away, Opponent is Home
        away_team = "Kraken Beers"
        home_team = opponent

      game_obj = {
          "date": current_date or "TBD",
          "time": time_str,
          "home_team": home_team,
          "away_team": away_team,
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
