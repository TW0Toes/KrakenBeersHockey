import json
import re
import requests

BASE_URL = "https://www.hna.com/leagues/front_pagehna.cfm?clientCode=HNA&leagueID=5805"
SCHEDULE_URL = "https://www.hna.com/leagues/sched_print.cfm?clientCode=HNA&leagueID=5805"
STANDINGS_URL = "https://www.hna.com/leagues/standings_print.cfm?clientCode=HNA&leagueID=5805"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def clean_text(text):
  return re.sub(r"\s+", " ", text).strip() if text else ""


def run_scraper():
  # Create a persistent session to hold cookies
  session = requests.Session()
  session.headers.update(HEADERS)

  # Step 1: Visit main page to initialize session/cookies and avoid 500 rejection
  print("Initializing HNA session...")
  try:
    init_res = session.get(BASE_URL, timeout=15)
    init_res.raise_for_status()
  except Exception as e:
    print(f"Warning: Session initialization failed: {e}")

  # Step 2: Fetch Schedule
  print("Fetching schedule...")
  schedule_data = {"last_game": None, "upcoming_games": []}

  try:
    # Pass main page as Referer header
    sched_headers = {"Referer": BASE_URL}
    res = session.get(SCHEDULE_URL, headers=sched_headers, timeout=15)
    res.raise_for_status()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")
    current_date = ""

    for row in rows:
      cols = [clean_text(td.text) for td in row.find_all(["td", "th"])]
      if len(cols) < 3:
        continue

      row_str = " ".join(cols)

      # Extract Date Header
      date_match = re.search(
          r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}", row_str
      )
      if date_match:
        current_date = date_match.group(0)

      # Target rows containing Kraken
      if "KRAKEN" in row_str.upper():
        time_str = next((c for c in cols if "PM" in c or "AM" in c), "")
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
            "home_team": home,
            "away_team": away,
            "location": location,
        })

  except Exception as e:
    print(f"Error fetching schedule: {e}")

  with open("schedule.json", "w") as f:
    json.dump(schedule_data, f, indent=2)
  print(
      f"Schedule updated! Found {len(schedule_data['upcoming_games'])} games."
  )

  # Step 3: Fetch Standings
  print("Fetching standings...")
  standings_list = []

  try:
    res = session.get(STANDINGS_URL, headers={"Referer": BASE_URL}, timeout=15)
    res.raise_for_status()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")
    in_f_div = False

    for row in rows:
      text = clean_text(row.text).upper()

      if "DIVISION" in text:
        in_f_div = any(
            x in text for x in ["F DIVISION", "DIVISION F", "DIV F", "DIV. F"]
        )
        continue

      if in_f_div:
        cols = [
            clean_text(td.text) for td in row.find_all(["td", "th"]) if td.text
        ]
        if not cols or "TEAM" in cols[0].upper() or "GP" in cols[0].upper():
          continue

        if len(cols) >= 6:
          try:
            standings_list.append({
                "team": cols[0],
                "gp": int(cols[1]),
                "w": int(cols[2]),
                "l": int(cols[3]),
                "t": int(cols[4]),
                "pts": int(cols[5]),
            })
          except (ValueError, IndexError):
            continue

    standings_list.sort(key=lambda x: x["pts"], reverse=True)

  except Exception as e:
    print(f"Error fetching standings: {e}")

  with open("standings.json", "w") as f:
    json.dump({"standings": standings_list}, f, indent=2)
  print(f"Standings updated! Saved {len(standings_list)} teams.")


if __name__ == "__main__":
  run_scraper()
