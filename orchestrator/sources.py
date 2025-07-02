import requests
from urllib.parse import quote


def fetch_wikipedia_extract(title: str) -> str:
    """Return summary extract for a Wikipedia page title."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    resp = requests.get(url, headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return data.get("extract", "")
