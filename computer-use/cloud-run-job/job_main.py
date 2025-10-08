from __future__ import annotations

import argparse
import os

from runner import run_and_print

DEFAULT_URL = "https://browser-use-demo-24173060393.us-central1.run.app/"
DEFAULT_NOTE = "Automated upload triggered by Gemini Computer Use agent."


def main() -> None:
    parser = argparse.ArgumentParser(description="Cloud Run job entrypoint")
    parser.add_argument(
        "--target-url",
        default=os.getenv("TARGET_URL", DEFAULT_URL),
        help="URL the automation should interact with.",
    )
    parser.add_argument(
        "--note-text",
        default=os.getenv("NOTE_TEXT", DEFAULT_NOTE),
        help="Optional note text to insert before uploading the PDF.",
    )
    parser.add_argument(
        "--pdf-uri",
        default=os.getenv("PDF_URI"),
        help="Path or gs:// URI to the PDF that should be uploaded.",
    )
    args = parser.parse_args()

    target_url = args.target_url
    if not target_url:
        raise RuntimeError("Target URL must be provided via --target-url or TARGET_URL env var.")

    note_text = args.note_text
    pdf_uri = args.pdf_uri

    print(f"Running automation against {target_url}")
    if pdf_uri:
        print(f"Using PDF source: {pdf_uri}")
    run_and_print(target_url, note_text, pdf_uri)


if __name__ == "__main__":
    main()
