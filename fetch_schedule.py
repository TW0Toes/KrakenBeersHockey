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
    """Generically strips team code suffixes (e.g. 'Kraken Beers KRA F' -> 'Kraken Beers')."""
    if not name:
        return ""
    
    cleaned = re.sub(r'\b[A-Z]{2,5}\s+[A-Z0-9]\b$', '', name.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'\b[A-Z]{3,5}\b$', '', cleaned.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'^\d+\s*(vs\.?|at|@)?\s*', '', cleaned, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', cleaned).strip()

def extract_date_from_cells(cols):
    """Checks each column individually for any valid date format."""
    # Pattern 1: Day + Month + Date (e.g., 'Sun Sep 13', 'Sun, Sep 13', 'Sun Sep 13, 2026')
    date_pattern_1 = r'\b(Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,?\s+[A-Z][a-z]{2}\s+\d{1,2}(?:,?\s*\d{4})?\b'
    # Pattern 2: Numerical date (e.g., '09/13/2026' or '9/13')
    date_pattern_2 = r'\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b'

    for col in cols:
        match = re.search(date_pattern_1, col, re.IGNORECASE)
        if match:
            return match.group(0).strip()
            
        match_num = re.search(date_pattern_2, col)
        if match_num:
            return match_num.group(0).strip()
            
    return ""

def run_scraper():
    print("Fetching schedule from HNA...")
    res = requests.get(URL, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    upcoming_games = []
    rows = soup.find_all('tr')

    current_date = ""

    for row in rows:
        cols = [re.sub(r'\s+', ' ', td.text).strip() for td in row.find_all(['td', 'th'])]
        
        if not cols:
            continue

        raw_row_text = ' '.join(cols).upper()

        # Extract date from cells if present
        found_date = extract_date_from_cells(cols)
        if found_date:
            current_date = found_date

        # Skip headers, results, or short rows
        if len(cols) < 4 or any(kw in raw_row_text for kw in ['RESULT', 'GAME #', 'VISITOR', 'FINAL']):
            continue

        # Look for time string (AM/PM) in any cell
        time_str = ""
        for cell in cols:
            if 'PM' in cell.upper() or 'AM' in cell.upper():
                time_str = cell
                break

        if time_str:
            raw_team_1 = cols[2] if len(cols) > 2 else ""
            raw_team_2 = cols[4] if len(cols) > 4 else (cols[3] if len(cols) > 3 else "")

            team_1_clean = clean_team_name(raw_team_1)
            team_2_clean = clean_team_name(raw_team_2)

            location = "Playland"
            for c in cols:
                if any(rink in c.lower() for rink in ['playland', 'ice', 'arena', 'rink', 'center', 'ctr']):
                    location = c
                    break

            upcoming_games.append({
                "date": current_date,
                "time": time_str,
                "home_team": team_2_clean,
                "away_team": team_1_clean,
                "location": location
            })

    output = {
        "upcoming_games": upcoming_games
    }

    with open('schedule.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Done! Saved {len(upcoming_games)} game(s) with dates.")

if __name__ == '__main__':
    run_scraper()
