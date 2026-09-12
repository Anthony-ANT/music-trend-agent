import json
import os
import glob
import re
import time
from claude_agent_sdk import tool
import musicbrainzngs

musicbrainzngs.set_useragent(
    "MusicTrendAgent", "0.1", "https://github.com/Anthony-ANT/music-trend-agent"
)

def extract_primary_artist(credit):
    """Strip collaboration credits down to the primary/lead artist name."""
    # Order matters: check longer/more specific patterns first
    split_patterns = [
        r"\s+Featuring\s+", r"\s+Feat\.\s+", r"\s+feat\.\s+",
        r"\s+With\s+", r"\s+&\s+", r"\s+[xX]\s+", r",\s+",
    ]
    primary = credit
    for pattern in split_patterns:
        parts = re.split(pattern, primary, maxsplit=1)
        primary = parts[0]
    return primary.strip()


async def _lookup_all_genres():
    raw_files = sorted(glob.glob("data/raw/billboard_hot100_*.json"))
    if not raw_files:
        return "No Billboard extracts found."

    all_credits = set()
    for path in raw_files:
        with open(path) as f:
            chart = json.load(f)
        all_credits.update(e["artist"] for e in chart["entries"])

    # Map each full credit string to its extracted primary artist
    credit_to_primary = {c: extract_primary_artist(c) for c in all_credits}
    unique_primaries = sorted(set(credit_to_primary.values()))

    primary_results = {}
    for i, name in enumerate(unique_primaries, 1):
        print(f"[{i}/{len(unique_primaries)}] Looking up: {name}", flush=True)
        result = None
        for attempt in range(3):
            try:
                search = musicbrainzngs.search_artists(artist=name, limit=1)
                hits = search.get("artist-list", [])
                if not hits or int(hits[0].get("ext:score", 0)) < 80:
                    result = {"tags": [], "found": False}
                    break
                artist = hits[0]
                detail = musicbrainzngs.get_artist_by_id(artist["id"], includes=["tags"])
                tags = [t["name"] for t in detail["artist"].get("tag-list", [])]
                result = {"mbid": artist["id"], "tags": tags, "found": True}
                break
            except Exception as e:
                if attempt == 2:
                    result = {"tags": [], "found": False, "error": str(e)}
                else:
                    time.sleep(2)
        primary_results[name] = result

    # Build final results keyed by the ORIGINAL full credit string,
    # so staging can still join against chart entries unchanged
    results = []
    for full_credit, primary_name in credit_to_primary.items():
        r = primary_results[primary_name]
        entry = {"artist": full_credit, "primary_artist_used": primary_name}
        entry.update(r)
        results.append(entry)

    out_path = "data/raw/musicbrainz_artists_all.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    found = sum(1 for r in results if r["found"])
    return (
        f"Looked up {len(unique_primaries)} unique primary artists "
        f"(resolved from {len(all_credits)} raw credit strings across {len(raw_files)} weeks), "
        f"found {found}/{len(all_credits)} matched. Saved to {out_path}"
    )


@tool(
    "get_artist_genres_bulk",
    "Look up genre/tag metadata from MusicBrainz for the primary artist behind every credit string across all Billboard raw extracts",
    {}
)
async def get_artist_genres_bulk(args):
    result_text = await _lookup_all_genres()
    return {"content": [{"type": "text", "text": result_text}]}