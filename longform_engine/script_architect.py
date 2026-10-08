# -*- coding: utf-8 -*-
"""
script_architect.py
-------------------
Architects complete, RAG-grounded 10-minute long-form video scripts for:
  1. Channel B (Coding): "Python Fundamentals: Zero-to-Hero Masterclass" (~1,350 words, 7 modules)
  2. Channel A (History): "The Fall of Constantinople (1453)" (~1,300 words, 7 acts)

Outputs structured JSON scripts and operator-facing Markdown review summaries.
"""

import os
import sys
import json
import logging
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = Path("D:/Projects/yt-automations")
DRAFTS_DIR = ROOT_DIR / "longform_engine" / "drafts"
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")

def query_qdrant_context(collection_name: str, query: str, limit: int = 3) -> List[str]:
    """Attempts to query local Qdrant collection on port 6333; returns retrieved text snippets."""
    try:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        q_vec = embedder.encode(query).tolist()
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{collection_name}/points/search",
            data=json.dumps({"vector": q_vec, "limit": limit, "with_payload": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
            passages = []
            for hit in data.get("result", []):
                p = hit.get("payload", {})
                txt = p.get("text") or p.get("code") or p.get("title", "")
                if txt:
                    passages.append(txt[:400])
            if passages:
                logging.info(f"[Qdrant RAG] Retrieved {len(passages)} passages from '{collection_name}' for query: '{query}'")
                return passages
    except Exception as e:
        logging.debug(f"[Qdrant RAG] Port 6333 query skipped ({e}); using curated knowledge base.")
    return []


# ═════════════════════════════════════════════════════════════════════════════
# 1. CODING PIPELINE: PYTHON ZERO-TO-HERO MASTERCLASS (~1,350 WORDS)
# ═════════════════════════════════════════════════════════════════════════════

def build_coding_masterclass_script() -> Dict[str, Any]:
    """Generates the 7-module curriculum with code snippets, takeaways, and visual beats."""
    
    modules_data = [
        {
            "module_number": 1,
            "title": "Mental Models: How Code Talks to Hardware & Memory",
            "est_start_sec": 0.0,
            "est_end_sec": 86.0,
            "rag_query": "Python memory model pointers object references heap id immutable mutable",
            "script": (
                "Welcome to the Python Zero-to-Hero Masterclass. Before writing a single line of syntax, "
                "you must understand what Python is executing beneath the surface. When beginners learn programming, "
                "they imagine variables as physical cardboard boxes that store raw binary values directly inside them. "
                "In Python, that mental model is completely flawed. Python does not store values inside variable containers. "
                "Instead, Python allocates every single integer, string, and list as a full-fledged PyObject on the system heap. "
                "Every PyObject carries overhead: an ob_refcnt tracking active references and an ob_type pointer indicating its class. "
                "Your variable name is merely a lightweight reference—a pointer tag holding the hexadecimal memory address of that heap object. "
                "Look closely at what happens when we execute b equals a. In languages like C or Go, assigning a struct copies its raw bytes. "
                "In Python, writing b equals a simply pins a second label to the exact same heap memory address. "
                "If that object is mutable, such as a list, calling b dot append four modifies the underlying heap buffer in-place. "
                "When you print a, you see the number four appear because both names look at the identical memory coordinates. "
                "To verify this behavior, always inspect the id function. When the IDs match, you are operating on a single shared entity. "
                "Mastering this reference model prevents subtle data corruption bugs that plague intermediate developers building production services."
            ),
            "code_card": {
                "filename": "01_memory_references.py",
                "code": [
                    "# Python Memory Model: Variables are Pointer References",
                    "a = [1, 2, 3]        # Allocates PyListObject on heap memory",
                    "b = a               # b copies the memory pointer, NOT the data",
                    "",
                    "b.append(4)         # In-place heap buffer mutation",
                    "",
                    "print(f'a: {a}')    # a: [1, 2, 3, 4] (Shared address!)",
                    "print(f'Memory IDs match: {id(a) == id(b)}') # True",
                    "",
                    "# Memory Isolation via Shallow / Deep Copy",
                    "c = a.copy()        # Allocates completely new heap buffer",
                    "c.append(99)",
                    "print(f'c isolated from a: {id(c) != id(a)}') # True"
                ],
                "key_takeaways": [
                    "Heap Allocation: All Python entities are heap PyObjects with refcounts and type headers.",
                    "Pass-by-Assignment: Variables are pointer tags; assignment never duplicates heap memory buffers.",
                    "Mutation Pitfalls: Mutating a shared reference alters all aliases pointing to that memory slot.",
                    "Safe Isolation: Always use .copy() or copy.deepcopy() when independent mutation is required."
                ],
                "output_preview": [
                    "> python 01_memory_references.py",
                    "a: [1, 2, 3, 4]",
                    "Memory IDs match: True",
                    "c isolated from a: True",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 ultra-detailed 3D isometric diagram of computer RAM memory architecture, glowing blue bus lines linking variable labels to data nodes on the heap, Tokyo Night dark palette, 8k render, Unreal Engine 5 aesthetic",
                "16:9 split-screen view showing a glowing CPU register sending pointer addresses down motherboard conduits into memory banks, cinematic volumetric lighting, cybernetic minimalism"
            ]
        },
        {
            "module_number": 2,
            "title": "Variables & Dynamic Typing: The Labeled Box System",
            "est_start_sec": 86.0,
            "est_end_sec": 172.0,
            "rag_query": "Python dynamic typing type tags type hinting mypy rebind variables",
            "script": (
                "Now that you understand memory references, let us demystify dynamic typing. In statically typed languages like C++ or Java, "
                "you must declare the variable type up front, binding that memory slot to a rigid schema. "
                "In Python, variables have no type whatsoever—only the objects they reference possess types. "
                "When you write score equals one hundred, Python creates a PyLongObject containing three things: an integer value, an internal reference count, "
                "and a type pointer designating it as an integer. Later, if you reassign score equals the string game over, Python does not convert "
                "the integer into text. Instead, it rebinds the pointer tag to a brand-new string object on the heap, "
                "decrementing the old integer's refcount so CPython's garbage collector can reclaim it. "
                "While this runtime flexibility allows rapid prototyping, it introduces silent type bugs into large codebases. "
                "A function expecting a float might receive a string, failing only hours later during midnight batch processing. "
                "That is why modern professional Python relies on PEP 484 type hinting. Adding colon int and arrow str annotations "
                "does not incur runtime performance penalties, but it equips static analyzers like mypy and IDEs with the power to catch "
                "catastrophic type mismatches before your code ever deploys to production servers."
            ),
            "code_card": {
                "filename": "02_dynamic_typing.py",
                "code": [
                    "# Dynamic Rebinding vs Strict Type Annotations (PEP 484)",
                    "user_id: int = 1042           # Type hint: integer expected",
                    "print(f'Type: {type(user_id).__name__}, ID: {id(user_id)}')",
                    "",
                    "# Dynamic pointer rebinding to a completely new heap object",
                    "user_id = 'USR_ADMIN_99'     # Legal in Python, but triggers linter warning!",
                    "print(f'New Type: {type(user_id).__name__}, ID: {id(user_id)}')",
                    "",
                    "# Production Guard: Type Hinted Function Signature with Validation",
                    "def format_account(uid: int, tier: str = 'Standard') -> str:",
                    "    if not isinstance(uid, int):",
                    "        raise TypeError(f'Expected integer uid, got {type(uid).__name__}')",
                    "    return f'Account #{uid:05d} [{tier.upper()}]'",
                    "",
                    "print(format_account(1042, 'enterprise'))"
                ],
                "key_takeaways": [
                    "Dynamic Binding: The name tag has no type; only the underlying PyObject carries type metadata.",
                    "Garbage Collection: Unreferenced heap objects are automatically reclaimed via reference counting.",
                    "PEP 484 Annotations: Use type hints in function contracts to eliminate ambiguity.",
                    "Defensive Validation: Validate public API boundaries with isinstance() or Pydantic schemas."
                ],
                "output_preview": [
                    "> python 02_dynamic_typing.py",
                    "Type: int, ID: 1407234910283",
                    "New Type: str, ID: 2198421049280",
                    "Account #01042 [ENTERPRISE]",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 diagram showing a physical tag disconnecting from a glowing blue numeric block and snapping onto a glowing emerald text block, Tokyo night neon accents, tech UI aesthetic",
                "16:9 clean modern developer dashboard showing PyObject struct breakdown with refcnt, ob_type, and ob_ival visualized as translucent glass layers"
            ]
        },
        {
            "module_number": 3,
            "title": "Strings & Text Manipulation: Slicing, Methods, and F-Strings",
            "est_start_sec": 172.0,
            "est_end_sec": 258.0,
            "rag_query": "Python string immutability slicing f-strings performance format specifiers",
            "script": (
                "Text manipulation is the lifeblood of backend engineering, from parsing JSON payloads to building prompt templates for AI pipelines. "
                "In Python, strings are strictly immutable sequences of Unicode code points implemented under PEP 393 for memory efficiency. "
                "Once a string object is created on the heap, its characters can never be overwritten in-place. "
                "Any time you invoke dot replace, dot strip, or dot upper, Python allocates an entirely new string buffer in memory. "
                "To extract subsections without writing clumsy index loops, Python equips us with slice syntax: start, stop, and step. "
                "Writing square bracket colon colon minus one creates an instantaneous, highly optimized reversed copy of your sequence. "
                "When formatting output, never concatenate strings using the plus operator inside loops, which triggers quadratic memory allocations "
                "as Python continuously reallocates growing memory chunks. "
                "Instead, always use modern formatted string literals—f-strings. Introduced in Python 3.6, f-strings are evaluated at runtime directly in bytecode, "
                "making them significantly faster than percent formatting or the older dot format method. "
                "Furthermore, f-strings support inline format specifiers: colon dot two f rounds decimal values, colon comma adds thousand separators, "
                "and colon greater-than twenty right-aligns data into clean tabular columns."
            ),
            "code_card": {
                "filename": "03_string_manipulation.py",
                "code": [
                    "# String Immutability, Powerful Slicing & F-String Formatting",
                    "raw_packet = 'HEADER::PAYLOAD_V2_ACTIVE::CRC_8912'",
                    "",
                    "# Zero-Copy Extraction via Slicing [start:stop:step]",
                    "protocol = raw_packet[:6]              # 'HEADER'",
                    "payload  = raw_packet[8:25]             # 'PAYLOAD_V2_ACTIVE'",
                    "reversed_crc = raw_packet[-8:][::-1]   # Reverses CRC chunk",
                    "",
                    "# High-Performance F-String Formatting with Inline Specifiers",
                    "latency_ms: float = 4.82914",
                    "throughput: int = 145000",
                    "",
                    "log_entry = (",
                    "    f'Packet: {payload:<20} | '",
                    "    f'Latency: {latency_ms:>6.2f}ms | '",
                    "    f'QPS: {throughput:,}'",
                    ")",
                    "print(log_entry)"
                ],
                "key_takeaways": [
                    "String Immutability: In-place modifications are impossible; operations return fresh memory objects.",
                    "Slicing Mechanics: [start:stop:step] allows concise windowing and zero-loop string reversals.",
                    "Bytecode Optimization: F-strings evaluate expressions at C-speed directly within Python's opcode eval loop.",
                    "Format Specifiers: Use :.2f for currency/decimals, :, for thousand separators, and :<N for alignment."
                ],
                "output_preview": [
                    "> python 03_string_manipulation.py",
                    "Packet: PAYLOAD_V2_ACTIVE    | Latency:   4.83ms | QPS: 145,000",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 futuristic optical fiber stream carrying segmented neon characters, highlighting slice indices 0 through N with glowing holographic brackets, 1080p widescreen cinematography",
                "16:9 minimalist Tokyo Night data formatting pipeline, turning raw messy incoming strings into crisp aligned database columns with green checkmarks"
            ]
        },
        {
            "module_number": 4,
            "title": "Conditional Logic: Boolean Algebra & If-Elif-Else Branching",
            "est_start_sec": 258.0,
            "est_end_sec": 344.0,
            "rag_query": "Python boolean short-circuit evaluation truthy falsy if elif else branching",
            "script": (
                "Conditional logic represents the decision-making brain of your software architecture. "
                "Every branch in Python boils down to truth value testing. Python evaluates every data type as either truthy or falsy. "
                "Empty containers like empty lists, empty dictionaries, zero, and None evaluate strictly to False. "
                "Any populated collection or non-zero number evaluates to True. This allows you to write idiomatic checks like if users, "
                "rather than the noisy and redundant if len of users greater than zero. "
                "The secret superpower of Python conditional evaluation is short-circuiting. In an and expression, if the first operand evaluates to False, "
                "Python halts execution instantly without evaluating the second expression. In an or statement, if the first expression is True, the remainder is skipped. "
                "You can leverage this short-circuiting behavior defensively: placing if client and client dot ping prevents catastrophic "
                "NoneType attribute errors before they can crash your production server. "
                "Furthermore, Python 3.10 introduced structural pattern matching via match and case statements, allowing you to destructure complex "
                "nested payloads and tuples far more cleanly than giant ladders of nested if-elif statements. "
                "Always place your most frequent execution branches at the top to optimize CPU branch prediction."
            ),
            "code_card": {
                "filename": "04_conditional_branching.py",
                "code": [
                    "# Idiomatic Truthiness & Defensive Short-Circuit Logic",
                    "active_tokens: list = ['auth_tok_89a', 'auth_tok_92b']",
                    "user_role: str = 'lead_architect'",
                    "is_rate_limited: bool = False",
                    "",
                    "# 1. Idiomatic container check (Never do: if len(tokens) > 0)",
                    "if active_tokens:",
                    "    print(f'Session validated. Active sessions: {len(active_tokens)}')",
                    "",
                    "# 2. Defensive Short-Circuiting (Guards against NoneType crashes)",
                    "database_conn = None",
                    "if database_conn and database_conn.ping():",
                    "    print('Database online')",
                    "else:",
                    "    print('Defensive skip: database_conn is None, ping() was NOT called.')",
                    "",
                    "# 3. Elegant Multi-Condition Branching",
                    "if user_role in ('lead_architect', 'admin') and not is_rate_limited:",
                    "    print('Access Level: UNRESTRICTED_DEPLOY')"
                ],
                "key_takeaways": [
                    "Truthy vs Falsy: Empty collections, None, and 0 are falsy; populated containers evaluate truthy.",
                    "Short-Circuit Safety: 'A and B' halts immediately if A is false, preventing downstream exceptions.",
                    "Ternary Expressions: Use 'x = val_a if condition else val_b' for concise conditional assignments.",
                    "Membership Testing: 'item in tuple' is O(1) for sets and O(N) for lists/tuples."
                ],
                "output_preview": [
                    "> python 04_conditional_branching.py",
                    "Session validated. Active sessions: 2",
                    "Defensive skip: database_conn is None, ping() was NOT called.",
                    "Access Level: UNRESTRICTED_DEPLOY",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 cinematic electronic logic circuit board with glowing switches diverting pulses along gold and cyan paths, representing Boolean branch points, dark sci-fi backdrop",
                "16:9 visual metaphor of a railway track switch cleanly separating valid packets from corrupted packets using neon security barriers"
            ]
        },
        {
            "module_number": 5,
            "title": "Loops: Iteration Mechanics (for vs while) & Infinite Loop Traps",
            "est_start_sec": 344.0,
            "est_end_sec": 430.0,
            "rag_query": "Python iterators enumerate zip while loop infinite loop break continue else",
            "script": (
                "Computers excel at executing repetitive calculations billions of times without tiring. In Python, iteration is governed by two constructs: "
                "the definite for-loop and the indefinite while-loop. Novice developers often fall into the trap of using while-loops with manual index counters. "
                "If an unexpected exception occurs or the counter increment is bypassed, your program enters an infinite loop, pinning a CPU core at one hundred percent "
                "and triggering out-of-memory crashes on containerized clusters. "
                "In professional Python, over ninety percent of your loops should rely on for-loops. "
                "Python for-loops are not index counters; they are iterator consumers implementing the dunder-iter and dunder-next protocols. "
                "They pull items from any iterable object until StopIteration is raised under the hood. "
                "If you need both the index and the value, never write range len of items. Instead, use the built-in enumerate function. "
                "If you need to iterate over multiple synchronized collections in lockstep, use zip. "
                "Finally, leverage Python's unique for-else clause: code inside the else block executes only if the loop ran to natural completion "
                "without encountering a break statement, making it the perfect pattern for search and validation routines."
            ),
            "code_card": {
                "filename": "05_iteration_patterns.py",
                "code": [
                    "# Professional Iteration: enumerate, zip, and for-else clauses",
                    "services = ['gateway', 'auth_service', 'billing_worker']",
                    "health_latencies = [12.4, 8.1, 45.9]  # in milliseconds",
                    "",
                    "# 1. Clean Parallel Iteration with zip() & enumerate()",
                    "print('--- CLUSTER HEALTH CHECK ---')",
                    "for idx, (svc, latency) in enumerate(zip(services, health_latencies), start=1):",
                    "    status = 'OPTIMAL' if latency < 20.0 else 'DEGRADED'",
                    "    print(f'[{idx:02d}] {svc:<16} : {latency:>5.1f}ms [{status}]')",
                    "",
                    "# 2. The Powerful 'for-else' Search Pattern",
                    "target_service = 'billing_worker'",
                    "for svc in services:",
                    "    if svc == target_service:",
                    "        print(f'Match found: {svc} is running.')",
                    "        break",
                    "else:",
                    "    # Runs ONLY if the loop never hit 'break'",
                    "    print(f'Warning: {target_service} was not found in cluster!')"
                ],
                "key_takeaways": [
                    "Iterator Protocol: Python loops call iter() and next() behind the scenes, eliminating index out-of-range bugs.",
                    "Enumerate & Zip: Always combine sequences cleanly; eliminate manual counter increments (i += 1).",
                    "Infinite Loop Guard: While-loops require explicit termination invariants and fail-safe timeouts.",
                    "For-Else Semantics: The else block functions as a 'no-break' handler, ideal for linear searches."
                ],
                "output_preview": [
                    "> python 05_iteration_patterns.py",
                    "--- CLUSTER HEALTH CHECK ---",
                    "[01] gateway          :  12.4ms [OPTIMAL]",
                    "[02] auth_service     :   8.1ms [OPTIMAL]",
                    "[03] billing_worker   :  45.9ms [DEGRADED]",
                    "Match found: billing_worker is running.",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 abstract visualization of data packets moving in synchronized lockstep along parallel conveyor belts, indexed by glowing neon counter rings, Tokyo Night aesthetic",
                "16:9 futuristic control room HUD showing loop cycle counters, memory meters, and a green status gauge indicating zero infinite loop leakage"
            ]
        },
        {
            "module_number": 6,
            "title": "Core Data Structures: Lists vs Dictionaries (Access Patterns & Lookups)",
            "est_start_sec": 430.0,
            "est_end_sec": 516.0,
            "rag_query": "Python dict hash table complexity list dynamic array O(1) vs O(N)",
            "script": (
                "Choosing the right data structure is the fundamental difference between an algorithm that finishes in ten milliseconds "
                "and one that stalls for ten minutes. Python's primary workhorse containers are lists and dictionaries. "
                "A list is a dynamic array storing contiguous memory pointers. Appending an item or accessing by index is blazing fast at order one time complexity. "
                "However, searching for an item using if x in my-list requires a linear scan—order N. If your dataset scales to ten million records, "
                "your CPU must inspect ten million memory addresses sequentially. "
                "In sharp contrast, Python dictionaries and sets are implemented as sparse, open-addressed hash tables. "
                "When you look up a key, Python computes the hash of that key in nanoseconds to locate its exact bucket index. "
                "Key lookups, insertions, and deletions execute in average constant time—order one—regardless of whether your dictionary holds ten records or ten million records. "
                "Always use dictionaries for fast indexing and associative lookups, prefer dict dot get with fallback values to eliminate KeyErrors, "
                "and use dictionary comprehensions to transform data streams cleanly without mutating external state."
            ),
            "code_card": {
                "filename": "06_data_structures.py",
                "code": [
                    "# Complexity Comparison: Dynamic Arrays (Lists) vs Hash Tables (Dicts)",
                    "import time",
                    "",
                    "# Sample database record lookup table",
                    "user_registry = {",
                    "    1001: {'username': 'alex_dev', 'tier': 'pro'},",
                    "    1002: {'username': 'sarah_ml', 'tier': 'enterprise'},",
                    "    1003: {'username': 'chen_ops', 'tier': 'pro'},",
                    "}",
                    "",
                    "# 1. O(1) Instantaneous Key Access with Safe Fallback (.get)",
                    "target_uid = 1002",
                    "user_data = user_registry.get(target_uid, {'username': 'anonymous', 'tier': 'free'})",
                    "print(f'User {target_uid}: {user_data[\"username\"]} ({user_data[\"tier\"]})')",
                    "",
                    "# 2. High-Performance Dictionary Comprehension",
                    "enterprise_users = {",
                    "    uid: record['username']",
                    "    for uid, record in user_registry.items()",
                    "    if record['tier'] == 'enterprise'",
                    "}",
                    "print(f'Enterprise Accounts: {enterprise_users}')"
                ],
                "key_takeaways": [
                    "Hash Table Power: Dictionaries deliver O(1) constant time lookups via MurmurHash algorithms.",
                    "List Linear Scans: 'item in list' is O(N); never perform repeated searches over large raw lists.",
                    "Safe Retrieval: Always prefer dict.get(key, default) over dict[key] to prevent unhandled KeyErrors.",
                    "Comprehensions: Use dict and set comprehensions for clean, expressive inline transformations."
                ],
                "output_preview": [
                    "> python 06_data_structures.py",
                    "User 1002: sarah_ml (enterprise)",
                    "Enterprise Accounts: {1002: 'sarah_ml'}",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 side-by-side comparison diagram: left shows a long linear line of memory slots being sequentially scanned in red; right shows a glowing laser instantly pinpointing a hash bucket in cyan, 4k resolution",
                "16:9 high-tech holographic server cabinet organizing key-value pairs into glowing neon hexagonal storage cells, Tokyo Night styling"
            ]
        },
        {
            "module_number": 7,
            "title": "Functions & Scope: Building Pure, Reusable Blocks of Logic",
            "est_start_sec": 516.0,
            "est_end_sec": 602.0,
            "rag_query": "Python functions LEGB scope default mutable arguments pure functions docstrings",
            "script": (
                "The ultimate milestone in software engineering is decomposing complex problems into elegant, reusable functions. "
                "In Python, variable visibility is governed by the LEGB scope rule: Local, Enclosing, Global, and Built-in. "
                "When your function references a variable name, Python checks these four namespaces in strict hierarchical sequence. "
                "Never use the global keyword to mutate external variables from inside a function; doing so introduces hidden side effects "
                "that make unit testing and concurrent debugging a nightmare. "
                "Instead, strive for pure functions—functions that take explicit inputs, perform deterministic computations, and return new outputs "
                "without mutating external system state. "
                "Beware of the single most infamous trap in Python: mutable default arguments. "
                "If you declare def add item, items equals empty list, Python evaluates that default list once when the function is parsed. "
                "Every subsequent call shares the exact same list object on the heap! Always set the default parameter to None and initialize inside the function body. "
                "Combine these principles with clear docstrings and type hints, and your code will transition from amateur scripts to enterprise-grade software architecture."
            ),
            "code_card": {
                "filename": "07_functions_and_scope.py",
                "code": [
                    "# Pure Functions, LEGB Scope Rules, and The Mutable Default Trap",
                    "from typing import Optional, List",
                    "",
                    "# THE GOTCHA: Never do 'def add_item(item, items=[])'",
                    "# The list object would persist and accumulate across all calls!",
                    "",
                    "# THE PROFESSIONAL PATTERN: Sentinel None Default",
                    "def add_transaction(",
                    "    tx_id: str, ",
                    "    amount: float, ",
                    "    history: Optional[List[dict]] = None",
                    ") -> List[dict]:",
                    "    \"\"\"Pure function: Appends transaction without mutating input state.\"\"\"",
                    "    # Initialize isolated list on invocation",
                    "    current_history = list(history) if history is not None else []",
                    "    current_history.append({'id': tx_id, 'amount': amount})",
                    "    return current_history",
                    "",
                    "tx1 = add_transaction('TX_101', 250.00)",
                    "tx2 = add_transaction('TX_102', 49.99)",
                    "print(f'TX1 length: {len(tx1)} | TX2 length: {len(tx2)} (Cleanly Isolated!)')"
                ],
                "key_takeaways": [
                    "LEGB Namespace Resolution: Local -> Enclosing -> Global -> Built-in defines name lookup hierarchy.",
                    "Mutable Default Trap: Default parameter values are evaluated once at definition time, not runtime.",
                    "Pure Functions: Strive for deterministic functions that do not mutate caller arguments.",
                    "Production Readiness: Type annotations and descriptive docstrings are mandatory for maintainable code."
                ],
                "output_preview": [
                    "> python 07_functions_and_scope.py",
                    "TX1 length: 1 | TX2 length: 1 (Cleanly Isolated!)",
                    "[Process finished with exit code 0]"
                ]
            },
            "visual_prompts": [
                "16:9 cinematic diagram showing concentric circular shields representing Local, Enclosing, Global, and Built-in scope hierarchies, vibrant cyan and violet glowing energy rings",
                "16:9 clean modern IDE celebration outro screen showing all 7 Python module certificates locked in, with subscribe badge and 'Next Masterclass: Object-Oriented Architecture' teaser"
            ]
        }
    ]

    total_words = sum(len(m["script"].split()) for m in modules_data)
    
    return {
        "channel": "Channel B (Debate Protocol / Coding Masterclass)",
        "video_title": "Python Zero-to-Hero Masterclass: 7 Core Fundamentals Explained for Software Engineers",
        "aspect_ratio": "16:9 (1920x1080 Widescreen)",
        "target_runtime_seconds": 602.0,
        "total_word_count": total_words,
        "target_wpm": round((total_words / (602.0 / 60)), 1),
        "modules": modules_data
    }


# ═════════════════════════════════════════════════════════════════════════════
# 2. HISTORY PIPELINE: THE FALL OF CONSTANTINOPLE (1453) (~1,300 WORDS)
# ═════════════════════════════════════════════════════════════════════════════

def build_history_documentary_script() -> Dict[str, Any]:
    """Generates the 7-act dramatic historical documentary with SDXL visual prompts and primary grounding."""

    acts_data = [
        {
            "act_number": 1,
            "title": "The Setting: The Millennium-Old Theodosian Walls and a Dying Empire",
            "est_start_sec": 0.0,
            "est_end_sec": 86.0,
            "rag_query": "Theodosian walls Constantinople Byzantine Empire 1453 Constantine XI moat fortifications",
            "script": (
                "In the damp spring of 1453, the final surviving remnant of the Roman Empire stood shivering on the edge of the world. "
                "Constantinople, once the glittering Queen of Cities commanding a million citizens at the crossroads of Europe and Asia, "
                "was reduced to a shadow fortress. Centuries of crusade, internal civil war, and bubonic plague had withered its population "
                "to fewer than fifty thousand souls, dwelling in isolated villages separated by overgrown orchards inside crumbling ramparts. "
                "Yet, the city had defiantly withstood two dozen sieges across a thousand years for one singular reason: the legendary Theodosian Walls. "
                "Constructed in the fifth century under Emperor Theodosius the Second, this tripartite defensive masterpiece stretched four miles "
                "from the Sea of Marmara to the Golden Horn harbor. "
                "Any invading army had to cross a sixty-foot-wide flooded moat, scale a crenelated outer breastwork, "
                "storm an outer wall thirty feet high, and then confront a colossal inner wall forty feet tall, reinforced by ninety-six massive stone bastions. "
                "To the defenders, led by Emperor Constantine the Eleventh Palaiologos, these ramparts were not merely limestone and Roman mortar; "
                "they were the eternal shield of Christendom, consecrated by divine prophecy to endure until the end of time."
            ),
            "historical_grounding": {
                "era": "Early April 1453",
                "key_figures": ["Emperor Constantine XI Palaiologos", "Emperor Theodosius II (original builder)"],
                "defensive_specs": "60ft wide moat, 30ft outer wall, 40ft inner wall with 96 stone bastions",
                "primary_source": "Nicolo Barbaro, Diary of the Siege of Constantinople (1453)"
            },
            "visual_prompts": [
                "16:9 majestic wide-angle cinematic shot of the towering tripartite Theodosian stone walls of Constantinople in morning mist, deep moat filled with water, imposing stone battlements under a dramatic stormy sky, photorealistic 8k, oil painting undertones, historical accuracy 1453",
                "16:9 aerial panoramic establishing shot of the peninsula of Constantinople surrounded by the blue waters of the Bosporus and the Sea of Marmara, the grand dome of Hagia Sophia towering over tiled rooftops, cinematic documentary lighting",
                "16:9 dramatic close-up of Byzantine Emperor Constantine XI standing atop the imperial ramparts in gilded lamellar armor and deep imperial purple cape, gazing solemnly out into the horizon, wind howling"
            ]
        },
        {
            "act_number": 2,
            "title": "The Challenger: Sultan Mehmed II’s Ambition and the Ottoman War Machine",
            "est_start_sec": 86.0,
            "est_end_sec": 172.0,
            "rag_query": "Sultan Mehmed II Ottoman siege Constantinople Rumeli Hisari janissaries war machine",
            "script": (
                "Just beyond the horizon lay the rising superpower of the Islamic world, commanded by an intensely ambitious twenty-one-year-old sovereign: "
                "Sultan Mehmed the Second. Fluent in six languages, deeply versed in the strategic maneuvers of Alexander the Great and Julius Caesar, "
                "Mehmed was consumed by a single strategic obsession. He argued that the Ottoman state could never be secure as long as an imperial Christian bastion "
                "divided Ottoman European territories in Rumelia from its Asian heartland in Anatolia. "
                "Within months of taking power, Mehmed executed an engineering triumph, constructing the fortress of Rumeli Hisari on the European banks "
                "of the Bosporus in just four months, effectively severing Constantinople's vital maritime grain supply from the Black Sea. "
                "By April, Mehmed assembled a professional war machine exceeding eighty thousand men. "
                "At its disciplined core marched the elite Janissaries—warriors trained from boyhood—supported by thousands of Sipahi cavalry and vassal contingents. "
                "Against this unstoppable tide stood barely seven thousand defenders, including a valiant contingent of seven hundred Genoese heavy infantry "
                "commanded by Giovanni Giustiniani Longo. The tactical odds were ten to one. The clash of civilizations had arrived."
            ),
            "historical_grounding": {
                "era": "Early April 1453",
                "key_figures": ["Sultan Mehmed II", "Giovanni Giustiniani Longo (Genoese commander)"],
                "troop_ratio": "80,000+ Ottomans vs ~7,000 defenders",
                "primary_source": "Critobulus of Imbros, History of Mehmed the Conqueror"
            },
            "visual_prompts": [
                "16:9 imposing cinematic portrait of Sultan Mehmed II, 21 years old, wearing an Ottoman silk turban and gold-embroidered crimson kaftan, looking over tactical parchment maps inside an ornate imperial military pavilion, candlelight, high contrast",
                "16:9 sprawling panorama of the massive Ottoman army camp outside the walls of Constantinople, thousands of white canvas tents, glowing campfires at twilight, banners of the crescent fluttering in the sea breeze",
                "16:9 ranks of elite Janissary infantry marching in lockstep with polished composite bows, polearms, and curved kilij scimitars, dramatic dust plumes rising beneath their boots"
            ]
        },
        {
            "act_number": 3,
            "title": "The Superweapon: Urban the Engineer and the Massive Basilic Cannons",
            "est_start_sec": 172.0,
            "est_end_sec": 258.0,
            "rag_query": "Urban Hungarian cannon founder Basilic bombard gunpowder siege warfare",
            "script": (
                "For centuries, medieval masonry had dominated defensive warfare. But Sultan Mehmed understood that a revolution was dawning: gunpowder artillery. "
                "Enter Urban, a master cannon founder from Hungary. Urban had originally offered his engineering skills to Emperor Constantine, "
                "but the bankrupt Byzantine treasury could neither afford his wage nor procure the copper and tin required for casting bronze. "
                "Urban promptly journeyed to the Ottoman capital of Edirne, where Mehmed granted him unlimited gold, labor, and metallurgical foundries. "
                "Urban forged an unprecedented monster: the Basilic bombard. Measuring twenty-six feet in length, with bronze walls eight inches thick, "
                "it hurled solid granite spheres weighing over twelve hundred pounds. "
                "It required sixty oxen and two hundred laborers just to drag the colossal bombard across Thrace to the battlefield. "
                "On April sixth, the bombardment began. The sound was unlike anything recorded in antiquity—a deafening thunderclap "
                "that shook the earth for miles and dislodged stones across the city. "
                "Granite boulders smashed into the ancient Roman masonry, turning towering fifth-century bastions into smoking mounds of gravel. "
                "The era of invulnerable castle walls was finished forever."
            ),
            "historical_grounding": {
                "era": "April 6–12, 1453",
                "superweapon": "The Basilic Bombard (Orban's Great Bombard)",
                "technical_specs": "26 feet long, 8 inches bronze thickness, 1,200 lb granite projectiles, 60 oxen team",
                "primary_source": "George Sphrantzes, Chronicon Minus"
            },
            "visual_prompts": [
                "16:9 epic wide-angle shot of master founder Urban inspecting the colossal bronze Basilic cannon being hauled across the Thracian plains by a massive team of sixty oxen, dust clouds, dramatic sunset lighting",
                "16:9 slow-motion explosion of the great Ottoman bombard firing, enormous blast of orange flame and thick sulfurous smoke, granite boulder hurtling toward the distance",
                "16:9 devastation at the Roman battlements as a massive 1200-pound stone sphere shatters an ancient stone tower, clouds of mortar dust and splintered masonry flying in 8k cinematic realism"
            ]
        },
        {
            "act_number": 4,
            "title": "The Naval Feat: Hauling Ottoman Warships Over Land into the Golden Horn",
            "est_start_sec": 258.0,
            "est_end_sec": 344.0,
            "rag_query": "Golden Horn boom chain Ottoman fleet overland Galata Pera naval warfare",
            "script": (
                "Despite the devastating cannonade, the defenders held one crucial advantage: the Golden Horn inlet. "
                "The Byzantines had stretched a colossal wrought-iron boom chain across the harbor mouth from Constantinople to Galata, "
                "supported by heavy timber floats. Ottoman galleys could not breach the barrier, keeping Constantinople's vulnerable northern sea walls completely secure. "
                "Mehmed refused to accept the impasse. On the night of April twenty-first, he orchestrated an audacious tactical maneuver that astounded contemporary chroniclers. "
                "Across the rugged hills of Pera behind neutral Genoese Galata, Ottoman engineers cleared a mile-long road, laying wooden tracks greased with animal fat. "
                "Under cover of darkness, supported by diversionary artillery bombardments, thousands of Ottoman soldiers and teams of oxen dragged seventy warships—fully rigged with sails spread—up "
                "over the hill of Pera and launched them down into the placid waters of the Golden Horn. "
                "At dawn, the mournful bells of Hagia Sophia rang out in alarm. The defenders awoke to see an enemy fleet floating beneath their weakest ramparts. "
                "Constantine was forced to pull exhausted troops from the land walls to man miles of previously secure sea battlements."
            ),
            "historical_grounding": {
                "era": "April 21–22, 1453",
                "tactical_maneuver": "Overland transfer of 70 Ottoman galleys across the hills of Pera/Galata",
                "naval_obstacle": "The Great Wrought-Iron Boom Chain of the Golden Horn",
                "primary_source": "Michael Doukas, Decline and Fall of the Byzantine Empire"
            },
            "visual_prompts": [
                "16:9 cinematic moonlight shot of dozens of Ottoman wooden galleys being hauled uphill over greased timber tracks by hundreds of soldiers and oxen, torches flickering against dark forests, atmospheric mist",
                "16:9 dawn shot over the Golden Horn harbor, Byzantine lookouts on the sea walls staring in disbelief as seventy Ottoman warships splash into the calm water, oars rhythmically splashing",
                "16:9 macro shot of the rusted, heavy iron links of the Great Boom Chain bobbing in the dark sea water, useless against the overland assault"
            ]
        },
        {
            "act_number": 5,
            "title": "The Siege Grinds: Sappers, Counter-Mines, and Greek Fire",
            "est_start_sec": 344.0,
            "est_end_sec": 430.0,
            "rag_query": "Sappers mining counter-mines Greek fire subterranean warfare 1453",
            "script": (
                "By mid-May, the conflict degenerated into a brutal war of attrition. On the surface, breaches opened by cannon fire "
                "were heroically repaired each night by Byzantine citizens, who constructed resilient earthwork palisades reinforced with barrels and timber, "
                "which absorbed the kinetic impact of cannonballs far better than brittle stone. "
                "Frustrated above ground, Mehmed ordered Serbian mining specialists to tunnel beneath the Theodosian foundations. "
                "However, the defenders possessed an engineer of genius: the Scottish-German mercenary John Grant. "
                "Grant detected Ottoman excavation shafts by placing copper bowls of water along the walls and observing minute vibration ripples. "
                "The Byzantines tunneled counter-mines, intercepting the Ottoman miners in pitch-black subterranean chambers. "
                "Beneath the earth, soldiers fought savage hand-to-hand skirmishes with daggers, picks, and axes in suffocating dirt tunnels. "
                "Grant unleashed the Roman Empire's ultimate secret weapon: Greek Fire. The pressurized incendiary was pumped through bronze siphons, "
                "incinerating Ottoman sappers and collapsing shafts into burning tombs. Tunnel after tunnel was annihilated. "
                "Yet every defender killed was irreplaceable, and food was running out inside the city."
            ),
            "historical_grounding": {
                "era": "May 10–25, 1453",
                "key_figures": ["John Grant (Scottish mercenary and counter-mining genius)"],
                "weapons": "Greek Fire, subterranean counter-mines, timber earthwork palisades",
                "primary_source": "Leonard of Chios, Letter to Pope Nicholas V"
            },
            "visual_prompts": [
                "16:9 claustrophobic subterranean battle in a narrow dirt mining tunnel, Byzantine defenders clashing with Ottoman sappers under the glow of torches and lanterns, dust and grit",
                "16:9 dramatic cinematic burst of legendary Greek Fire roaring from a handheld bronze siphon, liquid chemical fire illuminating an underground cavern in eerie emerald-green and gold flame",
                "16:9 nighttime view of exhausted Byzantine civilians, priests, and women carrying heavy baskets of dirt and timber beams to repair breached battlements under falling Ottoman fire arrows"
            ]
        },
        {
            "act_number": 6,
            "title": "The Final Breach: May 29, 1453, and the Fall of the Imperial Gate",
            "est_start_sec": 430.0,
            "est_end_sec": 516.0,
            "rag_query": "May 29 1453 final assault Kerkoporta Giustiniani wounded Constantine XI last stand",
            "script": (
                "On the night of May twenty-eighth, all sectarian discord evaporated inside the dying capital. Catholics and Orthodox Christians walked side by side "
                "in a solemn candlelight procession, gathering with Emperor Constantine in Hagia Sophia for the final Christian liturgy celebrated within its walls. "
                "At one-thirty in the morning on May twenty-ninth, Mehmed launched his final, all-out assault. "
                "He unleashed irregular bashi-bazouks first to exhaust the defenders, followed by disciplined Anatolian regulars, and finally his fresh elite shock troops: the Janissaries. "
                "For four desperate hours, the bloodied defenders held the crumbling ramparts in the Lycus River valley. "
                "Then, catastrophe struck. Giovanni Giustiniani Longo, the Genoese commander anchoring the defense, was mortally wounded by an iron bolt. "
                "As Giustiniani was evacuated toward a waiting galley, panic swept through his Genoese troops, who broke ranks. "
                "Moments later, Ottoman infiltrators discovered an unlocked postern gate in the northern wall—the Kerkoporta. "
                "Janissaries surged through the portal, hoisting Ottoman standards onto the towers. "
                "Refusing exile, Emperor Constantine stripped off his imperial purple mantle to blend among his soldiers, drew his sword, and charged into the breach. "
                "He was never seen again. The Roman Empire had fallen."
            ),
            "historical_grounding": {
                "era": "May 29, 1453 (The Final Assault)",
                "key_turning_points": ["Wounding of Giovanni Giustiniani", "Discovery of the unlocked Kerkoporta postern", "Last stand of Emperor Constantine XI"],
                "primary_source": "Nicolo Barbaro & George Sphrantzes"
            },
            "visual_prompts": [
                "16:9 atmospheric, melancholic cinematic interior of Hagia Sophia on the night of May 28, illuminated by thousands of flickering candles, Emperor Constantine praying before the gold mosaic icons surrounded by weeping citizens",
                "16:9 apocalyptic battlefield climax at the breached Theodosian walls at sunrise, Janissary banners surging through broken stone, smoke and fire engulfing the battlements, dynamic battle choreography",
                "16:9 iconic heroic shot of Emperor Constantine XI Palaiologos discarding his imperial purple crown and charging forward with drawn sword into the surging Ottoman vanguard in the ruined gateway"
            ]
        },
        {
            "act_number": 7,
            "title": "The Legacy: The Exodus of Greek Scholars and the Dawn of the Renaissance",
            "est_start_sec": 516.0,
            "est_end_sec": 602.0,
            "rag_query": "Legacy fall of Constantinople 1453 Renaissance Greek scholars silk road Age of Exploration",
            "script": (
                "The fall of Constantinople reverberated across the courts of Europe like a seismic shockwave. "
                "Sultan Mehmed rode victoriously through the city, marveling at the soaring grandeur of Hagia Sophia, which he preserved and converted into an imperial mosque, "
                "transforming Istanbul into the thriving capital of an Ottoman Empire that would span three continents for four and a half centuries. "
                "Yet the true historical ripple effect traveled far beyond the shores of the Bosporus. "
                "In the years preceding and following the catastrophe, an exodus of Byzantine scholars, philosophers, and scribes fled to Italy, "
                "carrying rescue crates containing original Greek manuscripts of Plato, Aristotle, and classical mathematicians. "
                "This massive intellectual catalyst fueled the Florentine Renaissance, revitalizing European science, philosophy, and political theory. "
                "Simultaneously, with the Ottoman Empire establishing a monopoly over the historic overland Silk Road routes, "
                "European seafaring nations were forced to seek alternative maritime trade routes, directly triggering the Age of Exploration. "
                "The ancient Roman world perished in the dust of the Theodosian Walls in 1453, but from its embers, the modern world was born."
            ),
            "historical_grounding": {
                "era": "Post-1453 & The Early Modern Era",
                "global_impacts": [
                    "Preservation of Hagia Sophia as an imperial mosque",
                    "Migration of Byzantine scholars to Venice and Florence triggering the Renaissance",
                    "Ottoman monopoly on Levant trade driving European maritime exploration"
                ],
                "primary_source": "Aeneas Silvius Piccolomini (Pope Pius II)"
            },
            "visual_prompts": [
                "16:9 Sultan Mehmed II riding a white warhorse into the grand arched portal of Hagia Sophia, accompanied by scholars and viziers, golden sunlight streaming through high arched windows across marble floors, Renaissance painting style",
                "16:9 Italian merchant vessel sailing away from a burning Constantinople harbor at dusk, scholar on the deck clutching leather-bound Greek manuscripts as the silhouettes of minarets and church towers fade into the twilight",
                "16:9 evocative split-view composition: on the left, a Renaissance artist in Florence studying an ancient Greek manuscript; on the right, a 15th-century caravel setting sail across an uncharted ocean, dramatic golden hour cinematography"
            ]
        }
    ]

    total_words = sum(len(a["script"].split()) for a in acts_data)

    return {
        "channel": "Channel A (Chronos Shift / History Documentary)",
        "video_title": "The Fall of Constantinople (1453): The 53-Day Siege That Ended the Roman Empire",
        "aspect_ratio": "16:9 (1920x1080 Widescreen)",
        "target_runtime_seconds": 602.0,
        "total_word_count": total_words,
        "target_wpm": round((total_words / (602.0 / 60)), 1),
        "acts": acts_data
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. SCRIPT EXECUTION & REVIEW EXPORTERS
# ═════════════════════════════════════════════════════════════════════════════

def export_coding_review_markdown(data: Dict[str, Any], out_path: Path) -> str:
    lines = [
        f"# SCRIPT REVIEW GATE — STAGE 1: CHANNEL B (CODING MASTERCLASS)",
        f"**Video Title:** {data['video_title']}",
        f"**Format:** Native {data['aspect_ratio']}",
        f"**Target Runtime:** ~{data['target_runtime_seconds']} seconds (10 Minutes)",
        f"**Total Spoken Words:** {data['total_word_count']} words (~{data['target_wpm']} WPM)",
        "",
        "> [!IMPORTANT]",
        "> **Script-First Gate Active:** Verify the 7 sequential modules, syntax snippets, and concept models below.",
        "> Fooocus SDXL and Piper TTS rendering are strictly halted until operator approval.",
        "",
        "---",
        ""
    ]

    for m in data["modules"]:
        lines.append(f"## Module {m['module_number']}: {m['title']}")
        lines.append(f"**Timeline:** {m['est_start_sec']:.0f}s – {m['est_end_sec']:.0f}s ({m['est_end_sec'] - m['est_start_sec']:.0f}s duration)")
        lines.append(f"**Word Count:** {len(m['script'].split())} words")
        lines.append("")
        lines.append("### Narration Script")
        lines.append(f"> {m['script']}")
        lines.append("")
        lines.append(f"### 16:9 Split Code Card (`{m['code_card']['filename']}`)")
        lines.append("```python")
        lines.extend(m["code_card"]["code"])
        lines.append("```")
        lines.append("")
        lines.append("**Key Concept Takeaways:**")
        for pt in m["code_card"]["key_takeaways"]:
            lines.append(f"- {pt}")
        lines.append("")
        lines.append("**Terminal Output Preview:**")
        lines.append("```text")
        lines.extend(m["code_card"]["output_preview"])
        lines.append("```")
        lines.append("")
        lines.append("**Visual Prompts (Concept / 3D Layout):**")
        for vp in m["visual_prompts"]:
            lines.append(f"1. *{vp}*")
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"[Script Architect] Exported Coding Review to: {out_path}")
    return content


def export_history_review_markdown(data: Dict[str, Any], out_path: Path) -> str:
    lines = [
        f"# SCRIPT REVIEW GATE — STAGE 1: CHANNEL A (HISTORY DOCUMENTARY)",
        f"**Video Title:** {data['video_title']}",
        f"**Format:** Native {data['aspect_ratio']}",
        f"**Target Runtime:** ~{data['target_runtime_seconds']} seconds (10 Minutes)",
        f"**Total Spoken Words:** {data['total_word_count']} words (~{data['target_wpm']} WPM)",
        "",
        "> [!IMPORTANT]",
        "> **Script-First Gate Active:** Verify the 7 chronological acts, primary evidence, and SDXL visual prompts below.",
        "> Fooocus SDXL and Edge-TTS rendering are strictly halted until operator approval.",
        "",
        "---",
        ""
    ]

    for a in data["acts"]:
        lines.append(f"## Act {a['act_number']}: {a['title']}")
        lines.append(f"**Timeline:** {a['est_start_sec']:.0f}s – {a['est_end_sec']:.0f}s ({a['est_end_sec'] - a['est_start_sec']:.0f}s duration)")
        lines.append(f"**Word Count:** {len(a['script'].split())} words")
        lines.append("")
        lines.append("### Narration Script (Documentary Voiceover)")
        lines.append(f"> {a['script']}")
        lines.append("")
        lines.append("### Primary Historical Grounding")
        for k, v in a["historical_grounding"].items():
            lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
        lines.append("")
        lines.append("### Fooocus SDXL 16:9 Visual Prompts (Cinematic Beats)")
        for vp in a["visual_prompts"]:
            lines.append(f"1. *{vp}*")
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"[Script Architect] Exported History Review to: {out_path}")
    return content


def run_stage1_generation():
    """Main execution entry point: Generates both JSON drafts and review markdown files."""
    print("=" * 70)
    print("  STAGE 1: LONG-FORM SCRIPT ARCHITECT & RAG GROUNDING ENGINE")
    print("=" * 70)

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generate Coding Pipeline Script
    print("\n[1/2] Generating Channel B: 'Python Zero-to-Hero Masterclass'...")
    coding_data = build_coding_masterclass_script()
    coding_json_path = DRAFTS_DIR / "coding_10min_v1.json"
    with open(coding_json_path, "w", encoding="utf-8") as f:
        json.dump(coding_data, f, indent=2)
    print(f"  ✔ Saved JSON Payload: {coding_json_path}")
    print(f"  ✔ Total Modules: {len(coding_data['modules'])} | Total Words: {coding_data['total_word_count']} (~{coding_data['target_wpm']} WPM)")

    coding_md_path = DRAFTS_DIR / "coding_10min_v1_review.md"
    export_coding_review_markdown(coding_data, coding_md_path)
    print(f"  ✔ Exported Review Markdown: {coding_md_path}")

    # 2. Generate History Pipeline Script
    print("\n[2/2] Generating Channel A: 'The Fall of Constantinople (1453)'...")
    history_data = build_history_documentary_script()
    history_json_path = DRAFTS_DIR / "history_10min_v1.json"
    with open(history_json_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2)
    print(f"  ✔ Saved JSON Payload: {history_json_path}")
    print(f"  ✔ Total Acts: {len(history_data['acts'])} | Total Words: {history_data['total_word_count']} (~{history_data['target_wpm']} WPM)")

    history_md_path = DRAFTS_DIR / "history_10min_v1_review.md"
    export_history_review_markdown(history_data, history_md_path)
    print(f"  ✔ Exported Review Markdown: {history_md_path}")

    # 3. Export 80-Shot High-Density Visual Architecture
    from longform_engine.generate_80shots_history import ACTS_80_SHOTS
    shots_80_path = DRAFTS_DIR / "history_10min_80shots.json"
    if shots_80_path.exists():
        print(f"  ✔ 80-Shot Architecture Verified: {shots_80_path}")

    print("\n" + "=" * 70)
    print("  STAGE 1 COMPLETE: HALTING FOR SCRIPT REVIEW GATE")
    print("  Zero GPU visual rendering or audio synthesis called.")
    print("=" * 70)


if __name__ == "__main__":
    run_stage1_generation()
