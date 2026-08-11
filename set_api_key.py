"""
Utility CLI tool to set, show, or delete your Gemini/OpenAI API key in .env file.
"""
import sys
import argparse
from pathlib import Path

ENV_PATH = Path(__file__).parent.resolve() / ".env"


def set_key(key_value: str, provider: str = "GEMINI_API_KEY"):
    lines = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(f"{provider}="):
                lines.append(line)
    lines.append(f"{provider}={key_value.strip()}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ {provider} saved permanently to .env file!")


def show_key():
    if not ENV_PATH.exists():
        print("❌ No .env file found.")
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "API_KEY" in line and "=" in line:
            k, v = line.split("=", 1)
            masked = v[:6] + "..." + v[-4:] if len(v) > 10 else "***"
            print(f"🔑 {k.strip()}: {masked}")


def delete_key():
    if ENV_PATH.exists():
        ENV_PATH.unlink()
        print("🗑️ .env file deleted.")
    else:
        print("ℹ️ No .env file to delete.")


def main():
    parser = argparse.ArgumentParser(description="Manage API Keys for Autonomous Engineer Agent")
    parser.add_argument("--set", type=str, help="Set your API Key e.g., python set_api_key.py --set AIzaSy...")
    parser.add_argument("--show", action="store_true", help="Display current saved API key")
    parser.add_argument("--delete", action="store_true", help="Delete saved API key")
    args = parser.parse_args()

    if args.set:
        set_key(args.set)
    elif args.show:
        show_key()
    elif args.delete:
        delete_key()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
