# -*- coding: utf-8 -*-
"""
ingest_tech_patterns.py
-----------------------
Batch ingestion and vectorization engine for Pipeline 2 (Debate Protocol / Senior Dev).
Expands Qdrant collection 'coding_education_rag' across 3 core categories:
1. 'post_mortem': Real-world engineering incident autopsies (Cloudflare, AWS, Knight Capital, CrowdStrike, GitLab, GitHub, Meta).
2. 'system_design': Distributed systems architectures, caching topologies, vector search / RAG, consensus, and database sharding.
3. 'code_pattern': Senior vs Junior Python pitfalls, asyncio event loop starvation, ORM N+1 queries, memory efficiency.
"""

import os
import sys
import uuid
import json
import logging
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COLLECTION_NAME = "coding_education_rag"
VECTOR_DIM = 384
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")

# Curated High-Density Technical Knowledge Corpus
CURATED_TECH_CORPUS: List[Dict[str, Any]] = [
    # ── System Design ─────────────────────────────────────────────────────────
    {
        "title": "Cache Invalidation and High-Throughput Caching Topologies",
        "category": "system_design",
        "tags": ["caching", "redis", "cache-aside", "thundering-herd", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """In high-scale architectures, caching bridges the gap between memory latency (sub-millisecond) and disk/network database latency (10-50ms). The primary topologies are:
1. Cache-Aside (Lazy Loading): The application queries cache first. On miss, it reads from the database and writes to cache. Pitfall: Stale reads during concurrent writes.
2. Write-Through: The application writes to cache, which synchronously writes to the database. Guarantees consistency at the cost of higher write latency.
3. Write-Back (Write-Behind): Application writes to cache immediately; cache asynchronously batches writes to disk. Fast writes, but risks data loss on node crash.
Thundering Herd Mitigations: When a hot cache key expires, thousands of concurrent requests slam the DB. Mitigations include Mutex/Distributed Locking (only 1 thread regenerates cache while others wait), Probabilistic Early Expiration (XFetch algorithm calculating refresh probability before expiration), and Soft TTL with background refresh workers."""
    },
    {
        "title": "Database Sharding and Consistent Hashing Rings",
        "category": "system_design",
        "tags": ["database", "sharding", "consistent-hashing", "scaling", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """When a relational database exceeds vertical hardware limits (CPU, RAM, IOPS), horizontal partitioning (sharding) distributes rows across independent database nodes.
1. Range-Based Sharding: Partitions data by contiguous ranges (e.g. User IDs 1-1M on Shard A, 1M-2M on Shard B). Problem: Hotspotting on newest active users.
2. Hash-Based Sharding: Shard = Hash(key) % N. Problem: Adding or removing a shard requires rehashing and moving 100% of data across the cluster.
3. Consistent Hashing: Maps both database nodes and keys to a 360-degree integer ring (e.g. 0 to 2^32-1) using cryptographic hashes (MD5/Murmur3). When a node is added or removed, only K/N keys are moved on average. To avoid data skew and uneven load distribution, each physical node is assigned multiple Virtual Nodes (tokens) distributed uniformly around the ring."""
    },
    {
        "title": "Vector Database Indexing: HNSW vs IVFFlat and Hybrid Search",
        "category": "system_design",
        "tags": ["vector-database", "qdrant", "hnsw", "rag", "embeddings", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """Vector search retrieves nearest neighbors in high-dimensional embedding space (e.g. 384-d to 1536-d). Exact KNN search requires O(N) brute-force cosine distance calculations, which is unsustainable for millions of vectors.
Approximate Nearest Neighbor (ANN) Algorithms:
1. IVFFlat (Inverted File Flat): Partitions vector space into Voronoi cells via k-means clustering. Searches only vectors within the closest centroids. Lower memory, but lower recall on boundary vectors.
2. HNSW (Hierarchical Navigable Small World): Constructs a multi-layer graph structure where upper layers have long-range links for fast exploration (skip-list concept) and bottom layers have dense local connections for high-precision recall. Delivers 95%+ recall with sub-5ms latency, but requires significant RAM.
Hybrid Search & RRF: Combines dense semantic vector embeddings with sparse lexical keyword search (BM25) using Reciprocal Rank Fusion (RRF: Score = sum(1 / (k + rank))), eliminating semantic false positives while preserving exact keyword matches."""
    },
    {
        "title": "Event-Driven Architectures: Kafka vs RabbitMQ and Outbox Pattern",
        "category": "system_design",
        "tags": ["kafka", "rabbitmq", "event-driven", "outbox-pattern", "idempotency", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """Choosing between message brokers depends on throughput, ordering, and retention needs:
1. Apache Kafka: Distributed append-only commit log. High throughput (millions of msgs/sec), long-term retention, ordered strictly within each partition. Consumers pull messages and manage offset pointers.
2. RabbitMQ: Smart broker, dumb consumer model. Advanced routing (Exchange types: Direct, Topic, Fanout, Headers), ephemeral queues, push-based delivery, per-message acknowledgement. Ideal for complex task queues.
Transactional Outbox Pattern: In distributed systems, writing to a database and publishing a message to Kafka must be atomic. Dual-write failures leave systems inconsistent. Solution: Write the event to an outbox table in the local relational DB within the same database transaction, then use Change Data Capture (Debezium/polling) to stream outbox rows to Kafka."""
    },
    {
        "title": "LLM Inference Optimization: KV Caching, PagedAttention, and vLLM",
        "category": "system_design",
        "tags": ["llm", "inference", "vllm", "kv-cache", "paged-attention", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """Transformer text generation operates in two phases: Prefill (processing input prompt tokens in parallel) and Decoding (generating output tokens autoregressively one by one).
1. KV Caching: Avoids recomputing Key and Value matrix states for previously generated tokens at each step by storing them in GPU VRAM. Memory complexity is O(batch_size * sequence_length * num_layers * hidden_dim).
2. PagedAttention (vLLM): Standard PyTorch allocations create severe memory fragmentation because max sequence length must be pre-allocated contiguously. PagedAttention divides the KV cache into non-contiguous virtual memory blocks (pages), reducing memory waste from 60-80% down to under 4%, enabling 2-4x higher concurrency on the same GPU.
3. Speculative Decoding: Uses a small draft model (e.g. 1B params) to generate candidate tokens quickly, which are verified in a single forward pass by the large target model (e.g. 70B), achieving 2-3x speedup with zero quality degradation."""
    },

    # ── Production Post-Mortems ───────────────────────────────────────────────
    {
        "title": "Cloudflare 2019 WAF Catastrophic Backtracking Global Outage",
        "category": "post_mortem",
        "tags": ["cloudflare", "regex", "cpu-exhaustion", "waf", "post_mortem"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """Incident Summary: On July 2, 2019, Cloudflare suffered a global 27-minute outage dropping 82% of global traffic.
Root Cause: Deployment of a new Web Application Firewall (WAF) rule to detect XSS attacks contained a poorly constructed regular expression: `(?:(?:^|[\?&]|;)\s*item\s*=\s*([^\s&;]+))`. The expression contained unanchored wildcard matching that triggered catastrophic exponential backtracking when evaluating certain payload strings.
Impact: CPU utilization spiked to 100% across all proxy processes (Nginx/Lua edge stack) globally. Because all CPU cores were locked executing regex evaluations, edge servers stopped accepting incoming connections.
Remediation: Hard CPU timeouts on regex execution engines, migration of WAF rules to re2 (Google non-backtracking linear time regex engine), and phased canary rollout procedures for security rules."""
    },
    {
        "title": "Knight Capital $440 Million 45-Minute Trading Disaster (2012)",
        "category": "post_mortem",
        "tags": ["knight-capital", "dead-code", "deployment", "high-frequency-trading", "post_mortem"],
        "has_code": False,
        "source_file": "curated_tech_corpus.json",
        "text": """Incident Summary: On August 1, 2012, market maker Knight Capital lost $440 million in 45 minutes, leading to immediate bankruptcy.
Root Cause: An engineer manually deployed new automated market-making code (SMARS) to 7 out of 8 production servers, accidentally omitting the 8th server. The new deployment repurposed an old configuration flag that previously controlled a legacy feature called 'Power Peg' (which had been inactive for 9 years). When the market opened, the 8th server evaluated the flag as enabling Power Peg, which had defect code that bought at the offer price and sold at the bid without checking order limits.
Impact: Sent over 4 million erroneous orders across 154 stocks, executing 397 million shares and accumulating billions in unintended market positions.
Remediation: Mandatory automated deployment pipelines, complete elimination and audit of dead/repurposed code flags, and independent hardware-level risk circuit breakers."""
    },
    {
        "title": "CrowdStrike July 2024 Channel File 291 Global Kernel Crash",
        "category": "post_mortem",
        "tags": ["crowdstrike", "windows", "kernel", "memory-safety", "post_mortem"],
        "has_code": False,
        "source_file": "curated_tech_corpus.json",
        "text": """Incident Summary: On July 19, 2024, a rapid configuration update from cybersecurity vendor CrowdStrike caused 8.5 million Windows computers and servers globally to crash into Blue Screen of Death (BSOD) loops, disrupting airlines, hospitals, and financial institutions.
Root Cause: CrowdStrike delivered an updated Rapid Response content file ('Channel File 291') to its Falcon sensor. The sensor driver (csagent.sys), running in Ring 0 Windows kernel space, expected 20 input fields in the template config. The updated channel file contained 21 inputs due to an untested parser mismatch. The driver attempted an out-of-bounds memory read on pointer slot 21 (address 0x000000000000009c), triggering an unhandled PAGE_FAULT_IN_NONPAGED_AREA exception in kernel mode.
Remediation: Enforcing staged canary deployment rings for content configuration updates, runtime kernel bounds-checking validators, and eBPF/user-space sandboxing isolation."""
    },
    {
        "title": "GitLab 2017 Live Database Deletion and Backup Restoration Failure",
        "category": "post_mortem",
        "tags": ["gitlab", "database", "postgresql", "backups", "human-error", "post_mortem"],
        "has_code": False,
        "source_file": "curated_tech_corpus.json",
        "text": """Incident Summary: On January 31, 2017, GitLab suffered an 18-hour outage resulting in the loss of 6 hours of production database data (issues, merge requests, comments).
Root Cause: Under severe database replication lag caused by a DDoS attack and high load, an engineer attempting to clean up a stale replication directory on the primary database server accidentally executed `rm -rf` on the live PostgreSQL data directory (/var/opt/gitlab/postgresql/data).
Secondary Failure: When attempting recovery, five separate backup/replication mechanisms failed: (1) LVM snapshots were configured for a different disk volume, (2) WAL archiving to S3 failed due to pg_dump version mismatches, (3) Daily backup cron jobs were silently failing without alerting, (4) Azure disk snapshots were disabled for databases, (5) Staging sync had wiped staging data earlier that week.
Remediation: Automated daily restore drills with verification alerts, directory write protection, and multi-region snapshot pipelines."""
    },
    {
        "title": "AWS S3 US-East-1 2017 Cascading Outage",
        "category": "post_mortem",
        "tags": ["aws", "s3", "cascading-failure", "typo", "post_mortem"],
        "has_code": False,
        "source_file": "curated_tech_corpus.json",
        "text": """Incident Summary: On February 28, 2017, AWS S3 in US-East-1 (Northern Virginia) experienced a 4-hour massive outage that took down major internet services (Quora, Trello, GitHub images, Docker Hub).
Root Cause: An authorized S3 engineer was debugging the S3 billing system and intended to take a small number of servers offline using an established runbook tool. A command input parameter typo caused a significantly larger number of servers to be decommissioned than intended.
Cascading Impact: The command took down servers for two core S3 subsystems: the Placement subsystem (allocates new storage) and the Index subsystem (manages metadata and location mappings). Restarting the Index subsystem required a full cold start and validation of trillions of keys, which overwhelmed dependent services across EC2, EBS, and Lambda.
Remediation: Adding strict guardrails and rate-limits to administrative operational tools to prevent large-scale instant server removals, and speeding up subsystem recovery time."""
    },

    # ── Senior vs Junior Code Patterns ────────────────────────────────────────
    {
        "title": "Senior vs Junior Python: Mutable Default Arguments and Memory Leaks",
        "category": "code_pattern",
        "tags": ["python", "anti-pattern", "memory", "senior-dev", "code_pattern"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """1. Mutable Default Arguments:
Junior Pitfall:
```python
def add_event(event_name: str, tags: list = []):
    tags.append(event_name)
    return tags
```
In Python, default parameter objects are evaluated ONCE at function definition time, not at invocation. Every call to add_event mutates the exact same list in memory.
Senior Implementation:
```python
def add_event(event_name: str, tags: list | None = None):
    if tags is None:
        tags = []
    tags.append(event_name)
    return tags
```

2. Generator Pipelines for Memory Efficiency:
Junior: Loading 10 million database rows into a list comprehension ([process(r) for r in query]) consuming 8GB RAM and triggering OOM.
Senior: Using streaming generator expressions ((process(r) for r in query)) consuming constant O(1) memory (~50KB) via iterator chunking."""
    },
    {
        "title": "Senior vs Junior AsyncIO: Event Loop Starvation and Thread Offloading",
        "category": "code_pattern",
        "tags": ["asyncio", "concurrency", "fastapi", "event-loop", "code_pattern"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """In asynchronous Python (FastAPI, asyncio, Tornado), a single OS thread drives the event loop.
Junior Pitfall: Running synchronous blocking I/O or CPU-heavy computation inside an async route handler:
```python
@app.get("/hash")
async def compute_hash(data: str):
    time.sleep(2.0) # BLOCKS THE ENTIRE SERVER FOR ALL USERS!
    return {"status": "done"}
```
While time.sleep or heavy Pillow/Bcrypt image hashing executes, the event loop cannot service any other incoming requests, causing latency spikes and socket timeouts.

Senior Implementation: Offload blocking work to the internal ThreadPoolExecutor using asyncio.to_thread (Python 3.9+):
```python
@app.get("/hash")
async def compute_hash(data: str):
    res = await asyncio.to_thread(sync_heavy_hash_function, data)
    return {"status": "done", "result": res}
```"""
    },
    {
        "title": "Senior vs Junior Database ORM: The N+1 Query Problem and Connection Leaks",
        "category": "code_pattern",
        "tags": ["orm", "sql", "n+1", "performance", "code_pattern"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """The N+1 Query Problem is the most common cause of database performance degradation in web applications.
Junior ORM Code:
```python
users = session.query(User).limit(100).all() # 1 Query
for user in users:
    print(user.profile.bio) # Emits 1 query PER USER! Total: 101 queries
```
Under production load with 10,000 requests/sec, 101 queries per request will instantly exhaust the database connection pool.

Senior Implementation: Use eager loading (joinedload or selectinload in SQLAlchemy):
```python
from sqlalchemy.orm import selectinload
users = session.query(User).options(selectinload(User.profile)).limit(100).all() # Exactly 2 Queries total!
```
Always use explicit connection context managers (with get_session() as session:) to prevent connection pool starvation from unclosed transactions."""
    },
    # ── Container Orchestration & Cloud-Native ───────────────────────────────
    {
        "title": "Kubernetes Control Plane Architecture and etcd Raft Consensus",
        "category": "system_design",
        "tags": ["kubernetes", "k8s", "etcd", "raft", "control-plane", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """The Kubernetes Control Plane maintains cluster state using a declarative reconciliation loop:
1. kube-apiserver: The stateless REST gateway. All cluster components (controllers, scheduler, kubelet) communicate exclusively via the API server.
2. etcd: Strongly consistent, distributed key-value store using the Raft consensus algorithm. Stores entire cluster state. Raft requires (N/2)+1 quorum nodes (typically 3 or 5 nodes) to tolerate (N-1)/2 node failures.
3. kube-scheduler: Evaluates resource requests, affinity/anti-affinity, taints, and tolerations to bind Pods to optimal worker nodes (Node Filtering & Scoring phases).
4. kube-controller-manager: Runs continuous control loops (DeploymentController, ReplicaSetController) that compare the actual cluster state against the desired spec and execute mutations to reconcile differences.
5. Worker Node Kubelet: Node agent that communicates with the Container Runtime Interface (CRI / containerd) to pull images, configure namespaces/cgroups, and monitor pod health probes."""
    },
    {
        "title": "Docker Container Internals: Linux Namespaces, cgroups v2, and Overlay2",
        "category": "system_design",
        "tags": ["docker", "containers", "linux", "cgroups", "namespaces", "overlay2", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """Containers are NOT lightweight virtual machines; they are standard isolated Linux OS processes created using kernel primitives:
1. Linux Namespaces (Process Isolation):
   - PID Namespace: Process tree isolation (container process sees itself as PID 1).
   - NET Namespace: Dedicated network stack, virtual eth0 interface, and routing table.
   - MNT Namespace: Isolated root filesystem mount points.
   - IPC, UTS, USER Namespaces: Inter-process communication, hostname, and UID/GID mapping isolation.
2. Control Groups (cgroups v2 - Resource Metering & Throttling):
   - Limits and accounts for CPU quota (CFS scheduler period/quota), memory ceilings (oom-killer invocation on limit breach), block I/O bandwidth, and maximum process IDs (pids.max preventing fork bombs).
3. OverlayFS (Overlay2 Storage Driver):
   - Stacks container image layers (read-only lowerdir) beneath a single writable container layer (upperdir). Merged view uses copy-on-write (CoW) semantics when a file is modified."""
    },
    {
        "title": "Serverless Architecture: AWS Lambda Cold Starts, MicroVMs, and Execution Models",
        "category": "system_design",
        "tags": ["serverless", "aws-lambda", "firecracker", "cold-starts", "cloud-native", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """Serverless compute abstracts server management into ephemeral, event-driven execution environments:
1. Firecracker MicroVMs: AWS Lambda and Fargate run on Firecracker, an open-source Rust-based Virtual Machine Monitor (VMM) using Linux KVM. Boots minimal guest microVMs in sub-5ms with ~5MB memory overhead.
2. Cold Start Lifecycle:
   - Phase 1 (Download Code & Start Sandbox): Pulls container image or ZIP package from S3/ECR, initializes Firecracker microVM.
   - Phase 2 (Runtime Init): Boots Python/Node runtime and executes top-level global imports and database connection setup.
   - Phase 3 (Function Invocation): Executes the request handler function.
3. Cold Start Mitigations:
   - Provisioned Concurrency: Pre-initializes a pool of execution environments ready to respond in sub-10ms.
   - Lazy Import Loading: Moving heavy ML/SDK imports inside the handler if rarely invoked.
   - Connection Pooling: Reusing global HTTP/Database clients across warm container invocations outside the handler."""
    },
    {
        "title": "API Gateway Architecture: Rate Limiting Algorithms and Circuit Breakers",
        "category": "system_design",
        "tags": ["api-gateway", "rate-limiting", "token-bucket", "circuit-breaker", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """An API Gateway acts as the reverse proxy front-door for microservices, handling routing, SSL termination, and traffic shaping.
1. Rate Limiting Algorithms:
   - Token Bucket: Tokens refill at a constant rate R up to max capacity B. Each request consumes 1 token. Accommodates bursts while enforcing average rate.
   - Leaky Bucket: Requests enter a FIFO queue and leak out at a constant fixed rate. Completely smooths out traffic bursts.
   - Sliding Window Log / Counter: Tracks request timestamps in Redis sorted sets (ZADD/ZREMRANGEBYSCORE), preventing 2x boundary traffic spikes common in Fixed Window algorithms.
2. Circuit Breaker Pattern (Netflix Hystrix):
   - Closed: Normal traffic flows to backend service.
   - Open: When downstream error rate exceeds threshold (e.g. >50% timeouts over 10s), circuit trips to OPEN. Requests fail immediately with fallback response without hitting downstream service.
   - Half-Open: After a cooldown timeout, allows a small percentage of probe requests through. If successful, resets to CLOSED; otherwise returns to OPEN."""
    },
    {
        "title": "PostgreSQL Connection Pooling: PgBouncer vs PGPool and Pool Exhaustion",
        "category": "system_design",
        "tags": ["postgresql", "pgbouncer", "connection-pooling", "database", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """PostgreSQL uses a process-per-connection architecture where each client connection spawns a backend OS process consuming 5-10MB RAM and competing for CPU scheduler time. Exceeding 200-500 direct connections causes severe throughput collapse.
1. PgBouncer Pooling Modes:
   - Session Pooling: A server connection is dedicated to a client until client disconnects. Compatible with all PG features (prepared statements, temporary tables, LISTEN/NOTIFY).
   - Transaction Pooling: A server connection is bound to a client only for the duration of a single database transaction (BEGIN to COMMIT). 10,000 application threads can share 50 backend connections. Caveat: Application cannot rely on session-level state.
   - Statement Pooling: Connection released after every single SQL statement. Breaks multi-statement transactions.
2. Pool Sizing Formula (Brian Cantrill / PostgreSQL Rule of Thumb):
   - connections = ((core_count * 2) + effective_spindle_count). On an 8-core SSD server, a pool of 16-20 backend connections delivers higher throughput than 500 unmanaged connections."""
    },
    # ── Security & Authentication Patterns ────────────────────────────────────
    {
        "title": "OAuth 2.0 and OpenID Connect: Authorization Code Flow with PKCE",
        "category": "security",
        "tags": ["oauth2", "oidc", "security", "pkce", "jwt", "authentication"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """OAuth 2.0 is a delegated authorization framework; OpenID Connect (OIDC) adds an identity layer on top providing an id_token (JWT).
1. Authorization Code Flow with PKCE (Proof Key for Code Exchange):
   - Client generates a cryptographically random secret string: `code_verifier`.
   - Client derives `code_challenge = BASE64URL(SHA256(code_verifier))`.
   - Client redirects user to Authorization Server with `code_challenge` and `code_challenge_method=S256`.
   - User authenticates; Authorization Server returns a short-lived `authorization_code` to the client redirect URI.
   - Client sends POST request to `/token` endpoint providing the `authorization_code` AND the original `code_verifier`.
   - Authorization Server hashes the verifier with SHA256 and verifies it matches the challenge stored earlier, preventing authorization code interception attacks on public clients (mobile apps, SPAs).
2. State Parameter: Cryptographic CSRF protection token passed in authorization request and verified on callback."""
    },
    {
        "title": "JWT Security Pitfalls: The 'none' Algorithm Exploit, RS256 vs HS256, and Revocation",
        "category": "security",
        "tags": ["jwt", "security", "cryptography", "authentication", "vulnerabilities"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """JSON Web Tokens (JWT) encode claims in Base64URL header, payload, and signature sections (header.payload.signature).
1. The 'alg: none' Exploit: Early JWT parsers accepted `{alg: "none"}` in the header and skipped signature verification, allowing attackers to forge admin tokens by stripping the signature. Modern libraries must strictly whitelist allowed algorithms.
2. Asymmetric (RS256/ES256) vs Symmetric (HS256) Key Confusion:
   - HS256 uses a shared secret for both signing and verification.
   - RS256 uses a private key to sign and public key to verify.
   - Attack: Attacker modifies header to `alg: HS256` and signs the token with the server's public key (acting as an HMAC secret). If server accepts HS256, verification succeeds.
3. Distributed Token Revocation: Because JWTs are stateless, instant logout requires a Redis blocklist of `jti` (JWT ID) claims with TTL matching token expiration, or issuing short-lived access tokens (5-15 min) with rotating refresh tokens stored in the DB."""
    },
    {
        "title": "CSRF vs XSS Defenses: SameSite Cookies, Synchronizer Tokens, and CSP",
        "category": "security",
        "tags": ["csrf", "xss", "security", "samesite", "csp", "web-security"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """1. Cross-Site Scripting (XSS): Malicious JavaScript injected into the DOM via stored, reflected, or DOM-based vectors.
   - Defenses: Context-aware HTML/JS output encoding, HttpOnly cookie flags (prevents document.cookie access from JS), and strict Content Security Policy (CSP: `default-src 'self'; script-src 'self' 'nonce-xyz'`).
2. Cross-Site Request Forgery (CSRF): An attacker tricks an authenticated user browser into executing unwanted actions on a trusted site where they are logged in.
   - SameSite Cookie Attribute:
     - `SameSite=Strict`: Cookie never sent on cross-site requests.
     - `SameSite=Lax`: Cookie sent only on top-level navigation GET requests.
     - `SameSite=None; Secure`: Required for cross-site iframes/APIs.
   - Anti-CSRF Synchronizer Token: Server generates a unique cryptographically random token embedded in forms and verified in POST request headers (`X-CSRF-Token`)."""
    },
    # ── Advanced Python Internals & Observability ─────────────────────────────
    {
        "title": "Python Memory Internals: GIL, Reference Counting, and GC Cyclic Collection",
        "category": "code_pattern",
        "tags": ["python", "memory", "gil", "garbage-collection", "internals", "code_pattern"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """CPython memory management combines reference counting with a generational cyclic garbage collector:
1. Reference Counting: Every Python PyObject contains `ob_refcnt`. When variable references increase, refcnt increments; when variables fall out of scope (del), refcnt decrements. When refcnt drops to 0, memory is immediately deallocated.
2. Cyclic Garbage Collector: Reference counting cannot detect circular references (Object A references B, B references A). CPython generational GC runs across 3 generations (Gen 0, Gen 1, Gen 2). Objects surviving young collections are promoted to older generations.
3. Memory Optimization with `__slots__`:
   - Standard Python classes store instance attributes in an internal `__dict__`, consuming ~150-200 bytes per object.
   - Declaring `__slots__ = ('x', 'y')` allocates a fixed-size C-struct array, reducing memory footprint by 60-70% when instantiating millions of objects."""
    },
    {
        "title": "Distributed Tracing and Observability: OpenTelemetry and W3C TraceContext",
        "category": "system_design",
        "tags": ["opentelemetry", "tracing", "observability", "distributed-systems", "system_design"],
        "has_code": True,
        "source_file": "curated_tech_corpus.json",
        "text": """In distributed microservices, a single user action may traverse 20 independent services. Logging alone cannot isolate latency bottlenecks.
1. OpenTelemetry Tracing Core Concepts:
   - Trace: Represents the end-to-end journey of a request across all services. Identified by a globally unique 16-byte `trace_id`.
   - Span: A single contiguous unit of work within a service (e.g. SQL query, Redis get, external HTTP call). Contains `span_id`, `parent_span_id`, start/end timestamps, and key-value attributes.
2. Context Propagation (W3C TraceContext):
   - Passes trace context across HTTP/gRPC network boundaries using standardized headers:
     `traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01` (Version-TraceID-ParentSpanID-TraceFlags).
3. P99 Tail Latency Debugging: Spans capture microservice fan-out serialization bottlenecks, database lock contention, and unindexed query executions across asynchronous message queues."""
    }
]

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        break_pos = text.rfind(". ", start, end)
        if break_pos == -1 or break_pos < start + (chunk_size // 2):
            break_pos = text.rfind("\n", start, end)
        if break_pos == -1 or break_pos < start + (chunk_size // 2):
            break_pos = text.rfind(" ", start, end)
        if break_pos == -1:
            break_pos = end
        else:
            break_pos += 1
        chunk = text[start:break_pos].strip()
        if chunk:
            chunks.append(chunk)
        start = break_pos - overlap if (break_pos - overlap) > start else break_pos
    return chunks

def parse_post_mortems_readme(readme_path: Path) -> List[Dict[str, Any]]:
    """Parses the 200+ post-mortems markdown file into structured records."""
    if not readme_path.exists():
        return []
    
    with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    entries = []
    # Match patterns like [Company](URL). Description text...
    pattern = re.compile(r"\[(.*?)\]\((https?://.*?)\)\.\s*(.*?)(?=\n\n\[|\n## |\Z)", re.DOTALL)
    for match in pattern.finditer(content):
        company = match.group(1).strip()
        url = match.group(2).strip()
        desc = match.group(3).strip().replace("\n", " ")
        if len(desc) > 50:
            entries.append({
                "title": f"{company} Outage Incident Post-Mortem",
                "category": "post_mortem",
                "tags": [company.lower(), "outage", "post_mortem", "incident"],
                "has_code": False,
                "source_file": "post_mortems/README.md",
                "url": url,
                "text": f"Company: {company}\nReference: {url}\nIncident Summary and Root Cause:\n{desc}"
            })
    logging.info(f"Parsed {len(entries)} real-world post-mortem case studies from {readme_path.name}")
    return entries

def parse_system_design_solutions(solutions_dir: Path) -> List[Dict[str, Any]]:
    """Parses English system design solution files and Python solutions."""
    if not solutions_dir.exists():
        return []
    
    entries = []
    for md_file in solutions_dir.rglob("*.md"):
        if any(x in md_file.name for x in ["-ja", "-zh", "TRANSLATIONS"]):
            continue
        try:
            with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if len(text) > 200:
                topic = md_file.parent.name.replace("_", " ").title()
                entries.append({
                    "title": f"System Design Solution: {topic}",
                    "category": "system_design",
                    "tags": [topic.lower(), "system_design", "solution", "architecture"],
                    "has_code": "```" in text,
                    "source_file": str(md_file.relative_to(solutions_dir.parent.parent)),
                    "text": text[:35000]
                })
        except Exception as e:
            logging.warning(f"Error reading {md_file}: {e}")
    logging.info(f"Parsed {len(entries)} system design architecture solution guides.")
    return entries

def run_ingestion(wipe_existing: bool = False):
    logging.info(f"Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    cols = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in cols or wipe_existing:
        if wipe_existing and COLLECTION_NAME in cols:
            client.delete_collection(COLLECTION_NAME)
        logging.info(f"Creating collection '{COLLECTION_NAME}' (size={VECTOR_DIM}, metric=Cosine)...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest_models.VectorParams(
                size=VECTOR_DIM,
                distance=rest_models.Distance.COSINE
            )
        )

    logging.info(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    base_dir = Path(__file__).parent / "data" / "coding_corpus"
    post_mortems_path = base_dir / "post_mortems" / "README.md"
    sys_design_dir = base_dir / "system_design" / "solutions"

    all_docs = list(CURATED_TECH_CORPUS)
    all_docs.extend(parse_post_mortems_readme(post_mortems_path))
    all_docs.extend(parse_system_design_solutions(sys_design_dir))

    logging.info(f"Preparing chunks for {len(all_docs)} technical articles and incident autopsies...")
    points = []

    for doc in all_docs:
        raw_text = doc.get("text", "")
        chunks = chunk_text(raw_text, chunk_size=550, overlap=100)
        for idx, chunk_str in enumerate(chunks):
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc.get('title')}_{idx}_{chunk_str[:30]}"))
            payload = {
                "id": chunk_id,
                "title": doc.get("title"),
                "category": doc.get("category", "system_design"),
                "tags": doc.get("tags", []),
                "has_code": str(doc.get("has_code", False)),
                "source_file": doc.get("source_file", "unknown"),
                "text": chunk_str,
                "chunk_index": idx,
                "total_chunks": len(chunks)
            }
            points.append((chunk_id, chunk_str, payload))

    logging.info(f"Generated {len(points)} text chunks across all categories. Calculating embeddings in batches...")
    BATCH_SIZE = 64
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        texts = [b[1] for b in batch]
        embeddings = embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        qdrant_points = [
            rest_models.PointStruct(
                id=chunk_id,
                vector=emb.tolist(),
                payload=payload
            )
            for (chunk_id, chunk_str, payload), emb in zip(batch, embeddings)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=qdrant_points)
        logging.info(f"Upserted batch {i // BATCH_SIZE + 1} / {(len(points) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(qdrant_points)} points)")

    info = client.get_collection(COLLECTION_NAME)
    logging.info(f"SUCCESS! Collection '{COLLECTION_NAME}' now contains {info.points_count} points.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 2 Technical Knowledge Ingestion")
    parser.add_argument("--wipe", action="store_true", help="Wipe and recreate collection")
    args = parser.parse_args()
    run_ingestion(wipe_existing=args.wipe)