#!/usr/bin/env python3
"""
アイキャッチ画像トリミングスクリプト

Gemini生成画像のウォーターマークを除去し、1200x630のJPEGに変換する。
ルール: 右200px・下140pxクロップ → 1200x630リサイズ → RGB変換 → JPEG保存

使い方:
  python3 trim-eyecatch.py <入力画像パス>

出力:
  入力ファイル名の拡張子を _trimmed.jpg に変えたファイル（同じディレクトリ）
"""

import sys
import os
from PIL import Image

# === トリミング定数（変更厳禁） ===
CROP_RIGHT = 200   # 右から除去するピクセル数
CROP_BOTTOM = 140  # 下から除去するピクセル数
OUTPUT_WIDTH = 1200
OUTPUT_HEIGHT = 630
JPEG_QUALITY = 95


def trim_eyecatch(input_path: str) -> str:
    if not os.path.exists(input_path):
        print(f"エラー: ファイルが見つかりません: {input_path}")
        sys.exit(1)

    img = Image.open(input_path)
    w, h = img.size
    print(f"元画像: {w}x{h}")

    # 右200px・下140pxクロップ
    cropped = img.crop((0, 0, w - CROP_RIGHT, h - CROP_BOTTOM))
    print(f"クロップ後: {cropped.size[0]}x{cropped.size[1]}")

    # 1200x630にリサイズ、RGB変換
    resized = cropped.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS).convert("RGB")

    # 出力パス: 元ファイル名_trimmed.jpg
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_trimmed.jpg"
    resized.save(output_path, "JPEG", quality=JPEG_QUALITY)
    print(f"保存完了: {output_path} ({OUTPUT_WIDTH}x{OUTPUT_HEIGHT})")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使い方: python3 trim-eyecatch.py <入力画像パス>")
        sys.exit(1)

    trim_eyecatch(sys.argv[1])
