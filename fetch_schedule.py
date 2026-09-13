import json
import re
from bs4 import BeautifulSoup
import requests

# Direct URL with teamID 679527
URL = 'https://www.hna.com/leagues/schedules.cfm?clientID=2296&leagueID=25148&teamID=679527&printPage=0'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}


def clean_team_name(name):
  """Cleans team names by removing team code suffixes (e.g., 'Wolves HCWOLF' -> 'Wolves HC')."""
  if not name:
    return ''
  # Remove trailing 3-6 uppercase letter team code block
  cleaned = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', name).strip()
  # Remove leading match numbers or 'vs.' / 'at' prefixes
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return cleaned.strip()


def run_scraper():
  print('Fetching schedule from Kraken Beers team page...')
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  rows = soup.find_all('tr')
  print(f'Total rows inspected: {len(rows)}')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]

    # Needs at least 4 columns (Date, Visitor, Home, Score/Time)
    if len(cols) < 4:
      continue

    row_text = ' '.join(cols).upper()

    # Skip header rows or irrelevant rows
    if 'DATE' in cols[0].upper() or 'VISITOR' in row_text:
      continue

    # Filter for Kraken Beers or KRAF
    if 'KRAKEN' in row_text or 'KRAF' in row_text or len(cols) >= 4:
      print(f'Matched Row: {cols}')

      date_str = cols[0]
      away_raw = cols[1] if len(cols) > 1 else ''
      home_raw = cols[2] if len(cols) > 2 else ''
      status_time = cols[3] if len(cols) > 3 else ''
      location = cols[4] if len(cols) > 4 else ''

      away_clean = clean_team_name(away_raw)
      home_clean = clean_team_name(home_raw)

      # Check if Completed Game vs Upcoming Game
      if 'FINAL' in status_time.upper() or '-' in status_time:
        past_games.append({
            'date': date_str,
            'home_team': home_clean,
            'away_team': away_clean,
            'score_status': status_time,
            'location': location,
        })
      else:
        upcoming_games.append({
            'date': date_str,
            'time': status_time,
            'home_team': home_clean,
            'away_team': away_clean,
            'location': location,
        })

  # Grab last completed game
  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Success! Saved {len(past_games)} past games and'
      f' {len(upcoming_games)} upcoming games to schedule.json.'
  )


if __name__ == '__main__':
  run_scraper()
