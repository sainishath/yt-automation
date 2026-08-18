# -*- coding: utf-8 -*-
"""
test_convo_qa_v2.py
-------------------
Comprehensive Unit Test Suite for Pipeline 2 Conversation QA V3 Layer.
Tests all 19 mandatory conversational quality, duration, initiative, and balance rules.
"""

import sys
import unittest
from pathlib import Path

# Add engine directory to path
engine_dir = Path(__file__).parent
sys.path.insert(0, str(engine_dir))

from media_engine import validate_and_analyze_conversation


class TestConversationQAV2(unittest.TestCase):

    def test_01_word_balance_exceeds_max_fails(self):
        """TEST 1: Speaker B = 63.3% (> 60.0%) MUST FAIL (Bug Fix Test)."""
        lines = [
            {"speaker": "A", "role": "hook", "information_beat": "ocean darkness", "text": "Deep in the ocean there is zero sunlight reaching the benthic floor."},
            {"speaker": "B", "role": "expand", "information_beat": "bioluminescence", "text": "That is right, but what is even more astonishing is how creatures produce light chemically inside their bodies to survive in this pitch dark realm."},
            {"speaker": "A", "role": "question", "information_beat": "lure", "text": "Do anglerfish use that bioluminescent light to hunt for food?"},
            {"speaker": "B", "role": "explain", "information_beat": "anglerfish biochemical lure", "text": "For example, the anglerfish uses a glowing lure on top of its head to attract prey in the dark depths using specialized enzymes, pigments, and oxygen."},
            {"speaker": "A", "role": "question", "information_beat": "luciferin", "text": "How does the chemical reaction work inside their bodies?"},
            {"speaker": "B", "role": "expand", "information_beat": "luciferin oxidation", "text": "It involves the oxidation of a molecule called luciferin, which reacts with oxygen to produce cold light without emitting thermal energy."},
            {"speaker": "A", "role": "question", "information_beat": "squid", "text": "What about squids in the deep sea?"},
            {"speaker": "B", "role": "expand", "information_beat": "squid communication", "text": "Some species of squid use their glowing spots to signal aggression or courtship in the dark sea."},
            {"speaker": "A", "role": "summarize", "information_beat": "summary", "text": "That is a truly remarkable biological adaptation."},
            {"speaker": "B", "role": "expand", "information_beat": "fungi payoff", "text": "And there are also glowing fungi and bacteria, showing the incredible adaptability of life on Earth across ecosystems."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Speaker B at 63.3% must fail validation.")
        self.assertTrue(any("ratio too high" in e for e in errors))

    def test_02_word_balance_ideal_passes(self):
        """TEST 2: Speaker B = 50.0% MUST PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "deep ocean darkness", "text": "Did you know deep ocean creatures can generate their own glowing light in pitch black darkness where sunlight cannot reach?"},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence lure", "text": "Yeah! An anglerfish uses a glowing lure on its head to attract unsuspecting prey right into its sharp mouth."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing bright light make them much easier targets for larger hungry predators swimming nearby?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "text": "Normally yes, but counter-illumination matches the faint light coming from above to completely erase their dark silhouette."},
            {"speaker": "A", "role": "connect", "interaction_type": "connect", "information_beat": "survival strategies", "text": "So the exact same glowing light helps one animal hunt for prey and another animal hide from predators."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "evolutionary impact", "text": "Exactly. It shows how extreme biological adaptation drives deep sea survival in Earth's harshest environment."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Speaker B at 50% must pass. Errors: {errors}")

    def test_03_repeated_role_streak_fails(self):
        """TEST 3: Speaker B having 4+ consecutive 'expand' roles MUST FAIL (Monotony Risk)."""
        lines = [
            {"speaker": "A", "role": "hook", "information_beat": "ocean darkness", "text": "Deep sea animals live in total pitch black darkness where no sunlight ever reaches."},
            {"speaker": "B", "role": "explain", "information_beat": "bioluminescence", "text": "They produce light using chemical reactions inside their cells."},
            {"speaker": "A", "role": "question", "information_beat": "anglerfish", "text": "How do anglerfish hunt for food?"},
            {"speaker": "B", "role": "explain", "information_beat": "anglerfish lure", "text": "They produce light through chemical reactions in their lure."},
            {"speaker": "A", "role": "question", "information_beat": "chemistry", "text": "What chemical is used for glowing?"},
            {"speaker": "B", "role": "explain", "information_beat": "luciferin", "text": "They produce light through chemical reactions involving luciferin."},
            {"speaker": "A", "role": "question", "information_beat": "squids", "text": "How do squids use glowing spots?"},
            {"speaker": "B", "role": "explain", "information_beat": "squid camouflage", "text": "They produce light through chemical reactions on their skin."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Consecutive identical role streaks for Speaker B must fail.")
        self.assertTrue(any("monotony" in e.lower() or "role" in e.lower() for e in errors))

    def test_04_balanced_substantive_dialogue_passes(self):
        """TEST 4: Both A and B have substantive information & varied roles -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "deep sea habitat", "text": "Sunlight vanishes completely one thousand meters underwater where extreme hydrostatic pressure rules supreme across the abyss floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemical reaction", "text": "Yet creatures generate their own light through luciferin chemical reactions inside their specialized cellular photophore organs."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator threat", "text": "Wait, wouldn't glowing expose them to hungry predators searching for easy meals in the dark ocean?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "text": "Counter-illumination matches the faint light from above to completely erase their dark silhouette against the sky."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "While anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their open razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid flash defense", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Balanced substantive dialogue must pass. Errors: {errors}")

    def test_05_speaker_b_question_only_fails(self):
        """TEST 5: Speaker B asking only questions MUST FAIL."""
        lines = [
            {"speaker": "A", "role": "explain", "information_beat": "deep ocean", "text": "Deep sea creatures produce light using bioluminescence chemical reactions in total darkness."},
            {"speaker": "B", "role": "question", "information_beat": "", "text": "Wait, really? How do they do that?"},
            {"speaker": "A", "role": "explain", "information_beat": "luciferin", "text": "They mix luciferin with oxygen and luciferase enzymes inside specialized light organs."},
            {"speaker": "B", "role": "question", "information_beat": "", "text": "Is that why anglerfish glow in the dark?"},
            {"speaker": "A", "role": "explain", "information_beat": "anglerfish lure", "text": "Yes, anglerfish dangle a glowing lure to attract prey right into their open jaws."},
            {"speaker": "B", "role": "question", "information_beat": "", "text": "Does it work for squid too?"}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Question-only Speaker B must fail.")

    def test_06_speaker_b_reaction_only_fails(self):
        """TEST 6: Speaker B saying only short reactions MUST FAIL."""
        lines = [
            {"speaker": "A", "role": "explain", "information_beat": "deep ocean", "text": "Deep ocean creatures generate light in total darkness using chemical reactions."},
            {"speaker": "B", "role": "react", "information_beat": "", "text": "That is crazy."},
            {"speaker": "A", "role": "explain", "information_beat": "bioluminescence lure", "text": "Anglerfish use glowing lures to trap prey in the pitch black sea."},
            {"speaker": "B", "role": "react", "information_beat": "", "text": "No way, seriously?"},
            {"speaker": "A", "role": "explain", "information_beat": "vampire squid", "text": "Vampire squids shoot glowing mucus to confuse hungry predators."},
            {"speaker": "B", "role": "react", "information_beat": "", "text": "That is mind blowing."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Reaction-only Speaker B must fail.")

    def test_07_speaker_a_monopolizes_info_fails(self):
        """TEST 7: Speaker A owning all information beats MUST FAIL."""
        lines = [
            {"speaker": "A", "role": "hook", "information_beat": "deep ocean darkness", "text": "Deep ocean creatures live in pitch black water with zero natural sunlight."},
            {"speaker": "A", "role": "explain", "information_beat": "bioluminescence mechanism", "text": "They produce light through luciferin chemical reactions inside specialized light cells."},
            {"speaker": "A", "role": "example", "information_beat": "anglerfish lure", "text": "Anglerfish use glowing lures to hunt prey in the deep ocean depths."},
            {"speaker": "A", "role": "reveal", "information_beat": "counterillumination", "text": "Squids use counter-illumination for camouflage against hungry predators below."},
            {"speaker": "B", "role": "react", "information_beat": "", "text": "That is an interesting fact."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Speaker A monopolizing information beats must fail.")

    def test_08_speaker_b_monopolizes_info_fails(self):
        """TEST 8: Speaker B owning all information beats MUST FAIL."""
        lines = [
            {"speaker": "A", "role": "question", "information_beat": "", "text": "Why do deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "information_beat": "bioluminescence mechanism", "text": "They produce light through luciferin chemical reactions inside their bodies."},
            {"speaker": "B", "role": "example", "information_beat": "anglerfish lure", "text": "Anglerfish use glowing lures on their heads to attract prey right to them."},
            {"speaker": "B", "role": "reveal", "information_beat": "counterillumination", "text": "And squids use counter-illumination to match light coming from above."},
            {"speaker": "B", "role": "summarize", "information_beat": "evolutionary payoff", "text": "It is the ultimate survival adaptation in total deep sea darkness."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Speaker B monopolizing information beats must fail.")

    def test_09_estimated_duration_too_long_fails(self):
        """TEST 9: Pre-TTS estimated duration > 58s MUST FAIL."""
        long_text = "word " * 180
        lines = [
            {"speaker": "A", "role": "hook", "information_beat": "darkness", "text": long_text[:90]},
            {"speaker": "B", "role": "explain", "information_beat": "bioluminescence", "text": long_text[90:]}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Script with estimated duration > 58s must fail.")
        self.assertTrue(any("duration" in e.lower() for e in errors))

    def test_10_second_narrator_two_monologues_fails(self):
        """TEST 10: Two alternating independent factual paragraphs with low interaction MUST FAIL."""
        lines = [
            {"speaker": "A", "role": "explain", "information_beat": "deep ocean", "text": "The deep ocean contains extreme pressure and zero sunlight reaching below one thousand meters depth in the abyss."},
            {"speaker": "B", "role": "explain", "information_beat": "bioluminescence definition", "text": "Bioluminescence is defined as light production by living organisms using specialized luciferin and luciferase enzymes inside photophores."},
            {"speaker": "A", "role": "explain", "information_beat": "anglerfish anatomy", "text": "Anglerfish possess an esca lure attached to their illicium bone structure that glows in total darkness."},
            {"speaker": "B", "role": "explain", "information_beat": "squid anatomy", "text": "Photophores are specialized light-emitting organs found along the ventral surface of oceanic squids for camouflage."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Second-narrator behavior (two independent monologues) must fail.")
        self.assertTrue(any("second-narrator" in e.lower() or "interaction" in e.lower() for e in errors))

    def test_11_natural_uneven_convo_passes(self):
        """TEST 11: Natural conversation with 45-55% word split MUST PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "darkness habitat", "text": "Sunlight vanishes completely one thousand meters beneath the ocean surface where darkness reigns supreme across the benthic depths."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemistry", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cell structures."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "text": "Counter-illumination matches faint light from above so predators below see no dark silhouette against the surface."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "While anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from threats."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Natural 45-55% conversation must pass. Errors: {errors}")

    def test_12_speaker_b_independent_initiative_passes(self):
        """TEST 12: Speaker B introduces multiple information beats independently -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "abyssal darkness", "text": "Did you know that below one thousand meters underwater sunlight is completely non-existent in the ocean abyssal depths?"},
            {"speaker": "B", "role": "reveal", "interaction_type": "lead", "information_beat": "bioluminescence luciferin", "text": "And that is where biological light takes over through a luciferin oxidation chemical reaction inside their cells!"},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator risk", "text": "Wait, but glowing in total darkness sounds like a beacon for larger hungry predators swimming nearby."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "counterillumination mechanism", "text": "Here is the catch: counter-illumination matches faint surface light from above to completely erase their dark silhouette."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "While anglerfish dangle a glowing esca lure like a fishing pole right in front of their open mouth."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid mucus cloud", "text": "And vampire squids shoot a glowing cloud of bioluminescent blue mucus to instantly blind attackers."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Speaker B with independent initiative beats must pass. Errors: {errors}")

    def test_13_speaker_b_only_responds_fails(self):
        """TEST 13: Speaker B only responds to A and never introduces a new concept -> FAIL."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "darkness", "text": "Deep sea animals live in pitch black water where sunlight never penetrates into the abyssal ocean depths."},
            {"speaker": "B", "role": "reaction", "interaction_type": "respond", "information_beat": "", "text": "Exactly! That makes sense."},
            {"speaker": "A", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence", "text": "They produce light chemically using luciferin and luciferase enzymes inside specialized light organs."},
            {"speaker": "B", "role": "reaction", "interaction_type": "respond", "information_beat": "", "text": "Right! Wow."},
            {"speaker": "A", "role": "example", "interaction_type": "lead", "information_beat": "anglerfish lure", "text": "Anglerfish dangle glowing lures to attract prey right into their sharp open razor jaws."},
            {"speaker": "B", "role": "reaction", "interaction_type": "respond", "information_beat": "", "text": "Yes! Unbelievable."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Speaker B with zero initiative beats must fail.")
        self.assertTrue(any("initiative" in e.lower() for e in errors))

    def test_14_alternating_monologues_no_interaction_fails(self):
        """TEST 14: Alternating turns with 0 conversational interaction -> FAIL."""
        lines = [
            {"speaker": "A", "role": "explain", "interaction_type": "lead", "information_beat": "ocean pressure", "text": "The abyssal zone features extreme hydrostatic pressure exceeding one thousand atmospheres."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "chemical reaction", "text": "Bioluminescence occurs through enzyme-catalyzed oxidation of luciferin molecules in specialized cells."},
            {"speaker": "A", "role": "explain", "interaction_type": "lead", "information_beat": "anglerfish morphology", "text": "Ceratioid anglerfish exhibit extreme sexual dimorphism alongside glowing modified dorsal fins."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "squid photophores", "text": "Ventral photophores on bioluminescent squid adjust light emission based on downwelling irradiance."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Alternating monologues with zero interaction must fail.")

    def test_15_natural_non_alternating_flow_passes(self):
        """TEST 15: Natural non-alternating flow (A -> B -> B -> A -> B) -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "abyssal darkness", "text": "Sunlight vanishes completely one thousand meters underwater where extreme hydrostatic pressure rules supreme across the dark benthic abyss."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemistry", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cell structures."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "luciferin oxidation", "text": "That light is produced when luciferin reacts with oxygen without emitting any heat energy at all!"},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark ocean?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "text": "Counter-illumination matches faint surface light from above so predators below see zero dark silhouette."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Natural non-alternating flow must pass. Errors: {errors}")

    def test_16_speaker_b_question_and_new_concept_passes(self):
        """TEST 16: Speaker B asks a meaningful question and introduces a new concept -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "darkness habitat", "text": "Did you know deep ocean creatures live in pitch black water where sunlight never penetrates?"},
            {"speaker": "B", "role": "challenge", "interaction_type": "lead", "information_beat": "predator question", "text": "Wait—if these animals produce light in total darkness, wouldn't that make them easier for predators to spot?"},
            {"speaker": "A", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination", "text": "Normally yes, but counter-illumination matches light from above so predators below see zero silhouette."},
            {"speaker": "B", "role": "reveal", "interaction_type": "lead", "information_beat": "vampire squid defense", "text": "And here is where it gets strange: vampire squids shoot glowing bioluminescent clouds of mucus to blind attackers!"},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "While anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their open jaws."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Speaker B asking meaningful question + introducing new concept must pass. Errors: {errors}")

    def test_17_both_speakers_have_initiative_passes(self):
        """TEST 17: Both speakers have initiative beats -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "One thousand meters beneath the ocean surface sunlight vanishes completely into eternal deep sea darkness across the benthic floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemistry", "text": "Yet deep sea creatures produce cold biological light using specialized luciferin chemical reactions inside photophore organs."},
            {"speaker": "A", "role": "reveal", "interaction_type": "lead", "information_beat": "anglerfish lure", "text": "Wait, anglerfish dangle glowing lures like fishing poles to snare unsuspecting prey in the pitch black sea."},
            {"speaker": "B", "role": "reveal", "interaction_type": "lead", "information_beat": "counterillumination camouflage", "text": "And squids use counter-illumination to erase their silhouette against faint light coming from above."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "adaptation summary", "text": "So it turns out biological light is one of nature's most extraordinary survival tools!"}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Both speakers having initiative beats must pass. Errors: {errors}")

    def test_18_fifty_fifty_two_narrators_no_interaction_fails(self):
        """TEST 18: Script is 50/50 word split but feels like two independent narrators -> FAIL."""
        lines = [
            {"speaker": "A", "role": "explain", "interaction_type": "lead", "information_beat": "deep sea zone", "text": "The abyssal bathypelagic zone encompasses regions devoid of natural sunlight penetration throughout marine environments."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "photophore biology", "text": "Organisms generate cold light via luciferin enzymatic pathways housed within ventral cutaneous photophore structures."},
            {"speaker": "A", "role": "explain", "interaction_type": "lead", "information_beat": "esca structure", "text": "Lophiiformes anglerfish possess an illicium appendicular organ functioning as a bioluminescent prey lure."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "squid photophores", "text": "Teuthoidea squids adjust photophore intensity dynamically to match downwelling ambient solar radiation levels."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "50/50 two independent narrators with zero interaction must fail.")

    def test_19_natural_asymmetric_45_55_convo_passes(self):
        """TEST 19: Natural asymmetric 45/55 conversation with initiative -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "darkness habitat", "text": "Sunlight vanishes completely one thousand meters underwater where eternal darkness reigns supreme."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemistry", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cell structures."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "text": "Counter-illumination matches faint light from above so predators below see no dark silhouette against the surface."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "While anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from threats."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Natural 45/55 conversation must pass. Errors: {errors}")

    def test_20_supported_factual_claim_passes(self):
        """TEST 20: Supported scientific claim -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "abyssal habitat", "text": "Did you know that below one thousand meters underwater sunlight is completely non-existent in the ocean abyssal depths where pressure rules supreme?"},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "luciferin chemical reaction", "claim": "Bioluminescence occurs through chemical reactions involving luciferin and oxygen.", "claim_type": "scientific_fact", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cell structures and photophore organs."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark ocean floor?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "claim": "Counter-illumination matches downwelling light to camouflage silhouettes.", "claim_type": "scientific_fact", "text": "Counter-illumination matches faint surface light from above so predators below see zero dark silhouette against the sky."},
            {"speaker": "A", "role": "summarize", "interaction_type": "summarize", "information_beat": "deep ocean adaptation", "text": "Nature has engineered perfect light solutions for the darkest ocean depths."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Supported factual claim must pass. Errors: {errors}")

    def test_21_contradicted_factual_claim_fails(self):
        """TEST 21: Clearly contradicted factual claim (e.g. only in low-oxygen) -> FAIL."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "abyssal darkness", "text": "Did you know deep ocean creatures can glow like tiny lanterns underwater in pitch black darkness where sunlight never reaches?"},
            {"speaker": "B", "role": "challenge", "interaction_type": "lead", "information_beat": "false mechanism claim", "claim": "Bioluminescence only occurs in low-oxygen environments.", "claim_type": "scientific_fact", "text": "But here's the catch: this reaction is only possible in low-oxygen environments deep in the sea."},
            {"speaker": "A", "role": "answer", "interaction_type": "answer", "information_beat": "jellyfish communication", "text": "Jellyfish use bioluminescence to communicate, find prey, and evade hungry marine predators swimming nearby."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "photophore organs", "text": "And some species even have specialized light-producing organs on their bellies for survival!"}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "Contradicted scientific claim must fail validation.")
        self.assertTrue(any("HIGH Severity" in e or "low-oxygen" in e for e in errors))

    def test_22_unsupported_high_severity_scientific_claim_fails(self):
        """TEST 22: High-severity false scientific mechanism -> FAIL."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "darkness habitat", "text": "Sunlight vanishes completely one thousand meters underwater where eternal darkness reigns supreme across the deep sea floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "false chemical claim", "claim": "Bioluminescence only possible in zero oxygen", "claim_type": "scientific_fact", "text": "That light is only possible in zero oxygen environments deep in the sea."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark ocean?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination", "text": "Counter-illumination matches faint light from above so predators below see zero dark silhouette against the sky."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid, "High-severity false scientific claim must fail validation.")

    def test_23_uncertain_claim_qualified_passes(self):
        """TEST 23: Uncertain claim with appropriate qualification -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Sunlight vanishes completely one thousand meters underwater into eternal deep sea darkness."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "qualified mechanism", "claim": "Scientists believe luciferin reactions evolved independently", "claim_type": "scientific_fact", "text": "Scientists believe deep sea creatures evolved cold biological light through specialized luciferin chemical reactions inside photophore organs."},
            {"speaker": "A", "role": "reveal", "interaction_type": "lead", "information_beat": "anglerfish lure", "text": "Wait, in some species anglerfish dangle glowing lures like fishing poles to snare unsuspecting prey in the pitch black ocean."},
            {"speaker": "B", "role": "reveal", "interaction_type": "lead", "information_beat": "counterillumination", "text": "And squids often use counter-illumination to erase their dark silhouette against faint surface light from above."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "qualified summary", "text": "Exactly, so researchers have found biological light is one of nature's most extraordinary deep sea survival mechanisms."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Qualified uncertain claim must pass. Errors: {errors}")

    def test_24_opinion_claim_passes(self):
        """TEST 24: Minor conversational opinion -> PASS without factual grounding error."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Did you know that deep sea creatures can glow like tiny underwater lanterns in pitch black darkness beneath the ocean?"},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemistry", "text": "They produce cold light chemically using luciferin and oxygen inside specialized cellular photophore light organs."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility", "text": "Wait, wouldn't glowing bright make them super easy targets for larger hungry predators searching for food?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination camouflage", "text": "Counter-illumination matches light coming from above so predators swimming below see zero dark silhouette."},
            {"speaker": "B", "role": "summarize", "interaction_type": "summarize", "claim": "opinion takeaway", "claim_type": "opinion", "text": "It's like they're all wearing their own personal glow-in-the-dark costumes for the deep ocean survival party!"}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Conversational opinion turn must pass. Errors: {errors}")

    def test_25_information_beat_a_turn_increments(self):
        """TEST 25: Information beat in A turn -> A ownership increments."""
        lines = [
            {"speaker": "A", "role": "explain", "interaction_type": "lead", "information_beat": "A beat concept", "text": "Sunlight vanishes completely one thousand meters underwater into deep sea darkness."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "B beat concept", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "A beat challenge", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark ocean depths?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "B beat answer", "text": "Counter-illumination matches faint surface light from above so predators below see zero dark silhouette against the sky."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "A additional concept", "text": "While anglerfish dangle glowing lures like fishing poles to snare unsuspecting prey in the pitch black sea."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertEqual(stats["beats_a_count"], 3)

    def test_26_information_beat_b_turn_increments(self):
        """TEST 26: Information beat in B turn -> B ownership increments."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "A beat 1", "text": "Sunlight vanishes completely one thousand meters underwater where extreme hydrostatic pressure rules supreme across the dark benthic abyss floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "B beat 1", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "A beat 2", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark ocean depths?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "B beat 2", "text": "Counter-illumination matches faint surface light from above so predators below see zero dark silhouette against the sky."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "B additional concept", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertEqual(stats["beats_b_count"], 3)

    def test_27_both_speakers_own_information_beats_passes(self):
        """TEST 27: Both speakers own information beats -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "A abyssal darkness", "text": "Sunlight vanishes completely one thousand meters underwater where extreme hydrostatic pressure rules supreme across the dark benthic abyss floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "B bioluminescence chemistry", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "A anglerfish lure", "text": "While anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their open razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "B squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "summarize", "information_beat": "A final summary", "text": "It is the ultimate evolutionary adaptation for survival in the deep ocean realm."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Both speakers owning information beats must pass. Errors: {errors}")
        self.assertGreaterEqual(stats["beats_a_count"], 1)
        self.assertGreaterEqual(stats["beats_b_count"], 1)

    def test_28_dashboard_counts_match_underlying_dialogue(self):
        """TEST 28: Dashboard information beat counts match underlying dialogue lines -> PASS."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "abyssal zone", "text": "Sunlight vanishes completely one thousand meters underwater where extreme hydrostatic pressure rules supreme across the dark benthic abyss floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence cell photophores", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "challenge", "interaction_type": "challenge", "information_beat": "predator visibility threat", "text": "Wait, wouldn't glowing make them easy targets for hungry predators searching for food in the dark ocean depths?"},
            {"speaker": "B", "role": "answer", "interaction_type": "answer", "information_beat": "counterillumination belly match", "text": "Counter-illumination matches faint surface light from above so predators below see zero dark silhouette against the sky."},
            {"speaker": "A", "role": "summarize", "interaction_type": "summarize", "information_beat": "adaptation summary", "text": "Deep sea bioluminescence shows the incredible versatility of life on Earth."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertEqual(stats["beats_a_count"], 3)
        self.assertEqual(stats["beats_b_count"], 2)

    def test_29_manifest_counts_match_qa_dashboard(self):
        """TEST 29: Manifest content_metrics matches QA dashboard convo_stats -> PASS."""
        from manifest_engine import generate_production_manifest
        import tempfile

        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Sunlight vanishes completely one thousand meters underwater where extreme hydrostatic pressure rules supreme across the dark benthic abyss floor."},
            {"speaker": "B", "role": "explain", "interaction_type": "lead", "information_beat": "bioluminescence chemistry", "text": "Yet deep sea creatures generate their own glowing light using chemical reactions inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "While anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their open razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "summarize", "information_beat": "deep sea adaptation", "text": "Nature has engineered perfect light solutions for the darkest places on Earth."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        
        with tempfile.NamedTemporaryFile(suffix=".manifest.json", delete=False) as tmp:
            tmp_path = tmp.name

        manifest = generate_production_manifest(
            short_id="Test_Short",
            topic="Test Topic",
            category="Test Cat",
            video_path="fake_video.mp4",
            duration=35.0,
            visual_count=5,
            voice_cfg={"A": {}, "B": {}},
            audio_stats={"mean_volume": -18.0, "max_volume": -2.0},
            qa_results=stats,
            out_manifest_path=tmp_path
        )
        
        c_metrics = manifest["synthetic_media"]["content_metrics"]
        self.assertEqual(c_metrics["information_beats_a"], stats["beats_a_count"])
        self.assertEqual(c_metrics["information_beats_b"], stats["beats_b_count"])

    def test_30_valid_short_natural_outro(self):
        """Test 30: Valid short natural outro passes QA."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a chemical reaction inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool in the dark ocean depths."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "Which somehow makes the deep ocean even stranger."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Expected valid outro script, got errors: {errors}")
        self.assertTrue(stats["outro"]["present"])
        self.assertTrue(stats["outro"]["validated"])
        self.assertEqual(stats["outro"]["word_count"], 8)

    def test_31_outro_introduces_new_information_beat(self):
        """Test 31: Outro introducing a new information beat fails QA."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a chemical reaction inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "new species discovery", "text": "Scientists recently discovered three new glowing species in the trench."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid)
        self.assertTrue(any("Outro turn must not introduce a new information beat" in err for err in errors))

    def test_32_outro_asks_unanswered_question(self):
        """Test 32: Outro asking an unanswered question fails QA."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a chemical reaction inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "Did you know there are actually five different types?"}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid)
        self.assertTrue(any("Outro turn must not contain an unanswered question" in err for err in errors))

    def test_33_outro_exceeds_20_words(self):
        """Test 33: Outro exceeding 20 words fails QA."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a chemical reaction inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "This incredible adaptation proves beyond any doubt that life will always find a brilliant way to flourish even in the absolute darkest depths of the ocean."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid)
        self.assertTrue(any("exceeds maximum 20 words" in err for err in errors))

    def test_34_multiple_outro_turns(self):
        """Test 34: Script with multiple outro turns fails QA."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a chemical reaction inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool."},
            {"speaker": "A", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "So down there, glowing isn't unusual at all."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "It's basically part of the neighborhood."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid)
        self.assertTrue(any("Multiple outro turns detected" in err for err in errors))

    def test_35_outro_not_final_turn(self):
        """Test 35: Outro that is not the final dialogue turn fails QA."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a chemical reaction inside specialized cellular photophore organs."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing lures like fishing poles to snare unsuspecting prey into their razor jaws."},
            {"speaker": "A", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "Nature really went overboard with that one."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue mucus to escape instantly from hungry marine threats."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertFalse(is_valid)
        self.assertTrue(any("Outro turn must be the final dialogue turn" in err for err in errors))

    def test_36_valid_script_without_outro(self):
        """Test 36: Valid script without an outro passes QA with a warning."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a specialized chemical reaction inside cellular photophore organs underwater in the ocean."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing bioluminescent lures like fishing poles to snare unsuspecting prey into their open razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue luminous mucus to escape instantly from hungry marine predators."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool in the absolute dark abyss."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Expected valid script, got errors: {errors}")
        self.assertFalse(stats["outro"]["present"])

    def test_37_outro_does_not_affect_factual_claim_count(self):
        """Test 37: Outro turn does not increment factual claim count."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "claim": "Sunlight vanishes underwater", "claim_type": "scientific_fact", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "claim": "Creatures generate light", "claim_type": "scientific_fact", "text": "It's due to luciferin, a specialized chemical reaction inside cellular photophore organs underwater."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "claim": "Anglerfish use lures", "claim_type": "example", "text": "For example, anglerfish use glowing bioluminescent lures like fishing poles to snare unsuspecting prey into their open razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "claim": "Squids shoot mucus", "claim_type": "scientific_fact", "text": "And vampire squids shoot glowing bioluminescent clouds of blue luminous mucus to escape instantly from hungry marine predators."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "claim": "Nature light solutions", "claim_type": "scientific_fact", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool in the absolute dark abyss."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "Which somehow makes the deep ocean even stranger."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Expected valid script, got errors: {errors}")
        g_sum = stats["grounding_summary"]
        self.assertEqual(g_sum["claims_a"] + g_sum["claims_b"], 5)

    def test_38_outro_does_not_create_information_beat(self):
        """Test 38: Outro turn does not increment information beat count."""
        lines = [
            {"speaker": "A", "role": "hook", "interaction_type": "lead", "information_beat": "ocean darkness", "text": "Have you ever wondered why deep ocean creatures glow in total darkness?"},
            {"speaker": "B", "role": "explain", "interaction_type": "answer", "information_beat": "bioluminescence chemistry", "text": "It's due to luciferin, a specialized chemical reaction inside cellular photophore organs underwater."},
            {"speaker": "A", "role": "example", "interaction_type": "example", "information_beat": "anglerfish lure", "text": "For example, anglerfish use glowing bioluminescent lures like fishing poles to snare unsuspecting prey into their open razor jaws."},
            {"speaker": "B", "role": "reveal", "interaction_type": "reveal", "information_beat": "squid defense cloud", "text": "And vampire squids shoot glowing bioluminescent clouds of blue luminous mucus to escape instantly from hungry marine predators."},
            {"speaker": "A", "role": "summarize", "interaction_type": "connect", "information_beat": "deep sea adaptation", "text": "So down there, glowing isn't unusual at all—it's their primary survival tool in the absolute dark abyss."},
            {"speaker": "B", "role": "outro", "interaction_type": "close", "information_beat": "", "text": "Nature really went overboard with that one."}
        ]
        is_valid, errors, stats = validate_and_analyze_conversation(lines)
        self.assertTrue(is_valid, f"Expected valid script, got errors: {errors}")
        self.assertEqual(stats["beats_a_count"] + stats["beats_b_count"], 5)


if __name__ == "__main__":
    unittest.main()

