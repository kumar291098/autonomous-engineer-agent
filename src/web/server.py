import os
import sys
import json
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add workspace root to sys.path
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from src.schemas.models import FeatureSpecification, SpringBootArtifacts, ReactArtifacts
from src.agent.llm_client import LLMClient
from src.agent.fullstack_orchestrator import FullStackOrchestrator


class CopilotWebHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Agent Copilot Chat & Validation Web Interface."""

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        if parsed_url.path == "/" or parsed_url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = Path(__file__).parent / "index.html"
            self.wfile.write(html_path.read_bytes())

        elif parsed_url.path == "/api/download":
            query = urllib.parse.parse_qs(parsed_url.query)
            target = query.get("target", ["output_app"])[0]
            target_path = WORKSPACE_ROOT / target
            zip_dest = WORKSPACE_ROOT / f"{target_path.name}.zip"

            orchestrator = FullStackOrchestrator(
                feature_requirement="Export",
                target_dir=str(target_path),
                llm_client=LLMClient(provider="mock"),
            )
            created_zip = orchestrator.export_as_zip(str(zip_dest))
            
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{Path(created_zip).name}"')
            self.end_headers()
            self.wfile.write(Path(created_zip).read_bytes())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        if self.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(body)

            prompt = data.get("prompt", "")
            provider = data.get("provider", "gemini")
            api_key = data.get("api_key", "")
            mode = data.get("mode", "fullstack")
            output_dir = data.get("output_dir", "./output_app")

            if api_key:
                if provider == "gemini":
                    os.environ["GEMINI_API_KEY"] = api_key
                elif provider == "openai":
                    os.environ["OPENAI_API_KEY"] = api_key

            target_path = WORKSPACE_ROOT / output_dir
            llm_client = LLMClient(provider=provider, api_key=api_key if api_key else None)
            orchestrator = FullStackOrchestrator(
                feature_requirement=prompt,
                target_dir=str(target_path),
                llm_client=llm_client,
            )

            res = orchestrator.generate_fullstack_app(run_app=False)

            response_data = {
                "status": "SUCCESS",
                "feature_title": res["feature_title"],
                "backend_path": res["backend_path"],
                "frontend_path": res["frontend_path"],
                "backend_files_count": res["backend_files_count"],
                "frontend_files_count": res["frontend_files_count"],
                "bundle": res["bundle"].model_dump(),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))


def start_copilot_web_server(port: int = 5000):
    """Starts Copilot Web Server and opens browser interface."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, CopilotWebHandler)
    url = f"http://localhost:{port}"

    print(f"\n=======================================================")
    print(f"🚀 AGENT COPILOT CHAT & VALIDATION WEB DASHBOARD ACTIVE")
    print(f"=======================================================")
    print(f"🌐 Access Dashboard at: {url}")
    print(f"Press Ctrl+C to stop the server.\n")

    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Agent Copilot Web Server...")
        httpd.server_close()
