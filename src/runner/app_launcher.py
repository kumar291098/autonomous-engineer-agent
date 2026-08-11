import subprocess
import webbrowser
import time
from pathlib import Path
from typing import Tuple


class AppLauncher:
    """Launches generated Java Spring Boot backend and React frontend locally for testing."""

    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir).resolve()
        self.backend_dir = self.target_dir / "backend"
        self.frontend_dir = self.target_dir / "frontend"

    def launch_local_servers(self) -> Tuple[bool, str]:
        """Launches backend and frontend local dev servers."""
        logs = []
        backend_proc = None
        frontend_proc = None

        print("\n=======================================================")
        print("🚀 LAUNCHING LOCAL DEVELOPMENT SERVERS FOR TESTING")
        print("=======================================================")

        # 1. Check if Maven is available & launch backend
        if self.backend_dir.exists() and (self.backend_dir / "pom.xml").exists():
            print("▶️ Starting Java Spring Boot Backend Server (mvn spring-boot:run)...")
            try:
                backend_proc = subprocess.Popen(
                    ["mvn", "spring-boot:run"],
                    cwd=str(self.backend_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                logs.append("Java Spring Boot process launched on http://localhost:8080")
                print("   [OK] Java Spring Boot Server started on http://localhost:8080")
            except FileNotFoundError:
                print("   ⚠️ Maven (mvn) not found in system PATH. Cannot auto-start Spring Boot backend.")
                logs.append("Maven not found in PATH.")

        # 2. Check if NPM is available & launch frontend
        if self.frontend_dir.exists() and (self.frontend_dir / "package.json").exists():
            print("▶️ Starting React Frontend UI Server (npm start)...")
            try:
                frontend_proc = subprocess.Popen(
                    ["npm", "start"],
                    cwd=str(self.frontend_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                logs.append("React UI process launched on http://localhost:3000")
                print("   [OK] React UI Server started on http://localhost:3000")
            except FileNotFoundError:
                print("   ⚠️ NPM (npm) not found in system PATH. Cannot auto-start React UI frontend.")
                logs.append("NPM not found in PATH.")

        # 3. Open Browser
        print("\n🌐 Opening Local Application URLs in Default Browser...")
        time.sleep(2)
        try:
            webbrowser.open("http://localhost:8080")
            webbrowser.open("http://localhost:3000")
        except Exception as ex:
            print(f"   Note: Could not auto-open browser: {ex}")

        return True, "\n".join(logs)
