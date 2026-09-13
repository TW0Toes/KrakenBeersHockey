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
  """Removes numeric game IDs and trailing 3-6 letter team code suffixes (e.g.

  'Kraken Beers KRA F' -> 'Kraken Beers').
  """
  if not name:
    return ''
  # Strip spacing/code patterns like KRA F, WOL F, HUR F or KRAF, HCWOLF
  cleaned = re.sub(
      r'\b[A-Z]{3,6}\b|\b[A-Z]{3,5}\s+[A-Z]\b', '', name, flags=re.IGNORECASE
  ).strip()
  # Remove leading match numbers or 'vs.' / 'at' prefixes
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return re.sub(r'\s+', ' ', cleaned).strip()


def parse_schedule():
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

    # Ignore headers or short layout rows
    if len(cols) < 5:
      continue

    row_text = ' '.join(cols).upper()

    # Skip table header rows
    if 'RESULT' in row_text or 'TIME' in row_text or 'GAME #' in row_text:
      continue

    # Identify date or game status in column 0 or 1
    # Standard HNA Team Schedule columns:
    # [Game#, Date/Day, Time/Status, Away Team, Home Team, Location, ...]
    # Or: [Date, Time/Status, Home Team, Away Team, Location]
    
    # Check for completed game (Final or numeric scores present)
    is_final = 'FINAL' in row_text

    # Extract fields with safe column fallbacks
    date_val = cols[0] if len(cols) > 0 else ''
    time_or_status = cols[1] if len(cols) > 1 else ''
    away_raw = cols[2] if len(cols) > 2 else ''
    home_raw = cols[3] if len(cols) > 3 else ''
    location_val = cols[4] if len(cols) > 4 else ''

    # If game number is in column 0, shift columns over
    if date_val.isdigit() and len(cols) >= 6:
      date_val = cols[1]
      time_or_status = cols[2]
      away_raw = cols[3]
      home_raw = cols[4]
      location_val = cols[5]

    away_clean = clean_team_name(away_raw)
    home_clean = clean_team_name(home_raw)

    if is_final or 'FINAL' in time_or_status.upper():
      # Parse final score if available in the text
      past_games.append({
          'date': date_val,
          'home_team': home_clean,
          'away_team': away_clean,
          'status': time_or_status,
          'location': location_val,
      })
    else:
      upcoming_games.append({
          'date': date_val,
          'time': time_or_status,
          'home_team': home_clean,
          'away_team': away_clean,
          'location': location_val,
      })

  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Successfully written: {len(past_games)} past game, {len(upcoming_games)} upcoming.'
  )


if __name__ == '__main__':
  parse_schedule()
