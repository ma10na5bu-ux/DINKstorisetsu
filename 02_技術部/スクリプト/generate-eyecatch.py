#!/usr/bin/env python3
"""
アイキャッチ画像生成スクリプト

Gemini Imagen 3 API を使ってアイキャッチ画像を生成する。

使い方:
  python3 generate-eyecatch.py <slug>

出力:
  01_編集部/画像/{slug}_eyecatch_raw.png を保存し、ファイルパスを stdout に出力する
"""

import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

PROMPT_DIR = PROJECT_ROOT / "01_編集部" / "画像"
OUTPUT_DIR = PROJECT_ROOT / "01_編集部" / "画像"

MODEL = "imagen-4.0-generate-001"
ASPECT_RATIO = "16:9"
NUMBER_OF_IMAGES = 1


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

    response = client.models.generate_images(
        model=MODEL,
        prompt=prompt_text,
        config=types.GenerateImagesConfig(
            number_of_images=NUMBER_OF_IMAGES,
            aspect_ratio=ASPECT_RATIO,
        ),
    )

    if not response.generated_images:
        print("エラー: 画像が生成されませんでした", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{slug}_eyecatch_raw.png"
    output_path.write_bytes(response.generated_images[0].image.image_bytes)

    print(str(output_path))


if __name__ == "__main__":
    main()
