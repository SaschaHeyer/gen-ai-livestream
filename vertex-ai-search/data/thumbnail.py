"""
Generate thumbnails for media_data.jsonl using Gemini image preview and upload to GCS.

Usage:
  GEMINI_API_KEY=... python data/thumbnail.py --bucket doit-vertex-ai-search --prefix data/ --jsonl data/media_data.jsonl [--overwrite]

Dependencies:
  pip install google-genai google-cloud-storage
"""

import argparse
import json
import mimetypes
import os
import tempfile
from typing import List

from google import genai
from google.genai import types
from google.cloud import storage
import time


def save_binary_file(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def build_prompt(title: str, description: str) -> str:
    base = (
        f"{title}. {description}\n"
        "[Subject/s doing XYZ in a futuristic city in evening in summer]\n"
        "Hyperealistic Amateur photography, Candid, 23mm focal length, detailed, Realism, "
        "Washed out, casual photography, natural lighting, 2020 vibe, amateur photo, slight JPEG artifacts, "
        "Overexposed, tiny imperfections, unpolished look, unedited snapshot"
    )
    return base


def gen_image_bytes(client: genai.Client, prompt: str, retries: int = 20, delay: float = 10.0) -> bytes:
    model = "gemini-3-pro-image-preview"
    contents: List[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(aspect_ratio="16:9", image_size="1K"),
    )

    attempt = 0
    while attempt < retries:
        try:
            for chunk in client.models.generate_content_stream(
                model=model, contents=contents, config=config
            ):
                if not chunk.candidates:
                    continue
                cand = chunk.candidates[0]
                if not cand.content or not cand.content.parts:
                    continue
                part = cand.content.parts[0]
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    return part.inline_data.data
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                raise
            print(f"Gemini overload/error ({e}); retrying {attempt}/{retries} in {delay}s...")
            time.sleep(delay)

    raise RuntimeError("No image data returned by Gemini after retries")


def upload_gcs(bucket_name: str, object_name: str, data: bytes) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type="image/png")
    # Uniform bucket-level access: public URL is deterministic
    return f"https://storage.googleapis.com/{bucket_name}/{object_name}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", default="data/media_data.jsonl")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="data/")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY env var is required")

    client = genai.Client(api_key=api_key)

    tmp = args.jsonl + ".tmp"
    with open(args.jsonl, "r", encoding="utf-8") as fin, open(
        tmp, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            rec = json.loads(line)
            struct = rec.get("structData", {})
            if struct.get("thumbnail") and not args.overwrite:
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue

            title = struct.get("title", rec.get("id"))
            desc = struct.get("description", "")
            prompt = build_prompt(title, desc)

            print(f"Generating image for: {title}")
            data = gen_image_bytes(client, prompt)

            object_name = f"{args.prefix.rstrip('/')}/{rec['id']}.png".lstrip("/")
            url = upload_gcs(args.bucket, object_name, data)

            struct["image_uri"] = url  # optional convenience
            struct["images"] = [{"uri": url, "name": rec.get("id", "img")}]  # aligns with media schema
            rec["structData"] = struct
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()

    os.replace(tmp, args.jsonl)
    print(f"Updated thumbnails written to {args.jsonl}")


if __name__ == "__main__":
    main()
