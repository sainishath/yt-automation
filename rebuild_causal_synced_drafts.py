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
    "modern clothing, wristwatches, eyeglasses, neon, sci-fi armor, "
    "mandalorian helmet, star wars, futuristic visor, glowing HUD, "
    "gibberish text, random letters, watermark, signature, logo, "
    "split screen, multi-panel grid, comic strip panels, collage, "
    "cartoon, anime, 3d render plastic, lowres, blurry, deformed hands, extra fingers"
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
            "beat_id": "short_beat_01",
            "causal_role": "1. CLEAR SETUP (What is this about?)",
            "narration": (
                "In 1453, a twenty-one-year-old Sultan named Mehmed tried to conquer Constantinople—a fortress city "
                "that twenty-three armies had failed to break for a thousand years."
            ),
            "prompt": (
                "9:16 vertical cinematic close-up of 21-year-old Ottoman Sultan Mehmed II staring at the towering stone walls "
                "of Constantinople across the water at dawn, photorealistic 8k"
            ),
        },
        {
            "beat_id": "short_beat_02",
            "causal_role": "2. CAUSE -> EFFECT (Why the cannon wasn't enough)",
            "narration": (
                "Because normal catapults couldn't break the city's forty-foot walls, Mehmed built a giant twenty-seven-foot cannon. "
                "But the cannon took three hours to reload, so the defenders simply rebuilt the wall every single night."
            ),
            "prompt": (
                "9:16 vertical action shot of a massive 27-foot bronze cannon firing a huge stone boulder at a stone castle wall "
                "in a cloud of fire and smoke, photorealistic 8k"
            ),
        },
        {
            "beat_id": "short_beat_03",
            "causal_role": "3. THE OBSTACLE (The Giant Iron Chain)",
            "narration": (
                "Because attacking from the land wasn't working, Mehmed needed to sail his warships into the city's weak harbor. "
                "But the Romans had stretched a giant floating iron chain across the water that blocked every ship."
            ),
            "prompt": (
                "9:16 vertical shot of a massive heavy iron chain floating on wooden logs across a blue harbor entrance, "
                "blocking wooden warships from entering, 8k"
            ),
        },
        {
            "beat_id": "short_beat_04",
            "causal_role": "4. THE CLEVER SOLUTION (70 Ships Over Dry Land)",
            "narration": (
                "So Mehmed did the impossible. In one night, his men greased thousands of wooden logs with animal fat "
                "and used oxen to drag seventy warships for two miles over a steep mountain right behind the chain."
            ),
            "prompt": (
                "9:16 vertical dramatic night shot of hundreds of soldiers and oxen pulling a giant wooden warship on greased "
                "wooden logs up a muddy hillside lit by glowing torches, 8k"
            ),
        },
        {
            "beat_id": "short_beat_05",
            "causal_role": "5. THE ENDING (Why the city fell)",
            "narration": (
                "Because seventy enemy ships suddenly appeared inside their safe harbor, the defenders had to split their tiny army in half. "
                "Days later, the walls were overwhelmed, and the fifteen-hundred-year-old Roman Empire ended forever."
            ),
            "prompt": (
                "9:16 vertical dawn shot from the city walls looking down at seventy Ottoman warships floating inside the Golden Horn "
                "harbor beneath the dome of Hagia Sophia, 8k"
            ),
        },
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