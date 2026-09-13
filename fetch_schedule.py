import json
import re
from bs4 import BeautifulSoup
import requests

# HNA League Schedule Page
URL = 'https://www.hna.com/leagues/sched_action.cfm?clientCode=HNA&leagueID=25148'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}


def clean_team_name(name):
  """Removes numeric game IDs or internal league codes attached to team names."""
  if not name:
    return ''
  # Strip trailing uppercase code suffixes (e.g. 'Wolves HCWOLF' -> 'Wolves HC')
  cleaned = re.sub(r'([a-zA-Z\s]+)[A-Z]{3,6}$', r'\1', name).strip()
  # Remove leading digits/game identifiers if present
  cleaned = re.sub(r'^\d+\s+', '', cleaned).strip()
  return cleaned


def parse_hna_schedule():
  response = requests.get(URL, headers=headers)
  soup = BeautifulSoup(response.text, 'html.parser')

  past_games = []
  upcoming_games = []

  # Find schedule table rows
  rows = soup.find_all('tr')

  for row in rows:
    cols = [col.text.strip() for col in row.find_all(['td', 'th'])]
    if len(cols) < 5:
      continue

    # Join row text to check if Kraken Beers is playing
    row_str = ' '.join(cols).upper()
    if 'KRAKEN BEERS' not in row_str and 'KRAF' not in row_str:
      continue

    date_str = cols[0]
    home_raw = cols[1]
    away_raw = cols[2]
    score_or_time = cols[3]
    location = cols[4]

    home_clean = clean_team_name(home_raw)
    away_clean = clean_team_name(away_raw)

    # Check if game is completed (contains a final score like '6-2' or 'Final: ...')
    if 'FINAL' in score_or_time.upper() or '-' in score_or_time:
      # Parse scores if formatted as numbers/scores
      past_games.append({
          'date': date_str,
          'home_team': home_clean,
          'away_team': away_clean,
          'score': score_or_time,
          'location': location,
      })
    else:
      upcoming_games.append({
          'date_time': f'{date_str} @ {score_or_time}',
          'date': date_str,
          'time': score_or_time,
          'home_team': home_clean,
          'away_team': away_clean,
          'location': location,
      })

  # Structure data output
  schedule_data = {
      'last_game': past_games[-1] if past_games else None,
      'upcoming_games': upcoming_games,
  }

  with open('schedule.json', 'w') as f:
    json.dump(schedule_data, f, indent=2)


if __name__ == '__main__':
  parse_hna_schedule()
