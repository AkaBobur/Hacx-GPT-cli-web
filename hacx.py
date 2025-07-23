# hacx.py
import argparse
from cli_app import ChatApp
from web_app import launch_webui

def main():
    parser = argparse.ArgumentParser(description="HacxGPT Launcher")
    parser.add_argument("--cli", action="store_true", help="Terminal versiyani ishga tushirish")
    parser.add_argument("--web", action="store_true", help="Gradio WebUI ni ishga tushirish")

    args = parser.parse_args()

    if args.cli:
        app = ChatApp()
        app.run()
    elif args.web:
        launch_webui()
    else:
        print("❓ Qaysi rejimni ishga tushirasiz?\n  --cli  Terminal\n  --web  Browser WebUI")

if __name__ == "__main__":
    main()
