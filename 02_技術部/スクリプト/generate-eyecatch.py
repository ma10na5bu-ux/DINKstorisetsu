#!/usr/bin/env python3
"""
画像生成スクリプト

Imagen 4 Ultra API を使って画像を生成し、1200×630にリサイズする。

使い方:
  python3 generate-eyecatch.py <slug>                    # アイキャッチのみ
  python3 generate-eyecatch.py <slug> --h2               # アイキャッチ＋H2画像すべて
  python3 generate-eyecatch.py <slug> --h2-only           # H2画像のみ
  python3 generate-eyecatch.py <slug> --h2-only 2 4       # H2の2番と4番のみ

出力:
  01_編集部/画像/{slug}_eyecatch.jpg (1200×630)
  01_編集部/画像/{slug}_h2_{n}.jpg   (1200×630)
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

MODEL = "imagen-4.0-ultra-generate-001"
ASPECT_RATIO = "16:9"
OUTPUT_WIDTH = 1200
OUTPUT_HEIGHT = 630
JPEG_QUALITY = 95


def resize_to_eyecatch(img: Image.Image) -> Image.Image:
    """1200×630にリサイズする（16:9ネイティブ生成なのでクロップは最小限）"""
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


def generate_image(client, prompt_text: str, output_path: Path):
    """Imagen 4 Ultra で画像を1枚生成して保存する"""
    response = client.models.generate_images(
        model=MODEL,
        prompt=prompt_text,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=ASPECT_RATIO,
        ),
    )

    img_bytes = response.generated_images[0].image.image_bytes
    img = Image.open(io.BytesIO(img_bytes))
    final = resize_to_eyecatch(img)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final.save(output_path, "JPEG", quality=JPEG_QUALITY)
    print(str(output_path))


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 generate-eyecatch.py <slug> [--h2 | --h2-only [番号...]]", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1]
    args = sys.argv[2:]

    h2_mode = False
    h2_only_mode = False
    h2_numbers = []

    if "--h2" in args:
        h2_mode = True
    elif "--h2-only" in args:
        h2_only_mode = True
        idx = args.index("--h2-only")
        h2_numbers = [int(n) for n in args[idx + 1:]]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # アイキャッチ生成
    if not h2_only_mode:
        eyecatch_prompt_path = PROMPT_DIR / f"{slug}_eyecatch_prompt.md"
        if not eyecatch_prompt_path.exists():
            print(f"エラー: プロンプトファイルが見つかりません: {eyecatch_prompt_path}", file=sys.stderr)
            sys.exit(1)

        prompt_text = eyecatch_prompt_path.read_text(encoding="utf-8").strip()
        output_path = OUTPUT_DIR / f"{slug}_eyecatch.jpg"
        generate_image(client, prompt_text, output_path)

    # H2画像生成
    if h2_mode or h2_only_mode:
        # H2プロンプトファイルを検索
        if h2_numbers:
            h2_prompts = [(n, PROMPT_DIR / f"{slug}_h2_{n}_prompt.md") for n in h2_numbers]
        else:
            h2_prompts = []
            for n in range(1, 20):
                p = PROMPT_DIR / f"{slug}_h2_{n}_prompt.md"
                if p.exists():
                    h2_prompts.append((n, p))

        for n, prompt_path in h2_prompts:
            if not prompt_path.exists():
                print(f"警告: H2_{n} プロンプトが見つかりません: {prompt_path}", file=sys.stderr)
                continue
            prompt_text = prompt_path.read_text(encoding="utf-8").strip()
            output_path = OUTPUT_DIR / f"{slug}_h2_{n}.jpg"
            generate_image(client, prompt_text, output_path)


if __name__ == "__main__":
    main()
