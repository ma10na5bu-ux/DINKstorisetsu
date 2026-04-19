#!/usr/bin/env python3
"""
アイキャッチ画像生成スクリプト

Gemini 3 Pro Image API を使ってアイキャッチ画像を生成し、1200×630にリサイズする。

使い方:
  python3 generate-eyecatch.py <slug>

出力:
  01_編集部/画像/{slug}_eyecatch.jpg (1200×630) を保存し、ファイルパスを stdout に出力する
"""

import io
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

PROMPT_DIR = PROJECT_ROOT / "01_編集部" / "画像"
OUTPUT_DIR = PROJECT_ROOT / "01_編集部" / "画像"

MODEL = "gemini-3-pro-image-preview"
OUTPUT_WIDTH = 1200
OUTPUT_HEIGHT = 630
JPEG_QUALITY = 95


def resize_to_eyecatch(img: Image.Image) -> Image.Image:
    """センタークロップして1200×630にリサイズする"""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = OUTPUT_WIDTH / OUTPUT_HEIGHT

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    elif src_ratio < target_ratio:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    return img.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS).convert("RGB")


def main():
    if len(sys.argv) != 2:
        print("使い方: python3 generate-eyecatch.py <slug>", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    prompt_path = PROMPT_DIR / f"{slug}_eyecatch_prompt.md"
    if not prompt_path.exists():
        print(f"エラー: プロンプトファイルが見つかりません: {prompt_path}", file=sys.stderr)
        sys.exit(1)

    prompt_text = prompt_path.read_text(encoding="utf-8").strip()

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt_text,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # レスポンスから画像データを取得
    image_data = None
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            image_data = part.inline_data.data
            break

    if image_data is None:
        print("エラー: 画像が生成されませんでした", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.open(io.BytesIO(image_data))
    final = resize_to_eyecatch(img)
    output_path = OUTPUT_DIR / f"{slug}_eyecatch.jpg"
    final.save(output_path, "JPEG", quality=JPEG_QUALITY)

    print(str(output_path))


if __name__ == "__main__":
    main()
