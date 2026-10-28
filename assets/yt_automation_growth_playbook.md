# YouTube AI Automation — Growth & Monetization Playbook

**Channels:** Chronos Shift (@ChronosShiftAI, alt-history) · Debate Protocol (@DebateProtocol, AI/psych debate) **System:** yt-automations monorepo — Pipeline 1 + Pipeline 2 + Growth Intelligence engine

> This is a living document. YouTube policy and monetization thresholds change — re-verify the numbers in this file every few months against YouTube's official Partner Program page before making decisions based on them.

---

## 1. Reality Check (read this first)

No automation system makes YouTube growth guaranteed. What you *can* control:

- Whether your channel survives policy review (engineering + compliance)  
- Whether your production is reliable and consistent (engineering)  
- Whether each video has a real reason to exist (creative judgment — the one part AI can't fully own)

What you *can't* control: algorithm changes, audience taste, competitor saturation, luck on any given upload. Build for the first category and accept uncertainty on the second.

"Passive income" is the wrong mental model for the first 6–12 months. Budget real time for: reviewing outputs, reading comments, watching analytics, and adjusting strategy. It becomes closer to passive only after the system has a proven track record and you trust it to run with lighter oversight.

---

## 2. System Snapshot

| Component | Channel A (Chronos Shift) | Channel B (Debate Protocol) |
| :---- | :---- | :---- |
| Format | Alternate-history "what if" narrative Shorts | Two-persona AI debate/discussion Shorts |
| Cadence target | 3–4/week | 5–7/week |
| Voice | Edge-TTS | Piper TTS (Adam & Brian) |
| Visuals | Fooocus SDXL + frozen Ken Burns motion | Fooocus SDXL + subway-surfers-style gameplay bg |
| Grounding | RAG v4 (arXiv, Europe PMC, OpenAlex, Wikipedia) | N/A (opinion/discussion format) |
| Shared backend | `growth/` closed-loop intelligence engine (topic scoring, A/B tests, strategy mutation) | Same |

---

## 3. YouTube Policy Compliance — Non-Negotiable Section

This is the section most likely to determine whether the whole system is wasted effort. Read it before scaling publish frequency.

### 3.1 The policy that governs you

YouTube's **Inauthentic Content policy** (renamed from "repetitious content" in July 2025, clarified further in July 2026) makes mass-produced, templated, or easily-replicable content ineligible for monetization — regardless of whether AI was used. It has three named categories:

1. **Generic/repetitive/template-based content** — little variation video to video  
2. **Off-putting or emotionally manipulative content**  
3. **AI personas giving advice on sensitive topics** (health, legal, financial, political)

**Enforcement is channel-wide, not per-video.** One bad pattern across your uploads can pull monetization from the entire channel. In January 2026, YouTube terminated 16 channels in a single wave — 4.7B combined lifetime views, ~$10M in annual ad revenue erased — specifically for this pattern, at real scale. This is being actively enforced, not theoretical.

### 3.2 Specific risk factors in your current build

- **Chronos Shift**: the "frozen Candidate A" Ken Burns motion used on every video, and the fixed 8-beat narrative template, are exactly the kind of invariant signal a reviewer is trained to flag. Freezing something means "quality floor," not "identical output" — vary the visible surface (pacing, hook phrasing, motion intensity within a range) even while keeping the underlying quality bar locked.  
- **Debate Protocol**: identical voice pair every video + identical gameplay background is a recognizable "template" pattern. Vary backgrounds/visual pacing across a rotating pool rather than one fixed loop.  
- **Both**: two channels run by the same operator, same tooling, same review process. Keep branding, thumbnail style, and pacing genuinely distinct so they don't read as a "channel farm."

### 3.3 Disclosure requirements

Toggle YouTube's **"Altered or synthetic content"** setting at upload for any video with AI voice/AI visuals presenting realistic scenes. Failure to disclose realistic synthetic media triggers a three-strike system: warning → 90-day monetization suspension → permanent YPP removal. Where your content is stylized/illustrative rather than photorealistic, the disclosure bar may not apply the same way — but default to disclosing when unsure; it doesn't hurt eligibility on its own.

### 3.4 Debate Protocol — extra caution

"AI dilemmas / philosophical paradoxes" content sits close to category 3 above (AI personas discussing sensitive topics). Mitigate by:

- Framing explicitly as discussion/entertainment, not advice ("what would you decide" not "here's the right answer")  
- Avoiding topics that read as medical, legal, financial, or political guidance  
- Never presenting either debate persona as a credentialed expert

### 3.5 Historical content — extra caution

Chronos Shift depicts real historical figures. If image/voice generation becomes photorealistic enough to make a real (even deceased) person appear to say/do something specific, research whether that trips the same "realistic altered content" disclosure trigger — this is worth a direct check against YouTube's current help documentation as your visual fidelity improves, since guidance in this specific area (deceased public figures) is less settled than for living people.

### 3.6 If you get flagged anyway

- Enforcement is channel-wide; you can fix the violating pattern and reapply after 30 days, or appeal if you believe it's a mistake.  
- Keep a paper trail: your QA gate outputs, RAG evidence packets, and review-approval logs are your evidence of human oversight and originality if you ever need to appeal.

---

## 4. Monetization Roadmap & Timeline

| Phase | Target | Requirements (current, 2026) |
| :---- | :---- | :---- |
| **0 — Stabilize** | Small controlled batch | 8–10 videos/channel through full human review before scaling automation frequency |
| **1 — Early access** | Super Thanks, memberships, Shopping | 500 subscribers + 3 public uploads (90 days) + either 3,000 watch hours (12mo) **or** 3M Shorts views (90 days) |
| **2 — Full YPP** | Ad + Premium revenue | 1,000 subscribers + either 4,000 watch hours (12mo) **or** 10M Shorts views (90 days) |
| **3 — Diversify** | Reduce single-platform risk | Affiliate links, sponsorships, localization, cross-platform repurposing |

**⚠️ Deadline worth planning around:** YouTube announced (Aug 10, 2026) that *new* applicants will need **double** the Phase 2 thresholds — 8,000 watch hours or 20M Shorts views — starting **February 1, 2027**. Creators already inside YPP keep current terms. Reaching full eligibility before that date is materially easier than after.

Watch hours and Shorts views are tracked on **separate paths** — Shorts feed views don't count toward the 4,000-hour long-form threshold. Since you're Shorts-only, the Shorts-views path is your realistic route.

---

## 5. Channel-Specific Growth Strategy

### 5.1 Chronos Shift (alt-history)

- Build a consistent narrator "voice" (tone, catchphrase, intro pattern) even without a face — this is what makes a channel feel authored rather than generated.  
- Lean into the comment-bait built into the format: "what do YOU think would've happened" prompts genuine debate in comments, which is a real engagement signal.  
- Rotate hook structures deliberately (counterfactual statement / question / direct address) — you already planned this; make sure the growth engine's A/B framework is actually testing across these, not just topics.  
- Historical accuracy is your moat — the RAG grounding + 0-unsupported-claims gate is a genuine differentiator vs. lower-effort alt-history channels. Consider surfacing sourcing in the description as a trust signal.

### 5.2 Debate Protocol

- Present genuinely balanced arguments — a debate format where one side always "wins" reads as scripted rather than authentic, and undermines the "off-putting/manipulative" risk category too.  
- Community-tab polls asking viewers to vote on who made the better argument drive return visits.  
- This format has a lower content-scarcity ceiling than history (debate topics are infinite) — the constraint will be quality/format fatigue, not topic exhaustion. Watch for format fatigue in retention data specifically, not just view counts.

### 5.3 Cross-channel discipline

- Don't cross-link the two channels obviously or run identical community posts on both — keep them operating as genuinely separate entities in presentation, even though the backend is shared.  
- Don't publish the same underlying "idea" reformatted across both channels — that's the reused-content risk in a different shape.

---

## 6. Technical Requirements Checklist

### 6.1 Content generation

- [ ] Topic sourcing: growth engine's scorer + anti-repetition guard (built)  
- [ ] Script generation: local draft (Ollama) → cloud model final pass (see §7)  
- [ ] RAG evidence retrieval: arXiv / Europe PMC / OpenAlex / Wikipedia (built, Pipeline 1 only)  
- [ ] Claim verification: separate model pass, not the same model that drafted (see §7)  
- [ ] Voice synthesis: Edge-TTS / Piper (built)  
- [ ] Visual generation: Fooocus SDXL with rotating (not frozen) prompt/motion variation  
- [ ] Assembly + captions: FFmpeg (built)  
- [ ] 17-point QA gate (built)

### 6.2 Review & publish

- [ ] Discord human review gate (built)  
- [ ] Channel identity hard-check before upload (built)  
- [ ] "Altered/synthetic content" disclosure toggle set programmatically at upload  
- [ ] Idempotent upload with manifest locks (built)

### 6.3 Ops / infrastructure (often skipped — don't skip these)

- [ ] **Secrets management** — your audit flagged a hardcoded Discord webhook; move all webhooks/keys to environment variables or a secrets manager before scaling  
- [ ] **Error alerting** — a Discord/Telegram webhook that pings you when a pipeline stage fails, not just when a video is ready for review  
- [ ] **API cost monitoring** — a running log of cloud LLM spend per video, so a bug doesn't silently burn budget  
- [ ] **Database backup verification** — you have the hot backup engine; actually test a restore once, don't assume it works  
- [ ] **Git workflow discipline** — given this is a monorepo across two production channels, protect `main`/production branches from direct pushes

### 6.4 Analytics loop

- [ ] YouTube Data/Analytics API ingestion (built)  
- [ ] **Add: policy-strike / monetization-status tracking** alongside view/retention metrics — this is your earliest warning system for §3  
- [ ] Weekly automated growth report review (you have the generator — actually read it weekly, don't let it run unread)

---

## 7. LLM / Model Strategy

Two separate decisions — don't conflate them.

### 7.1 Dev-time: the model that builds your code (inside Antigravity)

Antigravity 2.0 supports multiple models. Default to the fast/cheap option for routine iteration; switch models for high-stakes work.

| Task type | Recommended model | Why |
| :---- | :---- | :---- |
| Routine feature work, small fixes | Gemini 3.5 Flash (Antigravity default) | Fast, strong, free within Antigravity's default tier |
| Complex architecture, security-sensitive code (OAuth, credential handling) | Claude Sonnet (bring your own API key) | Stronger multi-file reasoning for high-stakes changes |
| Experimental/self-hosted work | GPT-OSS-120B | Open weights, no per-call cost if self-hosted |

### 7.2 Runtime: the model that writes your video scripts (this is the one that matters for monetization risk)

| Stage | Model tier | Reasoning |
| :---- | :---- | :---- |
| Topic outlining, rough draft | Local (Ollama llama3.2) | Free, private, fine for structure — low stakes |
| **Final script synthesis** | Cloud model (mid-tier) | Meaningfully better faithfulness to provided RAG evidence than a small local model |
| **Claim verification pass** | Cloud model, *different call than the drafter* | A model shouldn't grade its own homework — route this through a separate, stronger pass |

**Why this matters concretely:** small local models are more likely to "fill in" a plausible but ungrounded detail — exactly what your `verify_claims.py` gate exists to catch. If the same weak model drafts *and* verifies, it can miss its own hallucinations. Routing final synthesis + verification through a stronger cloud model costs pennies per 60-second script and directly protects the thing your whole compliance posture depends on: zero unsupported claims.

**What actually differs between model tiers for this job**, in order of importance for your use case:

1. **Faithfulness to source material** — matters most, given the verification gate  
2. **Context window** — matters for feeding full RAG evidence packets without truncation  
3. **Cost per call** — matters at volume, but even frontier-tier cost is trivial per video  
4. **Latency** — barely matters; this isn't a real-time pipeline

---

## 8. Cost & Budget Considerations

Rough categories to budget for (get current pricing before committing — don't rely on memorized numbers, they go stale fast):

- Cloud LLM calls for script synthesis + verification (per video, small)  
- Any cloud fallback for image/TTS generation if local generation fails or needs a quality boost  
- AdSense/YPP has no cost to join, but factor in time cost of the review/appeal cycle if flagged  
- Domain/branding assets if you formalize either channel's identity (logo, channel art)  
- Optional: paid Antigravity tier if you outgrow free preview limits

---

## 9. Risk Mitigation & Disaster Recovery

| Risk | Mitigation |
| :---- | :---- |
| Channel-wide demonetization flag | Human review gate (have it), disclosure toggles, format variation (§3) |
| Content ID claim on gameplay/music | Verify licensing status of all background assets before use, not after |
| API key leak | Secrets management (§6.3), key rotation policy |
| Pipeline silent failure | Error alerting (§6.3) |
| Database loss | Verified backup + restore test (§6.3) |
| Sudden policy change | Re-check this document's §3 and §4 quarterly against YouTube's official policy pages |
| Burnout from review queue at target cadence | Ramp cadence gradually (§Phase 0), don't jump straight to 5-7/week |

---

## 10. Non-Technical / Business Requirements

- **AdSense account** linked to each channel, 2-step verification enabled on the Google account  
- **Tax/GST awareness for AdSense income in India** — real implications once revenue starts; this needs an actual CA, not general advice, before money starts flowing  
- **Asset licensing** — confirm commercial-use rights on any gameplay footage, music, or fonts not generated in-house  
- **AI-generated image copyright status** — in several jurisdictions, purely AI-generated visual output has uncertain or limited copyright protection; this matters if you ever want to license, sell, or defend the visual assets as owned IP. Worth a quick check with counsel if the channels start generating meaningful revenue, rather than assuming full ownership by default.  
- **Time commitment** — comment engagement, weekly analytics review, periodic strategy adjustment; budget this explicitly rather than assuming zero-touch operation

---

## 11. Metrics & KPIs to Track Weekly

- Views, watch time, and retention curve per video (not just totals)  
- Subscriber conversion rate (views → subs)  
- Comment engagement rate  
- A/B experiment outcomes from the growth engine (accept/reject/insufficient data)  
- **Policy/strike status** (add this if not already tracked — see §6.4)  
- Progress toward Phase 1 → Phase 2 thresholds (§4), tracked against the Feb 2027 deadline

---

## 12. Additional Considerations to Maximize Success

- **Batch production, staggered publishing** — generate a week's content in one batch review session rather than reviewing one-off daily; reduces context-switching cost for you as the human reviewer.  
- **Competitive benchmarking** — periodically watch 3–5 top channels in each niche; note their hook structure, pacing, and thumbnail style as a sanity check, not to copy but to calibrate what's currently working.  
- **Thumbnail/title testing** — use YouTube Studio's native Test & Compare feature (already on your roadmap) once you have baseline traffic; this is free A/B infra you don't have to build yourself.  
- **Format fatigue monitoring** — retention trending down across recent uploads despite stable topic scores is your signal to introduce visual/structural variation, not just new topics.  
- **Consider a lightweight outsourcing step later** — once volume grows, a freelance editor doing a final human pass (even 10 minutes/video) adds a genuine authorship signal that's hard to fake and directly counters the "mass-produced" risk category.  
- **Document this as a case study** — separate from the revenue goal, the growth-intelligence engine (topic scoring, A/B testing, strategy mutation) is a legitimate differentiator for your AI-automation portfolio. Track results well enough that you could write this up as a case study independent of whether the channels themselves take off.

---

## 13. Immediate Next Actions

- [ ] Complete OAuth refresh for both channels  
- [ ] Fix hardcoded Discord webhook → env var  
- [ ] Add policy-status tracking to the analytics loop  
- [ ] Publish first controlled batch (8–10 videos/channel) with full manual review  
- [ ] Set disclosure toggle logic in the upload step  
- [ ] Introduce visual/format variation instead of the fully frozen production recipe  
- [ ] Re-verify all numbers in §3 and §4 against YouTube's current official policy before scaling further
