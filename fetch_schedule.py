import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.hna.com/leagues/schedules.cfm"
    "?clientID=2296"
    "&leagueID=5717"
    "&schedType=main"
    "&printPage=0"
    "&monthID=10"
    "&yearID=2026"
    "&selectedTeamID=683136"
    "&selectedOfficialID=0"
    "&gameType="
)

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.hna.com/"
}

response = requests.get(URL, headers=headers)

print("STATUS:", response.status_code)
print("\n===== FULL PAGE TEXT =====\n")

soup = BeautifulSoup(response.text, "html.parser")

print(soup.get_text("\n"))

print("\n===== END PAGE TEXT =====\n")
