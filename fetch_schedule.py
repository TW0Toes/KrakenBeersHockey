import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.hna.com/leagues/schedules.cfm"

CLIENT_ID = "2296"
LEAGUE_ID = "5717"
TEAM_ID = "683136"

OUTPUT_FILE = "schedule.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.hna.com/",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
}


# ============================================================
# HTTP
# ============================================================

def get_page(params):
    """Download one HNA schedule page."""

    response = requests.get(
        BASE_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# MONTH DISCOVERY
# ============================================================

def get_month_options(html):
    """
    Find all available month options from the HNA page.

    Returns values such as:

        9,2026
        10,2026
    """

    soup = BeautifulSoup(html, "html.parser")

    months = []

    for option in soup.find_all("option"):
        value = (option.get("value") or "").strip()
        text = option.get_text(" ", strip=True)

        if re.fullmatch(r"\d{1,2},\d{4}", value):
            if (value, text) not in months:
                months.append((value, text))

    return months


# ============================================================
# DATE PARSING
# ============================================================

def parse_date_heading(text):
    """
    Convert HNA date headings such as:

        Tue Sep 22, 2026

    into:

        2026-09-22
    """

    text = " ".join(text.split())

    patterns = [
        "%a %b %d, %Y",
        "%A %B %d, %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for pattern in patterns:
        try:
            dt = datetime.strptime(text, pattern)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def format_display_date(date_string):
    """
    Convert:

        2026-09-29

    into:

        Tuesday, September 29, 2026
    """

    dt = datetime.strptime(date_string, "%Y-%m-%d")

    # Using dt.day instead of %-d keeps this compatible with Windows.
    return f"{dt.strftime('%A, %B')} {dt.day}, {dt.year}"


# ============================================================
# DATE / TABLE ASSOCIATION
# ============================================================

def find_date_for_table(table):
    """
    Find the date heading associated with a schedule table.

    HNA places the date in an <h5> outside the table itself.
    """

    for heading in table.find_all_previous("h5"):
        text = heading.get_text(" ", strip=True)

        parsed = parse_date_heading(text)

        if parsed:
            return parsed

    current = table

    for _ in range(100):
        current = current.find_previous()

        if current is None:
            break

        text = current.get_text(" ", strip=True)

        if len(text) > 100:
            continue

        parsed = parse_date_heading(text)

        if parsed:
            return parsed

    return None


# ============================================================
# TEAM EXTRACTION
# ============================================================

def get_teams_from_row(row):
    """
    Extract the two teams from a game row.

    HNA includes both desktop and mobile versions of team links.

    For example:

        Kraken Beers
        KRA

    are actually the same team.

    We group links by teamID so they are treated as one team.
    """

    teams_by_id = {}

    for link in row.find_all("a"):
        href = link.get("href", "")

        match = re.search(
            r"teamID=(\d+)",
            href,
            re.IGNORECASE,
        )

        if not match:
            continue

        team_id = match.group(1)

        span = link.find("span")

        if span:
            name = span.get_text(" ", strip=True)
        else:
            name = link.get_text(" ", strip=True)

        name = " ".join(name.split())

        if not name:
            continue

        if team_id not in teams_by_id:
            teams_by_id[team_id] = []

        if name not in teams_by_id[team_id]:
            teams_by_id[team_id].append(name)

    teams = []

    for team_id, names in teams_by_id.items():

        # Prefer the full team name over the abbreviation.
        name = max(names, key=len)

        teams.append(
            {
                "team_id": team_id,
                "name": name,
            }
        )

    return teams


# ============================================================
# GAME ROW PARSING
# ============================================================

def parse_month(html):
    """
    Parse Kraken Beers games from one month's HNA page.

    Dates remain in ISO format internally so games can be
    sorted correctly.
    """

    soup = BeautifulSoup(html, "html.parser")

    games = []

    for table in soup.find_all("table"):

        date = find_date_for_table(table)

        if not date:
            continue

        for row in table.find_all("tr"):

            cells = row.find_all("td")

            if not cells:
                continue

            values = [
                " ".join(
                    cell.get_text(" ", strip=True).split()
                )
                for cell in cells
            ]

            if len(values) < 5:
                continue

            teams = get_teams_from_row(row)

            if len(teams) != 2:
                continue

            team_ids = {
                team["team_id"]
                for team in teams
            }

            # Only process games involving Kraken Beers.
            if TEAM_ID not in team_ids:
                continue

            # ------------------------------------------------
            # Determine team order from the actual row.
            # ------------------------------------------------

            team_links = []

            for link in row.find_all("a"):

                href = link.get("href", "")

                match = re.search(
                    r"teamID=(\d+)",
                    href,
                    re.IGNORECASE,
                )

                if not match:
                    continue

                team_id = match.group(1)

                if team_id not in [
                    team["team_id"]
                    for team in teams
                ]:
                    continue

                # Ignore the duplicate mobile/desktop link.
                if team_id not in team_links:
                    team_links.append(team_id)

            if len(team_links) != 2:
                continue

            team_lookup = {
                team["team_id"]: team["name"]
                for team in teams
            }

            away_team = team_lookup[team_links[0]]
            home_team = team_lookup[team_links[1]]

            # ------------------------------------------------
            # Time
            # ------------------------------------------------

            time_value = values[0] if values else ""

            if time_value.lower() == "final":
                time_value = ""

            elif not re.search(
                r"\d{1,2}:\d{2}",
                time_value,
            ):
                time_value = ""

            # ------------------------------------------------
            # Location
            # ------------------------------------------------

            location = ""

            if len(values) >= 7:
                location = values[6]

            # ------------------------------------------------
            # Save game
            # ------------------------------------------------

            game = {
                "date": date,
                "time": time_value,
                "away_team": away_team,
                "home_team": home_team,
                "location": location,
            }

            games.append(game)

    return games


# ============================================================
# DUPLICATION REMOVAL
# ============================================================

def deduplicate_games(games):
    """Remove duplicate games."""

    unique = {}

    for game in games:

        key = (
            game.get("date", ""),
            game.get("time", ""),
            game.get("away_team", ""),
            game.get("home_team", ""),
            game.get("location", ""),
        )

        unique[key] = game

    return list(unique.values())


# ============================================================
# SORTING
# ============================================================

def game_sort_key(game):
    """
    Sort games by date and time.

    Dates are still ISO format at this point.
    """

    date_string = game.get("date", "")

    try:
        date_value = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        )
    except ValueError:
        date_value = datetime.max

    time_string = game.get("time", "")

    if not time_string:
        time_value = datetime.min.time()

    else:
        try:
            time_value = datetime.strptime(
                time_string,
                "%I:%M %p",
            ).time()

        except ValueError:
            time_value = datetime.min.time()

    return date_value, time_value


# ============================================================
# MAIN SCRAPER
# ============================================================

def fetch_schedule():
    """
    Fetch the complete upcoming Kraken Beers schedule.

    Only upcoming games are returned.
    """

    # --------------------------------------------------------
    # Initial page
    # --------------------------------------------------------

    initial_params = {
        "clientID": CLIENT_ID,
        "leagueID": LEAGUE_ID,
        "schedType": "main",
        "printPage": "0",
        "selectedTeamID": TEAM_ID,
    }

    print("Loading HNA schedule...")

    initial_html = get_page(initial_params)

    # --------------------------------------------------------
    # Find all available months
    # --------------------------------------------------------

    months = get_month_options(initial_html)

    if not months:
        raise RuntimeError(
            "Could not find any month options on the HNA page."
        )

    print(f"Found {len(months)} month(s):")

    for month_value, month_name in months:
        print(
            f"  {month_value} -> {month_name}"
        )

    # --------------------------------------------------------
    # Fetch each month
    # --------------------------------------------------------

    all_games = []

    for month_value, month_name in months:

        print(
            f"Fetching {month_name}..."
        )

        params = {
            "clientID": CLIENT_ID,
            "leagueID": LEAGUE_ID,
            "schedType": "main",
            "printPage": "0",
            "selectedTeamID": TEAM_ID,
            "monthID": month_value,
        }

        html = get_page(params)

        month_games = parse_month(html)

        print(
            f"  Found {len(month_games)} "
            f"Kraken Beers game(s)"
        )

        all_games.extend(month_games)

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    all_games = deduplicate_games(all_games)

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    all_games.sort(
        key=game_sort_key
    )

    # --------------------------------------------------------
    # Keep ONLY upcoming games.
    #
    # HNA uses an empty time for completed games and a
    # scheduled time for upcoming games.
    # --------------------------------------------------------

    upcoming_games = [
        game
        for game in all_games
        if game.get("time")
    ]

    # Keep the next 5 upcoming games.
    upcoming_games = upcoming_games[:5]

    # --------------------------------------------------------
    # Convert dates to human-readable format AFTER sorting.
    # --------------------------------------------------------

    for game in upcoming_games:
        game["date"] = format_display_date(
            game["date"]
        )

    # --------------------------------------------------------
    # Final JSON structure
    # --------------------------------------------------------

    schedule = {
        "upcoming_games": upcoming_games
    }

    return schedule


# ============================================================
# SAVE JSON
# ============================================================

def save_schedule(schedule):
    """Write the schedule to schedule.json."""

    output_path = Path(OUTPUT_FILE)

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            schedule,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        f"Saved schedule to: "
        f"{output_path.resolve()}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        schedule = fetch_schedule()

        print()
        print("Schedule:")

        print(
            json.dumps(
                schedule,
                indent=2,
                ensure_ascii=False,
            )
        )

        save_schedule(schedule)

    except requests.RequestException as error:

        print()
        print(
            "ERROR: Could not download "
            "the HNA schedule."
        )

        print(error)

    except Exception as error:

        print()
        print("ERROR:")
        print(error)
