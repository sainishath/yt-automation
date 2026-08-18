# -*- coding: utf-8 -*-
"""
server.py
---------
Lightweight REST API Bridge connecting Growth Intelligence to n8n Automation Workflows.
Runs on Port 8010.
"""

import sys
import json
import logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
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
