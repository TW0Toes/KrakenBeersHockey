import json
import re
from bs4 import BeautifulSoup
import requests

# HNA Direct Printable / Team Schedule Frame Endpoint
PRINT_URL = 'https://www.hna.com/leagues/sched_print.cfm?clientCode=HNA&leagueID=25148&levelID=0'
TEAM_URL = 'https://www.hna.com/leagues/sched_action.cfm?clientCode=HNA&leagueID=25148&levelID=0'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
}


def clean_team_name(name):
  """Removes numeric match IDs, 'vs.' prefixes, and team codes (e.g.

  'Wolves HCWOLF' -> 'Wolves HC').
  """
  if not name:
    return ''
  # Strip trailing uppercase team code block (e.g. HCWOLF, KRAF)
  cleaned = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', name).strip()
  # Remove leading digits or vs/at prefixes
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return cleaned.strip()


def run_scraper():
  session = requests.Session()

  # 1. First visit main page to get ColdFusion session cookies (CFID / CFTOKEN)
  print('Initializing HNA session...')
  session.get(
      'https://www.hna.com/leagues/front_pageHNA.cfm?clientCode=HNA&leagueID=25148',
      headers=headers,
  )

  # 2. Try Printable View Endpoint
  print('Fetching schedule data...')
  res = session.get(PRINT_URL, headers=headers)

  # Fallback to team schedule endpoint if printable view returns small body
  if len(res.text) < 2000:
    print('Print view blocked/empty. Trying team schedule endpoint...')
    res = session.get(TEAM_URL, headers=headers)

  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  # Find all table rows
  rows = soup.find_all('tr')
  print(f'Total table rows found: {len(rows)}')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', col.text).strip()
        for col in row.find_all(['td', 'th'])
    ]
    if len(cols) < 4:
      continue

    row_text = ' '.join(cols).upper()

    # Search for Kraken Beers or KRAF identifier
    if 'KRAKEN' in row_text or 'KRAF' in row_text:
      print(f'Matched Game Row: {cols}')

      date_str = cols[0]
      away_raw = cols[1] if len(cols) > 1 else ''
      home_raw = cols[2] if len(cols) > 2 else ''
      status_time = cols[3] if len(cols) > 3 else ''
      location = cols[4] if len(cols) > 4 else ''

      away_clean = clean_team_name(away_raw)
      home_clean = clean_team_name(home_raw)

      # Determine if Completed Game vs Upcoming Game
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

  # Set last game structure
  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Finished! Saved {len(past_games)} past games and'
      f' {len(upcoming_games)} upcoming games to schedule.json.'
  )


if __name__ == '__main__':
  run_scraper()
