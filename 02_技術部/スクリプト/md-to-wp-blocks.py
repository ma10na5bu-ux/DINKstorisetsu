#!/usr/bin/env python3
"""
Markdown → WordPress Gutenbergブロック変換スクリプト

DINKsのトリセツ記事用。Markdownファイルを読み込み、
wp:paragraph / wp:heading / wp:list / wp:loos/balloon 形式のHTMLを出力する。

使い方:
  python3 md-to-wp-blocks.py <入力Markdownファイル>

出力:
  標準出力にWPブロックHTMLを出力（パイプやリダイレクトで使う）
  --file オプションで _wp.html ファイルにも保存可能
"""

import sys
import os
import re


def convert_inline(text):
    """インラインMarkdown（リンク・太字）をHTMLに変換"""
    # Markdownリンク [text](url) → <a href="url">text</a>
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        r'<a href="\2">\1</a>',
        text
    )
    # 太字 **text** → <strong>text</strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def is_metadata_line(line):
    """メタデータ行かどうか判定"""
    return (
        line.startswith('**カテゴリ**') or
        line.startswith('**メタディスクリプション**') or
        line.startswith('**キーワード**') or
        line.startswith('**スラッグ**') or
        line.startswith('**アイキャッチ**')
    )


def convert_md_to_wp_blocks(md_text):
    """MarkdownテキストをWPブロックHTMLに変換"""
    lines = md_text.split('\n')
    blocks = []
    i = 0
    in_metadata = False
    skip_first_hr = True  # メタデータ後の最初の---をスキップ

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行スキップ
        if not stripped:
            i += 1
            continue

        # H1タイトル行スキップ（WPはtitleフィールドで設定するため）
        if stripped.startswith('# ') and not stripped.startswith('## '):
            i += 1
            continue

        # メタデータ行スキップ
        if is_metadata_line(stripped):
            in_metadata = True
            i += 1
            continue

        # 区切り線
        if stripped == '---':
            if skip_first_hr and in_metadata:
                skip_first_hr = False
                in_metadata = False
                i += 1
                continue
            # 本文中の---はスキップ（WPではH2で十分区切れる）
            i += 1
            continue

        # HTMLコメント行（wp:loos/balloon等）はそのまま通す
        if stripped.startswith('<!-- wp:'):
            # balloonブロックや他のWPブロックをそのまま収集
            block_lines = [line]
            i += 1
            # 閉じタグまで収集
            while i < len(lines):
                block_lines.append(lines[i])
                if lines[i].strip().startswith('<!-- /wp:'):
                    i += 1
                    break
                i += 1
            blocks.append('\n'.join(block_lines))
            continue

        # H2見出し
        if stripped.startswith('## '):
            heading_text = stripped[3:]
            blocks.append(
                f'<!-- wp:heading -->\n'
                f'<h2>{heading_text}</h2>\n'
                f'<!-- /wp:heading -->'
            )
            i += 1
            continue

        # リスト（- で始まる行の連続）
        if stripped.startswith('- '):
            list_items = []
            while i < len(lines) and lines[i].strip().startswith('- '):
                item_text = convert_inline(lines[i].strip()[2:])
                list_items.append(f'<li>{item_text}</li>')
                i += 1
            items_html = ''.join(list_items)
            blocks.append(
                f'<!-- wp:list -->\n'
                f'<ul>{items_html}</ul>\n'
                f'<!-- /wp:list -->'
            )
            continue

        # 通常の段落
        para_text = convert_inline(stripped)
        blocks.append(
            f'<!-- wp:paragraph -->\n'
            f'<p>{para_text}</p>\n'
            f'<!-- /wp:paragraph -->'
        )
        i += 1

    return '\n\n'.join(blocks)


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 md-to-wp-blocks.py <Markdownファイル> [--file]")
        sys.exit(1)

    input_path = sys.argv[1]
    save_file = '--file' in sys.argv

    if not os.path.exists(input_path):
        print(f"エラー: ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    wp_html = convert_md_to_wp_blocks(md_text)

    # 標準出力
    print(wp_html)

    # --file オプションでファイル保存
    if save_file:
        base = os.path.splitext(input_path)[0]
        output_path = f"{base}_wp.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(wp_html)
        print(f"\n保存完了: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
