import json
import re
import requests
from bs4 import BeautifulSoup

# Using explicit clientID=2296 and printPage=0 to prevent ColdFusion 500 errors
SCHEDULE_URL = "https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=25148&teamID=679527&printPage=0"
STANDINGS_URL = "https://www.hna.com/leagues/standings.cfm?clientID=2296&leagueID=5717&printPage=0"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


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
  print("Fetching schedule...")
  schedule_data = {"last_game": None, "upcoming_games": []}

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

      found_date = extract_hna_date(raw_row_text)
      if found_date:
        current_date = found_date

      if any(
          kw in row_upper
          for kw in ["RESULT", "GAME #", "VISITOR", "FINAL", "RECORD:", "LAST:"]
      ):
        continue

      if "KRAKEN" in row_upper or len(cols) >= 3:
        time_str = next(
            (c for c in cols if "PM" in c.upper() or "AM" in c.upper()), ""
        )
        teams = [c for c in cols if " VS " in c.upper() or " AT " in c.upper()]

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

        schedule_data["upcoming_games"].append({
            "date": current_date or "TBD",
            "time": time_str,
            "home_team": clean_team_name(home),
            "away_team": clean_team_name(away),
            "location": location,
        })
  except Exception as e:
    print(f"Error fetching schedule: {e}")

  with open("schedule.json", "w") as f:
    json.dump(schedule_data, f, indent=2)
  print(
      f"Schedule complete! Saved {len(schedule_data['upcoming_games'])} games."
  )


def scrape_standings():
  print("Fetching standings...")
  standings_data = []

  try:
    res = requests.get(STANDINGS_URL, headers=HEADERS, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    in_f_division = False
    rows = soup.find_all("tr")

    for row in rows:
      text = row.text.strip().upper()

      if "DIVISION" in text:
        if any(
            x in text for x in ["F DIVISION", "DIVISION F", "DIV F", "DIV. F"]
        ):
          in_f_division = True
        else:
          in_f_division = False
        continue

      if not in_f_division:
        continue

      cols = [
          re.sub(r"\s+", " ", td.text).strip()
          for td in row.find_all(["td", "th"])
          if td.text.strip()
      ]

      if not cols or "TEAM" in cols[0].upper() or "GP" in cols[0].upper():
        continue

      if len(cols) >= 6:
        raw_team = cols[0]
        team_clean = clean_team_name(raw_team)

        try:
          standings_data.append({
              "team": team_clean,
              "gp": int(cols[1]),
              "w": int(cols[2]),
              "l": int(cols[3]),
              "t": int(cols[4]),
              "pts": int(cols[5]),
          })
        except ValueError:
          continue

    standings_data.sort(key=lambda x: x["pts"], reverse=True)
  except Exception as e:
    print(f"Error fetching standings: {e}")

  with open("standings.json", "w") as f:
    json.dump({"standings": standings_data}, f, indent=2)
  print(f"Standings complete! Saved {len(standings_data)} teams.")


if __name__ == "__main__":
  scrape_schedule()
  scrape_standings()
