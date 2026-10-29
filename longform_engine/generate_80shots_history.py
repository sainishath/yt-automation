# -*- coding: utf-8 -*-
"""
generate_80shots_history.py
---------------------------
Generates the complete 80-shot visual architecture for "The Fall of Constantinople (1453)".
Divides the 7 acts into 11-12 distinct visual beats each (~7.1 to 7.5 seconds per cut).
Ensures diverse visual taxonomy:
  - Wide landscape establishing shots
  - Medium character & troop formations
  - Macro weapon & architectural details
  - Tactical parchment siege maps
  - Atmospheric smoke, fire & lighting
Saves to longform_engine/drafts/history_10min_80shots.json
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT_DIR / "longform_engine" / "drafts" / "history_10min_80shots.json"

# Load existing base script
BASE_JSON = ROOT_DIR / "longform_engine" / "drafts" / "history_10min_v1.json"
with open(BASE_JSON, "r", encoding="utf-8") as f:
    base_data = json.load(f)

# Define the 80 detailed shots across the 7 acts
ACTS_80_SHOTS = [
    # ── Act 1: The Setting: The Millennium-Old Theodosian Walls ───────────────
    {
        "act_number": 1,
        "title": "The Setting: The Millennium-Old Theodosian Walls and a Dying Empire",
        "shots": [
            {
                "shot_id": "act01_shot01",
                "shot_type": "Wide Establishing",
                "motion": "push_in",
                "prompt": "16:9 majestic wide-angle cinematic shot of the towering tripartite Theodosian stone walls of Constantinople rising out of dense morning spring mist, flooded moat, Roman defensive battlements under a dramatic stormy sky, photorealistic 8k, oil painting undertones, historical accuracy 1453"
            },
            {
                "shot_id": "act01_shot02",
                "shot_type": "Tactical Map",
                "motion": "pan_right",
                "prompt": "16:9 top-down parchment tactical siege map of Constantinople peninsula in 1453, showing the Golden Horn, Sea of Marmara, and the four-mile land wall barrier, aged vellum texture, antique ink calligraphy, compass rose, dramatic candlelight illumination"
            },
            {
                "shot_id": "act01_shot03",
                "shot_type": "Medium Troop",
                "motion": "pull_out",
                "prompt": "16:9 cinematic medium shot of Byzantine sentries in iron conical helmets and weathered lamellar armor standing watch atop high stone battlements, gazing out into the misty horizon with solemn tense expressions"
            },
            {
                "shot_id": "act01_shot04",
                "shot_type": "Atmospheric Landscape",
                "motion": "pan_left_up",
                "prompt": "16:9 aerial panoramic shot looking down into the deep sixty-foot wide stone-lined flooded moat outside Constantinople, muddy water reflecting grey clouds, sharpened wooden stakes protruding along the breastwork"
            },
            {
                "shot_id": "act01_shot05",
                "shot_type": "Macro Detail",
                "motion": "push_in",
                "prompt": "16:9 extreme close-up macro of weathered fifth-century Roman limestone bricks bonded with crimson pozzolanic mortar, showing ancient chisel marks, moss, and repaired siege cracks from centuries past"
            },
            {
                "shot_id": "act01_shot06",
                "shot_type": "Wide Urban",
                "motion": "pan_right",
                "prompt": "16:9 desolate street view inside Constantinople in April 1453, sparse citizens in medieval cloaks walking past decaying classical marble colonnades and overgrown Roman ruins, melancholic atmospheric lighting"
            },
            {
                "shot_id": "act01_shot07",
                "shot_type": "Interior Sacred",
                "motion": "pull_out",
                "prompt": "16:9 awe-inspiring cinematic interior of Hagia Sophia cathedral, soaring dome with gold mosaic icons catching ethereal dust-mote sunbeams streaming through high arched clerestory windows, solemn silence"
            },
            {
                "shot_id": "act01_shot08",
                "shot_type": "Heroic Portrait",
                "motion": "push_in",
                "prompt": "16:9 dramatic cinematic portrait of Byzantine Emperor Constantine XI Palaiologos, 49 years old, wearing gilded Roman lamellar armor and deep imperial purple mantle, intense dignified eyes, heavy beard, wind blowing"
            },
            {
                "shot_id": "act01_shot09",
                "shot_type": "Architectural Detail",
                "motion": "pan_right",
                "prompt": "16:9 imposing stone bastion tower of the inner Theodosian wall, double-headed eagle Byzantine standard fluttering proudly in the sea wind against an approaching dark squall line"
            },
            {
                "shot_id": "act01_shot10",
                "shot_type": "Atmospheric Sentry",
                "motion": "pan_left_up",
                "prompt": "16:9 silhouette of a lone Roman archer atop the highest fortress tower at dusk, looking toward the dark Thracian forest as distant black birds scatter into the stormy sky"
            },
            {
                "shot_id": "act01_shot11",
                "shot_type": "Climactic Wide",
                "motion": "pull_out",
                "prompt": "16:9 epic sweeping wide shot of the entire unbroken four-mile Theodosian wall system glowing in the last fiery amber rays of sunset, eternal fortress standing alone against the darkness"
            }
        ]
    },

    # ── Act 2: The Challenger: Sultan Mehmed II & The War Machine ──────────────
    {
        "act_number": 2,
        "title": "The Challenger: Sultan Mehmed II’s Ambition and the Ottoman War Machine",
        "shots": [
            {
                "shot_id": "act02_shot01",
                "shot_type": "Character Portrait",
                "motion": "push_in",
                "prompt": "16:9 imposing close-up portrait of Sultan Mehmed II, 21 years old, sharp calculating eyes, wearing a white silk turban with a gold jewel agraffe and crimson fur-lined kaftan, illuminated by flickering tent torches"
            },
            {
                "shot_id": "act02_shot02",
                "shot_type": "Tactical Study",
                "motion": "pan_right",
                "prompt": "16:9 overhead shot of Mehmed II leaning over a massive wooden table covered in architectural sketches of Constantinople's walls, holding brass dividers, surrounded by viziers in silk robes"
            },
            {
                "shot_id": "act02_shot03",
                "shot_type": "Fortress Architecture",
                "motion": "pull_out",
                "prompt": "16:9 cinematic shot of the newly completed fortress Rumeli Hisari on the steep forested banks of the Bosporus straits, massive grey stone towers guarding the narrow water channel, morning mist"
            },
            {
                "shot_id": "act02_shot04",
                "shot_type": "Naval Blockade",
                "motion": "pan_left_up",
                "prompt": "16:9 row of Ottoman cannons pointing from Rumeli Hisari battlements down at the rushing dark waters of the Bosporus, cutting off Black Sea trade ships"
            },
            {
                "shot_id": "act02_shot05",
                "shot_type": "Mass Gathering",
                "motion": "push_in",
                "prompt": "16:9 sprawling panoramic vista of the Ottoman military encampment outside Constantinople, eighty thousand soldiers, thousands of white canvas tents and red pavilions stretching to the horizon"
            },
            {
                "shot_id": "act02_shot06",
                "shot_type": "Elite Troops",
                "motion": "pan_right",
                "prompt": "16:9 ranks of disciplined Janissary infantry marching in strict formation, tall white bork capes with gold embroidery, holding recurve composite bows and heavy halberds, dust rising"
            },
            {
                "shot_id": "act02_shot07",
                "shot_type": "Cavalry Formation",
                "motion": "pull_out",
                "prompt": "16:9 Ottoman Sipahi heavy cavalry on armored Arabian stallions, pennants bearing crescent moons fluttering, galloping across the Thracian hills toward the siege lines"
            },
            {
                "shot_id": "act02_shot08",
                "shot_type": "Defender Contrast",
                "motion": "push_in",
                "prompt": "16:9 somber medium shot of Genoese mercenary captain Giovanni Giustiniani Longo inspecting his company of seven hundred Italian plate-armored crossbowmen inside the Roman courtyard"
            },
            {
                "shot_id": "act02_shot09",
                "shot_type": "Weapon Inspection",
                "motion": "pan_right",
                "prompt": "16:9 macro shot of a Genoese steel crossbow being spanned with a goat's foot lever, heavy iron-tipped quarrel loaded into the polished walnut groove"
            },
            {
                "shot_id": "act02_shot10",
                "shot_type": "Tactical Confrontation",
                "motion": "pan_left_up",
                "prompt": "16:9 dramatic telephoto lens shot from the Byzantine battlements looking across the clearing at the Ottoman advance guard deploying siege mantlets and red battle standards"
            },
            {
                "shot_id": "act02_shot11",
                "shot_type": "Atmospheric War Camp",
                "motion": "pull_out",
                "prompt": "16:9 twilight panorama of the siege lines, thousands of Ottoman cooking fires twinkling like stars across the plain, war horns sounding in the cold spring air"
            }
        ]
    },

    # ── Act 3: The Superweapon: Urban the Engineer & Basilic Cannons ──────────
    {
        "act_number": 3,
        "title": "The Superweapon: Urban the Engineer and the Massive Basilic Cannons",
        "shots": [
            {
                "shot_id": "act03_shot01",
                "shot_type": "Industrial Foundry",
                "motion": "push_in",
                "prompt": "16:9 intense interior shot of master founder Urban's cannon foundry in Edirne, glowing molten bronze being poured from a clay crucible into a massive underground casting mould, bright orange sparks"
            },
            {
                "shot_id": "act03_shot02",
                "shot_type": "Engineer Portrait",
                "motion": "pan_right",
                "prompt": "16:9 close-up portrait of Hungarian master cannon engineer Urban, soot-streaked face, leather apron, measuring the bronze barrel calipers with intense scientific focus"
            },
            {
                "shot_id": "act03_shot03",
                "shot_type": "Colossal Transport",
                "motion": "pull_out",
                "prompt": "16:9 epic wide shot of the twenty-six foot long Basilic bronze bombard mounted on heavy timber carriages, hauled by sixty oxen and two hundred laborers across the muddy plains of Thrace"
            },
            {
                "shot_id": "act03_shot04",
                "shot_type": "Macro Projectile",
                "motion": "push_in",
                "prompt": "16:9 macro detail shot of a carved twelve-hundred pound solid Black Sea granite cannonball, textured stone surface, sitting next to heavy oak powder barrels and iron measuring scales"
            },
            {
                "shot_id": "act03_shot05",
                "shot_type": "Gun Battery Position",
                "motion": "pan_left_up",
                "prompt": "16:9 massive timber earthwork battery constructed opposite the Roman Lycus valley walls, Ottoman master gunners loading black powder sacks with wooden rammers into the giant bronze cannon"
            },
            {
                "shot_id": "act03_shot06",
                "shot_type": "The Ignition",
                "motion": "push_in",
                "prompt": "16:9 tense dramatic close-up of an Ottoman gunner applying a glowing linstock match to the touch-hole of the Basilic bombard, smoke hissing before the detonation"
            },
            {
                "shot_id": "act03_shot07",
                "shot_type": "Cataclysmic Firing",
                "motion": "pull_out",
                "prompt": "16:9 explosive ultra-slow-motion blast as the Basilic cannon fires, massive fireball erupting from the muzzle, shockwave blowing back soldiers, dense black sulfur smoke engulfing the battery"
            },
            {
                "shot_id": "act03_shot08",
                "shot_type": "Flight of Projectile",
                "motion": "pan_right",
                "prompt": "16:9 dynamic cinematic tracking shot following the massive granite boulder tearing through the sky toward the ancient stone fortifications of Constantinople"
            },
            {
                "shot_id": "act03_shot09",
                "shot_type": "Impact & Demolition",
                "motion": "push_in",
                "prompt": "16:9 catastrophic impact as the 1200-pound granite stone shatters an ancient Roman stone tower, wall exploding into thousands of fragments, limestone dust billowing violently"
            },
            {
                "shot_id": "act03_shot10",
                "shot_type": "Defenders in Terror",
                "motion": "pull_out",
                "prompt": "16:9 Byzantine defenders on the ramparts coughing in white limestone dust, shielding their faces as masonry rains down, clutching iron shields amidst ringing ears"
            },
            {
                "shot_id": "act03_shot11",
                "shot_type": "Ruined Breach",
                "motion": "pan_left_up",
                "prompt": "16:9 wide shot of the smoking jagged breach along the Lycus River wall, ancient imperial towers transformed into shattered gravel piles, the illusion of invulnerability broken"
            }
        ]
    },

    # ── Act 4: The Naval Feat: Warships Over Land into Golden Horn ─────────────
    {
        "act_number": 4,
        "title": "The Naval Feat: Hauling Ottoman Warships Over Land into the Golden Horn",
        "shots": [
            {
                "shot_id": "act04_shot01",
                "shot_type": "Harbor Barrier",
                "motion": "push_in",
                "prompt": "16:9 atmospheric shot of the Great Boom Chain stretching across the mouth of the Golden Horn harbor, massive rusted wrought-iron links floating on wooden pontoons, blocking Ottoman galleys"
            },
            {
                "shot_id": "act04_shot02",
                "shot_type": "Naval Impasse",
                "motion": "pan_right",
                "prompt": "16:9 Byzantine and Venetian war galleys anchored securely inside the calm waters of the Golden Horn harbor, looking out at the frustrated Ottoman fleet outside the iron boom"
            },
            {
                "shot_id": "act04_shot03",
                "shot_type": "Tactical Revelation",
                "motion": "pull_out",
                "prompt": "16:9 Sultan Mehmed II standing on a hilltop in Galata at night, gesturing toward the forested ridge between the Bosporus and the harbor, surrounded by shipwrights holding torches"
            },
            {
                "shot_id": "act04_shot04",
                "shot_type": "Timber Road Engineering",
                "motion": "push_in",
                "prompt": "16:9 Ottoman engineers laying heavy greased timber rollers and wooden tracks across the rugged earthen hillside of Pera, smearing animal tallow along the wooden logs"
            },
            {
                "shot_id": "act04_shot05",
                "shot_type": "Overland Haul",
                "motion": "pan_left_up",
                "prompt": "16:9 epic moonlight spectacle of a wooden war galley with sails unfurled being hauled uphill over timber tracks by hundreds of shouting soldiers and teams of straining oxen, torches blazing"
            },
            {
                "shot_id": "act04_shot06",
                "shot_type": "Diversionary Barrage",
                "motion": "pull_out",
                "prompt": "16:9 night sky illuminated by flashes of diversionary Ottoman mortar fire striking the seawalls of Galata, masking the screeching sound of wooden rollers"
            },
            {
                "shot_id": "act04_shot07",
                "shot_type": "Crest of the Ridge",
                "motion": "push_in",
                "prompt": "16:9 dramatic low-angle shot of the prow of an Ottoman galley cresting the hill of Galata, silhouettes of oarsmen perched on gunwales under a silver crescent moon"
            },
            {
                "shot_id": "act04_shot08",
                "shot_type": "Harbor Splashdown",
                "motion": "pan_right",
                "prompt": "16:9 dawn shot of an Ottoman warship sliding down the wooden ramp and splashing into the glassy green waters of the Golden Horn, wake spreading toward the city walls"
            },
            {
                "shot_id": "act04_shot09",
                "shot_type": "Byzantine Lookout Shock",
                "motion": "pull_out",
                "prompt": "16:9 Byzantine sentry on the northern harbor ramparts rubbing his eyes in horror as morning fog clears to reveal seventy Ottoman galleys anchored beneath the vulnerable sea wall"
            },
            {
                "shot_id": "act04_shot10",
                "shot_type": "Alarm Bells",
                "motion": "push_in",
                "prompt": "16:9 church bells of Constantinople swinging violently in stone belfries, bronze clappers striking in frantic cadence as flock of pigeons take flight in panic"
            },
            {
                "shot_id": "act04_shot11",
                "shot_type": "Divided Defense",
                "motion": "pan_left_up",
                "prompt": "16:9 Emperor Constantine XI directing small detachments of exhausted soldiers to split away from the main land wall, spreading the thin defense across miles of northern sea battlements"
            }
        ]
    },

    # ── Act 5: The Siege Grinds: Sappers, Counter-Mines, Greek Fire ───────────
    {
        "act_number": 5,
        "title": "The Siege Grinds: Sappers, Counter-Mines, and Greek Fire",
        "shots": [
            {
                "shot_id": "act05_shot01",
                "shot_type": "Night Reconstruction",
                "motion": "push_in",
                "prompt": "16:9 frantic nighttime scene at the breached walls, Byzantine civilians, priests, and women hauling wicker baskets of earth, timber logs, and gravel to rebuild palisades under fire"
            },
            {
                "shot_id": "act05_shot02",
                "shot_type": "Subterranean Shaft",
                "motion": "pan_right",
                "prompt": "16:9 claustrophobic mining tunnel beneath the earth, Serbian sappers in loincloths chipping through limestone bedrock by the dim orange glow of tallow candles, wooden props supporting the ceiling"
            },
            {
                "shot_id": "act05_shot03",
                "shot_type": "Acoustic Detection",
                "motion": "pull_out",
                "prompt": "16:9 Scottish mercenary engineer John Grant kneeling on the cellar floor inside the wall, staring intently at a polished copper bowl of water showing rhythmic circular vibration ripples"
            },
            {
                "shot_id": "act05_shot04",
                "shot_type": "Counter-Mine Digging",
                "motion": "push_in",
                "prompt": "16:9 Byzantine counter-miners digging furiously into the dirt wall, pickaxes striking sparks, suddenly breaking through into an enemy subterranean shaft with a burst of air"
            },
            {
                "shot_id": "act05_shot05",
                "shot_type": "Subterranean Combat",
                "motion": "pan_left_up",
                "prompt": "16:9 brutal hand-to-hand fight in the suffocating darkness of a narrow mining gallery, Byzantine soldiers and Ottoman miners clashing with picks, daggers, and wooden clubs"
            },
            {
                "shot_id": "act05_shot06",
                "shot_type": "Greek Fire Preparation",
                "motion": "push_in",
                "prompt": "16:9 Byzantine engineer pressurizing a heavy bronze siphon cylinder with hand bellows, viscous petroleum and sulfur liquid bubbling through bronze pipes"
            },
            {
                "shot_id": "act05_shot07",
                "shot_type": "Greek Fire Eruption",
                "motion": "pull_out",
                "prompt": "16:9 terrifying jet of liquid Greek Fire spewing from the bronze nozzle, roaring sheet of emerald-green and gold chemical flame illuminating the subterranean tunnel and burning upon dirt walls"
            },
            {
                "shot_id": "act05_shot08",
                "shot_type": "Tunnel Collapse",
                "motion": "pan_right",
                "prompt": "16:9 burning timber props splintering and giving way under intense fire, tons of earth and stone crashing down into the subterranean shaft, suffocating the Ottoman mining operation"
            },
            {
                "shot_id": "act05_shot09",
                "shot_type": "Exhausted Hero",
                "motion": "push_in",
                "prompt": "16:9 soot-covered Scottish engineer John Grant emerging from a stone cellar trapdoor onto the daylight ramparts, wiping sweat and blood from his forehead, breathing heavily"
            },
            {
                "shot_id": "act05_shot10",
                "shot_type": "Famine & Scarcity",
                "motion": "pull_out",
                "prompt": "16:9 grim interior of a Byzantine storehouse, empty grain bins and crying children clutching hollow crusts of bread, despair etched into gaunt sunken faces"
            },
            {
                "shot_id": "act05_shot11",
                "shot_type": "The Relentless Clock",
                "motion": "pan_left_up",
                "prompt": "16:9 view of the battered land wall at mid-May twilight, smoke rising continuously from smoldering wooden palisades, the defensive line hanging by a thread"
            }
        ]
    },

    # ── Act 6: The Final Breach: May 29, 1453 ─────────────────────────────────
    {
        "act_number": 6,
        "title": "The Final Breach: May 29, 1453, and the Fall of the Imperial Gate",
        "shots": [
            {
                "shot_id": "act06_shot01",
                "shot_type": "Candlelight Procession",
                "motion": "push_in",
                "prompt": "16:9 solemn midnight procession on May 28 through the streets of Constantinople, Greek Orthodox priests and Latin Catholic bishops carrying sacred gold icons together in candlelight"
            },
            {
                "shot_id": "act06_shot02",
                "shot_type": "Final Liturgy",
                "motion": "pull_out",
                "prompt": "16:9 emotional panorama inside Hagia Sophia, thousands of citizens weeping and embracing, Emperor Constantine taking the holy communion in the great church for the final time"
            },
            {
                "shot_id": "act06_shot03",
                "shot_type": "Midnight Assault",
                "motion": "push_in",
                "prompt": "16:9 pitch-black night suddenly illuminated by hundreds of Ottoman siege flares and war torches, thousands of irregular bashi-bazouk fighters charging the shattered Lycus valley breach"
            },
            {
                "shot_id": "act06_shot04",
                "shot_type": "Desperate Defense",
                "motion": "pan_right",
                "prompt": "16:9 ferocious combat on the earthwork barricades, Genoese and Byzantine soldiers thrusting spears and discharging crossbows down into the surging Ottoman assault waves"
            },
            {
                "shot_id": "act06_shot05",
                "shot_type": "Janissary Vanguard",
                "motion": "pull_out",
                "prompt": "16:9 Sultan Mehmed II signaling his fresh elite Janissaries, ranks of towering soldiers advancing shoulder-to-shoulder with drawn curved kilij swords through the smoke"
            },
            {
                "shot_id": "act06_shot06",
                "shot_type": "The Fatal Wound",
                "motion": "push_in",
                "prompt": "16:9 tragic slow-motion moment as Genoese general Giovanni Giustiniani Longo is struck in the breastplate by an iron crossbow bolt, blood blooming on polished steel"
            },
            {
                "shot_id": "act06_shot07",
                "shot_type": "Panic Spreads",
                "motion": "pan_left_up",
                "prompt": "16:9 Giustiniani being carried toward the harbor by weeping Genoese retainers, defensive ranks wavering as Italian soldiers abandon the inner stockade in confusion"
            },
            {
                "shot_id": "act06_shot08",
                "shot_type": "The Unlocked Postern",
                "motion": "push_in",
                "prompt": "16:9 low-angle shot of the small sunken stone postern gate—the Kerkoporta—ajar in the northern wall, Ottoman skirmishers peeking through and realizing it is unlocked"
            },
            {
                "shot_id": "act06_shot09",
                "shot_type": "The Crescent Rises",
                "motion": "pull_out",
                "prompt": "16:9 Ottoman soldiers swarming up the spiral stone stairs of the Kerkoporta tower, unfurling a red banner bearing the crescent moon over the high battlements"
            },
            {
                "shot_id": "act06_shot10",
                "shot_type": "Emperor's Last Stand",
                "motion": "push_in",
                "prompt": "16:9 iconic heroic shot of Emperor Constantine XI tearing off his gilded imperial insignia and purple cloak, drawing his double-edged spatha sword, and charging into the breach"
            },
            {
                "shot_id": "act06_shot11",
                "shot_type": "The Fall of Rome",
                "motion": "pan_right",
                "prompt": "16:9 sunrise breaking through thick black battlefield smoke over the breached walls of Constantinople, Ottoman forces flooding through the ruins, the Roman Empire fading into history"
            }
        ]
    },

    # ── Act 7: The Legacy: Scholars & Dawn of Renaissance ─────────────────────
    {
        "act_number": 7,
        "title": "The Legacy: The Exodus of Greek Scholars and the Dawn of the Renaissance",
        "shots": [
            {
                "shot_id": "act07_shot01",
                "shot_type": "The Conqueror's Entry",
                "motion": "push_in",
                "prompt": "16:9 Sultan Mehmed the Conqueror riding a majestic white stallion through the Bronze Gate into the captured city of Constantinople, escort of viziers and Janissary honor guards"
            },
            {
                "shot_id": "act07_shot02",
                "shot_type": "Sanctuary Preserved",
                "motion": "pull_out",
                "prompt": "16:9 Mehmed II standing beneath the monumental dome of Hagia Sophia, bending down to touch marble dust to his turban in reverence, ordering the grand basilica preserved as an imperial mosque"
            },
            {
                "shot_id": "act07_shot03",
                "shot_type": "Exodus at Sea",
                "motion": "pan_right",
                "prompt": "16:9 Italian merchant galleys sailing away from Constantinople into the Sea of Marmara at dusk, sails billowing, smoke rising on the distant horizon behind them"
            },
            {
                "shot_id": "act07_shot04",
                "shot_type": "Rescued Knowledge",
                "motion": "push_in",
                "prompt": "16:9 Greek scholars on the deck of a rolling wooden ship, carefully clutching leather-bound manuscript chests containing original ancient scrolls of Plato, Aristotle, and Euclid"
            },
            {
                "shot_id": "act07_shot05",
                "shot_type": "Arrival in Italy",
                "motion": "pull_out",
                "prompt": "16:9 arrival of Byzantine scholars at the stone docks of Venice, Italian scholars in velvet cloaks eagerly greeting them, unloading wooden crates of Greek classical philosophy"
            },
            {
                "shot_id": "act07_shot06",
                "shot_type": "Florentine Academy",
                "motion": "pan_left_up",
                "prompt": "16:9 interior of the Platonic Academy in Florence under warm candlelight, Italian humanist scholars and artists gathered around an open Greek codex, the spark of the Renaissance"
            },
            {
                "shot_id": "act07_shot07",
                "shot_type": "Trade Route Severed",
                "motion": "push_in",
                "prompt": "16:9 silhouette of an Ottoman customs outpost along the spice road trade route in Anatolia, European trade caravans turning back from high tariffs"
            },
            {
                "shot_id": "act07_shot08",
                "shot_type": "The Call to the Sea",
                "motion": "pull_out",
                "prompt": "16:9 Portuguese and Spanish navigators in Lisbon studying navigational charts and astrolabes by lanterns, looking westward toward the vast unexplored Atlantic Ocean"
            },
            {
                "shot_id": "act07_shot09",
                "shot_type": "Caravels at Dawn",
                "motion": "pan_right",
                "prompt": "16:9 three 15th-century caravels with cross-marked sails setting voyage across golden morning ocean waves, embarking on the Age of Discovery"
            },
            {
                "shot_id": "act07_shot10",
                "shot_type": "Ancient to Modern",
                "motion": "push_in",
                "prompt": "16:9 evocative split-screen composition: left shows the ancient weathered stone ruins of Constantinople's walls; right shows the bustling dome of the Florence Cathedral under a golden sky"
            },
            {
                "shot_id": "act07_shot11",
                "shot_type": "Monumental Finale",
                "motion": "pull_out",
                "prompt": "16:9 cinematic closing aerial view of Istanbul and the Bosporus at sunset, minarets and ancient domes silhouetted against a crimson sky, where the ancient world ended and the modern world began"
            }
        ]
    }
]

# Total shot count across all acts
total_shots = sum(len(a["shots"]) for a in ACTS_80_SHOTS)
print(f"Total Visual Shots Formatted: {total_shots} across 7 Acts")

# Merge into full 80-shot script payload
full_data = {
    "channel": base_data["channel"],
    "video_title": base_data["video_title"],
    "aspect_ratio": "16:9 (1920x1080 Widescreen)",
    "target_runtime_seconds": base_data["target_runtime_seconds"],
    "total_word_count": base_data["total_word_count"],
    "target_wpm": base_data["target_wpm"],
    "total_visual_shots": total_shots,
    "average_shot_duration_sec": round(base_data["target_runtime_seconds"] / total_shots, 2),
    "acts": []
}

for b_act, s_act in zip(base_data["acts"], ACTS_80_SHOTS):
    merged_act = dict(b_act)
    merged_act["shots"] = s_act["shots"]
    full_data["acts"].append(merged_act)

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(full_data, f, indent=2)

print(f"Saved complete 80-shot architecture to: {OUT_JSON}")
