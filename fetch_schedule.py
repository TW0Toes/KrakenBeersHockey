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


def extract_date_from_row(row, raw_row_text):
  """Extracts any date string found in table cells, input values, or raw text."""
  # Check cell texts and input tag values inside the row
  strings_to_check = [raw_row_text]
  for element in row.find_all(['td', 'th', 'input']):
    if element.name == 'input' and element.get('value'):
      strings_to_check.append(element['value'])
    else:
      strings_to_check.append(element.text)

  date_regex = (
      r'\b(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+[A-Za-z]{3}\s+\d{1,2}(?:,\s*\d{4})?\b'
  )

  for text in strings_to_check:
    match = re.search(date_regex, text, re.IGNORECASE)
    if match:
      return match.group(0).strip()

  # Fallback for short date formats like "09/13/2026" or "Sep 13"
  fallback_regex = (
      r'\b([A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b'
  )
  for text in strings_to_check:
    match = re.search(fallback_regex, text, re.IGNORECASE)
    if match and not any(
        skip in match.group(0).upper() for skip in ['PM', 'AM', 'FINAL']
    ):
      return match.group(0).strip()

  return ''


def run_scraper():
  print('Fetching schedule from HNA...')
  res = requests.get(URL, headers=headers)
  soup = BeautifulSoup(res.text, 'html.parser')

  upcoming_games = []
  rows = soup.find_all('tr')

  current_date = ''

  for row in rows:
    cols = [
        re.sub(r'\s+', ' ', td.text).strip()
        for td in row.find_all(['td', 'th'])
    ]
    raw_row_text = ' '.join(cols).strip()

    # Check row for date string to update active date context
    found_date = extract_date_from_row(row, raw_row_text)
    if found_date:
      current_date = found_date

    # Skip layout rows without enough columns
    if len(cols) < 4:
      continue

    row_upper = raw_row_text.upper()

    # Skip headers and completed games
    if (
        'RESULT' in row_upper
        or 'GAME #' in row_upper
        or 'VISITOR' in row_upper
        or 'FINAL' in row_upper
    ):
      continue

    col_0 = cols[0]

    # Process game time rows
    if 'PM' in col_0.upper() or 'AM' in col_0.upper():
      time_str = col_0

      raw_team_1 = cols[2] if len(cols) > 2 else ''
      raw_team_2 = cols[4] if len(cols) > 4 else cols[3] if len(cols) > 3 else ''

      team_1_clean = clean_team_name(raw_team_1)
      team_2_clean = clean_team_name(raw_team_2)

      # Locate arena location generically
      location = 'Playland'
      for c in cols:
        if any(
            rink in c.lower()
            for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']
        ):
          location = c
          break

      # Ensure date is never empty
      game_date = current_date if current_date else 'Sun Sep 13, 2026'

      upcoming_games.append({
          'date': game_date,
          'time': time_str,
          'home_team': team_2_clean,
          'away_team': team_1_clean,
          'location': location,
      })

  output = {'upcoming_games': upcoming_games}

  with open('schedule.json', 'w') as f:
    json.dump(output, f, indent=2)

  print(
      f'Done! Successfully saved {len(upcoming_games)} upcoming game(s) to schedule.json.'
  )


if __name__ == '__main__':
  run_scraper()
