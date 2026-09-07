#!/usr/bin/env python3
"""
Aether Exchange v3: a fictional news-driven economy and terminal trading game.
Run: python3 aether_feedwatch.py --offline --play
Space/Enter advances; b prices; r report; p portfolio; t trade; h histories; q quit.
Uses only Python's standard library (Python 3.10+).
Headlines are transient; only SHA-256 deduplication hashes are persisted.
Offline replay requires identical seed, start date, starting state and actions.
See README.md for model assumptions and limitations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field, asdict, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

STATE_PATH = Path("aether_state.json")
USER_AGENT = "AetherExchange-Sim/2.0 (fictional-market-simulator; polite; 1 req/source/poll)"

# ---------------------------------------------------------------------------
# SOURCES
# ---------------------------------------------------------------------------
# RSS endpoints are used rather than HTML scraping: lighter, stable, and the
# publisher-sanctioned path. Feed URLs do drift — verify before a long run and
# fix any source that reports 0 titles for several consecutive polls.

SOURCES = [
    # (label, feed_url, language)
    ("times_of_india", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "en"),
    ("hindustan_times", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "en"),
    ("the_hindu", "https://www.thehindu.com/news/national/feeder/default.rss", "en"),
    ("indian_express", "https://indianexpress.com/section/india/feed/", "en"),
    ("ndtv", "https://feeds.feedburner.com/ndtvnews-top-stories", "en"),
    ("india_today", "https://www.indiatoday.in/rss/1206578", "en"),
    ("news18", "https://www.news18.com/rss/india.xml", "en"),
    ("bbc_hindi", "https://feeds.bbci.co.uk/hindi/rss.xml", "hi"),
]

# ---------------------------------------------------------------------------
# WORLD: regions, races, companies
# ---------------------------------------------------------------------------

REGIONS = ["ironpeak", "verdant", "azure", "ember", "crownlands"]

RACES = {
    "dwarves":   {"home": "ironpeak",    "horizon": 40, "sectors": ["mining", "metal", "machinery"]},
    "humans":    {"home": "crownlands",  "horizon": 6,  "sectors": ["finance", "trade", "construction"]},
    "elves":     {"home": "verdant",     "horizon": 120, "sectors": ["herbal", "forestry", "seed"]},
    "gnomes":    {"home": "ember",       "horizon": 25, "sectors": ["crystal", "energy", "instruments"]},
    "orcs":      {"home": "ironpeak",    "horizon": 8,  "sectors": ["security", "haulage", "shipbreaking"]},
    "halflings": {"home": "verdant",     "horizon": 12, "sectors": ["farming", "food", "retail"]},
    "merfolk":   {"home": "azure",       "horizon": 30, "sectors": ["salvage", "fishing", "pilotage"]},
    "vaurex":    {"home": "ember",       "horizon": 60, "sectors": ["volcanic", "hazard", "crystal"]},
}

# ticker: (name, region, sectors, workforce{race: share}, start_price_GC, shares_out_millions)
COMPANIES = {
    "IRON": ("Ironpeak Mining",        "ironpeak",   ["mining", "metal"],            {"dwarves": .62, "orcs": .24, "humans": .14},   184.0, 42.0),
    "FRGE": ("Crownforge Industries",  "ironpeak",   ["machinery", "metal", "arms"], {"dwarves": .48, "humans": .34, "gnomes": .18}, 231.5, 31.0),
    "DLVE": ("Deepdelve Consolidated", "ironpeak",   ["mining", "gems"],             {"dwarves": .71, "orcs": .21, "gnomes": .08},   96.4,  28.0),
    "HMMR": ("Hammerfall Machineworks","ironpeak",   ["machinery"],                  {"dwarves": .55, "gnomes": .27, "humans": .18}, 143.0, 19.0),
    "VRDT": ("Verdant Harvest",        "verdant",    ["farming", "food"],            {"halflings": .58, "humans": .27, "elves": .15}, 77.2, 64.0),
    "LEAF": ("Moonleaf Remedies",      "verdant",    ["herbal", "food"],             {"elves": .66, "halflings": .21, "humans": .13}, 312.8, 12.0),
    "WOOD": ("Thornwood Timber",       "verdant",    ["forestry"],                   {"elves": .44, "halflings": .33, "orcs": .23},  58.9,  36.0),
    "VINE": ("Greenhollow Vintners",   "verdant",    ["food", "luxury"],             {"halflings": .61, "elves": .29, "humans": .10}, 121.0, 15.0),
    "SEED": ("Sylvan Seedbank",        "verdant",    ["seed", "farming"],            {"elves": .74, "halflings": .19, "humans": .07}, 88.5,  11.0),
    "SAIL": ("Azure Sails",            "azure",      ["shipping", "trade"],          {"humans": .41, "merfolk": .32, "orcs": .27},   167.3, 47.0),
    "TIDE": ("Tidecall Fisheries",     "azure",      ["fishing", "food"],            {"merfolk": .57, "halflings": .26, "humans": .17}, 44.6, 33.0),
    "SLVG": ("Saltmoor Salvage",       "azure",      ["salvage"],                    {"merfolk": .69, "orcs": .22, "humans": .09},   62.1,   9.0),
    "HRBR": ("Harborlight Trading Co", "azure",      ["trade", "commodities"],       {"humans": .55, "halflings": .24, "merfolk": .21}, 198.0, 26.0),
    "CRLF": ("Coralforge Shipyards",   "azure",      ["shipbuilding", "metal"],      {"orcs": .38, "merfolk": .31, "dwarves": .31},  109.7, 21.0),
    "EMBR": ("Emberstone Energy",      "ember",      ["crystal", "energy"],          {"gnomes": .52, "vaurex": .29, "orcs": .19},    276.4, 55.0),
    "PYRE": ("Pyrelight Utilities",    "ember",      ["energy", "utility"],          {"gnomes": .58, "humans": .26, "vaurex": .16},  142.2, 68.0),
    "ASHV": ("Ashvault Reclamation",   "ember",      ["hazard", "crystal"],          {"vaurex": .47, "gnomes": .38, "orcs": .15},    71.8,  14.0),
    "BSTN": ("Bastion Construction",   "crownlands", ["construction", "metal"],      {"humans": .49, "orcs": .28, "dwarves": .23},   93.6,  52.0),
    "BANK": ("Silverquill Bank",       "crownlands", ["finance"],                    {"humans": .78, "gnomes": .13, "elves": .09},   204.0, 88.0),
    "AEGS": ("Aegis Underwriters",     "crownlands", ["finance", "insurance"],       {"humans": .71, "elves": .18, "gnomes": .11},   158.9, 40.0),
    "GATE": ("Waygate Networks",       "crownlands", ["transport", "crystal"],       {"gnomes": .46, "humans": .35, "vaurex": .19},  341.0, 24.0),
    "MRDN": ("Meridian Ledger House",  "crownlands", ["finance", "infrastructure"],  {"humans": .69, "gnomes": .20, "dwarves": .11}, 267.5, 18.0),
    "LUMN": ("Lumengrave Press",       "crownlands", ["information"],                {"humans": .64, "halflings": .22, "gnomes": .14}, 39.4, 29.0),
    "GRFN": ("Griffin Express",        "crownlands", ["transport", "logistics"],     {"humans": .43, "elves": .31, "halflings": .26}, 187.6, 22.0),
    "WYRM": ("Wyrmwatch Security",     "ironpeak",   ["security", "hazard"],         {"orcs": .54, "dwarves": .27, "vaurex": .19},   125.3, 30.0),
}

RESOURCES = ["food", "metal", "timber", "stone", "energy", "credit"]

# ---------------------------------------------------------------------------
# ARCHETYPES — the only thing that crosses the content firewall
# ---------------------------------------------------------------------------
# Each archetype maps real-coverage *shape* onto an Eldrath event family.
# Keywords are matched case-insensitively against titles that are then dropped.

@dataclass(frozen=True)
class Archetype:
    key: str
    category: str
    keywords: tuple
    regions: tuple            # candidate Eldrath regions
    resources: tuple          # (resource, direction) direction +1 = price up
    sectors_hurt: tuple
    sectors_helped: tuple
    base_severity: float      # 0..1 before corroboration adjustment
    base_duration: int        # days
    race_linked: bool = False
    valence: int = -1         # -1 adverse, 0 mixed, +1 favourable


ARCHETYPES = [
    Archetype("weather_shock", "natural", (
        "rain", "flood", "cyclone", "monsoon", "heatwave", "storm", "downpour",
        "waterlogg", "imd", "बारिश", "बाढ़", "तूफान", "मौसम"),
        ("verdant", "azure"), (("food", +1), ("timber", +1)),
        ("farming", "food", "shipping"), ("salvage", "insurance"), 0.45, 9),

    Archetype("structural_disaster", "natural", (
        "earthquake", "landslide", "collapse", "building collapse", "tremor",
        "भूकंप", "भूस्खलन", "हादसा"),
        ("ironpeak", "crownlands"), (("stone", +1), ("metal", +1)),
        ("construction", "mining"), ("security", "hazard"), 0.58, 14),

    Archetype("industrial_accident", "magical", (
        "fire", "blast", "explosion", "factory", "boiler", "leak", "gas",
        "आग", "धमाका", "विस्फोट"),
        ("ember", "ironpeak"), (("energy", +1),),
        ("crystal", "energy", "machinery"), ("hazard", "insurance"), 0.52, 11),

    Archetype("labor_dispute", "labor", (
        "strike", "protest", "union", "wage", "workers", "farmers protest",
        "bandh", "layoff", "हड़ताल", "प्रदर्शन", "मजदूर"),
        ("ironpeak", "verdant", "azure"), (("metal", +1),),
        ("mining", "machinery", "shipping", "farming"), ("information",), 0.47, 12,
        race_linked=True),

    Archetype("civic_franchise", "civic", (
        "citizenship", "quota", "reservation", "migrant", "tribunal", "rights",
        "assembly passes", "नागरिकता", "आरक्षण", "प्रवासी"),
        ("crownlands", "azure"), (("credit", +1),),
        ("finance", "trade"), ("information", "security"), 0.40, 21,
        race_linked=True),

    Archetype("trade_policy", "policy", (
        "tariff", "export ban", "import", "customs", "duty", "trade deal",
        "wto", "shipment", "आयात", "निर्यात", "शुल्क"),
        ("azure", "crownlands"), (("food", +1), ("metal", +1)),
        ("trade", "shipping", "commodities"), ("mining", "farming"), 0.43, 18),

    Archetype("monetary_shift", "policy", (
        "rbi", "repo", "inflation", "rate cut", "rate hike", "rupee", "gdp",
        "budget", "fiscal", "sensex", "nifty", "महंगाई", "बजट", "ब्याज"),
        ("crownlands",), (("credit", +1),),
        ("finance", "construction", "luxury"), ("insurance",), 0.38, 25),

    Archetype("frontier_conflict", "conflict", (
        "border", "army", "defence", "missile", "clash", "militant", "troops",
        "सेना", "सीमा", "हमला"),
        ("ironpeak", "azure"), (("metal", +1), ("energy", +1)),
        ("trade", "shipping", "luxury"), ("arms", "security", "machinery"), 0.61, 20),

    Archetype("plague", "disease", (
        "outbreak", "virus", "dengue", "infection", "hospital", "vaccine",
        "epidemic", "flu", "संक्रमण", "बीमारी", "अस्पताल"),
        ("verdant", "crownlands"), (("food", +1),),
        ("food", "luxury", "construction"), ("herbal", "insurance"), 0.50, 24),

    Archetype("energy_stress", "resource", (
        "power cut", "electricity", "coal", "oil price", "fuel", "grid",
        "blackout", "petrol", "diesel", "बिजली", "ईंधन"),
        ("ember", "crownlands"), (("energy", +1),),
        ("energy", "machinery", "transport"), ("crystal",), 0.49, 16),

    Archetype("harvest_signal", "resource", (
        "crop", "harvest", "sowing", "msp", "wheat", "rice", "onion", "yield",
        "फसल", "किसान", "गेहूं"),
        ("verdant",), (("food", -1),),
        ("commodities",), ("farming", "food", "seed"), 0.33, 15),

    Archetype("transport_failure", "infrastructure", (
        "train", "derail", "highway", "flight", "airport", "crash", "traffic",
        "bridge", "रेल", "उड़ान", "दुर्घटना"),
        ("crownlands", "azure"), (("metal", +1),),
        ("transport", "logistics", "trade"), ("construction", "insurance"), 0.44, 10),

    Archetype("legal_ruling", "policy", (
        "court", "verdict", "supreme court", "probe", "cbi", "ed ", "fir",
        "bench", "अदालत", "फैसला", "जांच"),
        ("crownlands",), (("credit", +1),),
        ("finance", "information"), ("insurance",), 0.36, 22),

    Archetype("discovery", "innovation", (
        "isro", "launch", "research", "scientists", "ai ", "startup", "patent",
        "breakthrough", "satellite", "खोज", "अनुसंधान"),
        ("ember", "crownlands"), (("energy", -1),),
        (), ("crystal", "instruments", "machinery", "seed"), 0.30, 30),

    Archetype("beast_activity", "monster", (
        "tiger", "leopard", "elephant", "wildlife", "snake", "attack in village",
        "forest department", "बाघ", "हाथी", "तेंदुआ"),
        ("ironpeak", "verdant"), (("metal", +1),),
        ("mining", "forestry", "haulage"), ("security", "hazard", "insurance"), 0.42, 13),

    Archetype("political_cycle", "policy", (
        "election", "poll", "parliament", "cabinet", "bill", "minister",
        "assembly", "vote", "चुनाव", "संसद", "मंत्री"),
        ("crownlands", "verdant"), (("credit", +1),),
        ("construction", "finance"), ("information",), 0.35, 28, valence=0),

    # ---------------- favourable archetypes --------------------------------
    Archetype("corporate_win", "corporate", (
        "order", "contract", "deal", "profit", "revenue", "earnings", "record high",
        "expansion", "investment", "funding", "ipo", "acquire", "merger", "tie-up",
        "मुनाफा", "निवेश", "सौदा"),
        ("crownlands", "ironpeak", "azure"), (("credit", -1),),
        (), ("machinery", "arms", "metal", "trade", "finance", "construction"),
        0.44, 20, valence=+1),

    Archetype("infra_completion", "infrastructure", (
        "inaugurat", "commission", "opens", "completed", "new line", "expressway",
        "corridor", "terminal", "capacity added", "उद्घाटन", "शुरू", "परियोजना"),
        ("crownlands", "azure", "ember"), (("stone", -1), ("energy", -1)),
        (), ("construction", "transport", "logistics", "utility", "shipping"),
        0.38, 26, valence=+1),

    Archetype("treaty_accord", "policy", (
        "agreement", "pact", "mou", "summit", "signed", "accord", "cooperation",
        "talks conclude", "समझौता", "करार", "सहमति"),
        ("azure", "crownlands", "verdant"), (("food", -1), ("metal", -1)),
        ("security",), ("trade", "shipping", "commodities", "finance"),
        0.40, 24, valence=+1),

    Archetype("relief_recovery", "resource", (
        "relief", "rescue", "restored", "reopens", "normalcy", "recovery",
        "aid", "resumes", "बहाल", "राहत", "सामान्य"),
        ("verdant", "ironpeak", "azure"), (("food", -1), ("metal", -1)),
        ("insurance",), ("farming", "food", "mining", "shipping", "herbal"),
        0.35, 18, valence=+1),
]

ARCH_BY_KEY = {a.key: a for a in ARCHETYPES}

# Archetypes that read as good or neutral news; wording and escalation differ.
BENIGN_ARCHETYPES = {a.key for a in ARCHETYPES if a.valence >= 0}

INTENSITY_WORDS = (
    "massive", "record", "worst", "toll", "crisis", "emergency", "urgent",
    "shock", "collapse", "unprecedented", "alert", "बड़ा", "गंभीर", "संकट",
)

# ---------------------------------------------------------------------------
# NARRATIVE VOCABULARY (all invented)
# ---------------------------------------------------------------------------

PLACES = {
    "ironpeak":   ["Kald-Vorn", "the Grey Stair", "Hollowfast", "Anvilgate", "Rimehold"],
    "verdant":    ["Willowmere", "the Amber Furrows", "Thistledown", "Greenhollow", "Larkfen"],
    "azure":      ["Saltmoor", "Pellon Reach", "the Coral Narrows", "Windward Quay", "Tidecall"],
    "ember":      ["Cinderfall", "the Slag Terraces", "Vaurhold", "Emberwatch", "Glasswake"],
    "crownlands": ["Highcrown", "Ledger Row", "the Meridian Quarter", "Ashford Bridge", "Kingsmarket"],
}

HEADLINE_TEMPLATES = {
    "weather_shock":       ["Floodwaters Close {place} Roads for a Third Day",
                            "Season Turns Hard on {place}; Granary Wardens Warn of Short Stock"],
    "structural_disaster": ["Ground Gives Way Beneath {place}",
                            "Survey Halts Work at {place} After Shelf Fracture"],
    "industrial_accident": ["Containment Breach Reported at {place} Refinery",
                            "Crystal Flare Injures Crew at {place}"],
    "labor_dispute":       ["{race_title} Guilds Down Tools Across {place}",
                            "Wage Talks Break Off in {place}"],
    "civic_franchise":     ["Crown Bench to Rule on {race_title} Trading Rights",
                            "{place} Council Reopens the Charter Question"],
    "trade_policy":        ["Levy Imposed on Goods Moving Through {place}",
                            "{place} Harbourmasters Tighten Manifest Rules"],
    "monetary_shift":      ["Crown Treasury Moves the Lending Rate",
                            "Credit Tightens Across {place} Counting Houses"],
    "frontier_conflict":   ["Raiders Strike the Approaches to {place}",
                            "Garrison Reinforced at {place}"],
    "plague":              ["Fever Spreads in {place}; Wards Overfilled",
                            "Physicians Petition for Reserve Stock at {place}"],
    "energy_stress":       ["Crystal Supply Rationed in {place}",
                            "Grid Faults Darken {place} for Six Hours"],
    "harvest_signal":      ["Yields Come In Strong Around {place}",
                            "{place} Granaries Report a Full Season"],
    "transport_failure":   ["Span Closed at {place} After Structural Alarm",
                            "Freight Backs Up at {place}"],
    "legal_ruling":        ["Bench Rules Against Claimants in {place} Suit",
                            "Inquiry Opened Into {place} Accounts"],
    "discovery":           ["New Lattice Cut Raises Crystal Yield at {place}",
                            "{place} Workshops Publish a Refinement Method"],
    "beast_activity":      ["Wyrm Sighted Above the {place} Passes",
                            "Beast Attacks Close the {place} Road"],
    "political_cycle":     ["Assembly Called at {place}",
                            "{place} Delegates Split Over the Supply Bill"],
    "corporate_win":       ["Large Order Booked Out of {place}",
                            "{place} House Reports a Stronger Season Than Guided"],
    "infra_completion":    ["New Works Opened at {place}",
                            "{place} Capacity Comes Online Ahead of Schedule"],
    "treaty_accord":       ["Accord Signed at {place}; Duties to Fall",
                            "{place} Delegations Conclude a Carriage Pact"],
    "relief_recovery":     ["Roads Reopen Around {place}",
                            "{place} Wardens Declare Conditions Normal"],
}

BENIGN_RUMOUR_TEMPLATES = [
    "Factors in {place} say the terms are softer than the notice implies.",
    "A clerk claims the counterparty has not yet posted collateral.",
    "Brokers report unusual buying ahead of the notice; the house is unnamed.",
    "Word around {place} is that a second party walked away from the same terms.",
]

RUMOUR_TEMPLATES = [
    "Dock clerks say the figure is worse than the notice admits.",
    "A guild factor claims the closure was ordered a week before it was announced.",
    "Unattributed word in {place} puts the loss at twice the stated tally.",
    "Brokers report a large seller ahead of the announcement; the house is unnamed.",
    "A retired warden insists the survey was signed without inspection.",
]

UNDISCLOSED_TEMPLATES = [
    "True damage exceeds the public figure by {pct}%.",
    "Restoration will take {extra} days longer than announced.",
    "A second site is affected and has not been declared.",
    "Insurance cover lapsed on {ticker}'s exposure {extra} days before the event.",
    "The responsible party is known internally and is not {ticker}.",
]

# ---------------------------------------------------------------------------
# FETCH + CLASSIFY  (firewall lives here)
# ---------------------------------------------------------------------------

def fetch_titles(feed_url: str, timeout: int = 12) -> list[str]:
    """Return item titles from an RSS/Atom feed. Titles are transient."""
    req = urllib.request.Request(feed_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    titles = []
    for tag in ("./channel/item/title", ".//{http://www.w3.org/2005/Atom}entry/"
                "{http://www.w3.org/2005/Atom}title", ".//item/title"):
        for node in root.findall(tag):
            if node.text:
                titles.append(node.text.strip())
        if titles:
            break
    return titles


def classify(title: str) -> str | None:
    """Map one transient title to an archetype key. Title is not retained."""
    low = title.lower()
    best, best_hits = None, 0
    for arch in ARCHETYPES:
        hits = sum(1 for kw in arch.keywords if kw in low)
        if hits > best_hits:
            best, best_hits = arch.key, hits
    return best


def poll(sources=SOURCES, quiet=False) -> dict:
    """Poll all sources; return {archetype: {'outlets': n, 'intensity': n}}.

    This is the ONLY data structure that leaves the fetch layer.
    """
    table: dict[str, dict] = {}
    for label, url, _lang in sources:
        try:
            titles = fetch_titles(url)
        except (urllib.error.URLError, ET.ParseError, OSError) as exc:
            if not quiet:
                print(f"  [warn] {label}: {type(exc).__name__} — skipped", file=sys.stderr)
            continue

        seen_here, intensity_here = set(), Counter()
        for t in titles:
            key = classify(t)
            if not key:
                continue
            seen_here.add(key)
            if any(w in t.lower() for w in INTENSITY_WORDS):
                intensity_here[key] += 1
        for key in seen_here:
            slot = table.setdefault(key, {"outlets": 0, "intensity": 0})
            slot["outlets"] += 1
            slot["intensity"] += intensity_here[key]
        if not quiet:
            print(f"  {label}: {len(titles)} items -> {len(seen_here)} archetypes")
        time.sleep(1.0)  # politeness spacing between hosts
    # titles are out of scope here and unreferenced; nothing persisted
    return table


def synthetic_table(rng: random.Random) -> dict:
    """Offline stand-in for a poll, for reproducible runs and testing.

    Tuned so most days are ordinary: roughly one day in six is genuinely
    quiet, and heavy corroboration across many outlets is rare.
    """
    if rng.random() < 0.16:
        return {}
    table = {}
    for arch in ARCHETYPES:
        if rng.random() < 0.20:
            table[arch.key] = {
                "outlets": min(len(SOURCES), int(rng.paretovariate(1.6))),
                "intensity": 0 if rng.random() < 0.7 else rng.randint(1, 3),
            }
    return table


# ---------------------------------------------------------------------------
# EVENT MODEL
# ---------------------------------------------------------------------------

@dataclass
class Event:
    id: str
    sim_day: int
    date: str
    archetype: str
    category: str
    region: str
    place: str
    severity: float           # 0..1
    duration: int             # days
    uncertainty: float        # 0..1, higher = less corroborated
    anticipation: float       # 0..1, how expected it was
    race: str | None
    headline: str
    report: str
    implications: str
    unknowns: str
    tickers: list
    resource_effects: list    # [{resource, delta_pct, lag}]
    company_effects: list     # [{ticker, earnings_delta_pct, lag}]
    rumours: list
    undisclosed: list         # never printed to the news feed
    parent_id: str | None = None
    escalations: int = 0
    resolved_on: int | None = None


def stable_rng(*parts) -> random.Random:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def exposure(ticker: str, arch: Archetype, region: str, race: str | None) -> float:
    """Signed exposure of a company to an event. Positive = helped."""
    name, creg, sectors, workforce, _p, _s = COMPANIES[ticker]
    score = 0.0
    for s in sectors:
        if s in arch.sectors_hurt:
            score -= 1.0
        if s in arch.sectors_helped:
            score += 1.0
    if creg == region:
        score *= 1.6
    elif score:
        score *= 0.55                      # spillover, not direct hit
    if race and arch.race_linked:
        share = workforce.get(race, 0.0)
        score -= share * 1.4               # labour/civic shocks bite by headcount
    return round(score, 3)


def forge_events(table: dict, state: dict, sim_date: date, sim_day: int,
                 seed: int) -> list[Event]:
    """Turn an archetype table into Eldrath events, respecting world state."""
    events: list[Event] = []
    active = state["active"]

    for key, sig in sorted(table.items()):
        arch = ARCH_BY_KEY[key]
        rng = stable_rng(seed, sim_day, key)

        corroboration = sig["outlets"] / len(SOURCES)          # 0..1
        intensity = min(sig["intensity"] / 4.0, 1.0)
        severity = min(0.98, arch.base_severity * (0.55 + 0.75 * corroboration)
                       + 0.22 * intensity)
        uncertainty = round(max(0.05, 1.0 - corroboration), 3)

        region = rng.choice(arch.regions)
        scope = f"{key}:{region}"

        # --- contradiction + double-application guard -----------------------
        # A live event of the same family in the same region escalates rather
        # than spawning a second, incompatible event.
        if scope in active:
            parent = next(e for e in state["events"] if e["id"] == active[scope])
            if severity <= parent["severity"] + 0.06:
                continue                                       # nothing new
            old_severity = parent["severity"]
            parent["severity"] = round(min(0.98, severity), 3)
            ratio = parent["severity"] / max(old_severity, .01)
            for fx in parent["company_effects"]:
                fx["earnings_delta_pct"] *= ratio
            for fx in parent["resource_effects"]:
                fx["delta_pct"] *= ratio
            state.setdefault("updates", []).append(f"ESCALATION {parent['id']}: severity {old_severity:.2f} -> {severity:.2f}")
            parent["duration"] += max(2, int(arch.base_duration * 0.4))
            parent["escalations"] += 1
            parent["headline"] = "Escalation: " + parent["headline"].split(": ", 1)[-1]
            continue

        if severity < 0.22:
            continue                                           # quiet day

        place = rng.choice(PLACES[region])
        race = None
        if arch.race_linked:
            local = [r for r, d in RACES.items() if d["home"] == region] or list(RACES)
            race = rng.choice(local)

        duration = max(3, int(arch.base_duration * (0.7 + 0.9 * severity)))
        anticipation = round(rng.uniform(0.05, 0.55) * (1 - uncertainty), 3)

        # resource effects
        res_fx = []
        for res, direction in arch.resources:
            mag = round(direction * severity * rng.uniform(1.8, 5.4), 2)
            res_fx.append({"resource": res, "delta_pct": mag,
                           "lag": rng.choice([0, 1, 2, 3])})

        # company effects, ordered by absolute exposure
        exposures = [(t, exposure(t, arch, region, race)) for t in COMPANIES]
        exposures = [(t, x) for t, x in exposures if abs(x) > 0.01]
        exposures.sort(key=lambda p: -abs(p[1]))
        exposures = exposures[:9]
        co_fx = [{"ticker": t,
                  "earnings_delta_pct": round(x * severity * rng.uniform(2.0, 7.5), 2),
                  "lag": rng.choice([0, 1, 2, 4, 7])}
                 for t, x in exposures]

        eid = f"EV-{sim_date:%Y%m%d}-{key[:4].upper()}-{rng.randrange(1000, 9999)}"
        race_title = race.title() if race else "Guild"
        headline = rng.choice(HEADLINE_TEMPLATES[key]).format(place=place, race_title=race_title)

        benign = key in BENIGN_ARCHETYPES
        noun = "development" if benign else "incident"
        tail = ("effects expected to build over about "
                if benign else "disruption expected to persist about ")
        report = (
            f"Wardens at {place} in the {region.title()} confirmed the {noun} on "
            f"{sim_date:%d %b}. Magnitude is assessed at {severity:.2f} on the Exchange "
            f"scale, with {tail}{duration} days. "
            + (f"{race_title} labour bodies are directly involved. " if race else "")
            + "Figures are provisional."
        )
        helped = [t for t, x in exposures if x > 0][:3]
        hurt = [t for t, x in exposures if x < 0][:3]
        implications = (
            "Cost or volume pressure likely at " + (", ".join(hurt) or "no listed issuer")
            + "; possible benefit at " + (", ".join(helped) or "no listed issuer")
            + ". Effects land on inventories and contract renewals, not on the day."
        )
        unknowns = (
            f"Duration is uncertain (confidence {1-uncertainty:.0%}). Insurance "
            f"attachment points are undisclosed. Whether "
            f"{hurt[0] if hurt else 'affected issuers'} can source substitutes within "
            f"the quarter is unknown."
        )

        pool = BENIGN_RUMOUR_TEMPLATES if benign else RUMOUR_TEMPLATES
        rumours = [rng.choice(pool).format(place=place)] if uncertainty > 0.35 else []
        undisclosed = [rng.choice(UNDISCLOSED_TEMPLATES).format(
            pct=rng.randint(15, 90), extra=rng.randint(4, 40),
            ticker=(hurt[0] if hurt else "IRON"))]

        parent = None
        for prior in reversed(state["events"][-40:]):
            if prior["region"] == region and prior["category"] == arch.category \
                    and prior["id"] != eid:
                parent = prior["id"]
                break

        events.append(Event(
            id=eid, sim_day=sim_day, date=sim_date.isoformat(), archetype=key,
            category=arch.category, region=region, place=place,
            severity=round(severity, 3), duration=duration, uncertainty=uncertainty,
            anticipation=anticipation, race=race, headline=headline, report=report,
            implications=implications, unknowns=unknowns,
            tickers=[t for t, _ in exposures], resource_effects=res_fx,
            company_effects=co_fx, rumours=rumours, undisclosed=undisclosed,
            parent_id=parent,
        ))
        active[scope] = eid

    return events


# ---------------------------------------------------------------------------
# MARKET MODEL  (deliberately simple — limitations documented below)
# ---------------------------------------------------------------------------
# price_return = beta * earnings_surprise * (1 - anticipation) * liquidity_damp
#                + trend_term + noise
#
# LIMITATIONS: no order book, no cross-sectional correlation, no explicit
# volume constraint, no borrowing cost on shorts. Investor mix is compressed
# into two coefficients (surprise sensitivity, trend weight) rather than
# simulated agent-by-agent. Adequate for narrative causality; not adequate for
# execution or microstructure study.

INVESTOR_MIX = {   # weight, surprise sensitivity, trend weight, mean horizon (days)
    "fundamental": (0.40, 1.00, 0.05, 240),
    "trend":       (0.25, 0.20, 0.85, 20),
    "news":        (0.20, 1.35, 0.30, 3),
    "maker":       (0.15, 0.15, 0.00, 1),
}


def apply_market(state: dict, todays_events: list[Event], sim_day: int, seed: int):
    prices = state["prices"]
    trend = state["trend"]
    surprise = {t: 0.0 for t in COMPANIES}

    for ev in todays_events:
        for fx in ev.company_effects:
            if fx["lag"] == 0:
                surprise[fx["ticker"]] += fx["earnings_delta_pct"] * (1 - ev.anticipation)

    # pending (lagged) effects that mature today
    still_pending = []
    for p in state["pending"]:
        if p["day"] <= sim_day:
            surprise[p["ticker"]] += p["delta"] * 0.6      # lagged = partly priced
        else:
            still_pending.append(p)
    state["pending"] = still_pending

    for ev in todays_events:
        for fx in ev.company_effects:
            if fx["lag"] > 0:
                state["pending"].append({"ticker": fx["ticker"], "day": sim_day + fx["lag"],
                                         "delta": fx["earnings_delta_pct"] * (1 - ev.anticipation)})

    sens = sum(w * s for w, s, _t, _h in INVESTOR_MIX.values())
    tw = sum(w * t for w, _s, t, _h in INVESTOR_MIX.values())

    for tkr in COMPANIES:
        rng = stable_rng(seed, sim_day, tkr, "px")
        liq = 0.6 + 0.4 * min(COMPANIES[tkr][5] / 60.0, 1.0)   # bigger float = calmer
        ret = (sens * surprise[tkr] / 100.0) * (1.0 / liq)
        ret += tw * trend[tkr] * 0.35
        ret += rng.gauss(0, 0.009)
        if rng.random() < 0.06:                                 # occasional overreaction
            ret *= rng.uniform(1.5, 2.4)
        ret = max(-0.16, min(0.16, ret))
        prices[tkr] = round(max(0.5, prices[tkr] * (1 + ret)), 2)
        trend[tkr] = round(0.75 * trend[tkr] + 0.25 * ret, 5)
        state["last_return"][tkr] = round(ret, 5)


def apply_resources(state: dict, todays_events: list[Event], sim_day: int):
    idx = state["resources"]
    still = []
    for p in state["res_pending"]:
        if p["day"] <= sim_day:
            idx[p["resource"]] = round(idx[p["resource"]] * (1 + p["delta"] / 100.0), 2)
        else:
            still.append(p)
    state["res_pending"] = still

    for ev in todays_events:
        for fx in ev.resource_effects:
            if fx["lag"] == 0:
                idx[fx["resource"]] = round(idx[fx["resource"]] * (1 + fx["delta_pct"] / 100.0), 2)
            else:
                state["res_pending"].append({"resource": fx["resource"],
                                             "day": sim_day + fx["lag"],
                                             "delta": fx["delta_pct"]})
    # slow mean reversion toward 100
    for r in idx:
        idx[r] = round(idx[r] + (100.0 - idx[r]) * 0.02, 2)


def expire_events(state: dict, sim_day: int) -> list[str]:
    """Resolve matured events and return recovery notices for the feed."""
    notices = []
    for ev in state["events"]:
        if ev.get("resolved_on") is None and sim_day >= ev["sim_day"] + ev["duration"]:
            ev["resolved_on"] = sim_day
            scope = f"{ev['archetype']}:{ev['region']}"
            if state["active"].get(scope) == ev["id"]:
                del state["active"][scope]
            span = sim_day - ev["sim_day"]
            verb = ("normal service restored" if ev["escalations"] == 0
                    else "conditions eased after repeated setbacks")
            notices.append(
                f"RESOLVED  {ev['id']} — {ev['place']}, {ev['region'].title()}: {verb} "
                f"after {span} days. Affected issuers: {', '.join(ev['tickers'][:4])}."
            )
    return notices


# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------

def new_state(seed: int) -> dict:
    return {
        "seed": seed,
        "sim_day": 0,
        "start_date": date.today().isoformat(),
        "events": [],
        "active": {},
        "pending": [],
        "res_pending": [],
        "prices": {t: v[4] for t, v in COMPANIES.items()},
        "trend": {t: 0.0 for t in COMPANIES},
        "last_return": {t: 0.0 for t in COMPANIES},
        "resources": {r: 100.0 for r in RESOURCES},
    }


def load_state(path: Path, seed: int) -> dict:
    if path.exists():
        st = json.loads(path.read_text())
        st.setdefault("last_return", {t: 0.0 for t in COMPANIES})
        return st
    return new_state(seed)


def save_state(path: Path, state: dict):
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------

def print_feed(events: list[Event], state: dict, sim_date: date, sim_day: int,
               notices: list[str] | None = None):
    print(f"\n{'='*74}\n  THE AETHER HERALD  —  Day {sim_day}  ({sim_date:%d %b %Y})"
          f"   [SIMULATED — FICTIONAL]\n{'='*74}")
    for n in (notices or []):
        print(f"\n[RECOVERY] {n}")
    if not events:
        print("\n  Quiet across the five regions. Markets traded on flow alone.")
    for ev in events:
        print(f"\n[{ev.category.upper()}] {ev.headline}")
        print(f"  id={ev.id}  region={ev.region}  severity={ev.severity:.2f} "
              f"dur={ev.duration}d  uncertainty={ev.uncertainty:.2f}"
              + (f"  race={ev.race}" if ev.race else ""))
        print(f"  CONFIRMED : {ev.report}")
        print(f"  IMPLIES   : {ev.implications}")
        print(f"  UNKNOWN   : {ev.unknowns}")
        for r in ev.rumours:
            print(f"  RUMOUR    : {r}  (unverified)")
        print(f"  TICKERS   : {', '.join(ev.tickers)}")
        if ev.parent_id:
            print(f"  FOLLOWS   : {ev.parent_id}")
        # ev.undisclosed is intentionally NOT printed.

    prices, ret = state["prices"], state["last_return"]
    ranked = sorted(COMPANIES, key=lambda t: -ret[t])
    gainers = [t for t in ranked if ret[t] > 0][:4]
    losers = [t for t in reversed(ranked) if ret[t] < 0][:4]
    breadth = sum(1 for t in COMPANIES if ret[t] > 0)

    print(f"\n  {'-'*70}")
    print(f"  BOARD    {breadth} up / {len(COMPANIES)-breadth} down")
    print("  GAINERS  " + ("  ".join(
        f"{t} {prices[t]:>7.2f} {ret[t]*100:+6.2f}%" for t in gainers) or "none"))
    print("  LOSERS   " + ("  ".join(
        f"{t} {prices[t]:>7.2f} {ret[t]*100:+6.2f}%" for t in losers) or "none"))
    print("  INDICES  " + "  ".join(f"{r}={state['resources'][r]:.1f}" for r in RESOURCES))
    print()


def print_report(state: dict):
    print(f"\nAETHER EXCHANGE — world state  (seed {state['seed']}, day {state['sim_day']})")
    print(f"Events logged: {len(state['events'])}   Active: {len(state['active'])}   "
          f"Pending effects: {len(state['pending']) + len(state['res_pending'])}")
    print("\nRESOURCE INDICES (base 100)")
    for r in RESOURCES:
        print(f"  {r:<8} {state['resources'][r]:>7.2f}")
    print("\nPRICE BOARD (GC)")
    base = {t: v[4] for t, v in COMPANIES.items()}
    for t in sorted(COMPANIES, key=lambda x: -(state['prices'][x] / base[x])):
        chg = (state["prices"][t] / base[t] - 1) * 100
        mcap = state["prices"][t] * COMPANIES[t][5]
        print(f"  {t}  {COMPANIES[t][0]:<26} {state['prices'][t]:>8.2f}  "
              f"{chg:>+7.2f}%   mcap {mcap:>9.1f}M GC")
    print("\nACTIVE EVENTS")
    for scope, eid in state["active"].items():
        ev = next(e for e in state["events"] if e["id"] == eid)
        print(f"  {eid}  {scope:<28} sev={ev['severity']:.2f}  esc={ev['escalations']}")
    print()


# ---------------------------------------------------------------------------
# DRIVER
# ---------------------------------------------------------------------------

def run_day(state: dict, offline: bool, quiet: bool) -> tuple[list[Event], list[str]]:
    sim_day = state["sim_day"] + 1
    sim_date = date.fromisoformat(state["start_date"]) + timedelta(days=sim_day - 1)
    seed = state["seed"]

    if offline:
        table = synthetic_table(stable_rng(seed, sim_day, "feed"))
    else:
        if not quiet:
            print(f"\nPolling {len(SOURCES)} outlets…")
        table = poll(quiet=quiet)

    events = forge_events(table, state, sim_date, sim_day, seed)
    state["events"].extend(asdict(e) for e in events)
    apply_resources(state, events, sim_day)
    apply_market(state, events, sim_day, seed)
    notices = expire_events(state, sim_day)
    state["sim_day"] = sim_day
    return events, notices


def check_invariants(state: dict) -> list[str]:
    problems = []
    for t, p in state["prices"].items():
        if p <= 0:
            problems.append(f"{t}: non-positive price {p}")
    for r, v in state["resources"].items():
        if v <= 0:
            problems.append(f"{r}: non-positive index {v}")
    ids = [e["id"] for e in state["events"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate event ids")
    for scope, eid in state["active"].items():
        ev = next((e for e in state["events"] if e["id"] == eid), None)
        if ev is None:
            problems.append(f"active scope {scope} points at missing event")
        elif ev["resolved_on"] is not None:
            problems.append(f"active scope {scope} points at resolved event")
    for e in state["events"]:
        if e["parent_id"] and e["parent_id"] not in set(ids):
            problems.append(f"{e['id']}: dangling parent {e['parent_id']}")
    return problems


def read_key() -> str:
    """Read one keypress without waiting for Enter. Falls back to line input."""
    try:
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if ch == "\x03":          # Ctrl+C in raw mode
            return "q"
        return ch
    except Exception:
        try:
            return (input() or "\r")[:1]
        except EOFError:
            return "q"


def interactive(state: dict, args) -> int:
    """Advance the world one turn per keypress."""
    print("\n" + "=" * 74)
    print("  THE AETHER EXCHANGE — interactive session"
          + ("   [OFFLINE]" if args.offline else "   [LIVE FEEDS]"))
    print("  SPACE / ENTER  next turn        b  price board")
    print("  r  world report                 q  quit and save")
    print("=" * 74)
    while True:
        sys.stdout.write("\n  [space=next  b=board  r=report  q=quit] > ")
        sys.stdout.flush()
        key = read_key().lower()
        print(key if key.strip() else "next")

        if key in ("q", "\x1b"):
            save_state(args.state, state)
            print(f"\n  Saved at day {state['sim_day']} -> {args.state}\n")
            return 0
        if key == "r":
            print_report(state)
            continue
        if key == "b":
            base = {t: v[4] for t, v in COMPANIES.items()}
            print(f"\n  PRICE BOARD  (day {state['sim_day']}, GC)")
            for t in sorted(COMPANIES, key=lambda x: -(state["prices"][x] / base[x])):
                chg = (state["prices"][t] / base[t] - 1) * 100
                print(f"    {t}  {COMPANIES[t][0]:<26} {state['prices'][t]:>8.2f}"
                      f"  {chg:>+7.2f}% since open")
            continue

        try:
            evs, notes = run_day(state, args.offline, quiet=True)
        except KeyboardInterrupt:
            save_state(args.state, state)
            return 0
        sd = date.fromisoformat(state["start_date"]) + timedelta(days=state["sim_day"] - 1)
        print_feed(evs, state, sd, state["sim_day"], notes)
        save_state(args.state, state)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Aether Exchange news-driven event forge")
    ap.add_argument("--state", type=Path, default=STATE_PATH)
    ap.add_argument("--seed", type=int, default=20260907)
    ap.add_argument("--once", action="store_true", help="advance one day and exit")
    ap.add_argument("--days", type=int, default=0, help="advance N days")
    ap.add_argument("--watch", type=int, metavar="SECONDS", help="poll on a timer")
    ap.add_argument("--play", "-i", action="store_true",
                    help="interactive: one turn per keypress")
    ap.add_argument("--offline", action="store_true", help="no network; reproducible")
    ap.add_argument("--report", action="store_true", help="print state and exit")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--verify", action="store_true", help="run consistency checks")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.reset and args.state.exists():
        args.state.unlink()

    state = load_state(args.state, args.seed)

    if args.report:
        print_report(state)
        return 0

    if args.play:
        return interactive(state, args)

    n = args.days if args.days else 1
    if args.watch:
        try:
            while True:
                evs, notes = run_day(state, args.offline, args.quiet)
                sd = date.fromisoformat(state["start_date"]) + timedelta(days=state["sim_day"] - 1)
                print_feed(evs, state, sd, state["sim_day"], notes)
                save_state(args.state, state)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nstopped.")
            save_state(args.state, state)
            return 0

    for _ in range(n):
        evs, notes = run_day(state, args.offline, args.quiet)
        sd = date.fromisoformat(state["start_date"]) + timedelta(days=state["sim_day"] - 1)
        if not args.quiet:
            print_feed(evs, state, sd, state["sim_day"], notes)
    save_state(args.state, state)

    if args.verify:
        probs = check_invariants(state)
        print("INVARIANTS:", "OK" if not probs else "FAILED")
        for p in probs:
            print("  !", p)
        return 1 if probs else 0
    return 0



# Version 3: deterministic economic state, public market, and player ledger.
# All monetary accounts below are GC, quantities are standardized baskets.
RACES = {name: {"home": home} for name, home in [
    ("humans", "crownlands"), ("kharun", "ironpeak"), ("sylvari", "verdant"),
    ("veyri", "azure"), ("nerathi", "azure"), ("ashari", "ember"),
    ("myren", "verdant"), ("oruni", "ironpeak"), ("lumen", "crownlands"),
    ("forged", "ember")]}
# ticker, name, region, sectors, primary output, suppliers, history
CATALOG = [
("IRON","Ironpeak Mining","ironpeak","mining metal","metal","EMBR WYRM","Dera Flintwake and Tomas Vale united three indebted mines 180 years ago. A tunnel disaster forced a public listing; communities still contest its mineral rights."),
("EMBR","Emberstone Energy","ember","crystal energy","energy","PHNX WYRM","Ashari engineer Sera Venn stabilized crystals after the Great Eruption. Her cooperative became a commercial supplier whose oldest refinery sits above an unstable chamber."),
("FRGE","Crownforge Industries","ironpeak","machinery arms metal","metal","IRON EMBR","Oruni smith Maruk Sen and Forged designer Nine converted military scrap into farm tools. Government weapons orders later divided its civilian and military priorities."),
("VRDT","Verdant Harvest","verdant","farming food","food","TIDE DEEP","Human and Sylvari cooperatives founded it after the Three-Year Famine. Exporting emergency reserves restored profits but damaged public trust."),
("LEAF","Moonleaf Remedies","verdant","herbal","food","VRDT DEEP FROST","Myren researcher Pell-of-Rain and physician Anika Roe commercialized a marsh-fever treatment. Their affordable-medicine pledge now faces shareholder opposition."),
("SAIL","Azure Sails","azure","shipping trade","service","EMBR ATLS","Nerathi captains united against discriminatory docking fees. Debt-financed expansion secured inland markets but left an aging fleet and high repayments."),
("GRFN","Griffin Express","crownlands","transport logistics","service","VRDT ATLS","Veyri couriers and Oruni handlers delivered relief across avalanche-blocked passes. Urban contracts now draw resources away from remote communities."),
("BSTN","Bastion Construction","crownlands","construction","service","ROOT FRGE","Kharun architect Ona Deepwell rebuilt a flooded city with durable housing. A leveraged luxury-property acquisition increased its exposure to borrowing costs."),
("BANK","Silverquill Bank","crownlands","finance","credit","FAR ATLS","A human–Nerathi currency partnership survived the Copper Panic. Its newer infrastructure loans threaten the cautious reputation it inherited."),
("AEGS","Aegis Underwriters","crownlands","insurance","service","ATLS FAR","Merchants established Aegis after a warehouse fire. Lumen mathematician Issa Veil improved its risk tables, but magical-disaster policies remain difficult to price."),
("GATE","Waygate Networks","crownlands","transport crystal","service","EMBR BRAS","Sylvari physicist Elar Sen and Forged engineer Meridian opened the first commercial gate. A royal contract rescued them; aging components now threaten profitable routes."),
("WYRM","Wyrmwatch Security","ironpeak","security hazard","service","FRGE LEAF","An Oruni-led rescue group defended mines during the Redwing Migration. Buying military contractors created tension with its civilian rescue mission."),
("ROOT","Rootweave Materials","verdant","forestry","timber","VRDT DEEP","Sylvari foresters and Myren cultivators made structural composites from waste. Bastion enabled expansion; defective early batches still require repairs."),
("DEEP","Deepcurrent Utilities","azure","utility","service","EMBR BRAS","Nerathi engineer Tal Oss replaced salt-contaminated coastal wells. Old farm water-price guarantees now conflict with growing urban demand."),
("SPOR","Sunspore Foods","verdant","food farming","food","DEEP EMBR","Myren grower Ves and Ashari cook Nima Sar fed eruption refugees. Their expanded farms depend on a small number of vulnerable fungal cultures."),
("NITE","Nightglass Instruments","crownlands","instruments","service","IRON EMBR","Lumen craftswoman Rill Sovan invented glare-reducing lenses. Precision surveying brought success, but cheaper sensors now challenge its designs."),
("BRAS","Brassheart Works","ember","machinery","service","IRON EMBR PHNX","Former workers and emancipated Forged citizens acquired this construct manufacturer. It makes non-sentient automation and personal repair parts amid disputes over design access."),
("RAIL","Hearthline Rail","ironpeak","transport logistics","service","EMBR FRGE","Treaties between Kharun cities and Oruni confederations created its routes. Conflicting land concessions now obstruct its southern expansion."),
("FROST","Frostvault Logistics","azure","logistics","service","EMBR BRAS","Ashari engineer Varo Kes stored excess heat in reusable salts. Moonleaf financed early growth; a warehouse failure exposed inadequate backups."),
("FAR","Farvoice Communications","crownlands","information","service","EMBR NITE","A Veyri messenger guild built resonance towers and retrained couriers. Rural service obligations cost money while competitors target urban customers."),
("ATLS","Atlas Cartography","crownlands","information instruments","service","NITE FAR","An Oruni navigator and Lumen astronomer founded Atlas after a fatal mapping error. Exclusive surveys now conflict with its public-safety tradition."),
("INNS","Crown & Lantern Inns","crownlands","luxury food","service","VRDT SPOR DEEP","Mira Doss offered neutral refuge during a border war. Its inclusive inns expanded into prestigious city properties financed with substantial debt."),
("TIDE","Tidemark Salt & Chemicals","azure","commodities","service","EMBR SAIL","Nerathi salt cooperatives merged with Ashari processors to supply affordable fertilizer. Pollution from an old plant threatens its coastal permits."),
("PHNX","Phoenix Reclamation","ember","salvage hazard","metal","EMBR WYRM","Forged salvager Second Dawn recovered battlefield machinery. A government artifact-cleanup contract now contains hazards omitted from its budget."),
("STAR","Starfall Ventures","ember","mining gems crystal","metal","NITE WYRM","Sylvari geologist Thalen Orr proved meteor metals commercially useful. A second deposit remains uncertain, despite investors funding its exploration.")]
_old_companies = COMPANIES
COMPANIES = {}
HISTORIES = {}
SUPPLIERS = {}
OUTPUTS = {}
for i, (t, name, region, sectors, output, suppliers, history) in enumerate(CATALOG):
    old = _old_companies.get(t)
    people = list(RACES)
    workforce = {people[i % 10]: .4, people[(i+3) % 10]: .35, people[(i+6) % 10]: .25}
    COMPANIES[t] = (name, region, sectors.split(), workforce, old[4] if old else 65 + i * 5.7, old[5] if old else 20 + i)
    HISTORIES[t], SUPPLIERS[t], OUTPUTS[t] = history, suppliers.split(), output

# Directional classification avoids turning every monetary headline into tightening.
for base, key, resources, hurt, helped, headline in [
    ("monetary_shift", "rate_easing", (("credit",-1),), (), ("construction","finance","luxury"), "Treasury Reduces Borrowing Rate"),
    ("harvest_signal", "harvest_failure", (("food",1),), ("farming","food"), (), "Harvest Shortfall Confirmed at {place}")]:
    a = replace(ARCH_BY_KEY[base], key=key, resources=resources, sectors_hurt=hurt, sectors_helped=helped, valence=1 if key=="rate_easing" else -1)
    ARCHETYPES.append(a)
    ARCH_BY_KEY[key] = a
    HEADLINE_TEMPLATES[key] = [headline]
BENIGN_ARCHETYPES = {a.key for a in ARCHETYPES if a.valence >= 0} | {"discovery", "harvest_signal"}

def keyword(text, term):
    return bool(re.search(r"(?<!\w)" + re.escape(term.strip()) + (r"(?!\w)" if term[-1:].isspace() or not term.isascii() else r"\w*\b"), text))

def classify(title):
    low = title.lower()
    if re.search(r"\b(no|not|denies|avoids|averts|false)\b", low):
        return None  # conservative: ambiguous negated reports do not generate a shock
    if re.search(r"rate cut|cuts? rates?|reduces? .*rate", low):
        return "rate_easing"
    if re.search(r"crop failure|harvest fail|poor harvest|yield.*fall", low):
        return "harvest_failure"
    matches = []
    for a in ARCHETYPES:
        if a.key in ("rate_easing", "harvest_failure"):
            continue
        hits = sum(keyword(low, k) for k in a.keywords)
        if not hits:
            continue
        required = {
            "transport_failure": r"crash|derail|closed|closure|cancel|disrupt|collapse|दुर्घटना",
            "monetary_shift": r"rate hike|raises? rates?|inflation.*ris|tighten|महंगाई",
            "industrial_accident": r"fire|blast|explosion|leak|accident|धमाका|विस्फोट",
            "plague": r"outbreak|epidemic|infections? ris|cases? ris|संक्रमण",
            "harvest_signal": r"bumper|record harvest|yield.*ris|strong harvest|crop.*grow",
            "corporate_win": r"wins?|award|profit.*ris|growth|expansion|record high|funding|मुनाफा",
        }
        if a.key in required and not re.search(required[a.key], low):
            continue
        matches.append((hits, a.key))
    if not matches:
        return None
    matches.sort(reverse=True)
    return None if len(matches)>1 and matches[0][0]==matches[1][0] else matches[0][1]

def poll_new(state, quiet=False):
    table = {}
    today_seen = {}
    existing = state["seen_headlines"]
    successful = 0
    for label, url, lang in SOURCES:
        try:
            titles = fetch_titles(url)
            successful += 1
        except (urllib.error.URLError, ET.ParseError, OSError):
            if not quiet:
                print(f"Feed unavailable: {label}")
            continue
        for title in titles:
            fingerprint = hashlib.sha256((label+":"+title.strip().lower()).encode()).hexdigest()
            if fingerprint in existing or fingerprint in today_seen:
                continue
            today_seen[fingerprint] = state["sim_day"] + 1
            key = classify(title)
            if key:
                slot = table.setdefault(key, {"labels":set(),"intensity":0})
                slot["labels"].add(label)
                slot["intensity"] += int(any(keyword(title.lower(),w) for w in INTENSITY_WORDS))
    if successful == 0:
        raise RuntimeError("All feeds failed; world was not advanced. Try again or use --offline.")
    existing.update(today_seen)
    # Persist hashes only. No source headlines or article bodies are stored.
    return {k:{"outlets":len(v["labels"]),"intensity":v["intensity"]} for k,v in table.items()}

def exposure(ticker, arch, region, race):
    # Ancestry does not determine operating performance or investor behavior.
    sectors=COMPANIES[ticker][2]
    score=sum((s in arch.sectors_helped)-(s in arch.sectors_hurt) for s in sectors)
    if "insurance" in sectors and arch.category in ("natural","magical","disease","monster"):
        score=-1.0
    return score*(1.6 if COMPANIES[ticker][1]==region else .55)

def new_state(seed, start_date="2026-09-07"):
    st={"version":3,"seed":seed,"start_date":start_date,"sim_day":0,"events":[],"active":{},
        "pending":[],"res_pending":[],"prices":{t:v[4] for t,v in COMPANIES.items()},
        "trend":{t:0. for t in COMPANIES},"last_return":{t:0. for t in COMPANIES},
        "resources":{r:100. for r in RESOURCES},"seen_headlines":{},"history":[],"economy":{},
        "portfolio":{"cash":100000.,"holdings":{},"trades":[]},"books":{},"updates":[]}
    for t,v in COMPANIES.items():
        rng=stable_rng(seed,t,"accounts")
        capital=v[4]*v[5]*1e6
        sales=capital/(365*5)
        st["economy"][t]={"cash":capital*.08,"debt":capital*.12,"fixed_assets":capital*.3,
            "inventory":sales*5/100,"unit_cost":65.,"capacity":sales/100*1.2,
            "base_sales":sales,"base_profit":sales*.18,"profit_ema":sales*.18,
            "revenue":0.,"profit":0.,"production":0.,"sold":0.,"fulfillment":1.,
            "dividends":0.,"claims":0.,"bankrupt":False,"total_profit":0.,
            "total_dividends":0.,"initial_equity":capital*.26+sales*5*.65,
            "uncertainty":rng.uniform(.8,1.2),"equity":capital*.26+sales*5*.65}
    return st

def save_state(path,state):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(state,indent=2,ensure_ascii=False))
    tmp.replace(path)

def load_state(path,seed,start_date="2026-09-07"):
    if not path.exists():
        return new_state(seed,start_date)
    state=json.loads(path.read_text())
    if state.get("version")!=3:
        raise ValueError("Old state uses a different company roster. Choose a new --state file or explicitly use --reset.")
    return state

def active_effects(state,day,public=False):
    company={t:0. for t in COMPANIES}
    resources={r:0. for r in RESOURCES}
    for ev in state["events"]:
        if ev.get("resolved_on") is not None or day >= ev["sim_day"]+ev["duration"]:
            continue
        age=day-ev["sim_day"]
        hidden=1. if public else ev.get("true_multiplier",1.)
        for fx in ev["company_effects"]:
            if public or age>=fx["lag"]:
                company[fx["ticker"]]+=fx["earnings_delta_pct"]/100*hidden
        for fx in ev["resource_effects"]:
            if age>=fx["lag"]:
                resources[fx["resource"]]+=fx["delta_pct"]*hidden
    return company,resources

def settle_economy(state,day):
    shocks,res=active_effects(state,day)
    for r in RESOURCES:
        target=max(35.,min(300.,100+res[r]*3))
        state["resources"][r]=round(state["resources"][r]+.22*(target-state["resources"][r]),4)
    prior={t:e["fulfillment"] for t,e in state["economy"].items()}
    claims={t:0. for t in COMPANIES}
    # Explicit stylized policy: eligible operating losses above deductible;
    # claims capped by policy limit and insurer's available cash.
    for t,e in state["economy"].items():
        if t!="AEGS" and not e["bankrupt"]:
            claims[t]=min(e["base_sales"]*.08,max(0.,-shocks[t]-.025)*e["base_sales"]*.4)
    total=sum(claims.values())
    premiums=sum(x["base_sales"]*.002 for k,x in state["economy"].items() if k!="AEGS" and not x["bankrupt"])
    insurer=state["economy"]["AEGS"]
    scale=min(1.,insurer["cash"]*.05/total) if total and not insurer["bankrupt"] else 0.
    claims={t:x*scale for t,x in claims.items()}
    for t,e in state["economy"].items():
        if e["bankrupt"]:
            e.update(revenue=0.,profit=0.,production=0.,sold=0.,fulfillment=0.,dividends=0.,claims=0.)
            continue
        shock=max(-.65,min(.5,shocks[t]))
        supply=sum(prior[s] for s in SUPPLIERS[t])/len(SUPPLIERS[t])
        resource=OUTPUTS[t]
        selling_price=100*(state["resources"].get(resource,100)/100)
        unit_cost=65*(.5+.25*state["resources"]["energy"]/100+.25*state["resources"]["metal"]/100)
        capacity=e["capacity"]*max(.1,1+min(0,shock)*2)*(.4+.6*supply)
        desired=e["base_sales"]/100*max(.2,1+shock*2)
        opening_inv=e["inventory"]
        production=min(capacity,max(0,desired*3-opening_inv),max(0,e["cash"]*.1/unit_cost))
        inv_value=opening_inv*e["unit_cost"]+production*unit_cost
        available=opening_inv+production
        avg_cost=inv_value/available if available else unit_cost
        sold=min(available,desired)
        revenue=sold*selling_price
        overhead=e["base_sales"]*.17
        interest=e["debt"]*.05*state["resources"]["credit"]/100/365
        premium=0. if t=="AEGS" else e["base_sales"]*.002
        insurance_flow=(-sum(claims.values())+premiums) if t=="AEGS" else claims[t]-premium
        profit=revenue-sold*avg_cost-overhead-interest+insurance_flow
        e["cash"]+=revenue-production*unit_cost-overhead-interest+insurance_flow
        dividend=max(0,min(profit*.15,e["cash"]*.01)) if day%30==0 else 0.
        e["cash"]-=dividend
        e["total_profit"]+=profit
        e["total_dividends"]+=dividend
        e.update(inventory=available-sold,unit_cost=avg_cost,revenue=revenue,profit=profit,
            production=production,sold=sold,fulfillment=min(1.,sold/max(desired,.01)),
            dividends=dividend,claims=insurance_flow)
        e["equity"]=e["cash"]+e["inventory"]*e["unit_cost"]+e["fixed_assets"]-e["debt"]
        e["profit_ema"]=.9*e["profit_ema"]+.1*profit
        if e["cash"]<0 or e["equity"]<=0:
            e["bankrupt"]=True
            e["fulfillment"]=0.
            state["updates"].append(f"{t} entered insolvency; equity trading suspended at zero.")
        shares=COMPANIES[t][5]*1e6
        state["portfolio"]["cash"]+=dividend/shares*state["portfolio"]["holdings"].get(t,0)


def clear_book(book):
    bids=sorted(book["bids"],key=lambda x:-x["price"])
    asks=sorted(book["asks"],key=lambda x:x["price"])
    trades=[]
    i=j=0
    while i<len(bids) and j<len(asks):
        b,a=bids[i],asks[j]
        if b["price"]<a["price"]: break
        qty=min(b["qty"],a["qty"])
        px=round((b["price"]+a["price"])/2,2)
        trades.append({"price":px,"qty":qty})
        b["qty"]-=qty; a["qty"]-=qty
        if b["qty"]==0:i+=1
        if a["qty"]==0:j+=1
    return trades

def market_v3(state,day):
    public,_=active_effects(state,day,True)
    broad=stable_rng(state["seed"],day,"market").gauss(0,.002)
    for t,c in COMPANIES.items():
        old=state["prices"][t]
        e=state["economy"][t]
        if e["bankrupt"]:
            state["prices"][t]=0.; state["last_return"][t]=-1. if old else 0.
            state["books"][t]={"bids":[],"asks":[],"volume":0};continue
        rng=stable_rng(state["seed"],day,t,"orders")
        # Quarterly published accounts, not hidden event data, inform valuation.
        if day%90==0:
            e["published_ratio"]=max(.2,min(3.,e["profit_ema"]/e["base_profit"]))
        fair=c[4]*e.get("published_ratio",1.)*(1+max(-.65,min(.5,public[t])))
        move=max(-.12,min(.12,.06*(fair/max(old,.01)-1)+.15*state["trend"][t]+broad+rng.gauss(0,.003)))
        mid=max(.01,old*(1+move)-e["dividends"]/(c[5]*1e6))
        bids=[];asks=[]
        # Finite, regenerated daily liquidity from representative investor groups.
        for group,w in [("fundamental",.4),("trend",.25),("news",.2),("maker",.15)]:
            for level in range(4):
                qty=max(1,int(c[5]*1000*w/(level+1)))
                bids.append({"owner":group,"price":round(mid*(1.004-level*.004),2),"qty":qty})
                asks.append({"owner":group,"price":round(mid*(.996+level*.004),2),"qty":qty})
        book={"bids":bids,"asks":asks}
        trades=clear_book(book)
        price=trades[-1]["price"] if trades else old
        state["prices"][t]=price
        ret=price/old-1 if old else 0.
        state["last_return"][t]=ret
        state["trend"][t]=.75*state["trend"][t]+.25*ret
        book["volume"]=sum(x["qty"] for x in trades)
        state["books"][t]=book
    state["history"].append({"day":day,"prices":dict(state["prices"]),"resources":dict(state["resources"]),
        "volume":{t:b["volume"] for t,b in state["books"].items()},
        "accounts":{t:{k:e[k] for k in ("revenue","profit","cash","debt","inventory","equity","dividends")} for t,e in state["economy"].items()}})

def trade(state,side,ticker,qty):
    t=ticker.upper()
    if side not in ("buy","sell") or t not in COMPANIES or qty<=0:
        raise ValueError("Use buy/sell TICKER positive_integer.")
    p=state["portfolio"]
    if side=="sell" and p["holdings"].get(t,0)<qty:
        raise ValueError("Insufficient shares; short selling is disabled.")
    levels=state["books"].get(t,{}).get("asks" if side=="buy" else "bids",[])
    levels=sorted(levels,key=lambda x:x["price"] if side=="buy" else -x["price"])
    fills=[]; remaining=qty; cash=p["cash"]
    for level in levels:
        amount=min(remaining,level["qty"])
        if side=="buy":amount=min(amount,int(cash/(level["price"]*1.001)))
        if amount<=0:continue
        value=amount*level["price"]; fee=value*.001
        cash+=(-value-fee) if side=="buy" else value-fee
        level["qty"]-=amount;remaining-=amount
        fills.append({"qty":amount,"price":level["price"],"fee":fee})
        if remaining==0:break
    filled=qty-remaining
    if not filled:raise ValueError("No fill: insufficient cash, suspended stock, or no remaining liquidity. Advance a turn.")
    p["cash"]=cash
    p["holdings"][t]=p["holdings"].get(t,0)+(filled if side=="buy" else -filled)
    p["trades"].append({"day":state["sim_day"],"side":side,"ticker":t,"fills":fills})
    state["prices"][t]=fills[-1]["price"]
    if state["history"]:
        state["history"][-1]["prices"][t]=state["prices"][t]
    return f"{side.upper()} {filled}/{qty} {t}; cash {cash:,.2f} GC (0.1% fee)."

_original_print_feed=print_feed

def price_board(state):
    print("\nALL COMPANY PRICES (GC) — latest simulated daily change")
    for t,c in COMPANIES.items():
        print(f"{t:5} {c[0]:27} {state['prices'][t]:10.2f} {state['last_return'][t]*100:+8.2f}%")

def print_feed(events,state,sim_date,sim_day,notices=None):
    _original_print_feed(events,state,sim_date,sim_day,notices)
    price_board(state)

def run_day(state,offline,quiet):
    day=state["sim_day"]+1
    dt=date.fromisoformat(state["start_date"])+timedelta(days=day-1)
    table=synthetic_table(stable_rng(state["seed"],day,"feed")) if offline else poll_new(state,quiet)
    state["updates"]=[]
    notices=expire_events(state,day)
    events=forge_events(table,state,dt,day,state["seed"])
    for ev in events:
        data=asdict(ev)
        data["true_multiplier"]=stable_rng(state["seed"],ev.id,"truth").uniform(.75,1.5)
        data["undisclosed"]=[f"Actual operating magnitude multiplier: {data['true_multiplier']:.3f}"]
        state["events"].append(data)
    settle_economy(state,day)
    market_v3(state,day)
    state["sim_day"]=day
    return events,notices+state["updates"]

def check_invariants(state):
    errors=[]
    import math
    for t,e in state["economy"].items():
        expected=e["initial_equity"]+e["total_profit"]-e["total_dividends"]
        if abs(expected-e["equity"])>max(.1,abs(expected)*1e-9):errors.append(t+": accounting identity failed")
        if e["inventory"]<-.001:errors.append(t+": negative inventory")
        if state["prices"][t]<0:errors.append(t+": negative price")
        if not all(math.isfinite(e[k]) for k in ("cash","debt","equity","inventory","profit")):errors.append(t+": nonfinite account")
    ids=[e["id"] for e in state["events"]]
    if len(ids)!=len(set(ids)):errors.append("duplicate event IDs")
    for scope,eid in state["active"].items():
        if not any(e["id"]==eid and e["resolved_on"] is None for e in state["events"]):errors.append("invalid active event")
    if state["portfolio"]["cash"]<-.001:errors.append("negative player cash")
    if any(q<0 for q in state["portfolio"]["holdings"].values()):errors.append("negative player holdings")
    return errors

def interactive(state,args):
    print("\nSPACE or ENTER = NEXT TURN | b = prices | r = report | p = portfolio | t = trade | h = company histories | q = save and quit")
    price_board(state)
    while True:
        print("\nPress SPACE or ENTER for next turn > ",end="",flush=True)
        key=read_key().lower();print()
        if key in ("q","\x1b"):
            save_state(args.state,state);return 0
        if key=="b":price_board(state);continue
        if key=="r":print_report(state);continue
        if key=="h":
            for t in COMPANIES:print(f"{t}: {HISTORIES[t]}\n")
            continue
        if key=="p":
            p=state["portfolio"]
            worth=p["cash"]+sum(q*state["prices"][t] for t,q in p["holdings"].items())
            print(f"Cash: {p['cash']:,.2f} GC | Portfolio value: {worth:,.2f} GC\nHoldings: {p['holdings']}");continue
        if key=="t":
            try:
                side,t,qty=input("Trade (example: buy IRON 10): ").split()
                print(trade(state,side.lower(),t,int(qty)));save_state(args.state,state)
            except (ValueError,EOFError) as exc:print(exc)
            continue
        if key not in (" ","\r","\n"):
            print("Unrecognized key; turn unchanged.");continue
        try:
            ev,notes=run_day(state,args.offline,False)
        except RuntimeError as exc:print(exc);continue
        print_feed(ev,state,date.fromisoformat(state["start_date"])+timedelta(days=state["sim_day"]-1),state["sim_day"],notes)
        problems=check_invariants(state)
        if problems:raise RuntimeError("; ".join(problems))
        save_state(args.state,state)

def main(argv=None):
    ap=argparse.ArgumentParser(description="Aether Exchange v3 — fictional economic simulation")
    ap.add_argument("--state",type=Path,default=Path("aether_state_v3.json"))
    ap.add_argument("--seed",type=int,default=20260907)
    ap.add_argument("--start-date",default="2026-09-07",help="ISO simulation date; fixed default for reproducibility")
    ap.add_argument("--offline",action="store_true")
    ap.add_argument("--play","-i",action="store_true")
    ap.add_argument("--days",type=int,default=0)
    ap.add_argument("--once",action="store_true")
    ap.add_argument("--watch",type=int,help="seconds between polls; each poll explicitly represents one simulation day")
    ap.add_argument("--report",action="store_true")
    ap.add_argument("--reset",action="store_true")
    ap.add_argument("--verify",action="store_true")
    ap.add_argument("--quiet",action="store_true")
    args=ap.parse_args(argv)
    date.fromisoformat(args.start_date)
    if args.days<0 or (args.watch is not None and args.watch<=0):ap.error("days must be nonnegative and watch must be positive")
    if args.reset and args.state.exists():args.state.unlink()
    state=load_state(args.state,args.seed,args.start_date)
    if args.report:print_report(state);return 0
    try:
        if args.play or not (args.days or args.once or args.watch or args.verify):return interactive(state,args)
        if args.watch:print("Timer mode: each poll advances ONE SIMULATION DAY; repeated headlines are ignored.")
        count=0
        while args.watch or count<max(1,args.days):
            try:ev,notes=run_day(state,args.offline,args.quiet)
            except RuntimeError as exc:
                print(exc)
                if not args.watch:return 1
                time.sleep(args.watch);continue
            problems=check_invariants(state)
            if problems:raise RuntimeError("; ".join(problems))
            if not args.quiet:print_feed(ev,state,date.fromisoformat(state["start_date"])+timedelta(days=state["sim_day"]-1),state["sim_day"],notes)
            save_state(args.state,state);count+=1
            if args.watch:time.sleep(args.watch)
    except KeyboardInterrupt:
        save_state(args.state,state)
    if args.verify:print("INVARIANTS: OK")
    return 0

if __name__=="__main__":
    sys.exit(main())
