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

  'Kraken Beers KRA F' -> 'Kraken Beers', 'Rangers NY F' -> 'Rangers',
  'Bruins BRU' -> 'Bruins').
  """
  if not name:
    return ''

  # 1. Remove trailing 2-5 letter code combinations with optional trailing letter/number (e.g. KRA F, WOL F, HUR F, NY F)
  cleaned = re.sub(
      r'\b[A-Z]{2,5}\s+[A-Z0-9]\b$', '', name.strip(), flags=re.IGNORECASE
  )

  # 2. Remove trailing standalone 3-5 uppercase code words if present at end of string (e.g. KRAF, WOLF)
  cleaned = re.sub(r'\b[A-Z]{3,5}\b$', '', cleaned.strip(), flags=re.IGNORECASE)

  # 3. Clean up leading numbers, "vs", "at", or duplicate spaces
  cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
  cleaned = re.sub(r'\s+', ' ', cleaned).strip()

  return cleaned


def run_scraper():
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  upcoming_games = []
  rows = soup.find_all('tr')

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]

    # Must have enough columns for a schedule row
    if len(cols) < 5:
      continue

    row_text = ' '.join(cols).upper()

    # Skip header rows or completed past games
    if (
        'RESULT' in row_text
        'GAME #' in row_text
        or 'VISITOR' in row_text
        or 'FINAL' in row_text
    ):
      continue

    col_0 = cols[0]  # Time or Status (e.g., "7:55 PM")

    # Match time rows for upcoming games
    if 'PM' in col_0.upper() or 'AM' in col_0.upper():
      time_str = col_0

      # Extract Date from row (e.g., "Sun Sep 13", "Sun Sep 13, 2026", "09/13/2026")
      date_match = re.search(
          r'(Sun|Mon|Tue|Wed|Thu|Fri|Sat)?\s*([A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2})',
          row_text,
      )
      date_str = date_match.group(0) if date_match else ''

      # Dynamically parse away and home teams using column positions
      # Generically clean both team entries without hard-coded team strings
      raw_team_1 = cols[2] if len(cols) > 2 else ''
      raw_team_2 = cols[4] if len(cols) > 4 else ''

      team_1_clean = clean_team_name(raw_team_1)
      team_2_clean = clean_team_name(raw_team_2)

      # Determine location generically by checking row cells
      location = 'Playland'  # Default fallback
      for c in cols:
        if any(
            rink in c.lower()
            for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']
        ):
          location = c
          break

      upcoming_games.append({
          'date': date_str,
          'time': time_str,
          'home_team': team_2_clean,
          'away_team': team_1_clean,
          'location': location,
      })

  output = {'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(f'Done! Saved {len(upcoming_games)} upcoming game(s).')


if __name__ == '__main__':
  run_scraper()
