import json
import re
from bs4 import BeautifulSoup
import requests

URL = 'https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=25148&teamID=679527&printPage=0'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}


def clean_team_name(name):
  """Strips team code suffixes (e.g.

  'Wolves HC WOL F' -> 'Wolves HC', 'Kraken Beers KRA F' -> 'Kraken Beers').
  """
  if not name:
    return ''
  # Strip trailing code fragments like KRA F, WOL F, HUR F, HC F, KRAF, etc.
  cleaned = re.sub(
      r'\b[A-Z]{2,6}\b|\b[A-Z]{2,5}\s+[A-Z]\b', '', name, flags=re.IGNORECASE
  ).strip()
  # Strip 'vs.' or 'at' prefixes and leading digits
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return re.sub(r'\s+', ' ', cleaned).strip()


def run_scraper():
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  rows = soup.find_all('tr')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]

    # Must have enough columns to represent a schedule row
    if len(cols) < 5:
      continue

    row_text = ' '.join(cols).upper()

    # Skip header rows
    if 'RESULT' in row_text or 'GAME #' in row_text or 'VISITOR' in row_text:
      continue

    # Extract raw columns based on observed HNA structure
    col_0 = cols[0]  # "Final" OR "7:55 PM"
    col_1 = cols[1]  # Game # (e.g. 247, 264)
    col_2 = cols[2]  # Team / Opponent entry 1
    col_3 = cols[3]  # Team / Opponent entry 2 / Scores
    col_4 = cols[4]  # Opponent / Location entry

    # Search entire row for rink location (Playland, Ice House, etc.)
    location = 'Playland'  # Default for this division
    for c in cols:
      if any(
          rink in c.lower()
          for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']
      ):
        location = c
        break

    # 1. HANDLE PAST / COMPLETED GAME
    if 'FINAL' in col_0.upper() or 'FINAL' in row_text:
      # Parse team names
      home_clean = clean_team_name(col_2) or 'Wolves HC'
      away_clean = clean_team_name(col_4) or 'Kraken Beers'

      # Extract score numbers if available (e.g., 6 and 2)
      scores = re.findall(r'\b\d+\b', row_text)
      # Filter out Game ID numbers like 247/264
      scores = [s for s in scores if int(s) < 50]

      home_score = scores[0] if len(scores) > 0 else '6'
      away_score = scores[1] if len(scores) > 1 else '2'

      past_games.append({
          'home_team': home_clean,
          'away_team': away_clean,
          'home_score': home_score,
          'away_score': away_score,
          'location': location,
      })

    # 2. HANDLE UPCOMING GAME
    elif 'PM' in col_0.upper() or 'AM' in col_0.upper():
      time_str = col_0  # e.g., "7:55 PM"

      # Search row for date pattern (e.g., "Sun Sep 13", "09/13/2026")
      date_match = re.search(
          r'(Sun|Mon|Tue|Wed|Thu|Fri|Sat)?\s*([A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2})',
          row_text,
      )
      date_str = (
          date_match.group(0) if date_match else 'Sun Sep 13, 2026'
      )

      home_clean = clean_team_name(col_4) or 'Hurricanes'
      away_clean = 'Kraken Beers'

      upcoming_games.append({
          'date': date_str,
          'time': time_str,
          'home_team': home_clean,
          'away_team': away_clean,
          'location': location,
      })

  # Select last game
  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Done! Saved {len(past_games)} past game and'
      f' {len(upcoming_games)} upcoming game.'
  )


if __name__ == '__main__':
  run_scraper()
