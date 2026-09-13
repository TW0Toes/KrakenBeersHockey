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
  """Generically strips team code suffixes (e.g.

  'Kraken Beers KRA F' -> 'Kraken Beers', 'Hurricanes HUR F' -> 'Hurricanes').
  """
  if not name:
    return ''

  # 1. Strip trailing 2-5 uppercase letter codes with optional single letter suffix (e.g. KRA F, HUR F, WOL F, NY F)
  cleaned = re.sub(
      r'\b[A-Z]{2,5}\s+[A-Z0-9]\b$', '', name.strip(), flags=re.IGNORECASE
  )

  # 2. Strip standalone trailing uppercase code blocks (e.g. KRAF, WOLF, HUR)
  cleaned = re.sub(r'\b[A-Z]{3,5}\b$', '', cleaned.strip(), flags=re.IGNORECASE)

  # 3. Strip leading match IDs or prefixes ("vs", "at", etc.)
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)

  return re.sub(r'\s+', ' ', cleaned).strip()


def run_scraper():
  print('Fetching schedule...')
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  upcoming_games = []
  rows = soup.find_all('tr')

  current_date = ''  # Track date across row iterations

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]
    row_text = ' '.join(cols).strip()

    # Search for date pattern across any table row (e.g., "Sun Sep 13", "Sun Sep 13, 2026", "09/13/2026")
    date_match = re.search(
        r'\b(Sun|Mon|Tue|Wed|Thu|Fri|Sat)?\s*([A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2})(,\s*\d{4})?\b',
        row_text,
        re.IGNORECASE,
    )
    if date_match:
      current_date = date_match.group(0).strip()

    # Ignore layout rows without enough columns
    if len(cols) < 5:
      continue

    row_upper = row_text.upper()

    # Skip header rows and completed past games
    if (
        'RESULT' in row_upper
        or 'GAME #' in row_upper
        or 'VISITOR' in row_upper
        or 'FINAL' in row_upper
    ):
      continue

    col_0 = cols[0]  # Time or Status string

    # Process rows with valid game times
    if 'PM' in col_0.upper() or 'AM' in col_0.upper():
      time_str = col_0

      # Dynamically map and clean team columns
      raw_team_1 = cols[2] if len(cols) > 2 else ''
      raw_team_2 = cols[4] if len(cols) > 4 else ''

      team_1_clean = clean_team_name(raw_team_1)
      team_2_clean = clean_team_name(raw_team_2)

      # Locate arena location dynamically
      location = 'Playland'  # Fallback rink
      for c in cols:
        if any(
            rink in c.lower()
            for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']
        ):
          location = c
          break

      upcoming_games.append({
          'date': current_date,
          'time': time_str,
          'home_team': team_2_clean,
          'away_team': team_1_clean,
          'location': location,
      })

  output = {'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Done! Successfully saved {len(upcoming_games)} upcoming game(s) with dates.'
  )


if __name__ == '__main__':
  run_scraper()
