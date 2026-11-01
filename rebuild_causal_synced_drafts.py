#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rebuild_causal_synced_drafts.py
-------------------------------
Generates 100% Shot-Synced, Causal-Chain ("Because -> Therefore -> But -> So")
scripts for testing and production on Chronos Shift (@ChronosShiftHistory).

Key Upgrades Over Legacy Drafts:
1. Explicit 0-15s Topic Setup & Hook: Never starts randomly. Clearly states what
   the video is about, the central problem, and the stakes in the first 2 sentences.
2. Child-Clear Causal Chain: Every beat uses simple, concrete cause-and-effect
   ("Because of this... But... So... And as a result...") with zero academic jargon.
3. 1-to-1 Audio-Visual Shot Sync: Every single shot object contains its own
   `narration` string (1-2 sentences) and an exact matching visual `prompt` so
   `assemble_longform.py` renders each image for the exact duration of the words
   being spoken about it.
4. Standalone Causal Shorts: Every Short has a complete Beginning -> Middle -> End
   causal script rather than slicing mid-sentence out of an Act.

Usage (from repo root):
  python rebuild_causal_synced_drafts.py
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if (ROOT_DIR / "longform_engine").exists():
    DRAFTS_DIR = ROOT_DIR / "longform_engine" / "drafts"
else:
    DRAFTS_DIR = Path("/tmp/yt_causal_drafts")

FOOOCUS_NEGATIVE_PROMPT_LOCK = (
    "modern, 20th century, 21st century, modern boats, modern ships, cruise ship, ferry boat, "
    "motorboat, steamship, yacht, cargo container, modern buildings, skyscrapers, asphalt roads, "
    "streetlights, cars, electricity, power lines, contemporary clothing, wristwatch, eyeglasses, "
    "cartoon, anime, 3d render plastic, watermark, text, signature, lowres, blurry, deformed hands, "
    "extra fingers, distorted anatomy, split screen, multi-panel grid, comic strip panels, collage"
)

CONSTANTINOPLE_CAUSAL_ACTS = [
    {
        "act_number": 1,
        "title": "What This Story Is About: The Unbreakable City",
        "historical_date": "April 1453",
        "shots": [
            {
                "shot_id": "act01_shot01",
                "causal_step": "THE TOPIC SETUP (0-12s)",
                "shot_type": "Wide Establishing",
                "motion": "push_in",
                "narration": (
                    "This is the story of how a twenty-one-year-old ruler named Sultan Mehmed "
                    "captured Constantinople, the most unbreakable city on Earth, in just fifty-three days."
                ),
                "prompt": (
                    "16:9 cinematic wide shot of young 21-year-old Ottoman Sultan Mehmed II on a white horse "
                    "on a grassy hill at sunrise, pointing his sword toward the distant walled city of Constantinople "
                    "across the water, photorealistic 8k, historical accuracy 1453"
                ),
            },
            {
                "shot_id": "act01_shot02",
                "causal_step": "THE HOOK PROMISE (12-24s)",
                "shot_type": "Wide Establishing",
                "motion": "pan_right",
                "narration": (
                    "For over a thousand years, twenty-three different armies had tried to take this city and failed. "
                    "To finally break it, Mehmed had to do something nobody had ever seen: sail seventy warships across dry land."
                ),
                "prompt": (
                    "16:9 dramatic cinematic shot of dozens of wooden warships being pulled by oxen over greased timber logs "
                    "up a steep muddy forested hill at night with hundreds of men holding torches, photorealistic 8k"
                ),
            },
            {
                "shot_id": "act01_shot03",
                "causal_step": "WHY IT WAS UNBREAKABLE (CAUSE #1)",
                "shot_type": "Tactical Map",
                "motion": "push_in",
                "narration": (
                    "Why was Constantinople so hard to capture? Because the city sat on a triangle of land surrounded "
                    "by deep water on two sides, and the only land entrance was blocked by three giant stone walls."
                ),
                "prompt": (
                    "16:9 clear top-down illustrated tactical map of the triangle peninsula of Constantinople surrounded by "
                    "the Sea of Marmara and Golden Horn water on two sides and the triple red defensive land wall on the left"
                ),
            },
            {
                "shot_id": "act01_shot04",
                "causal_step": "THE DEFENDER PROBLEM (EFFECT #1)",
                "shot_type": "Medium Troop",
                "motion": "pull_out",
                "narration": (
                    "Because plagues and past wars had shrunk the Roman Empire down to this one last city, "
                    "Emperor Constantine had only seven thousand soldiers left to defend the walls against eighty thousand Ottoman troops."
                ),
                "prompt": (
                    "16:9 cinematic medium shot of a small group of exhausted Byzantine soldiers in iron helmets and chainmail "
                    "standing atop a high stone wall looking down at a massive sea of thousands of red Ottoman army tents filling the horizon, 8k"
                ),
            },
        ],
    },
    {
        "act_number": 2,
        "title": "Because Catapults Failed: The 27-Foot Monster Cannon",
        "historical_date": "April 6–18, 1453",
        "shots": [
            {
                "shot_id": "act02_shot01",
                "causal_step": "BECAUSE WALLS WERE TOO THICK -> BUILD A GIANT CANNON",
                "shot_type": "Macro Detail",
                "motion": "push_in",
                "narration": (
                    "Even with only seven thousand men, the defenders felt safe because no catapult in history could break their forty-foot walls. "
                    "So Sultan Mehmed hired an engineer named Urban to build a twenty-seven-foot bronze monster cannon."
                ),
                "prompt": (
                    "16:9 dramatic close-up of the colossal 27-foot bronze Basilica cannon resting on heavy oak timbers outside "
                    "Constantinople, Ottoman artillerymen loading a massive round granite boulder into the barrel, 8k"
                ),
            },
            {
                "shot_id": "act02_shot02",
                "causal_step": "THE CANNON FIRES -> WALLS SHATTER",
                "shot_type": "Wide Establishing",
                "motion": "pull_out",
                "narration": (
                    "When this giant cannon fired, the explosion shook the ground for two miles, "
                    "and its twelve-hundred-pound stone ball smashed huge sections of the ancient wall into dust."
                ),
                "prompt": (
                    "16:9 action shot of the giant bronze cannon firing with a massive orange fireball and thick white smoke, "
                    "a huge stone cannonball smashing directly into a stone fortress tower and sending rocks flying, 8k"
                ),
            },
            {
                "shot_id": "act02_shot03",
                "causal_step": "BUT THE CANNON HAD A FLAW -> DEFENDERS REBUILD OVERNIGHT",
                "shot_type": "Medium Troop",
                "motion": "pan_right",
                "narration": (
                    "But the giant cannon had a huge problem: the bronze barrel got so hot that it took three hours to cool down and reload. "
                    "Because it could only fire seven times a day, the city's citizens ran out every night with barrels of dirt and wood to plug the holes before morning."
                ),
                "prompt": (
                    "16:9 night scene illuminated by torches showing Byzantine men and women frantically stacking wooden barrels "
                    "filled with earth and broken stones to repair a gap in the ruined castle wall before dawn, 8k"
                ),
            },
        ],
    },
    {
        "act_number": 3,
        "title": "Because the Harbor Was Blocked: Sailing 70 Ships Across a Mountain",
        "historical_date": "April 20–22, 1453",
        "shots": [
            {
                "shot_id": "act03_shot01",
                "causal_step": "BECAUSE LAND ATTACK STALLED -> LOOK TO THE HARBOR CHAIN",
                "shot_type": "Wide Establishing",
                "motion": "push_in",
                "narration": (
                    "Because attacking the thick land walls wasn't working, Mehmed realized he needed to attack the northern harbor, where the city wall was thin and weak. "
                    "But the defenders had stretched a giant floating iron chain across the harbor entrance, blocking every Ottoman ship from sailing in."
                ),
                "prompt": (
                    "16:9 wide shot looking across the blue water of the Golden Horn harbor entrance where a massive heavy iron chain "
                    "supported by wooden log floats stretches from tower to tower, blocking Ottoman warships outside, 8k"
                ),
            },
            {
                "shot_id": "act03_shot02",
                "causal_step": "SO MEHMED GOES OVER THE HILL ON GREASED LOGS",
                "shot_type": "Tactical Map",
                "motion": "pan_right",
                "narration": (
                    "Because his ships couldn't go through the iron chain, Mehmed decided to go around it across dry land. "
                    "On the night of April twenty-first, thousands of workers built a two-mile road of wooden logs over the steep hill behind the chain and greased the wood with animal fat."
                ),
                "prompt": (
                    "16:9 animated overland transit map of Galata hill showing the iron chain blocking the harbor mouth "
                    "and a glowing red path going up and over the land ridge into the Golden Horn water behind the chain"
                ),
            },
            {
                "shot_id": "act03_shot03",
                "causal_step": "AND AS A RESULT -> 70 SHIPS APPEAR INSIDE THE HARBOR",
                "shot_type": "Wide Establishing",
                "motion": "pull_out",
                "narration": (
                    "Using teams of oxen and hundreds of soldiers pulling ropes, they dragged seventy warships up and over the hill in a single night. "
                    "When the defenders woke up the next morning, they were horrified to see an entire enemy fleet floating inside their safe harbor."
                ),
                "prompt": (
                    "16:9 dramatic dawn shot from atop the city walls of Constantinople looking down in shock as seventy Ottoman "
                    "warships with red sails float calmly inside the Golden Horn harbor right beneath the city walls, 8k"
                ),
            },
            {
                "shot_id": "act03_shot04",
                "causal_step": "THEREFORE -> DEFENDERS ARE STRETCHED TOO THIN",
                "shot_type": "Primary Source",
                "motion": "push_in",
                "narration": (
                    "Because the harbor wall was now in danger, the Emperor was forced to pull soldiers away from the main land walls to guard the water. "
                    "His tiny army was now stretched to the breaking point."
                ),
                "prompt": (
                    "16:9 primary source parchment callout of Venetian eyewitness Niccolo Barbaro's 1453 diary describing the fleet "
                    "crossing the mountain into the harbor, warm candlelight"
                ),
            },
        ],
    },
    {
        "act_number": 4,
        "title": "The Final Twist: One Unlocked Door Ends a 1,500-Year Empire",
        "historical_date": "May 29, 1453",
        "shots": [
            {
                "shot_id": "act04_shot01",
                "causal_step": "DAY 53 -> THE FINAL DAWN ASSAULT BEGINS",
                "shot_type": "Wide Establishing",
                "motion": "push_in",
                "narration": (
                    "By Day fifty-three, on May twenty-ninth, Mehmed knew the defenders were exhausted and out of supplies. "
                    "Before sunrise, he ordered an all-out attack against both the land walls and the harbor at the exact same time."
                ),
                "prompt": (
                    "16:9 epic pre-dawn battle shot of thousands of Ottoman Janissary troops charging with scaling ladders and torches "
                    "toward the burning stone breach of Constantinople's walls, smoke and fire filling the sky, 8k"
                ),
            },
            {
                "shot_id": "act04_shot02",
                "causal_step": "DEFENDERS HOLD TWO WAVES -> BUT A SMALL DOOR IS LEFT UNLOCKED",
                "shot_type": "Macro Detail",
                "motion": "push_in",
                "narration": (
                    "For two hours, the defenders fought bravely and pushed back two huge waves of attackers. "
                    "But in the chaos, a retreating group of soldiers made one fatal mistake: they forgot to lock a tiny side door in the wall called the Kerkoporta."
                ),
                "prompt": (
                    "16:9 suspenseful close-up shot of a small heavy oak wooden postern door set into the base of a massive "
                    "stone fortress wall standing slightly ajar in the morning smoke, iron bolt left unlatched, 8k"
                ),
            },
            {
                "shot_id": "act04_shot03",
                "causal_step": "BECAUSE THE DOOR WAS OPEN -> ENEMY FLAG RAISED ON THE TOWER",
                "shot_type": "Medium Troop",
                "motion": "pan_left_up",
                "narration": (
                    "Fifty Ottoman soldiers spotted the unlocked door, rushed inside, climbed to the top of the tower, and raised the Ottoman flag. "
                    "When the defenders fighting below looked up and saw the enemy flag flying above them, they panicked and shouted that the city had fallen."
                ),
                "prompt": (
                    "16:9 dramatic low-angle shot of Ottoman soldiers atop a high stone watchtower raising a crimson silk banner "
                    "against the smoky dawn sky while defenders below look up in shock, 8k"
                ),
            },
            {
                "shot_id": "act04_shot04",
                "causal_step": "THE EMPEROR'S LAST CHARGE -> THE CITY FALLS",
                "shot_type": "Medium Troop",
                "motion": "pull_out",
                "narration": (
                    "Seeing the line collapse, Emperor Constantine tore off his royal purple cape so nobody would recognize him, "
                    "charged into the battle like an ordinary soldier, and was never seen alive again."
                ),
                "prompt": (
                    "16:9 emotional cinematic medium shot of Byzantine Emperor Constantine XI dropping his purple royal cloak "
                    "into the mud and drawing his sword to charge into the smoky breach beside his last loyal guards, 8k"
                ),
            },
            {
                "shot_id": "act04_shot05",
                "causal_step": "THE ENDING & WHY IT CHANGED THE WORLD FOREVER",
                "shot_type": "Wide Establishing",
                "motion": "push_in",
                "narration": (
                    "By noon, Sultan Mehmed rode through the gates into the city. Because Constantinople had fallen, the fifteen-hundred-year-old "
                    "Roman Empire ended forever, the trade routes to Asia were closed, and European explorers were forced to sail west across the Atlantic—leading "
                    "directly to the discovery of the Americas."
                ),
                "prompt": (
                    "16:9 majestic cinematic wide shot of young Sultan Mehmed II riding his white horse into the grand sunlit square "
                    "before the towering dome of Hagia Sophia as dust settles over Constantinople, photorealistic 8k"
                ),
            },
        ],
    },
]

CONSTANTINOPLE_TEST_SHORT = {
    "short_id": "test_short_constantinople_ships",
    "title": "How a 21-Year-Old Sailed 70 Warships Across a Mountain (1453)",
    "beats": [
        {
            "beat_id": "cut_01",
            "causal_role": "Cut 1 (0:00–0:03 • Portrait)",
            "narration": "In 1453, Sultan Mehmed attacked Constantinople.",
            "prompt": "9:16 vertical cinematic medium close-up portrait of 21-year-old Ottoman Sultan Mehmed II, intense dark eyes, neatly trimmed dark beard, wearing an elaborate gold-embroidered crimson velvet kaftan and traditional 15th-century Ottoman royal turban with jewel brooch, early morning golden sunlight, soft atmospheric mist, photorealistic 8k, 35mm film still, historical authenticity 1453",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_02",
            "causal_role": "Cut 2 (0:03–0:07 • The Fortress)",
            "narration": "Twenty-three armies had failed to take it for a thousand years.",
            "prompt": "9:16 vertical wide establishing shot of the colossal medieval Theodosian limestone fortress walls of Constantinople rising out of dawn mist, deep stone-lined moat filled with water in foreground, dramatic dark storm clouds, photorealistic 8k, historical authenticity 1453, cinematic depth",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_03",
            "causal_role": "Cut 3 (0:07–0:11 • Defenders)",
            "narration": "Only seven thousand defenders faced eighty thousand Ottoman troops.",
            "prompt": "9:16 vertical high-angle shot from stone battlements looking down, five Byzantine guards in iron conical helmets and weathered scale armor clutching spears, looking down anxiously at thousands of red Ottoman army tents filling the grassy horizon, dramatic lighting, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_04",
            "causal_role": "Cut 4 (0:11–0:14 • Useless Catapult)",
            "narration": "Catapults shattered against forty-foot walls with zero damage.",
            "prompt": "9:16 vertical dynamic action shot of a heavy medieval wooden trebuchet catapult arm slamming forward on a muddy battlefield, throwing a boulder that shatters against a colossal 40-foot stone castle wall with zero damage, dust flying, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_05",
            "causal_role": "Cut 5 (0:14–0:18 • The Monster Cannon)",
            "narration": "So Mehmed built a twenty-seven-foot supercannon to blast the stones.",
            "prompt": "9:16 vertical dramatic low-angle shot of the 27-foot bronze Basilica supercannon resting on heavy oak beam carriages outside the fortress, medieval Ottoman artillerymen using iron levers and hemp ropes to load a giant round 1,200-pound granite boulder into the bronze muzzle, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_06",
            "causal_role": "Cut 6 (0:18–0:21 • Blast & Impact)",
            "narration": "The blast blew huge breaches straight through the outer towers.",
            "prompt": "9:16 vertical violent explosion shot of a colossal bronze cannon firing toward a stone castle tower, massive orange fireball with thick billowing black smoke, stone masonry exploding into flying rock shards, photorealistic 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_07",
            "causal_role": "Cut 7 (0:21–0:25 • Nighttime Rebuild)",
            "narration": "Yet reloading took three hours, so citizens rebuilt the walls every night.",
            "prompt": "9:16 vertical night scene lit by orange torchlight, Byzantine soldiers and citizens frantically stacking heavy wooden barrels packed with earth and broken stone blocks into a smoking breach in the fortress wall before dawn, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_08",
            "causal_role": "Cut 8 (0:25–0:28 • The Weak Sea Wall)",
            "narration": "With the land attack stalled, Mehmed eyed the weaker sea walls.",
            "prompt": "9:16 vertical panoramic view looking down across the quiet blue water of the Golden Horn harbor toward the thin low medieval stone sea-walls of Constantinople, no modern structures, ancient tiled roofs, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_09",
            "causal_role": "Cut 9 (0:28–0:32 • The Great Iron Chain)",
            "narration": "But a colossal iron chain blocked his fleet from the harbor.",
            "prompt": "9:16 vertical close-up of massive forged iron chain links supported by weathered floating wooden timber logs stretching across blue harbor water, blocking distant 15th-century wooden rowed galleys from entering, water splashing on rust, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_10",
            "causal_role": "Cut 10 (0:32–0:36 • Tactical Blockade)",
            "narration": "Trapped outside, his navy could not strike the city's rear.",
            "prompt": "9:16 vertical top-down illustrated tactical parchment map of the Constantinople peninsula showing the Golden Horn entrance blocked by a heavy red spiked chain barrier, ancient ink calligraphy, compass rose, dramatic candlelight",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_11",
            "causal_role": "Cut 11 (0:36–0:40 • Greased Log Road)",
            "narration": "So Mehmed laid greased timber logs across the mountain.",
            "prompt": "9:16 vertical night shot on a steep muddy wooded ridge lit by torches, Ottoman workers pouring wooden buckets of glistening animal fat over thousands of smoothed timber tree trunks laid side-by-side like a wooden rail road climbing up a hill, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_12",
            "causal_role": "Cut 12 (0:40–0:44 • The Warship on Land — The Climax)",
            "narration": "Oxen and soldiers dragged seventy warships over dry land.",
            "prompt": "9:16 vertical dramatic cinematic night shot of a massive 15th-century wooden Ottoman warship with furled sails sitting upright on heavy greased timber log rollers, being pulled uphill across a muddy forest slope by teams of black oxen and hundreds of straining soldiers pulling thick ropes, glowing torches, photorealistic 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_13",
            "causal_role": "Cut 13 (0:44–0:48 • Cresting the Mountain)",
            "narration": "By midnight, the fleet crested the peak and plunged into the bay.",
            "prompt": "9:16 vertical low-angle silhouette shot of the wooden warship bow cresting the high summit of Galata hill at midnight under a starry crescent moon sky, soldiers cheering with torches, breathtaking scale, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_14",
            "causal_role": "Cut 14 (0:48–0:54 • Fleet in Harbor — Zero Modern Boats)",
            "narration": "At dawn, defenders were horrified to see seventy enemy warships inside their harbor.",
            "prompt": "9:16 vertical dawn shot from atop the medieval stone city walls looking down in shock at seventy 15th-century wooden oared galleys with Ottoman crimson crescent flags floating calmly inside the Golden Horn harbor beneath the dome of Hagia Sophia, completely medieval wooden ships with oars, zero modern boats, zero cruise ships, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        },
        {
            "beat_id": "cut_15",
            "causal_role": "Cut 15 (0:54–1:00 • The Final Breach)",
            "narration": "Surrounded on two fronts, the line broke, and Rome fell forever.",
            "prompt": "9:16 vertical emotional cinematic medium shot of Byzantine Emperor Constantine XI throwing his imperial purple cloak into the mud and drawing an iron sword to lead his final guard into the smoky breach, morning sun piercing dust clouds, historical authenticity 1453, 8k",
            "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
            "tts_rate": "+15%"
        }
    ],
}


def build_causal_test_json() -> dict:
    all_shots = []
    acts_out = []
    for act in CONSTANTINOPLE_CAUSAL_ACTS:
        act_script = " ".join(s["narration"] for s in act["shots"])
        shots_formatted = []
        for s in act["shots"]:
            shot_entry = {
                "shot_id": s["shot_id"],
                "causal_step": s["causal_step"],
                "shot_type": s["shot_type"],
                "motion": s["motion"],
                "narration": s["narration"],
                "prompt": s["prompt"],
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "event_slug": "constantinople_1453",
                "act_number": act["act_number"],
                "act_title": act["title"],
                "historical_date": act["historical_date"],
            }
            shots_formatted.append(shot_entry)
            all_shots.append(shot_entry)

        acts_out.append({
            "act_number": act["act_number"],
            "title": act["title"],
            "historical_date": act["historical_date"],
            "script": act_script,
            "shots": shots_formatted,
        })

    total_words = sum(len(s["narration"].split()) for s in all_shots)
    return {
        "channel": "Chronos Shift (@ChronosShiftHistory)",
        "video_title": "How a 21-Year-Old Conquered the Unbreakable City: Constantinople (1453)",
        "event_slug": "constantinople_1453",
        "mode": "factual_causal_sync",
        "sync_mode": "per_shot_narration",
        "bgm_mode": "clean_voice_or_subbass_only",
        "aspect_ratio": "16:9",
        "total_word_count": total_words,
        "total_visual_shots": len(all_shots),
        "acts": acts_out,
        "standalone_short_test": CONSTANTINOPLE_TEST_SHORT,
    }


def main():
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = DRAFTS_DIR / "constantinople_1453_causal_test.json"
    payload = build_causal_test_json()
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(
        f"[OK] Wrote {out_file.name}: {len(payload['acts'])} causal acts, "
        f"{payload['total_visual_shots']} synced audio-visual shots, "
        f"{payload['total_word_count']} words, plus 5-beat standalone Short test."
    )


if __name__ == "__main__":
    main()