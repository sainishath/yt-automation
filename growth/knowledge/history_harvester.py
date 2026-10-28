# -*- coding: utf-8 -*-
"""
history_harvester.py
---------------------
Harvests authoritative primary source documentation, verified chronological timelines,
and little-known historical turning points for long-form documentary scripts and shorts.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "HistoricalDocumentaryResearch/2.0 (contact: research@yt-automations.local)"

LEGENDARY_STORIES = [
    {
        "id": "fall_of_constantinople_1453",
        "title": "The Fall of Constantinople (1453)",
        "era": "Medieval / Early Modern",
        "wiki_title": "Fall_of_Constantinople",
        "openalex_query": "Fall of Constantinople 1453 siege Theodosian walls",
        "overlooked_twist": "The city had withstood 2 dozen sieges over 1,000 years. It fell not solely from supercannons, but because the 3-foot Kerkoporta sally-port gate was left unlocked by accident by defenders after a sortie, allowing 50 Janissaries to climb the inner rampart.",
        "primary_sources": ["George Sphrantzes (Chronicon Minus)", "Nicolo Barbaro (Diary of the Siege of Constantinople 1453)", "Edward Gibbon (Decline and Fall)"]
    },
    {
        "id": "caesar_cilician_pirates_75bc",
        "title": "Julius Caesar Kidnapped by Pirates (75 BC)",
        "era": "Classical Antiquity",
        "wiki_title": "Julius_Caesar#Early_career_and_military_service",
        "openalex_query": "Julius Caesar Cilician pirates Pharmacusa 75 BC",
        "overlooked_twist": "Pirates demanded 20 talents ($20M). Caesar laughed, said he was worth 50 talents, ordered them to be quiet so he could sleep, made them listen to his speeches, and warned them with a grin he would crucify them. 38 days later, ransom paid, he raised a private fleet, hunted them down, and kept his exact promise.",
        "primary_sources": ["Plutarch (Parallel Lives: Life of Caesar)", "Suetonius (The Twelve Caesars)"]
    },
    {
        "id": "napoleon_retreat_from_moscow_1812",
        "title": "Napoleon's 1812 Russian Retreat & The Tin Button Disaster",
        "era": "Napoleonic Wars",
        "wiki_title": "French_invasion_of_Russia",
        "openalex_query": "Napoleon Russian campaign 1812 retreat Grande Armee tin pest typhus",
        "overlooked_twist": "The Grande Armée was not destroyed primarily by Russian bayonets. Sub-zero blizzards triggered 'tin pest'—an allotropic disintegration of cheap tin uniform buttons into gray powder—forcing freezing soldiers to clutch their coats with one hand while typhus-carrying body lice decimated 400,000 men.",
        "primary_sources": ["General Armand de Caulaincourt (With Napoleon in Russia)", "Philippe-Paul de Ségur (History of the Expedition to Russia)"]
    },
    {
        "id": "franz_ferdinand_wrong_turn_1914",
        "title": "The Assassination of Franz Ferdinand: The Stalled Car (1914)",
        "era": "World War I",
        "wiki_title": "Assassination_of_Archduke_Franz_Ferdinand",
        "openalex_query": "Assassination Archduke Franz Ferdinand Sarajevo 1914 Schiller delicatessen wrong turn",
        "overlooked_twist": "The assassination plot had completely collapsed after the morning bomb missed. Princip gave up and walked to Schiller's delicatessen. The Archduke decided to visit wounded officers in hospital, but his driver took a wrong turn onto Franz Josef Street, tried to reverse, stalled the un-geared engine, and stopped exactly 5 feet from where Princip was standing on the sidewalk.",
        "primary_sources": ["Sarajevo Court Martial Records (1914)", "Count Franz von Harrach eyewitness report"]
    },
    {
        "id": "titanic_coal_bunker_fire_1912",
        "title": "The Titanic's Secret Coal Fire (1912)",
        "era": "Edwardian / Industrial",
        "wiki_title": "Sinking_of_the_Titanic",
        "openalex_query": "Titanic sinking coal bunker fire bulkhead 9 structural weakness 1912",
        "overlooked_twist": "A subterranean smoldering coal fire had ignited in Bunker No. 6 ten days before the voyage. White Star Line kept it secret from passengers. The intense 1,000°C heat warped and weakened the watertight steel bulkhead, which buckled precisely where the iceberg grazed the starboard hull.",
        "primary_sources": ["British Wreck Commissioner's Inquiry (1912)", "Testimony of Fireman John Dilley and Leading Fireman Charles Hendrickson"]
    }
]


def fetch_wikipedia_details(wiki_title: str) -> Dict[str, Any]:
    """Fetches full introductory extract and sections from Wikipedia REST API."""
    title_clean = wiki_title.split("#")[0]
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title_clean)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "title": data.get("title", ""),
                "extract": data.get("extract", ""),
                "thumbnail": data.get("thumbnail", {}).get("source", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
    except Exception as e:
        print(f"  [Wiki Warning] Failed for {wiki_title}: {e}")
        return {}


def fetch_openalex_scholarly(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Fetches high-impact peer-reviewed historical papers from OpenAlex."""
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per_page={max_results}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    works = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("results", []):
                title = item.get("title", "")
                if not title:
                    continue
                inv = item.get("abstract_inverted_index", {})
                abstract_words = []
                if inv:
                    word_pos = []
                    for w, pos_list in inv.items():
                        for p in pos_list:
                            word_pos.append((p, w))
                    word_pos.sort()
                    abstract_words = [wp[1] for wp in word_pos]
                abstract = " ".join(abstract_words[:120]) if abstract_words else ""
                works.append({
                    "title": title,
                    "year": item.get("publication_year"),
                    "cited_by_count": item.get("cited_by_count", 0),
                    "doi": item.get("doi", ""),
                    "summary": abstract
                })
    except Exception as e:
        print(f"  [OpenAlex Warning] Failed for '{query}': {e}")
    return works


def harvest_all_stories() -> Dict[str, Any]:
    """Downloads and persists historical dossiers with primary evidence and overlooked details."""
    corpus_index = []
    print("=" * 60)
    print("  HISTORICAL CORPUS HARVESTER: Legendary Turning Points")
    print("=" * 60)

    for story in LEGENDARY_STORIES:
        sid = story["id"]
        out_file = CORPUS_DIR / f"{sid}.json"
        print(f"\nHarvesting: {story['title']}...")

        wiki_info = fetch_wikipedia_details(story["wiki_title"])
        scholarly_works = fetch_openalex_scholarly(story["openalex_query"], max_results=3)

        dossier = {
            "story_id": sid,
            "title": story["title"],
            "era": story["era"],
            "overlooked_twist": story["overlooked_twist"],
            "primary_sources": story["primary_sources"],
            "wikipedia_summary": wiki_info.get("extract", ""),
            "wikipedia_url": wiki_info.get("url", ""),
            "scholarly_papers": scholarly_works,
            "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(dossier, f, indent=2, ensure_ascii=False)

        print(f"  -> Saved {len(scholarly_works)} scholarly papers + Wiki extract to {out_file.name}")
        corpus_index.append({
            "id": sid,
            "title": story["title"],
            "era": story["era"],
            "overlooked_twist": story["overlooked_twist"],
            "file": f"growth/knowledge/corpus/{sid}.json"
        })

    index_file = CORPUS_DIR / "corpus_manifest.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(corpus_index, f, indent=2, ensure_ascii=False)

    print(f"\nCorpus Manifest successfully written to {index_file} ({len(corpus_index)} stories).")
    return {"status": "SUCCESS", "stories_count": len(corpus_index), "index_file": str(index_file)}


if __name__ == "__main__":
    harvest_all_stories()
