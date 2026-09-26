import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.hna.com/leagues/schedules.cfm"
    "?clientID=2296"
    "&leagueID=5717"
    "&schedType=main"
    "&printPage=0"
)

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
    )
}


def main():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True
    )

    print("STATUS:", response.status_code)
    print("URL:", response.url)
    print("LENGTH:", len(response.text))

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    print("\n===== ROW DEBUG =====\n")

    for i, row in enumerate(rows):
        cols = [
            td.get_text(" ", strip=True)
            for td in row.find_all(["td", "th"])
        ]

        if cols:
            print(f"ROW {i}: {cols}")

    print("\n===== END DEBUG =====\n")

    print("\n===== PAGE TEXT =====\n")
    print(soup.get_text("\n"))
    print("\n===== END PAGE TEXT =====\n")


if __name__ == "__main__":
    main()
