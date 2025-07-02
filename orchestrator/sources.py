import requests
from urllib.parse import quote


def fetch_wikipedia_extract(title: str) -> str:
    """Return summary extract for a Wikipedia page title."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    resp = requests.get(url, headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return data.get("extract", "")

  
def fetch_wikivoyage_extract(title: str) -> str:
    """Return introductory extract for a Wikivoyage page title."""
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": "",
        "explaintext": "",
        "titles": title,
        "format": "json",
    }
    resp = requests.get(
        "https://en.wikivoyage.org/w/api.php",
        params=params,
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    if pages:
        return next(iter(pages.values())).get("extract", "")
    return ""