import json
import re
from bs4 import BeautifulSoup
import requests

# HNA Direct Search Action Endpoint
URL = 'https://www.hna.com/leagues/sched_action.cfm'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Content-Type': 'application/x-www-form-urlencoded',
}

# Form payload required to trigger HNA schedule render
payload = {
    'clientCode': 'HNA',
    'leagueID': '25148',
    'levelID': '0',
    'teamID': '0',
    'facilityID': '0',
    'month': '0',
}


def clean_team_name(name):
  """Strips team code suffixes (e.g.

  'Wolves HCWOLF' -> 'Wolves HC', 'Kraken BeersKRAF' -> 'Kraken Beers').
  """
  if not name:
    return ''
  # Strip trailing uppercase codes (e.g. HCWOLF, KRAF)
  cleaned = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', name).strip()
  # Remove leading match numbers or 'vs.' prefixes
  cleaned = re.sub(r'^\d+\s*(vs\.?|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return cleaned.strip()


def run_scraper():
  print('Posting schedule request to HNA...')
  session = requests.Session()

  # 1. Warm up session
  session.get(
      'https://www.hna.com/leagues/front_pageHNA.cfm?clientCode=HNA&leagueID=25148',
      headers=headers,
  )

  # 2. Submit form POST request
  res = session.post(URL, data=payload, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  rows = soup.find_all('tr')
  print(f'Total rows returned: {len(rows)}')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]
    row_text = ' '.join(cols).upper()

    # Match Kraken Beers or team code KRAF
    if 'KRAKEN' in row_text or 'KRAF' in row_text:
      print(f'Matched Kraken Game: {cols}')

      if len(cols) >= 4:
        date_str = cols[0]
        away_raw = cols[1] if len(cols) > 1 else ''
        home_raw = cols[2] if len(cols) > 2 else ''
        status_time = cols[3] if len(cols) > 3 else ''
        location = cols[4] if len(cols) > 4 else ''

        away_clean = clean_team_name(away_raw)
        home_clean = clean_team_name(home_raw)

        # Separate Completed vs Upcoming
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
      f'Done! Found {len(past_games)} past games and'
      f' {len(upcoming_games)} upcoming games.'
  )


if __name__ == '__main__':
  run_scraper()
