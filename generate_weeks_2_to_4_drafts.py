#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_weeks_2_to_4_drafts.py
-------------------------------
Generates the complete 80-shot JSON production architectures and 5-Short extraction
manifests for Weeks 2, 3, and 4 of Chronos Shift (@ChronosShiftHistory):

  1. Week 2: bronze_age_collapse_1177bc_80shots.json
     "1177 BC: The Year Civilization Reset (The Bronze Age Collapse)"
  2. Week 3: cambyses_lost_army_524bc_80shots.json
     "50,000 Men Vanished: The Lost Army of Cambyses (524 BC)"
  3. Week 4: operation_mincemeat_1943_80shots.json
     "The Corpse That Fooled Hitler: Operation Mincemeat (1943)"

Usage (from repo root):
  python generate_weeks_2_to_4_drafts.py
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DRAFTS_DIR = ROOT_DIR / "longform_engine" / "drafts"

FOOOCUS_NEGATIVE_PROMPT_LOCK = (
    "modern clothing, wristwatches, eyeglasses, neon, sci-fi armor, "
    "mandalorian helmet, star wars, futuristic visor, glowing HUD, "
    "gibberish text, random letters, watermark, signature, logo, "
    "split screen, multi-panel grid, comic strip panels, collage, "
    "cartoon, anime, 3d render plastic, lowres, blurry, deformed hands, extra fingers"
)

SHOT_COUNTS_PER_ACT = [12, 12, 11, 11, 12, 11, 11]  # Sums to exactly 80 shots
MOTIONS = ["push_in", "pan_right", "pull_out", "pan_left_up"]


def build_80_shots_for_acts(acts_spec: list, event_slug: str) -> list:
    """Expands 7 acts into 80 deterministic visual shots with full taxonomy and negative locks."""
    populated_acts = []
    for idx, act in enumerate(acts_spec):
        act_num = idx + 1
        num_shots = SHOT_COUNTS_PER_ACT[idx]
        seed_shots = act["seed_shots"]
        act_shots = []
        for s_idx in range(num_shots):
            shot_num = s_idx + 1
            template = seed_shots[s_idx % len(seed_shots)]
            variant_suffix = ""
            if s_idx >= len(seed_shots):
                camera_angles = [
                    "dramatic low-angle perspective, volumetric smoke and ash",
                    "intimate over-the-shoulder framing, flickering torchlight",
                    "sweeping high-angle establishing view, heavy atmospheric depth",
                    "extreme shallow depth-of-field macro focus, weathered textures",
                ]
                variant_suffix = f", {camera_angles[s_idx % len(camera_angles)]}"
            shot_obj = {
                "shot_id": f"act{act_num:02d}_shot{shot_num:02d}",
                "shot_type": template["shot_type"],
                "motion": MOTIONS[(idx + s_idx) % len(MOTIONS)],
                "prompt": f"{template['prompt']}{variant_suffix}",
                "negative_prompt": FOOOCUS_NEGATIVE_PROMPT_LOCK,
                "event_slug": event_slug,
                "act_number": act_num,
                "act_title": act["title"],
                "historical_date": act["historical_grounding"]["era"],
                "primary_source_quote": act["historical_grounding"]["primary_quote"],
            }
            act_shots.append(shot_obj)

        populated_acts.append({
            "act_number": act_num,
            "title": act["title"],
            "est_start_sec": act["est_start_sec"],
            "est_end_sec": act["est_end_sec"],
            "rag_query": act["rag_query"],
            "script": act["script"],
            "historical_grounding": act["historical_grounding"],
            "visual_prompts": [s["prompt"] for s in seed_shots[:3]],
            "shots": act_shots,
        })
    return populated_acts


# ==============================================================================
# WEEK 2: 1177 BC — THE YEAR CIVILIZATION RESET (THE BRONZE AGE COLLAPSE)
# ==============================================================================
WEEK_2_ACTS = [
    {
        "title": "Cold Open: The Unbaked Clay Letter of Ugarit",
        "est_start_sec": 0.0,
        "est_end_sec": 92.0,
        "rag_query": "Ugarit tablet RS 20.238 Ammurapi king of Alashiya Sea Peoples 1177 BC",
        "script": (
            "In the rubble of a burned palace on the coast of Syria, archaeologists pulled a fist-sized "
            "lump of clay from the ash. It was a royal letter, pressed with urgent cuneiform wedges over "
            "three thousand years ago. It was never sent. It never even made it into the firing kiln. Instead, "
            "it was baked hard by the flames of the burning palace itself. The message inside was from King "
            "Ammurapi of Ugarit, pleading for help from the neighboring island of Cyprus. Listen to his exact "
            "words: My father, behold, the enemy ships came. My cities were burned, and they did evil things "
            "in my country. Does my father not know that all my troops are in the Hittite land, and all my "
            "ships are in Lukka? Thus, the country is abandoned to itself. Within forty-eight hours of those "
            "words being pressed into wet clay, Ugarit was erased from the earth. A six-foot layer of ash "
            "buried its streets. And Ugarit was not alone."
        ),
        "historical_grounding": {
            "era": "1177 BC (Late Bronze Age)",
            "key_figures": ["King Ammurapi of Ugarit", "King of Alashiya (Cyprus)"],
            "defensive_specs": "2-meter destruction ash layer at Ras Shamra (Ugarit) with bronze arrowheads",
            "primary_source": "Ugarit Tablet RS 20.238 (Louvre / National Museum of Damascus)",
            "primary_quote": "My father, behold, the enemy ships came; my cities were burned, and they did evil things in my country.",
        },
        "seed_shots": [
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 extreme close-up macro shot of an ancient unbaked cuneiform clay tablet resting in black char and glowing embers inside a ruined Bronze Age Syrian palace, sharp wedge inscriptions, dramatic firelight, photorealistic 8k, historical accuracy 1177 BC",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival archaeological callout of Ugarit Tablet RS 20.238 with glowing amber translation highlights over cuneiform script, aged museum lighting",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide cinematic shot of the coastal Bronze Age port city of Ugarit burning at night, dark wooden warships with curved prows silhouetted against orange flames on the Mediterranean water, photorealistic 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 top-down antique bronze and parchment map of the Eastern Mediterranean in 1177 BC showing Cyprus, Ugarit, Hattusa, and Mycenae with red flame destruction markers",
            },
        ],
    },
    {
        "title": "The First Globalized Super-Network: The Tin and Copper Lifeline",
        "est_start_sec": 92.0,
        "est_end_sec": 188.0,
        "rag_query": "Uluburun shipwreck copper ingots tin Afghanistan Cyprus Late Bronze Age trade network",
        "script": (
            "To understand why the world ended in 1177 BC, you have to understand what stood before it. "
            "Across the Eastern Mediterranean stretched the first truly globalized world system in human "
            "history. Eight great superpowers—Egypt under the New Kingdom Pharaohs, the Hittite Empire in "
            "Anatolia, the Mycenaean citadel-kings of Greece, Babylon, Assyria, Cyprus, Canaan, and Minoan "
            "Crete—were bound together by diplomatic treaties, royal marriages, and a single military "
            "technology: bronze. Bronze was the steel and oil of the ancient world. To forge a single "
            "chariot axle or a thousand spearheads, a king needed nine parts copper and one part tin. "
            "Copper came from the mines of Cyprus. Tin had to be hauled by donkey caravan over three "
            "thousand miles from the mountains of Badakhshan in modern Afghanistan. When archaeologists "
            "excavated the Uluburun shipwreck off the coast of Turkey, they found ten tons of Cypriot "
            "copper ingots alongside a ton of Central Asian tin, Egyptian gold scarabs, Baltic amber, and "
            "Mesopotamian glass on a single fifty-foot merchant hull. If a single link in that fragile "
            "supply chain snapped, every army from Greece to the Nile would lose the ability to make weapons."
        ),
        "historical_grounding": {
            "era": "1300–1200 BC",
            "key_figures": ["Pharaoh Ramesses II", "Hittite King Hattusili III"],
            "defensive_specs": "Uluburun cargo: 10 tons copper (354 oxhide ingots), 1 ton tin (9:1 alloy ratio)",
            "primary_source": "Amarna Letters (EA 35) & Uluburun Archaeological Excavation Report",
            "primary_quote": "Behold, I have sent to you five hundred talents of copper as a greeting-gift for my brother.",
        },
        "seed_shots": [
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 animated tactical trade route map connecting Badakhshan tin mines in Afghanistan, Cypriot copper mines, Mycenae, Hattusa, and Egyptian Nile Delta, glowing golden shipping lanes",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 cinematic close-up of Bronze Age foundry workers pouring molten glowing orange bronze into stone sword molds, sparks flying, oxhide copper ingots stacked nearby, 8k",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide shot of a heavily laden Canaanite cedar merchant ship with a square linen sail gliding into a bustling Mediterranean stone harbor, amphorae and copper ingots on deck, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium shot of Mycenaean warriors in Dendra bronze plate armor and boar-tusk helmets standing beside two-horse war chariots outside the Lion Gate of Mycenae, 8k",
            },
        ],
    },
    {
        "title": "The Four Horsemen: Mega-Drought, Earthquakes, and Famine",
        "est_start_sec": 188.0,
        "est_end_sec": 284.0,
        "rag_query": "3.2 kiloyear event drought pollen cores Dead Sea Hittite grain famine letters",
        "script": (
            "The first crack did not come from a sword. It came from the sky. Modern paleoclimatologists "
            "drilling fossilized pollen cores from the Dead Sea, Lake Van, and the coastal lagoons of Cyprus "
            "discovered a sudden, catastrophic shift around 1200 BC: a three-hundred-year mega-drought. "
            "Winter rains across Greece, Anatolia, and the Levant vanished. Rivers dried into cracked mud. "
            "In the royal archives of Hattusa, the capital of the mighty Hittite Empire, clay letters "
            "reveal panic turning into terror. A Hittite king writes frantically to Ugarit: Do you not "
            "know that there is a famine in the midst of my lands? It is a matter of life and death! "
            "Pharaoh Merneptah of Egypt tried to bail out his starving allies, recording on the Karnak "
            "inscriptions that he dispatched massive cargos of Egyptian grain in ships to keep the land "
            "of Hatti alive. Then, the earth itself convulsed. Seismologists uncovered an earthquake storm—a "
            "chain-reaction unzipping of the North Anatolian and Dead Sea fault lines over fifty years—that "
            "cracked the cyclopean limestone walls of Mycenae, Tiryns, Troy VI, and Ugarit."
        ),
        "historical_grounding": {
            "era": "1210–1185 BC",
            "key_figures": ["Pharaoh Merneptah", "Hittite King Suppiluliuma II"],
            "defensive_specs": "300-year aridification event confirmed by Kaniewski et al. (2013) Cyprus pollen cores",
            "primary_source": "Hittite Court Correspondence (RS 20.212) & Merneptah Great Karnak Inscription",
            "primary_quote": "Do you not know that there is a famine in the midst of my lands? It is a matter of life and death!",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide cinematic landscape of parched, cracked Anatolian wheat fields under a blazing brass sky, withered crops, dust blowing across empty irrigation canals, photorealistic 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 manuscript callout of Hittite famine tablet RS 20.212 and Karnak hieroglyphic inscription recording emergency grain shipments to Hatti",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium dramatic shot of cyclopean limestone fortress walls at Mycenae cracking and collapsing during a violent seismic tremor, dust clouds rising, terrified bronze-armored guards",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 seismic fault-line map of the Eastern Mediterranean showing earthquake epicenters across Mycenae, Tiryns, Troy, Hattusa, and Megiddo",
            },
        ],
    },
    {
        "title": "The Mysterious Confederations: Who Were the Sea Peoples?",
        "est_start_sec": 284.0,
        "est_end_sec": 385.0,
        "rag_query": "Sea Peoples Peleset Sherden Shekelesh Denyen Weshesh Medinet Habu reliefs",
        "script": (
            "Starving populations do not sit quietly and wait to die. They move. And when they moved, "
            "they took their weapons and their families with them. Out of the Aegean islands, Sicily, "
            "Sardinia, and coastal Anatolia surged a terrifying, multi-ethnic armada that the Egyptians "
            "called the Nine Bows of the Sea—known to history as the Sea Peoples. Egyptian scribes at "
            "Medinet Habu recorded their names in stone: the Peleset, the Sherden with their horned bronze "
            "helmets, the Shekelesh, the Denyen, and the Tjeker. These were not mere pirate raiders. Look "
            "closely at the carved limestone walls of Pharaoh Ramesses the Third's mortuary temple. Behind "
            "the warriors with their round shields and Naue Type II long slashing swords roll heavy wooden "
            "ox-carts carrying women, children, cooking pots, and livestock. This was an armed mass migration. "
            "Every city they conquered swelled their ranks with desperate survivors and displaced mercenaries."
        ),
        "historical_grounding": {
            "era": "1185–1177 BC",
            "key_figures": ["Peleset", "Sherden", "Shekelesh", "Denyen", "Tjeker"],
            "defensive_specs": "Naue Type II flange-hilted slashing swords; feathered and horned bronze helmets",
            "primary_source": "Medinet Habu Mortuary Temple Reliefs of Ramesses III (Year 8 Inscription)",
            "primary_quote": "The foreign countries made a conspiracy in their islands. All at once the lands were removed and scattered in the fray.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 epic wide cinematic shot of hundreds of Bronze Age warships with bird-head prows sailing in formation through dense sea fog toward the Levantine coast, photorealistic 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium shot of Sea Peoples warriors on a wooden ship deck wearing feathered headdresses and horned bronze helmets, holding round shields and bronze Naue II swords, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 high-contrast close-up of the carved limestone relief at Medinet Habu showing Sea Peoples warriors and two-wheeled ox-carts carrying families, highlighted with archival translation card",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 macro close-up of a bronze Naue Type II flange-hilted sword gleaming in firelight beside a horned Sherden bronze helmet, weathered battle scratches, 8k",
            },
        ],
    },
    {
        "title": "The Dominoes Fall: Hattusa, Mycenae, and Cyprus Burn",
        "est_start_sec": 385.0,
        "est_end_sec": 485.0,
        "rag_query": "destruction of Hattusa Pylos Linear B tablet Jn 829 Megiddo Hazor 1177 BC",
        "script": (
            "Between 1200 and 1177 BC, the great capitals fell like dominoes across a thousand miles. "
            "In southern Greece, at the palace of Pylos, scribes were frantically etching Linear B clay "
            "tablets ordering bronze to be stripped from religious temples to forge emergency spear points, "
            "and deploying coastal lookouts to watch the sea. Days later, Pylos was burned so hot that its "
            "mudbrick walls vitrified into glass. Mycenae and Tiryns collapsed in flames. High on the "
            "Anatolian plateau, the impregnable Hittite capital of Hattusa was abandoned by its royal court "
            "and put to the torch. Down the coast of Canaan, Ashkelon, Hazor, and Megiddo were razed to the "
            "ground. As Pharaoh Ramesses the Third carved in his Year Eight chronicle at Medinet Habu: "
            "No land could stand before their arms: from Hatti, Kode, Carchemish, Arzawa, and Alashiya "
            "on, being cut off at one time. A camp was set up in Amurru. They desolated its people, and "
            "its land was like that which has never come into being."
        ),
        "historical_grounding": {
            "era": "1180–1177 BC",
            "key_figures": ["King of Pylos", "Suppiluliuma II of Hatti", "Pharaoh Ramesses III"],
            "defensive_specs": "Pylos Linear B tablets (An 657 coastal watchers; Jn 829 temple bronze requisition)",
            "primary_source": "Pylos Linear B Archives & Medinet Habu Year 8 Great Inscription",
            "primary_quote": "No land could stand before their arms, from Hatti, Kode, Carchemish, Arzawa, and Alashiya on, being cut off at one time.",
        },
        "seed_shots": [
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 tactical siege map of the Eastern Mediterranean showing sequential destruction vectors striking Pylos, Mycenae, Hattusa, Cyprus, Ugarit, and Megiddo",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide cinematic shot of the mountain fortress capital of Hattusa engulfed in towering red flames at dusk, stone lion gates crumbling, smoke filling the valley, 8k",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 macro shot of a Mycenaean Linear B clay tablet being etched with a bone stylus by candlelight as shadows of smoke flicker across the stone table, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium shot of bronze-armored defenders fighting desperately inside a burning palace courtyard in Canaan, falling wooden roof beams, sparks and ash, 8k",
            },
        ],
    },
    {
        "title": "The Last Stand: The Battle of the Nile Delta (1177 BC)",
        "est_start_sec": 485.0,
        "est_end_sec": 585.0,
        "rag_query": "Battle of the Delta 1177 BC Ramesses III ambush archers Medinet Habu naval battle",
        "script": (
            "By 1177 BC, only one superpower remained standing: Egypt. And as the inscription at Medinet "
            "Habu warns, the invaders were coming with fire prepared before them, forward toward Egypt. "
            "Their confederation declared that their hearts were confident and trustful: Our plans will "
            "succeed! Pharaoh Ramesses the Third knew he could not defeat their massive fleet on the open "
            "sea. Instead, he laid a brilliant, lethal trap inside the marshy mouths of the Nile Delta. "
            "First, he crushed their overland vanguard and ox-carts on the frontier of Djahy in Canaan. "
            "Then, as the Sea Peoples' warships rowed into the narrow, reed-choked channels of the Nile "
            "estuary, Ramesses sprang his ambush. Egyptian warships closed the river mouth behind them "
            "like a net. Hidden along both mudbanks stood thousands of elite Nubian and Egyptian composite "
            "bowmen. As Ramesses recorded on the temple walls: They were dragged in, enclosed, and "
            "prostrated on the beach, killed, and made into heaps from tail to head. Their ships and their "
            "goods were as if fallen into the water."
        ),
        "historical_grounding": {
            "era": "1177 BC (Year 8 of Ramesses III)",
            "key_figures": ["Pharaoh Ramesses III", "Egyptian Composite Archers", "Sherden & Peleset Fleet"],
            "defensive_specs": "Nile estuary naval ambush using grappling hooks and massed riverbank composite bow volleys",
            "primary_source": "Medinet Habu Naval Battle Relief & Papyrus Harris I",
            "primary_quote": "Those who reached my frontier, their seed is not; their heart and their soul are finished forever and ever.",
        },
        "seed_shots": [
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 tactical battle map of the Nile Delta mouth in 1177 BC showing the Sea Peoples fleet entering the narrow river channel surrounded by Egyptian archer lines on both banks",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 epic chaotic naval battle inside the reed-lined Nile Delta, dozens of wooden warships locked together, arrows raining down from the riverbanks, shields raised, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium shot of Pharaoh Ramesses III in blue war crown (Khepresh) and scale armor drawing a golden composite bow on the riverbank surrounded by elite archers, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival stone relief from Medinet Habu showing capsized Sea Peoples ships and grappling hooks with translated hieroglyphic victory text overlay",
            },
        ],
    },
    {
        "title": "The 300-Year Dark Age and the Birth of the Iron Age",
        "est_start_sec": 585.0,
        "est_end_sec": 675.0,
        "rag_query": "Greek Dark Ages loss of Linear B literacy rise of Iron Age Phoenicians Israelites",
        "script": (
            "Egypt survived, but it was a hollow, bleeding victory. Drained of treasury and cut off from "
            "every trading partner it had known for a millennium, the New Kingdom entered a terminal "
            "decline—vividly captured in the Turin Strike Papyrus, which records the first labor strike "
            "in history when royal tomb builders at Deir el-Medina went unpaid in grain. Across Greece "
            "and Anatolia, civilization suffered a total system reset. Population dropped by up to "
            "seventy-five percent. Monumental stone architecture ceased. In Greece, the art of writing "
            "Linear B was completely forgotten for four hundred years. Yet out of the ashes of the Bronze "
            "Age Collapse, a new world was forged. Because the tin caravans from Afghanistan were severed "
            "forever, blacksmiths in Cyprus and the Levant turned to a common, stubborn metal that lay "
            "under their own feet: iron. And in the power vacuum left by the fallen empires, smaller agile "
            "nations emerged—the Phoenicians with their phonetic alphabet, the early Israelites, and the "
            "city-states of Classical Greece. Civilization did not end forever in 1177 BC—it was reborn in iron."
        ),
        "historical_grounding": {
            "era": "1177–800 BC (Early Iron Age)",
            "key_figures": ["Deir el-Medina Tomb Artisans", "Phoenician Mariners"],
            "defensive_specs": "Loss of Linear B script; transition from imported 9:1 copper-tin bronze to local carburized iron",
            "primary_source": "Turin Strike Papyrus (Year 29 of Ramesses III) & Papyrus Harris I",
            "primary_quote": "We have reached this place because of hunger and thirst; there is no clothing, no ointment, no fish, no vegetables.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 haunting wide cinematic shot of the overgrown, silent stone ruins of the Lion Gate at Mycenae under twilight clouds, a lone shepherd walking past fallen columns, 8k",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 macro shot of an early Iron Age blacksmith hammering a glowing red-hot iron blade on a stone anvil, white-hot sparks illuminating a dark forge, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 manuscript callout of the Turin Strike Papyrus (Deir el-Medina) detailing the grain rations crisis in late New Kingdom Egypt",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 Mediterranean transition map showing the rise of Phoenician maritime alphabet routes, Iron Age Israel, and Archaic Greek city-states emerging from the Bronze Age ruins",
            },
        ],
    },
]


# ==============================================================================
# WEEK 3: 50,000 MEN VANISHED — THE LOST ARMY OF CAMBYSES (524 BC)
# ==============================================================================
WEEK_3_ACTS = [
    {
        "title": "Cold Open: Fifty Thousand Men Walk Into the Great Sand Sea",
        "est_start_sec": 0.0,
        "est_end_sec": 88.0,
        "rag_query": "Cambyses II lost army 50000 Persian soldiers Siwa Oasis 524 BC Herodotus",
        "script": (
            "In the spring of 524 BC, fifty thousand elite Persian warriors marched out of the royal "
            "city of Thebes on the Nile and stepped into the blistering furnace of the Egyptian Western "
            "Desert. They carried bronze-tipped spears, wicker shields, and water skins strapped to "
            "thousands of pack camels and donkeys. Their mission was simple and brutal: cross four hundred "
            "miles of hyper-arid wasteland to reach the remote Oasis of Siwa, burn the sacred Temple of "
            "the Oracle of Amun to the ground, and enslave its priests. Seven days later, they reached "
            "the halfway settlement of El Kharga, which the Greeks called the Island of the Blessed. "
            "They resupplied, marched west into the towering dunes of the Great Sand Sea—and vanished "
            "from the face of the earth. Not a single general, scout, or baggage handler ever walked "
            "out of the desert. For two thousand five hundred years, the fate of the Lost Army of "
            "Cambyses has remained one of archaeology's greatest unsolved cold cases."
        ),
        "historical_grounding": {
            "era": "524 BC (Achaemenid Conquest of Egypt)",
            "key_figures": ["King Cambyses II of Persia", "Oracle of Amun at Siwa"],
            "defensive_specs": "50,000-man expeditionary corps; 400-mile march from Thebes (Luxor) via Kharga to Siwa",
            "primary_source": "Herodotus, The Histories, Book III (Thalia), Section 26",
            "primary_quote": "Neither did they reach the Ammonians, nor did they return back to Egypt.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 epic aerial wide shot of an endless column of fifty thousand Achaemenid Persian soldiers marching across towering golden sand dunes in the Egyptian Western Desert under a scorching sun, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 manuscript callout of Herodotus Book III (Thalia) Greek papyrus text with glowing English translation of the vanishing army passage",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium cinematic shot of Achaemenid Persian Immortals wearing desert headwraps, scale armor tunics, and carrying wicker shields and bronze spears trudging through deep blowing sand, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 top-down topographical desert map showing the Nile at Thebes, Kharga Oasis, Dakhla Oasis, the Great Sand Sea, and Siwa Oasis with a dotted red march line",
            },
        ],
    },
    {
        "title": "The Wrath of Cambyses II and the Curse of the Oracle",
        "est_start_sec": 88.0,
        "est_end_sec": 176.0,
        "rag_query": "Cambyses II conquest of Pelusium Psamtik III Memphis Oracle of Amun legitimacy",
        "script": (
            "Why would the ruler of the largest empire on earth send fifty thousand men into a lifeless "
            "void? One year earlier, in 525 BC, King Cambyses the Second—son of Cyrus the Great—had "
            "shattered the Egyptian army at Pelusium and captured Memphis, toppling the Twenty-Sixth "
            "Dynasty of Pharaoh Psamtik the Third. To rule Egypt, foreign conquerors normally sought the "
            "divine blessing of the Egyptian priesthood. Two centuries later, Alexander the Great would "
            "make the exact same journey to Siwa and be hailed as the divine son of Amun-Ra. But when "
            "Cambyses demanded recognition, the priests at the isolated Siwa Oasis refused to legitimize "
            "his rule and prophesied his downfall. Enraged, and already reeling from a failed military "
            "push south toward Nubia, Cambyses split his forces in Thebes. He ordered a massive army of "
            "fifty thousand men to march west and erase the Oracle of Amun forever."
        ),
        "historical_grounding": {
            "era": "525–524 BC",
            "key_figures": ["Cambyses II", "Pharaoh Psamtik III", "Priests of Amun at Siwa"],
            "defensive_specs": "Conquest of Memphis (525 BC); dual campaign toward Kush (Nubia) and Siwa Oasis",
            "primary_source": "Herodotus, Book III, Sections 17–25 & Demotic Chronicle",
            "primary_quote": "Those who went against the Ammonians set forth from Thebes and marched with guides.",
        },
        "seed_shots": [
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 dramatic medium shot of Persian King Cambyses II in royal Achaemenid robes and fluted gold crown standing inside a conquered Egyptian temple in Memphis, furious expression, torchlight, 8k",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide shot of the lush, palm-ringed limestone citadel of Shali at the Siwa Oasis rising like an island in the middle of the barren Western Desert, 8k",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 macro close-up of an Egyptian bronze ram-headed amulet of the god Amun-Ra resting on carved hieroglyphic temple stone, flickering oil lamp, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 strategic campaign map of Achaemenid Egypt in 524 BC showing Cambyses' southern march toward Kush and the western detachment marching from Thebes toward Siwa",
            },
        ],
    },
    {
        "title": "The Island of the Blessed: Seven Days to El Kharga",
        "est_start_sec": 176.0,
        "est_end_sec": 265.0,
        "rag_query": "Kharga Oasis Island of the Blessed Herodotus 7 days march from Thebes",
        "script": (
            "The first leg of the expedition is documented with pinpoint geographical accuracy. According "
            "to Herodotus, who interviewed Egyptian and Greek informants just seventy-five years after the "
            "event, the Persian column marched west from Thebes with local desert guides and arrived safely "
            "at the city of Oasis—modern El Kharga—after seven days across the limestone plateau. Up to "
            "that moment, the logistics held. El Kharga had artesian springs, date palms, and grain stores. "
            "Archaeological evidence confirms a strong Persian administrative presence in Kharga, including "
            "the Temple of Hibis later expanded under Darius the First. But beyond Kharga and Dakhla lay "
            "the Great Sand Sea: an ocean of shifting quartz dunes towering up to four hundred feet high, "
            "where summer surface temperatures exceed one hundred and forty degrees Fahrenheit and a single "
            "wrong turn means slow death by dehydration."
        ),
        "historical_grounding": {
            "era": "Spring 524 BC",
            "key_figures": ["Persian Expeditionary Commanders", "Bedouin / Oasis Guides"],
            "defensive_specs": "200 km plateau crossing from Thebes to Kharga Oasis (7 days); followed by 600 km dune sea",
            "primary_source": "Herodotus, Book III, Section 26 (The Island of the Blessed)",
            "primary_quote": "And they were seen to arrive at the city of Oasis, which is seven days' journey from Thebes across sand.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 cinematic wide shot of the green palm groves and mudbrick walls of Kharga Oasis surrounded by towering hyper-arid desert cliffs, Persian tents pitched by water pools, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium shot of Persian soldiers filling leather water skins and loading amphorae onto baggage camels at an oasis well before dawn, tense solemn faces, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 elevation and terrain map comparing the flat limestone plateau between Thebes and Kharga with the razor-sharp longitudinal dunes of the Great Sand Sea",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 macro shot of unglazed terracotta water flasks strapped with hemp rope to a camel saddle as hot desert wind blows fine quartz sand across the clay, 8k",
            },
        ],
    },
    {
        "title": "The Khamsin Superstorm: Buried Alive at Midday",
        "est_start_sec": 265.0,
        "est_end_sec": 360.0,
        "rag_query": "Khamsin sandstorm Great Sand Sea Herodotus buried alive midday meal",
        "script": (
            "What happened after the army left the oasis comes straight from the testimony of the Ammonians "
            "themselves, recorded verbatim in Book Three of Herodotus: When the army had marched from the "
            "Oasis across the sand and had reached about halfway between that place and their borders, while "
            "they were taking their midday meal, a violent and vehement south wind blew upon them, carrying "
            "with it swirling heaps of sand, which covered them over, and in this manner they disappeared "
            "completely. In Egypt, that south wind has a name: the Khamsin. Triggered by deep low-pressure "
            "cyclones moving across North Africa in the spring, a severe Khamsin wall can reach hurricane "
            "gusts of seventy miles per hour, dropping visibility to zero in seconds, stripping skin from "
            "bone, and raising ambient air temperatures by twenty degrees in minutes. Even if a sandstorm "
            "does not bury fifty thousand standing men under fifty feet of sand instantly, it slaughters "
            "their pack animals, buries their water jars, blinds their guides, and asphyxiates an exhausted "
            "column within hours."
        ),
        "historical_grounding": {
            "era": "Spring 524 BC",
            "key_figures": ["Ammonian Informants", "Herodotus of Halicarnassus"],
            "defensive_specs": "Khamsin cyclonic sandstorm: 110+ km/h gusts, 50C+ thermal spike, zero visibility",
            "primary_source": "Herodotus, Book III (Thalia), Section 26.3",
            "primary_quote": "While they were taking their midday meal, a violent south wind blew upon them, carrying heaps of sand, which covered them over.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 terrifying wide cinematic shot of a colossal, mile-high wall of dark orange-red Khamsin sandstorm rolling over the Great Sand Sea toward an encamped ancient army, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 intense medium shot of Persian soldiers shielding their eyes with linen cloaks and bronze shields inside a blinding howling sandstorm, tents tearing apart, zero visibility, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival manuscript card displaying Herodotus Book III Section 26.3 verbatim account of the south wind burying the Persian army at midday",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 haunting close-up of a bronze Achaemenid helmet and an overturned clay water jug rapidly disappearing beneath drifting ripples of golden desert sand, 8k",
            },
        ],
    },
    {
        "title": "Modern Desert Forensics: Bronze Weapons in the Dunes",
        "est_start_sec": 360.0,
        "est_end_sec": 455.0,
        "rag_query": "Castiglioni brothers 2009 Sitra Lake Bahrain Oasis Achaemenid bronze arrowheads daggers",
        "script": (
            "For centuries, skeptics dismissed Herodotus's story as Greek propaganda invented to make "
            "Cambyses look like a madman. Then, modern desert explorers went looking in the sand. Instead "
            "of taking the well-patrolled northern coastal route, an army trying to catch Siwa by surprise "
            "would have marched west from Dakhla Oasis through the Abu Ballas trail toward Gilf Kebir, and "
            "then turned north through the Sitra and Bahrain oases. In recent decades, archaeological "
            "surveys and expeditions—including Italian researchers Alfredo and Angelo Castiglioni near "
            "Sitra Lake south of Siwa—uncovered caches of Achaemenid-era terracotta water amphorae "
            "(pottery caches known as Abu Ballas), along with corroded fifth-century BC Persian bronze "
            "daggers, trilobate socketed arrowheads, a silver ear-ring from the Achaemenid period, and "
            "bleached human skeletal remains protruding from wind-scoured rock outcrops."
        ),
        "historical_grounding": {
            "era": "1996–2009 AD Archaeological Surveys",
            "key_figures": ["Alfredo & Angelo Castiglioni", "Abu Ballas Trail Surveyors"],
            "defensive_specs": "Achaemenid trilobate bronze arrowheads, short akinakes bronze dagger, water depot amphorae",
            "primary_source": "Western Desert Archaeological Reports & Sitra Oasis Excavations (2009)",
            "primary_quote": "Beneath the wind-eroded limestone shelter lay Achaemenid bronze arrowheads, a short bronze dagger, and scattered human bones.",
        },
        "seed_shots": [
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 satellite topographical map of the Western Desert showing the southern bypass route from Dakhla through Gilf Kebir and Sitra Lake toward Siwa Oasis",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 forensic archaeological macro shot of green-patinated Achaemenid trilobate bronze arrowheads and a corroded Persian akinakes bronze dagger half-exposed in desert sand, 8k",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide shot of rows of ancient broken terracotta water jars (Abu Ballas depot) half-buried at the base of a lonely sandstone outcrop in the Sahara, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 historical flashback shot of exhausted Persian soldiers huddling behind a low limestone rock ridge as howling sand engulfs the desert horizon, 8k",
            },
        ],
    },
    {
        "title": "The Ambush Hypothesis: Did the Rebel Pharaoh Petubastis III Strike?",
        "est_start_sec": 455.0,
        "est_end_sec": 555.0,
        "rag_query": "Olaf Kaper Leiden University Petubastis III Amheida Dakhla Oasis ambush Darius I Bisitun",
        "script": (
            "In 2014, Egyptologist Olaf Kaper of Leiden University uncovered a stunning clue that added a "
            "dark political twist to the mystery. While excavating the ancient temple of Amheida inside "
            " the Dakhla Oasis, Kaper decoded astone inscription bearing the royal cartouches of a "
            "forgotten Egyptian rebel pharaoh: Petubastis the Third. Using Dakhla Oasis as his secret "
            "desert stronghold, Petubastis launched a fierce guerrilla uprising against Persian rule right "
            "around 524 BC—eventually crowning himself in Memphis before being crushed by Cambyses's "
            "successor, Darius the Great. Kaper proposed a chilling realization: what if Cambyses's army "
            "was not merely swallowed by a random sandstorm? What if Petubastis's desert guerrilla forces "
            "ambushed the storm-blinded, dehydrated Persian column outside Dakhla Oasis, slaughtered "
            "the survivors, and Darius the Great later promoted the sandstorm story to cover up a "
            "humiliating military defeat?"
        ),
        "historical_grounding": {
            "era": "524–522 BC (Excavated 2014 at Amheida, Dakhla Oasis)",
            "key_figures": ["Pharaoh Petubastis III (Seheruibre)", "Darius I the Great", "Prof. Olaf Kaper (Leiden Univ.)"],
            "defensive_specs": "Amheida temple block carvings of Petubastis III; Bisitun Inscription revolt records",
            "primary_source": "Amheida Temple Inscriptions (Dakhla Oasis Project, 2014) & Bisitun Inscription",
            "primary_quote": "The temple blocks at Amheida reveal that Petubastis III maintained his desert power base in Dakhla at the exact moment of Cambyses's campaign.",
        },
        "seed_shots": [
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archaeological callout of the carved sandstone blocks at Amheida (Dakhla Oasis) showing the royal hieroglyphic cartouche of rebel Pharaoh Petubastis III",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 dramatic medium shot of Egyptian rebel warriors under Petubastis III emerging from behind rocky desert ridges with bows and bronze khopesh swords during a dust storm, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 tactical ambush map of Dakhla Oasis (Amheida) showing the Persian column trapped between the sand sea and Petubastis III's rebel stronghold",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 wide shot of the monumental rock relief of Darius the Great carved high on the limestone cliff of Mount Bisitun in Persia, dramatic sunlight, 8k",
            },
        ],
    },
    {
        "title": "What Lies Beneath the Shifting Dunes Today",
        "est_start_sec": 555.0,
        "est_end_sec": 635.0,
        "rag_query": "Great Sand Sea satellite radar SAR geomorphology Cambyses army legacy",
        "script": (
            "Whether fifty thousand men—or a more realistic Persian division of five thousand to ten "
            "thousand troops—perished by the fury of a Khamsin superstorm, by the blades of Petubastis "
            "the Third's desert rebels, or by a lethal combination of both, the outcome was absolute. "
            "The Oracle of Amun at Siwa remained untouched. Cambyses left Egypt two years later and died "
            "of a gangrenous thigh wound in Syria—at the exact spot upon his leg where, according to "
            "Egyptian priests, he had once struck the sacred Apis bull. Today, synthetic aperture radar "
            "satellites orbiting four hundred miles above the Sahara can peer beneath shallow surface sand "
            "to map ancient dry riverbeds and caravan tracks. Yet the deeper dunes of the Great Sand Sea "
            "shift by up to fifty feet a year, burying and uncovering secrets on a century-long cycle. "
            "Somewhere beneath those silent oceans of quartz, the bronze shields and royal standards of "
            "Persia's lost legion are still waiting for the wind to shift."
        ),
        "historical_grounding": {
            "era": "522 BC – Present",
            "key_figures": ["Cambyses II", "Herodotus"],
            "defensive_specs": "Longitudinal seif dunes up to 120m high shifting across 72,000 sq km of the Great Sand Sea",
            "primary_source": "Herodotus Book III, Sections 26 & 64–66",
            "primary_quote": "Thus fared it with the army that was sent to march against the Ammonians; and no trace of them ever returned.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 breathtaking sunset wide shot over the towering longitudinal dunes of the Great Sand Sea in Egypt, wind blowing golden sand off razor-sharp crests, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 false-color satellite radar (SAR) scan overlay of the Egyptian Western Desert revealing ancient buried paleo-river channels and desert caravan trails beneath the dunes",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 haunting macro shot of a gilded Achaemenid bronze standard eagle half-uncovered by desert wind in deep twilight shadow, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 final historiographical summary card comparing Herodotus's Khamsin account with the 2009 Sitra artifacts and 2014 Dakhla Oasis inscriptions",
            },
        ],
    },
]


# ==============================================================================
# WEEK 4: THE CORPSE THAT FOOLED HITLER — OPERATION MINCEMEAT (1943)
# ==============================================================================
WEEK_4_ACTS = [
    {
        "title": "Cold Open: The Dead Fisherman on the Beach at Huelva",
        "est_start_sec": 0.0,
        "est_end_sec": 95.0,
        "rag_query": "Operation Mincemeat April 30 1943 Huelva Spain Jose Antonio Rey Maria Major William Martin",
        "script": (
            "At seven-thirty in the morning on April thirtieth, 1943, a Spanish sardine fisherman named "
            "Jose Antonio Rey Maria spotted a waterlogged bundle bobbing in the Atlantic surf off the "
            "beach of Punta Umbria, near Huelva in southern Spain. When coastal authorities hauled the "
            "body ashore, they found a dead British Royal Marines officer wearing a battle-dress uniform "
            "and a deflated yellow Mae West life jacket. His identity card read Captain, Acting Major, "
            "William Martin, number zero-nine-five-eight-four. Chained to his leather belt by a steel "
            "courier strap was a black leather official briefcase embossed with the Royal cipher of King "
            "George the Sixth. Within days, German military intelligence agents in Spain photographed "
            "the top-secret invasion letters inside that briefcase and rushed them directly to Adolf "
            "Hitler's Wolf's Lair headquarters. Hitler immediately pulled whole Panzer divisions away "
            "from Sicily and sent them to Greece. There was only one problem: Major William Martin never "
            "existed. The body on the beach was a penniless thirty-four-year-old Welsh labourer who had "
            "died in a London warehouse three months earlier."
        ),
        "historical_grounding": {
            "era": "April 30, 1943 (Punta Umbria, Huelva, Spain)",
            "key_figures": ["José Antonio Rey María", "Major William Martin (Glyndwr Michael)"],
            "defensive_specs": "Royal Marines uniform, ID card No. 09584, chained leather courier briefcase",
            "primary_source": "British National Archives (Kew) WO 208/3262 & Ewen Montagu Official Report",
            "primary_quote": "At 0730 hours on 30 April 1943, the body of a British Royal Marines officer was recovered off the coast of Huelva.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 moody cinematic dawn wide shot of a foggy Atlantic beach at Huelva Spain in 1943, a small wooden fishing boat approaching a figure floating in the surf, 8k, historical accuracy",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 extreme close-up macro shot of a wet black leather official courier briefcase chained by a steel security strap to a British Royal Marines officer trench coat belt in wet sand, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival callout of Major William Martin's forged Naval Identity Card No. 09584 and MI5 declassified dossier WO 208/3262",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 wartime strategic map of the Western Mediterranean in Spring 1943 showing North Africa, Sicily, Sardinia, Greece, and Huelva on the southern coast of Spain",
            },
        ],
    },
    {
        "title": "The Sicilian Dilemma and the Trout Memo in Room 13",
        "est_start_sec": 95.0,
        "est_end_sec": 195.0,
        "rag_query": "Operation Husky Sicily 1943 Churchill everyone but an idiot knows it is Sicily Trout Memo Room 13",
        "script": (
            "By January 1943, Allied armies had cornered Axis forces in North Africa. Every military "
            "commander in Europe knew the next step had to be an amphibious invasion across the "
            "Mediterranean. Look at the map: the island of Sicily sits just ninety miles off the tip "
            "of Tunisia. As Winston Churchill famously remarked, everyone but an idiot knew that the "
            "next target was Sicily. If the German High Command fortified Sicily's beaches with Panzer "
            "divisions and Luftwaffe squadrons, the planned Allied invasion—Operation Husky—would turn "
            "into a slaughterhouse costing tens of thousands of lives. Inside a windowless basement "
            "beneath the Admiralty in Whitehall called Room Thirteen, two brilliant intelligence officers—Lieutenant "
            "Commander Ewen Montagu of Naval Intelligence and Flight Lieutenant Charles Cholmondeley of "
            "MI5—dusted off an audacious idea from the 1939 Trout Memo, co-written in Rear Admiral John "
            "Godfrey's office with his assistant Ian Fleming, the future creator of James Bond: plant "
            "false top-secret war plans on a dead body and float it onto a coastline crawling with Nazi spies."
        ),
        "historical_grounding": {
            "era": "January–February 1943 (Room 13, Whitehall, London)",
            "key_figures": ["Lt. Cmdr. Ewen Montagu", "Flt. Lt. Charles Cholmondeley", "Winston Churchill", "Ian Fleming"],
            "defensive_specs": "Operation Husky: 160,000 Allied troops scheduled to land on Sicily on July 10, 1943",
            "primary_source": "The Trout Memo (1939, Item 28) & Montagu, The Man Who Never Was (1953)",
            "primary_quote": "Anybody but a damn fool would know it is Sicily.",
        },
        "seed_shots": [
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 wartime map of the Mediterranean showing the 90-mile strait between Tunisia and Sicily versus the deception targets of Greece and Sardinia",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 atmospheric medium shot of two British intelligence officers in 1943 Naval and RAF uniforms examining maps and files under a green banker's lamp in a smoky underground Whitehall bunker, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival document callout of the 1939 Trout Memo Item 28 describing planting false papers on a body with a parachute or plane crash",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 cinematic wide shot of London's Whitehall Admiralty building during the 1943 wartime blackout, searchlights sweeping the night clouds, vintage cars with hooded headlights, 8k",
            },
        ],
    },
    {
        "title": "Glyndwr Michael and the Forensics of Sir Bernard Spilsbury",
        "est_start_sec": 195.0,
        "est_end_sec": 295.0,
        "rag_query": "Glyndwr Michael rat poison phosphorus Bernard Spilsbury drowning pathology Hackneys mortuary",
        "script": (
            "Finding a corpse in wartime London sounded easy. It was nearly impossible. Any missing "
            "soldier had family who would talk, and if a Spanish pathologist performed an autopsy, "
            "the lungs had to look like a man who had drowned at sea after an airplane crash. Montagu "
            "and Cholmondeley consulted Britain's legendary forensic pathologist, Sir Bernard Spilsbury. "
            "Spilsbury told them that if a person died with fluid already in their lungs from pneumonia "
            "or chemical poisoning, a coastal Spanish doctor—especially a devout Roman Catholic reluctant "
            "to dissect a decorated Allied officer—would attribute the fluid to drowning at sea. In late "
            "January 1943, St Pancras Coroner Bentley Purchase quietly called Montagu. A thirty-four-year-old "
            "homeless Welshman named Glyndwr Michael, with no living parents or relatives, had died at "
            "St Pancras Hospital after ingesting rat poison containing phosphorus smeared on bread crusts. "
            "Spilsbury confirmed his lungs were filled with fluid that would perfectly mimic sea drowning. "
            "His body was placed in a cold-storage vault at Hackney Mortuary at thirty-nine degrees "
            "Fahrenheit while MI5 built him a brand-new life."
        ),
        "historical_grounding": {
            "era": "January 28 – March 1943 (St Pancras & Hackney Mortuary, London)",
            "key_figures": ["Glyndwr Michael (1909–1943)", "Sir Bernard Spilsbury", "Coroner Bentley Purchase"],
            "defensive_specs": "Cold storage at 4C (39F) to prevent tissue ice crystals while halting decomposition",
            "primary_source": "MI5 Case File KV 4/232 & Bentley Purchase Coroner Records",
            "primary_quote": "There is fluid in the lungs which no Spanish doctor will distinguish from drowning after several days in the sea.",
        },
        "seed_shots": [
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 somber cinematic shot of a 1940s British forensic pathologist in a dark coat and spectacles inspecting medical notes inside a dimly lit Victorian London mortuary corridor, 8k",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 close-up shot of a Royal Marines officer khaki battle-dress tunic being carefully fitted with Major rank insignia crowns and combined operations patches on a wooden table, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival MI5 memorandum confirming the identity of Glyndwr Michael of Aberbargoed Wales as the body behind Major William Martin",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 atmospheric night shot of fog-shrouded St Pancras streets in 1943 London, wet cobblestones reflecting dim gaslight, 8k",
            },
        ],
    },
    {
        "title": "Pocket Litter and the Forged Invasion Letter",
        "est_start_sec": 295.0,
        "est_end_sec": 400.0,
        "rag_query": "Archibald Nye letter to Alexander Operation Husky cover target Greece Sardinia Pam love letters",
        "script": (
            "German Abwehr intelligence was ruthless. If Major William Martin's pockets contained only "
            "military papers, they would smell a trap immediately. So Montagu and Cholmondeley created "
            "the most intricate legend in espionage history—what spies call pocket litter. Because you "
            "cannot photograph a corpse and make him look alive, Montagu found a living lookalike in MI5 "
            "named Captain Ronnie Reed to pose for Identity Card zero-nine-five-eight-four, rubbing the "
            "card on his trousers for weeks to give it authentic pocket wear. Into Martin's pockets went "
            "two passionate love letters from a fictional fiancée named Pam—actually MI5 secretary Jean "
            "Leslie, who even contributed a snapshot of herself in a bathing suit—along with a bill for "
            "a fifty-three-pound diamond engagement ring from a Bond Street jeweler, an angry overdraft "
            "warning from Lloyds Bank, and two ticket stubs from the Prince of Wales Theatre dated April "
            "twenty-second. And inside the chained briefcase sat the crown jewel: a personal, top-secret "
            "letter from General Sir Archibald Nye, Vice-Chief of the Imperial General Staff, to General "
            "Sir Harold Alexander in Tunisia. It casually revealed that Sicily was merely a fake cover "
            "story for the real Allied double-invasion: Greece under Operation Husky, and Sardinia under "
            "Operation Brimstone."
        ),
        "historical_grounding": {
            "era": "March–April 1943",
            "key_figures": ["General Sir Archibald Nye", "General Sir Harold Alexander", "Jean Leslie ('Pam')"],
            "defensive_specs": "Personal Vice-Chief to Commander-in-Chief letter bypassing official signals to explain 'cover target'",
            "primary_source": "Archibald Nye Deception Letter (Dated April 23, 1943, National Archives CAB 154/61)",
            "primary_quote": "We have a good chance of making them think we will go for Sicily—it is an obvious objective and one about which they must be nervous.",
        },
        "seed_shots": [
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 overhead macro flat-lay shot of Major William Martin's wallet contents on a wooden desk: Naval ID card, black-and-white photo of a 1940s woman, theatre ticket stubs, jeweler receipt, keys, and silver coins, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival document callout of General Sir Archibald Nye's personal letter to General Alexander with a real black eyelash trapped inside the wax envelope seal",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 medium shot of an MI5 officer sealing an official War Office envelope with red sealing wax and slowly tucking a single tiny dark eyelash under the flap for tamper detection, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 strategic deception map contrasting the fake Allied landing arrows pointing at Kalamata (Greece) and Sardinia against the true target of Sicily",
            },
        ],
    },
    {
        "title": "HMS Seraph and the Midnight Canister Drop off Spain",
        "est_start_sec": 400.0,
        "est_end_sec": 495.0,
        "rag_query": "HMS Seraph Lieutenant Bill Jewell Holy Loch canister dry ice April 30 1943 Huelva",
        "script": (
            "On April seventeenth, 1943, the dressed body of Major Martin was packed inside a custom "
            "four-hundred-pound steel cylinder insulated with twenty-one pounds of dry ice. The sublimating "
            "carbon dioxide displaced all oxygen inside the tube, keeping the body preserved without "
            "freezing it.Montagu and Cholmondeley drove the canister overnight in a Fordson van to Holy "
            "Loch in Scotland and loaded it aboard the Royal Navy submarine HMS Seraph, commanded by "
            "Lieutenant Bill Jewell. Jewell told his crew the steel cylinder labeled Optical Instruments "
            "was a top-secret meteorological buoy. For eleven days, HMS Seraph slipped past German U-boat "
            "patrols and depth charges through the Bay of Biscay. At four-fifteen in the morning on April "
            "thirtieth, one mile off the mouth of the Huelva River—chosen because its strong onshore "
            "current led directly to a town where German Abwehr agent Adolf Clauss operated freely with "
            "corrupt Spanish officials—Jewell ordered all enlisted crew below deck. Five officers opened "
            "the canister on the wet submarine casing, read Psalm thirty-nine aloud, inflated the life "
            "vest, and pushed Major William Martin into the tide."
        ),
        "historical_grounding": {
            "era": "April 19–30, 1943 (Holy Loch to Huelva Coast)",
            "key_figures": ["Lt. Norman 'Bill' Jewell", "HMS Seraph (P219)", "Abwehr Agent Adolf Clauss"],
            "defensive_specs": "400-lb airtight steel canister packed with dry ice; dropped at 04:15 hrs on April 30, 1943",
            "primary_source": "HMS Seraph Patrol Log (ADM 199/1847) & Lt. Bill Jewell Operational Report",
            "primary_quote": "At 0415 the canister was opened on the forward casing, the 39th Psalm was read, and Major Martin was slipped into the inshore current.",
        },
        "seed_shots": [
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 dramatic night wide shot of a British S-class submarine (HMS Seraph) surfaced in dark choppy Atlantic waves off the Spanish coast under a crescent moon, 8k",
            },
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 tense medium shot of five British Royal Navy submarine officers in dark wool sweaters on the wet forward deck casing opening a heavy bolted steel cylinder at night, 8k",
            },
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 naval navigation map tracking HMS Seraph's 11-day voyage from Holy Loch Scotland around the Iberian Peninsula to the exact drop point 1 mile off Huelva",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 close-up of a heavy grey steel cylinder stamped 'HANDLE WITH CARE - OPTICAL INSTRUMENTS' with frost forming around the bolted lid, 8k",
            },
        ],
    },
    {
        "title": "The Eyelash Trap and the Enigma Intercepts at Bletchley Park",
        "est_start_sec": 495.0,
        "est_end_sec": 595.0,
        "rag_query": "Adolf Clauss Karl-Erich Kuhlenthal Bletchley Park Ultra Enigma intercept Mincemeat swallowed whole",
        "script": (
            "In Huelva, the Spanish autopsy lasted less than thirty minutes. Exhausted by the midday "
            "heat and the smell of decomposition, Doctor Eduardo Fernandez del Torno certified death by "
            "asphyxiation through immersion in the sea. Major William Martin was buried with full military "
            "honors at the cemetery of Nuestra Senora de la Soledad on May second. Meanwhile, behind closed "
            "doors, pro-German elements in the Spanish Navy handed the wet leather briefcase to Major "
            "Karl-Erich Kuhlenthal of the German Abwehr in Madrid. Using steaming needles and delicate "
            "forceps, German technicians extracted the letters without breaking the wax seals, photographed "
            "every page on Leica microfilm, dried the paper, folded the letters back inside, and returned "
            "the briefcase to the British Embassy. When MI5 flew the briefcase back to London and examined "
            "the letters under ultraviolet light, the tiny black eyelash Montagu had placed inside the "
            "fold was gone—and the paper fibers showed microscopic salt-water drying rings. Days later, "
            "codebreakers at Bletchley Park decrypted a top-secret German Ultra Enigma telegram from "
            "Berlin High Command: the landings in the Peloponnese of Greece were designated top priority. "
            "Montagu sent a three-word cable to Winston Churchill in Washington: Mincemeat swallowed whole."
        ),
        "historical_grounding": {
            "era": "May 2–14, 1943 (Huelva, Madrid, Bletchley Park, London)",
            "key_figures": ["Dr. Eduardo Fernández del Torno", "Major Karl-Erich Kühlenthal (Abwehr)", "Bletchley Park Codebreakers"],
            "defensive_specs": "Missing eyelash tamper trap; Bletchley Park Ultra decrypt confirming OKW order of May 12, 1943",
            "primary_source": "Bletchley Park Ultra Decrypts (HW 1/1677) & Churchill Cable ('Mincemeat Swallowed Whole')",
            "primary_quote": "The Fuhrer does not agree with Duce that the most likely invasion point is Sicily. Furthermore, he believes that the discovered Anglo-Saxon order confirms the assumption that the planned attacks will be directed mainly against Sardinia and the Peloponnese.",
        },
        "seed_shots": [
            {
                "shot_type": "Medium Troop",
                "prompt": "16:9 suspenseful medium shot of German intelligence technicians in a dark Madrid room using a Leica camera on a copy stand to photograph British War Office letters by red safelight, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 archival callout of Adolf Hitler's May 1943 OKW Directive ordering reinforcements to Greece, paired with Ewen Montagu's cable 'MINCEMEAT SWALLOWED WHOLE'",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 forensic laboratory close-up of a British expert examining the unsealed War Office letter with a magnifying glass and tweezers under a bright forensic lamp, 8k",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 cinematic shot of the sunlit Spanish cemetery in Huelva as a British vice-consul and Spanish naval officers stand beside the white marble grave of Major William Martin, 8k",
            },
        ],
    },
    {
        "title": "The Payoff: Hitler Moves His Panzers and 10,000 Lives Are Saved",
        "est_start_sec": 595.0,
        "est_end_sec": 685.0,
        "rag_query": "1st Panzer Division moved to Greece Operation Husky July 10 1943 Glyndwr Michael grave inscription",
        "script": (
            "The strategic fallout was immediate and catastrophic for Nazi Germany. Convinced by the "
            "briefcase from Huelva, Adolf Hitler overruled Benito Mussolini and Field Marshal Kesselring. "
            "He ordered the elite First Panzer Division transferred all the way from France to Greece. "
            "He diverted German E-boat naval flotillas from Sicily to the Aegean Sea, laid three new "
            "minefields off the Greek coast, and dispatched Field Marshal Erwin Rommel to Athens to take "
            "command. When one hundred and sixty thousand Allied soldiers stormed the beaches of Sicily "
            "at dawn on July tenth, 1943, they caught Axis defenders completely off balance. Even after "
            "Allied troops were ashore on Sicilian soil, Hitler remained so mesmerized by Major Martin's "
            "letter that he waited twenty-four critical hours before releasing reserves, convinced Sicily "
            "was still the diversion. British commanders estimated expected first-week casualties at ten "
            "thousand dead and wounded; actual casualties were a fraction of that, and Sicily fell in "
            "thirty-eight days, toppling Mussolini's regime. Today, on the quiet white marble headstone "
            "in Huelva, Spain, beneath the name of Major William Martin, a second inscription is carved "
            "in stone: Glyndwr Michael; Served as Major William Martin, RM. A homeless man who had nothing "
            "in life had altered the course of World War Two in death."
        ),
        "historical_grounding": {
            "era": "July 10, 1943 – Present",
            "key_figures": ["Field Marshal Erwin Rommel", "Adolf Hitler", "Glyndwr Michael"],
            "defensive_specs": "1st Panzer Division redeployed from France to Peloponnese; German R-boats moved from Sicily to Aegean",
            "primary_source": "OKW War Diary (May–July 1943) & Commonwealth War Graves Commission (Huelva Grave)",
            "primary_quote": "Glyndwr Michael; Served as Major William Martin, RM.",
        },
        "seed_shots": [
            {
                "shot_type": "Tactical Map",
                "prompt": "16:9 animated strategic map of Europe in June 1943 showing the 1st Panzer Division moving east to Greece while Allied Operation Husky amphibious task forces converge on Sicily",
            },
            {
                "shot_type": "Wide Establishing",
                "prompt": "16:9 epic dawn wide shot of hundreds of Allied landing craft and warships approaching the golden beaches of Sicily on July 10 1943, naval guns flashing on the horizon, 8k",
            },
            {
                "shot_type": "Macro Detail",
                "prompt": "16:9 poignant close-up of the white marble gravestone in Huelva Spain engraved with 'William Martin' and 'Glyndwr Michael; Served as Major William Martin, RM', fresh red poppies resting on the stone, 8k",
            },
            {
                "shot_type": "Primary Source",
                "prompt": "16:9 final historiographical tribute card summarizing Operation Mincemeat's casualty reduction and Commonwealth War Graves recognition in 1997",
            },
        ],
    },
]


# ==============================================================================
# DERIVED SHORTS MANIFESTS (15 VIRAL SHORTS ACROSS WEEKS 2, 3, AND 4)
# ==============================================================================
SHORTS_MANIFEST = {
    "week_2_bronze_age_collapse": [
        {
            "short_id": "w2_short_01",
            "title": "The Unsent Clay Letter Baked by a Burning Empire (1177 BC)",
            "source_act": 1,
            "start_sec": 0.0,
            "duration_sec": 44.0,
            "hook_script": (
                "In the ashes of a destroyed Syrian palace, archaeologists found a royal clay letter that "
                "never made it into the kiln—it was baked hard by the flames of the burning palace itself. "
                "King Ammurapi of Ugarit wrote: 'My father, behold, the enemy ships came. My cities were "
                "burned, and they did evil things in my country.' Forty-eight hours later, Ugarit was erased "
                "under six feet of ash. Watch the full documentary on how eight empires collapsed at once."
            ),
        },
        {
            "short_id": "w2_short_02",
            "title": "Why 8 Ancient Superpowers Depended on One Single Ship",
            "source_act": 2,
            "start_sec": 92.0,
            "duration_sec": 45.0,
            "hook_script": (
                "In 1200 BC, every army from Greece to Egypt depended on a single military metal: bronze. "
                "To make it, kings needed nine parts copper from Cyprus and one part tin hauled three "
                "thousand miles by donkey from Afghanistan. On a single sunken hull at Uluburun, divers "
                "found ten tons of copper and one ton of tin—enough to equip an entire Bronze Age army. "
                "When that supply chain snapped, the ancient world went dark."
            ),
        },
        {
            "short_id": "w2_short_03",
            "title": "Who Were the Mysterious Sea Peoples of 1177 BC?",
            "source_act": 4,
            "start_sec": 284.0,
            "duration_sec": 45.0,
            "hook_script": (
                "They toppled the Hittite Empire, burned Mycenae, and erased Ugarit—yet for centuries "
                "nobody knew where the Sea Peoples came from. Look closely at the carved walls of Medinet "
                "Habu in Egypt: behind the warriors in horned helmets and slashing bronze swords roll wooden "
                "ox-carts carrying women, children, and livestock. This wasn't a pirate raid—it was an "
                "armed migration of starving nations."
            ),
        },
        {
            "short_id": "w2_short_04",
            "title": "How Ramesses III Trapped the Sea Peoples in the Nile",
            "source_act": 6,
            "start_sec": 485.0,
            "duration_sec": 44.0,
            "hook_script": (
                "By 1177 BC, every empire in the Mediterranean had burned except Egypt. Knowing he couldn't "
                "beat the Sea Peoples' armada on the open sea, Pharaoh Ramesses the Third lured their ships "
                "into the narrow, reed-choked channels of the Nile Delta. Egyptian warships sealed the exit "
                "behind them while thousands of hidden archers opened fire from both mudbanks—saving Egypt "
                "from total annihilation."
            ),
        },
        {
            "short_id": "w2_short_05",
            "title": "The Collapse That Made Humanity Forget How to Write",
            "source_act": 7,
            "start_sec": 585.0,
            "duration_sec": 42.0,
            "hook_script": (
                "The Bronze Age Collapse of 1177 BC was so severe that population in Greece dropped by "
                "seventy-five percent, stone architecture stopped, and the Mycenaeans completely forgot "
                "how to read and write for four hundred years. Yet because tin shipments from Afghanistan "
                "were cut off forever, blacksmiths turned to a stubborn metal under their own feet: iron."
            ),
        },
    ],
    "week_3_cambyses_lost_army": [
        {
            "short_id": "w3_short_01",
            "title": "How 50,000 Persian Soldiers Vanished Without a Trace",
            "source_act": 1,
            "start_sec": 0.0,
            "duration_sec": 45.0,
            "hook_script": (
                "In 524 BC, fifty thousand elite Persian soldiers marched out of Thebes into the Egyptian "
                "Western Desert to burn the sacred Oracle of Amun at Siwa. Seven days later, they resupplied "
                "at El Kharga oasis, walked into the towering dunes of the Great Sand Sea—and vanished from "
                "the face of the earth. Not a single soldier ever walked back out."
            ),
        },
        {
            "short_id": "w3_short_02",
            "title": "Why the King of Persia Declared War on a Desert Oracle",
            "source_act": 2,
            "start_sec": 88.0,
            "duration_sec": 43.0,
            "hook_script": (
                "When Persian King Cambyses the Second conquered Egypt in 525 BC, the priests at the remote "
                "Siwa Oasis refused to recognize him as a legitimate Pharaoh and prophesied his death. "
                "Furious, Cambyses dispatched fifty thousand troops across four hundred miles of waterless "
                "sand dunes to burn the temple to the ground—triggering the greatest disappearance in "
                "ancient military history."
            ),
        },
        {
            "short_id": "w3_short_03",
            "title": "Buried Alive at Midday: The Khamsin Superstorm of 524 BC",
            "source_act": 4,
            "start_sec": 265.0,
            "duration_sec": 44.0,
            "hook_script": (
                "According to the Greek historian Herodotus, Cambyses's army had reached the halfway mark "
                "in the Great Sand Sea and stopped for their midday meal when a violent south wind struck—the "
                "Egyptian Khamsin. With seventy-mile-per-hour gusts and temperatures spiking past one hundred "
                "and thirty degrees, the storm blinded the guides, buried their water jars, and swallowed "
                "the column whole."
            ),
        },
        {
            "short_id": "w3_short_04",
            "title": "What Archaeologists Found in the Sahara Dunes in 2009",
            "source_act": 5,
            "start_sec": 360.0,
            "duration_sec": 44.0,
            "hook_script": (
                "For centuries, historians thought the Lost Army of Cambyses was a myth. Then explorers "
                "searched the southern desert bypass near Sitra Lake south of Siwa—and uncovered shattered "
                "water amphorae, fifth-century BC Persian trilobate bronze arrowheads, a corroded Achaemenid "
                "bronze dagger, and bleached human bones protruding from a wind-scoured limestone ridge."
            ),
        },
        {
            "short_id": "w3_short_05",
            "title": "Was Cambyses's Lost Army Actually Ambushed? (The 2014 Clue)",
            "source_act": 6,
            "start_sec": 455.0,
            "duration_sec": 45.0,
            "hook_script": (
                "In 2014, archaeologists excavating Dakhla Oasis decoded inscriptions of a forgotten Egyptian "
                "rebel Pharaoh named Petubastis the Third—whose guerrilla base sat directly in the path of "
                "Cambyses's marching army. Did Petubastis ambush and slaughter the storm-blinded Persian "
                "column, only for Darius the Great to blame a sandstorm to cover up the military disaster?"
            ),
        },
    ],
    "week_4_operation_mincemeat": [
        {
            "short_id": "w4_short_01",
            "title": "How a Dead Homeless Man Fooled Hitler and Saved 10,000 Troops",
            "source_act": 1,
            "start_sec": 0.0,
            "duration_sec": 45.0,
            "hook_script": (
                "On April 30, 1943, Spanish fishermen pulled the body of a British Royal Marines officer "
                "from the surf with a top-secret leather briefcase chained to his belt. Inside were Allied "
                "invasion plans that convinced Adolf Hitler to move his Panzer divisions away from Sicily "
                "to Greece. The twist? Major William Martin never existed—he was a penniless Welshman who "
                "had died in London three months earlier."
            ),
        },
        {
            "short_id": "w4_short_02",
            "title": "The Fake Fiancée and Pocket Litter Inside Major Martin's Coat",
            "source_act": 4,
            "start_sec": 295.0,
            "duration_sec": 45.0,
            "hook_script": (
                "To make Nazi spies believe a dead courier was real, British MI5 filled his pockets with "
                "an entire fake life: love letters from a fictional fiancée named Pam, a bill for a "
                "fifty-three-pound diamond engagement ring on Bond Street, an angry overdraft letter from "
                "Lloyds Bank, and London theatre ticket stubs from eight days before his body washed ashore."
            ),
        },
        {
            "short_id": "w4_short_03",
            "title": "The 400-Pound Dry Ice Canister Aboard HMS Seraph",
            "source_act": 5,
            "start_sec": 400.0,
            "duration_sec": 44.0,
            "hook_script": (
                "How do you carry a corpse on a submarine for eleven days without the crew finding out? "
                "In April 1943, MI5 packed the body of Major William Martin inside a four-hundred-pound "
                "airtight steel cylinder filled with dry ice and stamped 'Optical Instruments.' At 4:15 AM "
                "off the Spanish coast, five officers sent the crew below, read Psalm 39, and pushed him "
                "into the tide."
            ),
        },
        {
            "short_id": "w4_short_04",
            "title": "How a Single Black Eyelash Proved Nazi Spies Took the Bait",
            "source_act": 6,
            "start_sec": 495.0,
            "duration_sec": 44.0,
            "hook_script": (
                "Before sealing the fake Allied invasion letter inside Major Martin's briefcase, MI5 officer "
                "Ewen Montagu tucked a single tiny black eyelash inside the fold of the paper. When the "
                "Spanish Navy returned the briefcase as 'unopened,' the eyelash was gone—proving German "
                "spies had steamed open the envelope, photographed the fake plans, and sent them straight "
                "to Hitler."
            ),
        },
        {
            "short_id": "w4_short_05",
            "title": "Why Hitler Moved His Panzers to Greece Right Before Sicily",
            "source_act": 7,
            "start_sec": 595.0,
            "duration_sec": 43.0,
            "hook_script": (
                "Fooled by the fake briefcase found off Spain, Adolf Hitler overruled Mussolini, sent the "
                "First Panzer Division from France all the way to Greece, and dispatched Erwin Rommel to "
                "Athens. When 160,000 Allied troops stormed Sicily on July 10, 1943, Hitler still held "
                "back reserves for 24 hours—convinced Sicily was a diversion."
            ),
        },
    ],
}


def build_documentary_json(video_title: str, acts_spec: list, event_slug: str, shorts_list: list) -> dict:
    acts = build_80_shots_for_acts(acts_spec, event_slug)
    total_words = sum(len(a["script"].split()) for a in acts)
    target_runtime = acts[-1]["est_end_sec"]
    return {
        "channel": "Chronos Shift (@ChronosShiftHistory)",
        "video_title": video_title,
        "event_slug": event_slug,
        "mode": "factual",
        "aspect_ratio": "16:9",
        "target_runtime_seconds": target_runtime,
        "total_word_count": total_words,
        "target_wpm": 145,
        "total_visual_shots": 80,
        "average_shot_duration_sec": round(target_runtime / 80.0, 2),
        "acts": acts,
        "derived_shorts": shorts_list,
    }


def main():
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    configs = [
        (
            "bronze_age_collapse_1177bc_80shots.json",
            "1177 BC: The Year Civilization Reset (The Bronze Age Collapse)",
            WEEK_2_ACTS,
            "bronze_age_collapse_1177bc",
            SHORTS_MANIFEST["week_2_bronze_age_collapse"],
        ),
        (
            "cambyses_lost_army_524bc_80shots.json",
            "50,000 Men Vanished: The Lost Army of Cambyses (524 BC)",
            WEEK_3_ACTS,
            "cambyses_lost_army_524bc",
            SHORTS_MANIFEST["week_3_cambyses_lost_army"],
        ),
        (
            "operation_mincemeat_1943_80shots.json",
            "The Corpse That Fooled Hitler: Operation Mincemeat (1943)",
            WEEK_4_ACTS,
            "operation_mincemeat_1943",
            SHORTS_MANIFEST["week_4_operation_mincemeat"],
        ),
    ]

    for filename, title, acts_spec, slug, shorts_list in configs:
        out_path = DRAFTS_DIR / filename
        payload = build_documentary_json(title, acts_spec, slug, shorts_list)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(
            f"[OK] Wrote {out_path.name}: {len(payload['acts'])} acts, "
            f"{payload['total_visual_shots']} shots, "
            f"{len(payload['derived_shorts'])} derived Shorts, "
            f"{payload['total_word_count']} narration words."
        )


if __name__ == "__main__":
    main()