import json
import re
from bs4 import BeautifulSoup
import requests

# Direct schedule URL for HNA League ID 25148
URL = 'https://www.hna.com/leagues/sched_action.cfm?clientCode=HNA&leagueID=25148&levelID=0'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}


def clean_team_name(name):
  """Strips out numeric IDs and short code suffixes (e.g., '247 vs. Wolves HCWOLF' -> 'Wolves HC')."""
  if not name:
    return ''

  # Remove leading numbers/vs prefix
  cleaned = re.sub(r'^\d+\s*(vs\.?|@)?\s*', '', name, flags=re.IGNORECASE)

  # Remove trailing 3-6 letter team code uppercase block at the end (e.g. HCWOLF, KRAF)
  cleaned = re.sub(r'([a-zA-Z0-9\s]+?)([A-Z]{3,6})$', r'\1', cleaned).strip()

  return cleaned.strip()


def parse_schedule():
  response = requests.get(URL, headers=headers)
  soup = BeautifulSoup(response.text, 'html.parser')

  past_games = []
  upcoming_games = []

  # Target table rows
  rows = soup.find_all('tr')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', col.text).strip()
        for col in row.find_all(['td', 'th'])
    ]

    # HNA schedule rows usually contain 5+ columns (Date, Visitor, Home, Score/Time, Location)
    if len(cols) < 5:
      continue

    row_text = ' '.join(cols).upper()

    # Match Kraken Beers or team code KRAF
    if 'KRAKEN' not in row_text and 'KRAF' not in row_text:
      continue

    date_str = cols[0]
    away_raw = cols[1]
    home_raw = cols[2]
    status_or_time = cols[3]
    location = cols[4]

    away_clean = clean_team_name(away_raw)
    home_clean = clean_team_name(home_raw)

    # Check if game is completed (contains Final or a score dash)
    if 'FINAL' in status_or_time.upper() or '-' in status_or_time:
      # Parse scores if available (e.g. "Final: 6-2" or "6-2")
      scores = re.findall(r'\d+', status_or_time)
      home_score = scores[0] if len(scores) > 0 else ''
      away_score = scores[1] if len(scores) > 1 else ''

      past_games.append({
          'date': date_str,
          'home_team': home_clean,
          'away_team': away_clean,
          'home_score': home_score,
          'away_score': away_score,
          'status': status_or_time,
          'location': location,
      })
    else:
      upcoming_games.append({
          'date': date_str,
          'time': status_or_time,
          'home_team': home_clean,
          'away_team': away_clean,
          'location': location,
      })

  # Select the most recent completed game as last_game
  last_game = past_games[-1] if past_games else None

  # Fallback formatting if last game scores couldn't be parsed directly from HTML columns
  if last_game and not last_game['home_score']:
    last_game_output = {
        'summary': f"Final: {last_game['home_team']} vs {last_game['away_team']}",
        'raw_status': last_game['status'],
    }
  elif last_game:
    last_game_output = {
        'home_team': last_game['home_team'],
        'home_score': last_game['home_score'],
        'away_team': last_game['away_team'],
        'away_score': last_game['away_score'],
    }
  else:
    last_game_output = None

  output = {'last_game': last_game_output, 'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)


if __name__ == '__main__':
  parse_schedule()
