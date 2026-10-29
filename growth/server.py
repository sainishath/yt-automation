# -*- coding: utf-8 -*-
"""
server.py
---------
Lightweight REST API Bridge connecting Growth Intelligence to n8n Automation Workflows.
Runs on Port 8010.
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db, get_db
from growth.db.models import GrowthRepository, VideoModel
from growth.planner.content_planner import ContentPlanner
from growth.analytics.collector import AnalyticsCollector
from growth.learning.learning_engine import LearningEngine

PORT = 8010
LOG_FILE = Path("growth_server.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GrowthServer] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


class GrowthRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        repo = GrowthRepository()

        if path == "/api/growth/health" or path == "/health":
            self._send_json(200, {
                "status": "ok",
                "service": "growth-intelligence-server",
                "port": PORT
            })

        elif path == "/api/growth/plan-next":
            channel = params.get("channel", ["channel_a"])[0]
            try:
                planner = ContentPlanner(repo)
                plan = planner.plan_next_video(channel)
                self._send_json(200, {"status": "success", "plan": plan})
            except Exception as e:
                logging.error(f"Planning failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/growth/dashboard":
            try:
                ch_a_vids = repo.list_videos_by_channel("channel_a")
                ch_b_vids = repo.list_videos_by_channel("channel_b")
                self._send_json(200, {
                    "status": "success",
                    "channels": {
                        "channel_a": {"video_count": len(ch_a_vids)},
                        "channel_b": {"video_count": len(ch_b_vids)}
                    }
                })
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/channels":
            try:
                from growth.external_intelligence.repository import ExternalIntelligenceRepository
                ext_repo = ExternalIntelligenceRepository(repo.db_path)
                channel = params.get("channel", [None])[0]
                channels = ext_repo.list_external_channels(channel)
                self._send_json(200, {"status": "success", "external_channels": channels})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/patterns":
            try:
                from growth.external_intelligence.repository import ExternalIntelligenceRepository
                ext_repo = ExternalIntelligenceRepository(repo.db_path)
                channel = params.get("channel", ["channel_a"])[0]
                patterns = ext_repo.list_patterns(channel)
                self._send_json(200, {"status": "success", "patterns": patterns})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/recommendations":
            try:
                from growth.external_intelligence.repository import ExternalIntelligenceRepository
                from growth.external_intelligence.recommendation_engine import build_explainable_recommendation
                from growth.external_intelligence.schemas import ExternalPriorModel, ExternalPatternModel, TransferabilityScoreModel, TransferabilityClassification, PriorStatus, PatternType
                ext_repo = ExternalIntelligenceRepository(repo.db_path)
                channel = params.get("channel", ["channel_a"])[0]
                priors = ext_repo.list_external_priors(channel)
                recs = []
                for pr in priors:
                    pat_data = ext_repo.get_pattern(pr["pattern_id"])
                    ts_data = ext_repo.get_transferability_score(pr["pattern_id"], channel)
                    if pat_data and ts_data:
                        pat_model = ExternalPatternModel(
                            pattern_id=pat_data["pattern_id"], target_channel_id=channel,
                            pattern_type=PatternType(pat_data["pattern_type"]), name=pat_data["name"],
                            description=pat_data["description"], surface_technique=pat_data["surface_technique"],
                            underlying_principle=pat_data["underlying_principle"], our_possible_implementation=pat_data["our_possible_implementation"],
                            channel_count=pat_data["channel_count"], video_count=pat_data["video_count"], confidence=pat_data["confidence"]
                        )
                        ts_model = TransferabilityScoreModel(
                            transferability_id=ts_data["transferability_id"], pattern_id=pr["pattern_id"],
                            target_channel_id=channel, topic_similarity=ts_data["topic_similarity"],
                            audience_similarity=ts_data["audience_similarity"], format_similarity=ts_data["format_similarity"],
                            production_similarity=ts_data["production_similarity"], evidence_strength=ts_data["evidence_strength"],
                            repeatability=ts_data["repeatability"], overall_transferability_score=ts_data["overall_transferability_score"],
                            classification=TransferabilityClassification(ts_data["classification"]), reason=ts_data["reason"]
                        )
                        prior_model = ExternalPriorModel(
                            prior_id=pr["prior_id"], target_channel_id=channel, pattern_id=pr["pattern_id"],
                            hypothesis=pr["hypothesis"], transferability_classification=TransferabilityClassification(pr["transferability_classification"]),
                            prior_weight=pr["prior_weight"], status=PriorStatus(pr["status"])
                        )
                        recs.append(build_explainable_recommendation(prior_model, pat_model, ts_model))
                self._send_json(200, {"status": "success", "recommendations": recs})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/growth/experiments/external":
            try:
                channel = params.get("channel", [None])[0]
                experiments = repo.list_experiments(channel_id=channel)
                ext_experiments = [
                    e for e in experiments
                    if e.get("external_prior_id") or e.get("provenance") in ["EXTERNAL_INTELLIGENCE", "PUBLIC_YOUTUBE", "SIMULATION"]
                ]
                self._send_json(200, {"status": "success", "count": len(ext_experiments), "experiments": ext_experiments})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/experiments/ready", "/api/growth/experiments/ready"]:
            try:
                from growth.experiments.experiment_queue import ExperimentQueue
                queue = ExperimentQueue(repo=repo)
                channel = params.get("channel", [None])[0]
                if channel:
                    ready = queue.get_ready_experiments(channel)
                else:
                    ready = queue.get_ready_experiments("channel_a") + queue.get_ready_experiments("channel_b")
                self._send_json(200, {"status": "success", "count": len(ready), "ready_experiments": ready})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path.endswith("/outcome") and (path.startswith("/api/experiments/") or path.startswith("/api/growth/experiments/")):
            try:
                from growth.experiments.experiment_manager import ExperimentManager
                exp_id = path.split("/")[-2]
                mgr = ExperimentManager(repo=repo)
                outcome = mgr.evaluate_experiment_from_db(exp_id)
                self._send_json(200, {"status": "success", "outcome": outcome})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path.endswith("/lineage") and (path.startswith("/api/experiments/") or path.startswith("/api/growth/experiments/")):
            try:
                from growth.experiments.lineage_tracker import ExperimentLineageTracker
                exp_id = path.split("/")[-2]
                tracker = ExperimentLineageTracker(repo=repo)
                lineage = tracker.trace_experiment(exp_id)
                self._send_json(200, {"status": "success", "lineage": lineage})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/strategy-versions", "/api/growth/strategy-versions"]:
            try:
                from growth.strategy.strategy_manager import StrategyManager
                strat_mgr = StrategyManager()
                strat_a = strat_mgr.get_active_strategy("channel_a")
                strat_b = strat_mgr.get_active_strategy("channel_b")
                self._send_json(200, {"status": "success", "strategy_versions": {"channel_a": strat_a, "channel_b": strat_b}})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/experiments", "/api/growth/experiments"] or path.startswith("/api/experiments/") or path.startswith("/api/growth/experiments/"):
            try:
                clean_path = path.replace("/api/growth/experiments/", "").replace("/api/experiments/", "").strip()
                if clean_path and clean_path not in ["/api/experiments", "/api/growth/experiments"]:
                    exp = repo.get_experiment(clean_path)
                    if exp:
                        arms = repo.get_experiment_arms(clean_path)
                        self._send_json(200, {"status": "success", "experiment": exp, "arms": arms})
                    else:
                        self._send_json(404, {"status": "error", "message": f"Experiment '{clean_path}' not found"})
                else:
                    channel = params.get("channel", [None])[0]
                    status_filter = params.get("status", [None])[0]
                    experiments = repo.list_experiments(channel_id=channel, status=status_filter)
                    self._send_json(200, {"status": "success", "count": len(experiments), "experiments": experiments})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        else:
            self._send_json(404, {"status": "error", "message": "Endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}

        repo = GrowthRepository()
        collector = AnalyticsCollector(repo, use_mock_engine=True)

        if path == "/api/growth/record-upload":
            try:
                vid_id = payload.get("video_id")
                channel_id = payload.get("channel_id", "channel_a")
                title = payload.get("title", f"Video {vid_id}")
                duration = float(payload.get("duration", 45.0))
                yt_id = payload.get("youtube_video_id")
                yt_url = payload.get("youtube_url")

                vid = VideoModel(
                    video_id=vid_id,
                    channel_id=channel_id,
                    pipeline_id="alternate-history-shorts" if channel_id == "channel_a" else "convo-shorts",
                    title=title,
                    duration=duration,
                    youtube_video_id=yt_id,
                    youtube_url=yt_url,
                    upload_status="UPLOADED",
                    privacy_status=payload.get("privacy_status", "public"),
                    review_status="APPROVED",
                    strategy_version=payload.get("strategy_version", "v1.0")
                )
                repo.upsert_video(vid)
                collector.collect_snapshots_for_video(vid_id, duration=duration)

                self._send_json(200, {"status": "success", "video_id": vid_id, "message": "Upload recorded and snapshots queued"})
            except Exception as e:
                logging.error(f"Record upload failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/growth/run-learning-cycle":
            channel = payload.get("channel_id", "channel_a")
            try:
                engine = LearningEngine(repo, collector)
                res = engine.run_channel_learning_cycle(channel)
                self._send_json(200, {"status": "success", "learning_cycle": res})
            except Exception as e:
                logging.error(f"Learning cycle failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/research":
            channel = payload.get("channel_id", "channel_a")
            use_live = payload.get("use_live_api", False)
            try:
                from growth.external_intelligence.researcher import ExternalResearcher
                researcher = ExternalResearcher(repo=None)
                res = researcher.run_channel_research(channel, use_live_api=use_live)
                self._send_json(200, {"status": "success", "research_result": res})
            except Exception as e:
                logging.error(f"External research failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/experiments/approve", "/api/growth/experiments/approve"]:
            try:
                exp_id = payload.get("experiment_id")
                from growth.experiments.experiment_queue import ExperimentQueue
                queue = ExperimentQueue(repo=repo)
                res = queue.approve_experiment(exp_id)
                self._send_json(200, res)
            except Exception as e:
                logging.error(f"Approve experiment failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/jobs/create-experiment-job", "/api/growth/jobs/create-experiment-job"]:
            try:
                channel = payload.get("channel_id", "channel_a")
                topic_override = payload.get("topic_override")
                from growth.experiments.production_adapter import ProductionJobAdapter
                adapter = ProductionJobAdapter(repo=repo)
                job_res = adapter.create_experiment_production_job(channel, topic_override=topic_override)
                self._send_json(200, {"status": "success", "job": job_res})
            except Exception as e:
                logging.error(f"Create experiment job failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/videos/register-upload", "/api/growth/videos/register-upload"]:
            try:
                vid_id = payload.get("video_id")
                yt_id = payload.get("youtube_video_id")
                yt_url = payload.get("youtube_url")
                privacy = payload.get("privacy_status", "public")
                from growth.experiments.sample_tracker import ExperimentSampleTracker
                tracker = ExperimentSampleTracker(repo=repo)
                res = tracker.register_real_upload(video_id=vid_id, youtube_video_id=yt_id, youtube_url=yt_url, privacy=privacy)
                self._send_json(200, res)
            except Exception as e:
                logging.error(f"Register upload failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/upload-approved", "/api/growth/upload-approved"]:
            try:
                job_id = payload.get("job_id")
                privacy = payload.get("privacy_status", "public")
                if not job_id:
                    self._send_json(400, {"status": "error", "message": "Missing 'job_id' parameter in payload"})
                    return

                with get_db(repo.db_path) as conn:
                    job_row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

                if not job_row:
                    self._send_json(404, {"status": "error", "message": f"Job '{job_id}' not found in growth.db"})
                    return

                job_dict = dict(job_row)
                channel_id = job_dict.get("channel_id", "channel_a")
                pipeline_id = job_dict.get("pipeline_id", "alternate-history-shorts")
                video_id = job_dict.get("video_id")
                job_status = job_dict.get("status")

                # Strict Scrapped / Rejection Guard: Never upload rejected/scrapped videos in any mode
                if job_status == "REJECTED":
                    self._send_json(403, {
                        "status": "error",
                        "error_code": "CANNOT_UPLOAD_SCRAPPED_VIDEO",
                        "message": f"Job '{job_id}' was rejected by human reviewer and is permanently scrapped. All uploads (including private) are strictly barred."
                    })
                    return

                if video_id:
                    with get_db(repo.db_path) as conn:
                        v_row = conn.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
                        if v_row:
                            v_dict = dict(v_row)
                            if v_dict.get("review_status") == "REJECTED" or v_dict.get("upload_status") == "SCRAPPED":
                                self._send_json(403, {
                                    "status": "error",
                                    "error_code": "CANNOT_UPLOAD_SCRAPPED_VIDEO",
                                    "message": f"Video '{video_id}' was rejected by human reviewer and is permanently scrapped. All uploads (including private) are strictly barred."
                                })
                                return

                logging.info(f"Processing upload approval for Job '{job_id}' (Channel: {channel_id}, Pipeline: {pipeline_id}, Video: {video_id})")

                # Update job status to UPLOADING
                with get_db(repo.db_path) as conn:
                    conn.execute("UPDATE jobs SET status = 'UPLOADING', updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", (job_id,))

                yt_id = None
                yt_url = None
                video_file = None

                if channel_id == "channel_a" or pipeline_id == "alternate-history-shorts":
                    # Channel A Upload via alternate-history-shorts/scripts/upload_video.py
                    p1_script_dir = ROOT_DIR / "alternate-history-shorts" / "scripts"
                    if str(p1_script_dir) not in sys.path:
                        sys.path.insert(0, str(p1_script_dir))
                    from upload_video import upload_video as p1_upload
                    
                    video_folder = ROOT_DIR / "alternate-history-shorts" / "output" / video_id
                    final_mp4 = video_folder / "final" / f"{video_id}_final.mp4"
                    if not final_mp4.exists():
                        # Check direct mp4
                        mp4_candidates = list((video_folder / "final").glob("*.mp4"))
                        if mp4_candidates:
                            final_mp4 = mp4_candidates[0]

                    if not final_mp4.exists():
                        raise FileNotFoundError(f"Final MP4 not found for video {video_id} at {final_mp4}")

                    video_file = str(final_mp4)
                    meta_path = video_folder / "metadata.json"
                    title = f"What If {job_dict.get('topic_text')}?"
                    description = ""
                    tags = ["#shorts", "#history", "#whatif"]
                    if meta_path.exists():
                        with open(meta_path, "r", encoding="utf-8") as mf:
                            m = json.load(mf)
                            title = m.get("title", title)
                            description = m.get("description", description)
                            tags = m.get("tags", tags)

                    up_res = p1_upload(
                        video_id=video_id,
                        final_mp4=final_mp4,
                        title=title,
                        description=description,
                        tags=tags,
                        privacy=privacy
                    )
                    yt_id = up_res.get("youtube_video_id")
                    yt_url = up_res.get("public_url")

                else:
                    # Channel B Upload via convo-shorts/yt-automation-engine/uploader.py
                    p2_engine_dir = ROOT_DIR / "convo-shorts" / "yt-automation-engine"
                    if str(p2_engine_dir) not in sys.path:
                        sys.path.insert(0, str(p2_engine_dir))
                    from uploader import upload_to_youtube as p2_upload
                    from metadata_generator import generate_metadata

                    p2_candidates = [
                        ROOT_DIR / "data" / "yt-automation-engine" / "videos" / f"{video_id}.mp4",
                        ROOT_DIR / "convo-shorts" / "data" / "videos" / f"{video_id}.mp4",
                        ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "data" / "yt-automation-engine" / "videos" / f"{video_id}.mp4",
                        ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "data" / "videos" / f"{video_id}.mp4"
                    ]
                    final_mp4 = None
                    for cand in p2_candidates:
                        if cand.exists():
                            final_mp4 = cand
                            break

                    if not final_mp4:
                        # Fallback: search anywhere in repo
                        found = list(ROOT_DIR.rglob(f"*{video_id}*.mp4"))
                        # Exclude temp proxies
                        found = [f for f in found if "review_proxy" not in f.name and "temp" not in str(f)]
                        if found:
                            final_mp4 = found[0]

                    if not final_mp4 or not final_mp4.exists():
                        raise FileNotFoundError(f"Final MP4 not found for video {video_id} across workspace directories.")

                    video_file = str(final_mp4)
                    meta = generate_metadata(job_dict.get("topic_text", ""), "Coding & Software Engineering")
                    up_res = p2_upload(
                        video_path=str(final_mp4),
                        title=meta.get("title", f"Short: {job_dict.get('topic_text')}"),
                        description=meta.get("description", job_dict.get("topic_text", "")),
                        hashtags=meta.get("tags", ["#shorts", "#programming", "#coding"]),
                        privacy_status=privacy
                    )
                    yt_id = up_res.get("video_id")
                    yt_url = up_res.get("url")

                # Update growth.db: Register upload & set Job to PUBLISHED
                from growth.experiments.sample_tracker import ExperimentSampleTracker
                tracker = ExperimentSampleTracker(repo=repo)
                tracker.register_real_upload(
                    video_id=video_id,
                    youtube_video_id=yt_id,
                    youtube_url=yt_url,
                    privacy=privacy
                )

                with get_db(repo.db_path) as conn:
                    conn.execute("""
                        UPDATE jobs 
                        SET status = 'PUBLISHED', updated_at = CURRENT_TIMESTAMP 
                        WHERE job_id = ?
                    """, (job_id,))

                logging.info(f"Job '{job_id}' successfully uploaded and published to YouTube! ({yt_url})")

                self._send_json(200, {
                    "status": "success",
                    "job_id": job_id,
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "youtube_video_id": yt_id,
                    "youtube_url": yt_url,
                    "privacy_status": privacy
                })

            except Exception as e:
                logging.error(f"Approval upload execution failed for job: {e}", exc_info=True)
                with get_db(repo.db_path) as conn:
                    conn.execute("UPDATE jobs SET status = 'FAILED', error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?", (str(e), payload.get("job_id", "")))
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/reject", "/api/growth/reject"]:
            try:
                job_id = payload.get("job_id")
                reason = payload.get("reason", "REJECTED_BY_USER")
                if not job_id:
                    self._send_json(400, {"status": "error", "message": "Missing 'job_id' parameter in payload"})
                    return

                with get_db(repo.db_path) as conn:
                    job_row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

                if not job_row:
                    self._send_json(404, {"status": "error", "message": f"Job '{job_id}' not found in growth.db"})
                    return

                job_dict = dict(job_row)
                channel_id = job_dict.get("channel_id", "channel_a")
                pipeline_id = job_dict.get("pipeline_id", "alternate-history-shorts")
                video_id = job_dict.get("video_id")

                logging.info(f"Processing rejection/scrap request for Job '{job_id}' (Channel: {channel_id}, Pipeline: {pipeline_id}, Video: {video_id})")

                # 1. Update growth.db: Job -> REJECTED, Video -> REJECTED / SCRAPPED
                with get_db(repo.db_path) as conn:
                    conn.execute("""
                        UPDATE jobs 
                        SET status = 'REJECTED', error_message = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE job_id = ?
                    """, (f"SCRAPPED: {reason}", job_id))
                    
                    if video_id:
                        conn.execute("""
                            UPDATE videos 
                            SET review_status = 'REJECTED', upload_status = 'SCRAPPED', privacy_status = 'NONE'
                            WHERE video_id = ?
                        """, (video_id,))

                # 2. File Scrapping & Quarantine on disk
                scrapped_files = []
                if channel_id == "channel_a" or pipeline_id == "alternate-history-shorts":
                    video_folder = ROOT_DIR / "alternate-history-shorts" / "output" / video_id
                    if video_folder.exists():
                        for mp4 in video_folder.rglob("*.mp4"):
                            try:
                                scrapped_files.append(str(mp4))
                                mp4.unlink(missing_ok=True)
                            except Exception:
                                pass
                        manifest_p = video_folder / "run_manifest.json"
                        if manifest_p.exists():
                            try:
                                with open(manifest_p, "r", encoding="utf-8") as mf:
                                    m_data = json.load(mf)
                                m_data["status"] = "REJECTED_SCRAPPED"
                                m_data["scrapped_reason"] = reason
                                with open(manifest_p, "w", encoding="utf-8") as mf:
                                    json.dump(m_data, mf, indent=2)
                            except Exception:
                                pass
                else:
                    p2_video_candidates = [
                        ROOT_DIR / "convo-shorts" / "data" / "videos" / f"{video_id}.mp4",
                        ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "data" / "yt-automation-engine" / "videos" / f"{video_id}.mp4",
                        ROOT_DIR / "convo-shorts" / "yt-automation-engine" / "data" / "videos" / f"{video_id}.mp4",
                        ROOT_DIR / "data" / "yt-automation-engine" / "videos" / f"{video_id}.mp4"
                    ]
                    for vf in p2_video_candidates:
                        if vf.exists():
                            scrapped_files.append(str(vf))
                            try:
                                vf.unlink(missing_ok=True)
                            except Exception:
                                pass
                        manifest_vf = vf.with_suffix(".manifest.json")
                        if manifest_vf.exists():
                            try:
                                with open(manifest_vf, "r", encoding="utf-8") as mf:
                                    m_data = json.load(mf)
                                m_data["status"] = "REJECTED_SCRAPPED"
                                m_data["scrapped_reason"] = reason
                                with open(manifest_vf, "w", encoding="utf-8") as mf:
                                    json.dump(m_data, mf, indent=2)
                            except Exception:
                                pass

                # 3. Dispatch Discord confirmation notification
                try:
                    webhook_url = (
                        os.getenv("DISCORD_WEBHOOK_URL_P1" if channel_id == "channel_a" else "DISCORD_WEBHOOK_URL_P2")
                        or os.getenv("DISCORD_ERROR_WEBHOOK_URL")
                        or os.getenv("DISCORD_REVIEW_WEBHOOK_URL", "")
                    )
                    if webhook_url:
                        notif_text = (
                            f"🔴 **[VIDEO SCRAPPED]**\n"
                            f"Job `{job_id}` (`{video_id}`) was **REJECTED** and permanently scrapped.\n"
                            f"• Upload Status: **SCRAPPED (Zero uploads allowed, including private)**\n"
                            f"• Reason: `{reason}`\n"
                            f"• Files deleted: {len(scrapped_files)} video artifact(s)"
                        )
                        requests.post(webhook_url, json={"content": notif_text}, timeout=10)
                except Exception as n_err:
                    logging.warning(f"Failed to post rejection notification to Discord: {n_err}")

                logging.info(f"Job '{job_id}' successfully rejected and scrapped. Scrapped files: {scrapped_files}")

                self._send_json(200, {
                    "status": "success",
                    "action": "SCRAPPED",
                    "job_id": job_id,
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "scrapped_files_count": len(scrapped_files),
                    "message": "Video successfully rejected and scrapped. Upload barred."
                })
            except Exception as e:
                logging.error(f"Rejection execution failed for job: {e}", exc_info=True)
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/snapshots/check-due", "/api/growth/snapshots/check-due"]:
            try:
                import threading
                from growth.analytics.fetch_analytics import fetch_due_snapshots
                dry_run_flag = payload.get("dry_run", False)

                def _async_fetch():
                    try:
                        logging.info("[Async Fetch] Starting background analytics snapshot ingestion...")
                        fetch_res = fetch_due_snapshots(repo=repo, dry_run=dry_run_flag)
                        logging.info(f"[Async Fetch] Finished: {fetch_res.get('collected_count')} collected, {fetch_res.get('skipped_count')} skipped.")
                    except Exception as err:
                        logging.error(f"[Async Fetch Error] Background analytics fetch failed: {err}")

                thread = threading.Thread(target=_async_fetch, daemon=True)
                thread.start()

                self._send_json(202, {
                    "status": "accepted",
                    "message": "Analytics snapshot ingestion triggered in background.",
                    "dry_run": dry_run_flag
                })
            except Exception as e:
                logging.error(f"Check due snapshots dispatch failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        else:
            self._send_json(404, {"status": "error", "message": "Endpoint not found"})


def run_server(port: int = PORT):
    init_db()
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, GrowthRequestHandler)
    logging.info(f"Growth Intelligence REST API server running on http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down Growth server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
