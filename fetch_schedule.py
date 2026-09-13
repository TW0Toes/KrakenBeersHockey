import json
import re
from bs4 import BeautifulSoup
import requests

# HNA Direct Schedule Endpoint
URL = 'https://www.hna.com/leagues/sched_action.cfm?clientCode=HNA&leagueID=25148&levelID=0'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}


def clean_name(name):
  """Removes leading game IDs, 'vs.', and trailing HNA team uppercase codes (e.g., KRAF, HCWOLF)."""
  if not name:
    return ''
  # Strip team codes at the end (e.g. 'Wolves HCWOLF' -> 'Wolves')
  text = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', name).strip()
  # Strip numbers or vs/at prefixes
  text = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', text, flags=re.IGNORECASE)
  return text.strip()


def run_scraper():
  print('Fetching schedule from HNA...')
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  past_games = []
  upcoming_games = []

  rows = soup.find_all('tr')
  print(f'Total table rows found: {len(rows)}')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', col.text).strip()
        for col in row.find_all(['td', 'th'])
    ]

    # Skip rows without enough columns
    if len(cols) < 4:
      continue

    row_text = ' '.join(cols).upper()

    # Match Kraken Beers or team code KRAF
    if 'KRAKEN' not in row_text and 'KRAF' not in row_text:
      continue

    print(f'Matched Row: {cols}')

    # Map columns based on standard HNA row layouts
    # typical layout: [Date, Away Team, Home Team, Time/Score, Location]
    date_str = cols[0]
    away_raw = cols[1] if len(cols) > 1 else ''
    home_raw = cols[2] if len(cols) > 2 else ''
    time_or_score = cols[3] if len(cols) > 3 else ''
    location = cols[4] if len(cols) > 4 else ''

    away_clean = clean_name(away_raw)
    home_clean = clean_name(home_raw)

    # Detect Completed Game vs Upcoming
    if 'FINAL' in time_or_score.upper() or '-' in time_or_score:
      past_games.append({
          'date': date_str,
          'home_team': home_clean or 'Kraken Beers',
          'away_team': away_clean or 'Opponent',
          'summary': f'Final: {time_or_score}',
          'raw_score': time_or_score,
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

  # Set last game structure
  last_game = past_games[-1] if past_games else None

  output = {'last_game': last_game, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f"Finished! Found {len(past_games)} past games and"
      f" {len(upcoming_games)} upcoming games."
  )


if __name__ == '__main__':
  run_scraper()
