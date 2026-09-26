
import re
import json
import requests

from bs4 import BeautifulSoup
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.hna.com/leagues/schedules.cfm"

CLIENT_ID = "2296"
LEAGUE_ID = "5717"
TEAM_ID = "683136"          # Kraken Beers

OUTPUT_FILE = "schedule.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0 Safari/537.36"
    ),
    "Referer": "https://www.hna.com/",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "*/*;q=0.8"
    ),
}


session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# FETCH HNA PAGE
# ============================================================

def get_page(params):
    response = session.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# FIND AVAILABLE MONTHS
#
# HNA uses values such as:
#
#   9,2026
#   10,2026
#
# These are month selectors, NOT game dates.
# ============================================================

def get_month_options(html):
    soup = BeautifulSoup(html, "html.parser")

    months = []

    month_select = soup.find(
        "select",
        {"name": "monthID"}
    )

    if not month_select:
        return months

    for option in month_select.find_all("option"):
        value = option.get("value", "").strip()

        if re.fullmatch(r"\d{1,2},\d{4}", value):
            if value not in months:
                months.append(value)

    return months


# ============================================================
# PARSE DATE HEADING
#
# HNA uses headings such as:
#
#   Tue Sep 22, 2026
#   Tue Sep 29, 2026
# ============================================================

def parse_date_heading(text):

    if not text:
        return None

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    match = re.search(
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2}),\s*(\d{4})",
        text
    )

    if not match:
        return None

    try:
        dt = datetime.strptime(
            match.group(0),
            "%a %b %d, %Y"
        )

        return dt.strftime("%Y-%m-%d")

    except ValueError:
        return None


# ============================================================
# FIND DATE FOR A GAME TABLE
# ============================================================

def find_date_for_table(table):

    heading = table.find_previous("h5")

    if not heading:
        return None

    return parse_date_heading(
        heading.get_text(" ", strip=True)
    )


# ============================================================
# GET UNIQUE TEAMS FROM A GAME ROW
#
# IMPORTANT:
#
# HNA provides TWO links for each team:
#
# Desktop:
#   Hurricanes
#
# Mobile:
#   CANE
#
# They have the SAME teamID.
#
# We therefore group links by teamID and keep only
# one team record.
# ============================================================

def get_teams_from_row(row):

    teams = []

    seen_team_ids = set()

    for anchor in row.find_all("a", href=True):

        href = anchor.get("href", "")

        match = re.search(
            r"teamID=(\d+)",
            href,
            re.IGNORECASE
        )

        if not match:
            continue

        team_id = match.group(1)

        if team_id in seen_team_ids:
            continue

        seen_team_ids.add(team_id)

        # Prefer the desktop team name.
        desktop_span = anchor.find_parent(
            "span",
            class_=lambda c: c and "d-sm-inline" in c
        )

        if desktop_span:
            name_anchor = desktop_span.find(
                "a",
                href=True
            )

            if name_anchor:
                name = name_anchor.get_text(
                    " ",
                    strip=True
                )
            else:
                name = anchor.get_text(
                    " ",
                    strip=True
                )
        else:
            name = anchor.get_text(
                " ",
                strip=True
            )

        name = re.sub(
            r"\s+",
            " ",
            name
        ).strip()

        if not name:
            continue

        teams.append({
            "team_id": team_id,
            "name": name,
        })

    return teams


# ============================================================
# PARSE ONE MONTH
# ============================================================

def parse_month(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    games = []

    for table in soup.find_all("table"):

        game_date = find_date_for_table(table)

        if not game_date:
            continue

        for row in table.find_all("tr"):

            teams = get_teams_from_row(row)

            # A game needs exactly two unique teams.
            if len(teams) != 2:
                continue

            # Make sure Kraken Beers is one of them.
            if not any(
                team["team_id"] == TEAM_ID
                for team in teams
            ):
                continue

            cells = row.find_all("td")

            if len(cells) < 7:
                continue

            cell_text = [
                re.sub(
                    r"\s+",
                    " ",
                    cell.get_text(
                        " ",
                        strip=True
                    )
                ).strip()
                for cell in cells
            ]

            status_or_time = cell_text[0]
            location = cell_text[6]

            away_team = teams[0]["name"]
            home_team = teams[1]["name"]

            # ------------------------------------------------
            # Determine whether game is final.
            # ------------------------------------------------

            is_final = bool(
                re.search(
                    r"\bFinal\b",
                    status_or_time,
                    re.IGNORECASE
                )
            )

            # ------------------------------------------------
            # Extract scheduled time.
            # ------------------------------------------------

            time_match = re.search(
                r"\d{1,2}:\d{2}\s*(AM|PM)",
                status_or_time,
                re.IGNORECASE
            )

            game_time = (
                time_match.group(0)
                if time_match
                else ""
            )

            game = {
                "date": game_date,
                "time": game_time,
                "away_team": away_team,
                "home_team": home_team,
                "location": location,
                "_completed": is_final,
            }

            games.append(game)

    return games


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def deduplicate_games(games):

    seen = set()
    unique = []

    for game in games:

        key = (
            game["date"],
            game["time"],
            game["away_team"],
            game["home_team"],
            game["location"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(game)

    return unique


# ============================================================
# SORT GAMES
# ============================================================

def game_sort_key(game):

    try:

        if game["time"]:

            return datetime.strptime(
                f'{game["date"]} {game["time"]}',
                "%Y-%m-%d %I:%M %p"
            )

        return datetime.strptime(
            game["date"],
            "%Y-%m-%d"
        )

    except ValueError:

        return datetime.max


# ============================================================
# BUILD SCHEDULE
# ============================================================

def fetch_schedule():

    # --------------------------------------------------------
    # Initial request.
    #
    # This is your original URL:
    #
    # https://www.hna.com/leagues/schedules.cfm?
    # clientID=2296&
    # leagueID=5717&
    # schedType=main&
    # printPage=0
    #
    # We use it to discover available months.
    # --------------------------------------------------------

    base_params = {
        "clientID": CLIENT_ID,
        "leagueID": LEAGUE_ID,
        "schedType": "main",
        "printPage": "0",
    }

    initial_html = get_page(
        base_params
    )

    month_options = get_month_options(
        initial_html
    )

    if not month_options:

        raise RuntimeError(
            "Could not find HNA month options."
        )

    print()
    print("HNA months found:")

    for month in month_options:
        print(f"  {month}")

    print()

    # --------------------------------------------------------
    # Fetch each available month for Kraken Beers.
    # --------------------------------------------------------

    all_games = []

    for month_id in month_options:

        print(
            f"Fetching {month_id}..."
        )

        params = {
            "clientID": CLIENT_ID,
            "leagueID": LEAGUE_ID,
            "schedType": "main",
            "printPage": "0",
            "selectedTeamID": TEAM_ID,
            "monthID": month_id,
        }

        html = get_page(params)

        month_games = parse_month(
            html
        )

        print(
            f"  Found {len(month_games)} Kraken games"
        )

        all_games.extend(
            month_games
        )

    # --------------------------------------------------------
    # Deduplicate.
    # --------------------------------------------------------

    all_games = deduplicate_games(
        all_games
    )

    # --------------------------------------------------------
    # Sort chronologically.
    # --------------------------------------------------------

    all_games.sort(
        key=game_sort_key
    )

    # --------------------------------------------------------
    # Split completed/upcoming.
    # --------------------------------------------------------

    now = datetime.now()

    completed_games = []
    upcoming_games = []

    for game in all_games:

        try:

            game_date = datetime.strptime(
                game["date"],
                "%Y-%m-%d"
            ).date()

        except ValueError:
            continue

        # HNA explicitly says Final.
        if game["_completed"]:

            completed_games.append(
                game
            )

            continue

        # Future date.
        if game_date > now.date():

            upcoming_games.append(
                game
            )

            continue

        # Past date that wasn't marked Final.
        if game_date < now.date():

            continue

        # Today.
        if game["time"]:

            try:

                game_datetime = datetime.strptime(
                    f'{game["date"]} {game["time"]}',
                    "%Y-%m-%d %I:%M %p"
                )

                if game_datetime >= now:

                    upcoming_games.append(
                        game
                    )

            except ValueError:

                upcoming_games.append(
                    game
                )

    # --------------------------------------------------------
    # Most recent completed game.
    # --------------------------------------------------------

    last_game = None

    if completed_games:

        completed_games.sort(
            key=game_sort_key
        )

        last_game = completed_games[-1].copy()

    # --------------------------------------------------------
    # Remove internal fields.
    # --------------------------------------------------------

    for game in upcoming_games:
        game.pop(
            "_completed",
            None
        )

    if last_game:
        last_game.pop(
            "_completed",
            None
        )

    # --------------------------------------------------------
    # Final schedule object.
    # --------------------------------------------------------

    return {
        "last_game": last_game,
        "upcoming_games": upcoming_games,
    }


# ============================================================
# WRITE schedule.json
# ============================================================

def save_schedule(schedule):

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            schedule,
            f,
            indent=2,
            ensure_ascii=False
        )

        f.write("\n")

    print()
    print(
        f"Saved schedule to {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        schedule = fetch_schedule()

        # Print result for debugging.
        print()
        print(
            "============================================================"
        )
        print(
            "FINAL SCHEDULE"
        )
        print(
            "============================================================"
        )

        print(
            json.dumps(
                schedule,
                indent=2,
                ensure_ascii=False
            )
        )

        # IMPORTANT:
        # Actually update schedule.json.
        save_schedule(
            schedule
        )

    except Exception as e:

        print()
        print(
            "ERROR:"
        )

        print(
            str(e)
        )

        raise
