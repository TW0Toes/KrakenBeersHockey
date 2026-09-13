import json
import re
from bs4 import BeautifulSoup
import requests

# HNA Schedule Direct Endpoint
URL = 'https://www.hna.com/leagues/sched_action.cfm?clientCode=HNA&leagueID=25148&levelID=0&printable=1'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    ),
}


def clean_team_name(name):
  """Cleans team names by removing team code suffixes (e.g.

  'Wolves HCWOLF' -> 'Wolves HC') and game numbers.
  """
  if not name:
    return ''
  # Strip trailing 3-6 uppercase letters (league team codes like KRAF, HCWOLF)
  cleaned = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', name).strip()
  # Remove leading digits or vs/at prefixes
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  return cleaned.strip()


def run_scraper():
  print('Fetching schedule from HNA printable view...')
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  # Find all table rows across the document
  rows = soup.find_all('tr')
  print(f'Total rows inspected: {len(rows)}')

  for row in rows:
    # Extract cell text
    cells = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]
    row_text = ' '.join(cells).upper()

    # Search for team identifier
    if 'KRAKEN' in row_text or 'KRAF' in row_text:
      print(f'Found Kraken Row: {cells}')

      # Format: [Date, Away/Visitor, Home, Score/Time, Location]
      if len(cells) >= 4:
        date_str = cells[0]
        away_raw = cells[1] if len(cells) > 1 else ''
        home_raw = cells[2] if len(cells) > 2 else ''
        time_or_score = cells[3] if len(cells) > 3 else ''
        location = cells[4] if len(cells) > 4 else ''

        away_clean = clean_team_name(away_raw)
        home_clean = clean_team_name(home_raw)

        if 'FINAL' in time_or_score.upper() or '-' in time_or_score:
          past_games.append({
              'date': date_str,
              'home_team': home_clean,
              'away_team': away_clean,
              'score_status': time_or_score,
              'location': location,
          })
        else:
          upcoming_games.append({
              'date': date_str,
              'time': time_or_score,
              'home_team': home_clean,
              'away_team': away_clean,
              'location': location,
          })

  # Structure output
  last_game = past_games[-1] if past_games else None
  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Success: Saved {len(past_games)} past games and'
      f' {len(upcoming_games)} upcoming games to schedule.json.'
  )


if __name__ == '__main__':
  run_scraper()
