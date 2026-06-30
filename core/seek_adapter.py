"""SEEK adapter — fetches jobs from Apify and normalises them to our common shape."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.environ["APIFY_TOKEN"]
ACTOR_URL = (
    "https://api.apify.com/v2/acts/websift~seek-job-scraper"
    "/run-sync-get-dataset-items"
)


def fetch_raw(title: str, location: str, max_results: int = 50) -> list[dict]:
    """Call Apify and return raw job dicts exactly as the actor returns them."""
    response = httpx.post(
        ACTOR_URL,
        params={"token": APIFY_TOKEN},
        json={"searchTerm": title, "location": location, "maxResults": max_results},
        timeout=120,  # actor can take a while to run
    )
    response.raise_for_status()
    return response.json()


def normalise(raw: dict) -> dict:
    """Map a raw Apify job dict to our common job shape."""
    return {
        "source":      "seek",
        "source_id":   str(raw["id"]),
        "title":       raw.get("title", ""),
        "company":     (raw.get("advertiser") or {}).get("name", ""),
        "location":    (raw.get("joblocationInfo") or {}).get("displayLocation", ""),
        "description": (raw.get("content") or {}).get("unEditedContent", ""),
        "url":         raw.get("jobLink", ""),
        "posted_at":   raw.get("listedAt", ""),
        "expires_at":  raw.get("expiresAtUtc", ""),
    }


def fetch_and_normalise(title: str, location: str, max_results: int = 50) -> list[dict]:
    """Fetch from Apify and return normalised job dicts ready for the DB."""
    raw_jobs = fetch_raw(title, location, max_results)
    return [normalise(r) for r in raw_jobs]
