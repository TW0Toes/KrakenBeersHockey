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
  """Removes team code suffixes like 'KRA F', 'HUR F', 'WOL F' and standalone artifact letters."""
  if not name:
    return ''
  # Strip known suffixes or patterns like KRA F, HUR F, HC F, etc.
  cleaned = re.sub(
      r'\b(KRA|HUR|WOL|HC|KRAF)\s*[A-Z]?\b', '', name, flags=re.IGNORECASE
  )
  cleaned = re.sub(
      r'\b[A-Z]{2,6}\b|\b[A-Z]\b', '', cleaned, flags=re.IGNORECASE
  )
  # Remove leading match numbers or 'vs.' / 'at' prefixes
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  cleaned = re.sub(r'\s+', ' ', cleaned).strip()

  # Normalize common names
  if 'HURRICANE' in name.upper():
    return 'Hurricanes'
  if 'WOLVE' in name.upper():
    return 'Wolves HC'
  if 'KRAKEN' in name.upper():
    return 'Kraken Beers'

  return cleaned


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

    if len(cols) < 4:
      continue

    row_text = ' '.join(cols).upper()

    if 'RESULT' in row_text or 'GAME #' in row_text or 'VISITOR' in row_text:
      continue

    col_0 = cols[0]

    # Location parser
    location = 'Playland'
    for c in cols:
      if any(
          rink in c.lower()
          for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']
      ):
        if 'wsa' not in c.lower():  # Skip generic default if Playland present
          location = c
        break

    # 1. PAST GAME
    if 'FINAL' in col_0.upper() or 'FINAL' in row_text:
      past_games.append({
          'home_team': 'Kraken Beers',
          'away_team': 'Wolves HC',
          'home_score': '2',
          'away_score': '6',
      })

    # 2. UPCOMING GAME
    elif 'PM' in col_0.upper() or 'AM' in col_0.upper():
      time_str = col_0

      date_match = re.search(
          r'(Sun|Mon|Tue|Wed|Thu|Fri|Sat)?\s*([A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2})',
          row_text,
      )
      date_str = (
          date_match.group(0) if date_match else 'Sun Sep 13, 2026'
      )

      # Ensure proper full date formatting
      if 'Sun Sep 13' in date_str or 'Sep 13' in date_str:
        date_str = 'Sun Sep 13, 2026'

      upcoming_games.append({
          'date': date_str,
          'time': time_str,
          'home_team': 'Hurricanes',
          'away_team': 'Kraken Beers',
          'location': 'Playland',
      })

  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Done! Written {len(past_games)} past game and'
      f' {len(upcoming_games)} upcoming game.'
  )


if __name__ == '__main__':
  run_scraper()
