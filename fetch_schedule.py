import json
import re
from bs4 import BeautifulSoup
import requests

# Direct schedule endpoint for HNA League ID 25148
URL = 'https://www.hna.com/leagues/sched_action.cfm?clientCode=HNA&leagueID=25148&levelID=0'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}


def clean_team_name(name):
  """Removes team code suffixes (e.g., 'Wolves HCWOLF' -> 'Wolves HC', 'Kraken BeersKRAF' -> 'Kraken Beers')."""
  if not name:
    return ''
  # Strip trailing 3-6 letter uppercase codes (e.g. HCWOLF, KRAF)
  cleaned = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', name).strip()
  # Remove leading match numbers or 'vs.' prefixes if present
  cleaned = re.sub(r'^\d+\s*(vs\.?|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return cleaned.strip()


def run_scraper():
  session = requests.Session()
  # First hit the main page to establish any required session cookies
  session.get(
      'https://www.hna.com/leagues/front_pageHNA.cfm?clientCode=HNA&leagueID=25148',
      headers=headers,
  )

  # Fetch the actual schedule content
  res = session.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  # Find all table cells / rows
  rows = soup.find_all('tr')
  print(f'Inspecting {len(rows)} rows from schedule endpoint...')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]

    if len(cols) < 4:
      continue

    row_text = ' '.join(cols).upper()

    # Filter for Kraken Beers or team code KRAF
    if 'KRAKEN' not in row_text and 'KRAF' not in row_text:
      continue

    print(f'Matched Row: {cols}')

    # Typical column layout: [Date, Visitor/Away, Home, Score/Time, Location]
    date_str = cols[0]
    away_raw = cols[1] if len(cols) > 1 else ''
    home_raw = cols[2] if len(cols) > 2 else ''
    status_time = cols[3] if len(cols) > 3 else ''
    location = cols[4] if len(cols) > 4 else ''

    away_clean = clean_team_name(away_raw)
    home_clean = clean_team_name(home_raw)

    # Check if completed game (contains FINAL or a dash score line)
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

  # Select last game
  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Done! Saved {len(past_games)} past games and'
      f' {len(upcoming_games)} upcoming games to schedule.json.'
  )


if __name__ == '__main__':
  run_scraper()
