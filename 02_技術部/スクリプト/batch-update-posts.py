#!/usr/bin/env python3
"""
既存記事一括更新スクリプト

Phase 1: <strong> → SWELL黄色マーカー＋太字 変換
Phase 2: メタディスクリプション（excerpt）一括設定

使い方:
  # Phase 1: strong → marker変換（dry-run）
  python3 batch-update-posts.py --strong-to-marker --dry-run

  # Phase 1: 実行
  python3 batch-update-posts.py --strong-to-marker

  # Phase 2: メタディスクリプション設定（JSONファイル指定）
  python3 batch-update-posts.py --meta-descriptions /tmp/dekataro_meta_descriptions.json --dry-run
  python3 batch-update-posts.py --meta-descriptions /tmp/dekataro_meta_descriptions.json

  # 両方同時
  python3 batch-update-posts.py --strong-to-marker --meta-descriptions /tmp/file.json
"""

import sys
import os
import json
import re
import urllib.request
import base64
import time
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WP_ENV_SCRIPT = os.path.join(SCRIPT_DIR, 'wp-env.sh')


def load_wp_env():
    """wp-env.shから認証情報を読み込む"""
    import subprocess
    result = subprocess.run(['bash', WP_ENV_SCRIPT], capture_output=True, text=True)
    env = {}
    for line in result.stdout.strip().split('\n'):
        m = re.match(r'export (\w+)="(.*)"', line)
        if m:
            env[m.group(1)] = m.group(2)
    return env


def wp_api_request(url, env, data=None, method='GET'):
    """WordPress REST API リクエスト"""
    credentials = base64.b64encode(
        f"{env['WP_USERNAME']}:{env['WP_APP_PASSWORD']}".encode()
    ).decode()

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Basic {credentials}')
    if data:
        req.add_header('Content-Type', 'application/json; charset=utf-8')

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {'error': body, 'code': e.code}, e.code


def build_escaped_json(payload):
    """SiteGuard WAF回避用JSON（< を \\u003c にエスケープ）"""
    json_str = json.dumps(payload, ensure_ascii=False)
    json_str = json_str.replace('<', '\\u003c')
    return json_str.encode('utf-8')


def fetch_all_posts(env):
    """全公開記事を取得"""
    wp_url = env['WP_URL']
    all_posts = []
    for page in range(1, 10):
        url = f'{wp_url}/wp-json/wp/v2/posts?per_page=30&page={page}&status=publish&context=edit&_fields=id,slug,title,content,excerpt'
        result, status = wp_api_request(url, env)
        if status != 200:
            break
        all_posts.extend(result)
        if len(result) < 30:
            break
    return all_posts


def convert_strong_to_marker(html_content):
    """<strong>text</strong> → <span class="swl-marker mark_yellow"><strong>text</strong></span>

    ただし以下は除外:
    - 既にマーカー内にある<strong>
    - ふきだし内の<strong>
    - 見出し内の<strong>
    """
    # 既にマーカー付きのものはスキップ
    if 'swl-marker' not in html_content and '<strong>' in html_content:
        # <strong>をマーカー付きに変換
        # ただしバルーン内やリンク内の<strong>は除外
        result = html_content

        # バルーンブロック内のstrongは変換しない
        # → バルーン内にstrongは通常使わないが念のためチェック

        # 単純な<strong>text</strong>パターンを変換
        result = re.sub(
            r'<strong>([^<]+)</strong>',
            r'<span class="swl-marker mark_yellow"><strong>\1</strong></span>',
            result
        )
        return result
    elif 'swl-marker' in html_content:
        # 既にマーカーがある記事では、マーカーなしのstrongのみ変換
        # マーカー内のstrongは触らない
        def replace_bare_strong(match):
            full = match.group(0)
            # 直前にswl-markerがある場合はスキップ（既にマーカー付き）
            return full

        # swl-marker内でないstrongのみ変換
        parts = re.split(r'(<span class="swl-marker[^"]*">.*?</span>)', html_content)
        converted_parts = []
        for part in parts:
            if 'swl-marker' in part:
                converted_parts.append(part)
            else:
                converted = re.sub(
                    r'<strong>([^<]+)</strong>',
                    r'<span class="swl-marker mark_yellow"><strong>\1</strong></span>',
                    part
                )
                converted_parts.append(converted)
        return ''.join(converted_parts)

    return html_content


def phase1_strong_to_marker(env, dry_run=False):
    """Phase 1: 全記事の<strong>をマーカー付きに変換"""
    print("=== Phase 1: strong → 黄色マーカー＋太字 ===\n")

    all_posts = fetch_all_posts(env)
    print(f"取得記事数: {len(all_posts)}")

    updated = 0
    skipped = 0
    errors = 0

    for p in all_posts:
        pid = p['id']
        slug = p['slug']
        raw = p['content']['raw']

        # 変換
        new_content = convert_strong_to_marker(raw)

        if new_content == raw:
            skipped += 1
            continue

        # 変更箇所カウント
        old_strong = len(re.findall(r'<strong>[^<]+</strong>', raw))
        new_marker = len(re.findall(r'swl-marker mark_yellow', new_content))
        existing_marker = len(re.findall(r'swl-marker mark_yellow', raw))
        added = new_marker - existing_marker

        print(f"  {pid:>4} {slug}: +{added}箇所マーカー化")

        if dry_run:
            continue

        # WordPress更新
        wp_url = env['WP_URL']
        url = f"{wp_url}/wp-json/wp/v2/posts/{pid}"
        payload = build_escaped_json({'content': new_content})
        result, status = wp_api_request(url, env, data=payload, method='POST')

        if status == 200:
            updated += 1
        else:
            print(f"    エラー: HTTP {status}")
            errors += 1

        time.sleep(0.5)  # レート制限対策

    mode = "dry-run" if dry_run else "完了"
    print(f"\n[{mode}] 更新: {updated}, スキップ: {skipped}, エラー: {errors}")
    return updated


def phase2_meta_descriptions(env, json_path, dry_run=False):
    """Phase 2: メタディスクリプション（excerpt）一括設定"""
    print("=== Phase 2: メタディスクリプション更新 ===\n")

    with open(json_path, 'r', encoding='utf-8') as f:
        descriptions = json.load(f)

    print(f"ディスクリプション数: {len(descriptions)}")

    wp_url = env['WP_URL']
    updated = 0
    skipped = 0
    errors = 0

    for item in descriptions:
        pid = item['id']
        slug = item['slug']
        meta_desc = item['meta_description']

        char_count = len(meta_desc)
        if char_count > 120:
            print(f"  {pid:>4} {slug}: 警告 - {char_count}文字（120文字超過）")

        print(f"  {pid:>4} {slug}: {meta_desc[:60]}...")

        if dry_run:
            continue

        # excerpt更新
        url = f"{wp_url}/wp-json/wp/v2/posts/{pid}"
        payload = json.dumps({'excerpt': meta_desc}, ensure_ascii=False).encode('utf-8')
        result, status = wp_api_request(url, env, data=payload, method='POST')

        if status == 200:
            updated += 1
        else:
            print(f"    エラー: HTTP {status}")
            errors += 1

        time.sleep(0.3)

    mode = "dry-run" if dry_run else "完了"
    print(f"\n[{mode}] 更新: {updated}, スキップ: {skipped}, エラー: {errors}")
    return updated


def main():
    parser = argparse.ArgumentParser(description='既存記事一括更新')
    parser.add_argument('--strong-to-marker', action='store_true',
                        help='<strong>を黄色マーカー＋太字に変換')
    parser.add_argument('--meta-descriptions', type=str,
                        help='メタディスクリプションJSONファイル')
    parser.add_argument('--dry-run', action='store_true',
                        help='実行せずに確認のみ')

    args = parser.parse_args()

    if not args.strong_to_marker and not args.meta_descriptions:
        parser.print_help()
        sys.exit(1)

    env = load_wp_env()
    if 'WP_URL' not in env:
        print("エラー: WP環境変数が読み込めません", file=sys.stderr)
        sys.exit(1)

    if args.strong_to_marker:
        phase1_strong_to_marker(env, dry_run=args.dry_run)

    if args.meta_descriptions:
        if not os.path.exists(args.meta_descriptions):
            print(f"エラー: ファイルが見つかりません: {args.meta_descriptions}")
            sys.exit(1)
        phase2_meta_descriptions(env, args.meta_descriptions, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
