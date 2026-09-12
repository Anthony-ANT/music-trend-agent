import json
import os
import glob
from collections import Counter
from claude_agent_sdk import tool

GENRE_ALLOWLIST = {
    "pop", "rock", "pop rock", "r&b", "country", "standards", "adult contemporary",
    "blues rock", "folk rock", "soft rock", "roots rock", "singer-songwriter",
    "folk pop", "country pop", "hip hop", "contemporary r&b", "new jack swing",
    "power pop", "pop punk", "soul", "jazz", "dance-pop", "big band",
    "traditional pop", "vocal jazz", "contemporary country", "trap", "blues",
    "alternative r&b", "pop rap", "swing", "alternative pop", "funk", "rap",
    "southern hip hop", "alternative rock", "dance", "trap soul", "electronic",
    "hardcore hip hop", "synth-pop", "folk", "americana", "easy listening",
    "bluegrass", "nashville sound", "hip hop soul", "hip-hop", "trap rap",
    "indie pop", "alternative", "alternative/indie rock", "indie rock",
    "psychedelic pop", "psychedelic rock", "disco", "electropop", "pop soul",
    "singer/songwriter", "adult standards", "folk music", "classical",
    "orchestral", "k-pop", "latin", "avant-garde", "avant-garde jazz",
    "dixieland", "free jazz", "hard bop", "modern creative", "post-bop",
    "progressive jazz", "saxophone jazz",
}

# Known MusicBrainz name-collisions: the automated search matched the wrong
# real-world person despite passing the confidence-score check. Empty list
# means "no verified genre" rather than trusting the bad match. Update this
# as spot-checks surface more cases.
MANUAL_GENRE_OVERRIDES = {
    "Junior H": [],
    "Julia Wolf": [],
    "George Birge": [],
    "J. Cole": [],
    "Olivia Dean": [],
    "John": [],
    "John Morgan": [],
    "Josiah Queen": [],
    "Leon Thomas": [],
    "Ella Langley": [],
    "Steve Lacy": [],
    "Jordan Davis": [],
    "Dylan Scott": [],
    "Rod Wave": [],
}

async def _stage_all_weeks():
    billboard_files = sorted(glob.glob("data/raw/billboard_hot100_*.json"))
    mb_path = "data/raw/musicbrainz_artists_all.json"

    if not billboard_files or not os.path.exists(mb_path):
        return "Missing raw extract(s). Run backfill + genre lookup first."

    with open(mb_path) as f:
        mb_data = json.load(f)
    genre_lookup = {r["artist"]: r for r in mb_data}

    os.makedirs("data/staged", exist_ok=True)
    staged_files = []
    total_dropped_tags = 0
    total_overridden = 0

    for bpath in billboard_files:
        with open(bpath) as f:
            chart = json.load(f)

        debut_counts = Counter(
            e["artist"] for e in chart["entries"] if e["weeks_on_chart"] == 1
        )
        BULK_THRESHOLD = 5

        staged = []
        for e in chart["entries"]:
            is_debut = e["weeks_on_chart"] == 1
            is_sentinel_anomaly = (e["last_pos"] == 0 and not is_debut)
            clean_last_pos = None if (is_debut or is_sentinel_anomaly) else e["last_pos"]

            mb_entry = genre_lookup.get(e["artist"])
            primary_artist_used = None
            mbid = None

            if mb_entry and mb_entry.get("found"):
                primary_artist_used = mb_entry.get("primary_artist_used", e["artist"])
                mbid = mb_entry.get("mbid")

                if primary_artist_used in MANUAL_GENRE_OVERRIDES:
                    tags = MANUAL_GENRE_OVERRIDES[primary_artist_used]
                    total_overridden += 1
                else:
                    raw_tags = mb_entry["tags"]
                    filtered_tags = [t for t in raw_tags if t in GENRE_ALLOWLIST]
                    total_dropped_tags += (len(raw_tags) - len(filtered_tags))
                    tags = filtered_tags
            else:
                tags = []

            staged.append({
                "chart_date": chart["chart_date"],
                "rank": e["rank"],
                "title": e["title"],
                "artist": e["artist"],
                "primary_artist_used": primary_artist_used,
                "weeks_on_chart": e["weeks_on_chart"],
                "peak_pos": e["peak_pos"],
                "last_pos": clean_last_pos,
                "is_debut": is_debut,
                "is_reentry_anomaly": is_sentinel_anomaly,
                "is_release_week_bulk_entry": debut_counts[e["artist"]] >= BULK_THRESHOLD,
                "mbid": mbid,
                "genre_tags": tags,
            })

        out_path = f"data/staged/chart_staged_{chart['chart_date']}.json"
        with open(out_path, "w") as f:
            json.dump(staged, f, indent=2)
        staged_files.append(out_path)

    return (
        f"Staged {len(staged_files)} weeks ({staged_files[0]} to {staged_files[-1]}). "
        f"{total_dropped_tags} non-genre tags filtered out. "
        f"{total_overridden} rows used a manual override to correct a known MusicBrainz mismatch."
    )


@tool(
    "clean_and_stage_all_weeks",
    "Join every Billboard raw extract with the bulk MusicBrainz genre data, apply cleaning rules and manual overrides, and stage each week separately",
    {}
)
async def clean_and_stage_all_weeks(args):
    result_text = await _stage_all_weeks()
    return {"content": [{"type": "text", "text": result_text}]}