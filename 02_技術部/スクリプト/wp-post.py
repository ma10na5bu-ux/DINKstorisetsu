#!/usr/bin/env python3
"""
WordPress記事投稿スクリプト（SiteGuard WAF対策込み）

SiteGuard LiteのWAFが、HTMLコメント（<!-- -->）+ 特定キーワード（and/or/select等）の
組み合わせをSQLインジェクションと誤検知してブロックする問題に対応。

対策:
  1. JSON内の < を \u003c にunicodeエスケープしてWAFを回避
  2. WAFがブロックするキーワード（and等）を安全な形に一時変換して投稿
  3. ブロックされた場合は段階的投稿にフォールバック

使い方:
  # 新規投稿（下書き）
  python3 wp-post.py <WPブロックHTML or Markdownファイル> \\
    --title "記事タイトル" \\
    --slug "slug-name" \\
    --excerpt "メタディスクリプション" \\
    --media 167

  # 既存記事の更新
  python3 wp-post.py <ファイル> --post-id 168

  # 公開
  python3 wp-post.py --post-id 168 --publish

  # Markdownから一括（変換→投稿）
  python3 wp-post.py <Markdown.md> --title "タイトル" --slug "slug" --auto
"""

import sys
import os
import json
import re
import urllib.request
import base64
import subprocess
import time
import argparse

# SiteGuard WAFがブロックするキーワード（HTMLコメントとの組み合わせで誤検知）
# 大文字小文字を問わずブロックされる
WAF_BLOCKED_KEYWORDS = ['and', 'or', 'select', 'union', 'drop', 'insert', 'update', 'delete']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WP_ENV_SCRIPT = os.path.join(SCRIPT_DIR, 'wp-env.sh')
MD_TO_WP_SCRIPT = os.path.join(SCRIPT_DIR, 'md-to-wp-blocks.py')

# WAF回避用プレースホルダー（コンテンツに出現しない文字列）
PLACEHOLDER_PREFIX = '\ufffe'  # Unicode noncharacter


def load_wp_env():
    """wp-env.shから認証情報を読み込む"""
    result = subprocess.run(
        ['bash', WP_ENV_SCRIPT],
        capture_output=True, text=True
    )
    env = {}
    for line in result.stdout.strip().split('\n'):
        m = re.match(r'export (\w+)="(.*)"', line)
        if m:
            env[m.group(1)] = m.group(2)
    return env


def sanitize_for_waf(content):
    """SiteGuard WAFにブロックされるキーワードを一時的に安全な形に変換"""
    sanitized = content
    replacements = {}

    for keyword in WAF_BLOCKED_KEYWORDS:
        # HTMLコメント内またはその近くにあるキーワードのみ対象
        # 実際にはSiteGuardはリクエスト全体を見るので、全置換が安全
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
        matches = list(pattern.finditer(sanitized))

        if matches:
            # キーワードを & 記号で代用（andの場合）、または全角に変換
            for match in reversed(matches):
                original = match.group()
                if original.lower() == 'and':
                    # "and" → "&"（自然な代替）
                    replacement = '&'
                else:
                    # その他のキーワードはそのまま（出現する可能性は低い）
                    replacement = original

                if original != replacement:
                    sanitized = sanitized[:match.start()] + replacement + sanitized[match.end():]
                    replacements[original] = replacement

    return sanitized, replacements


def build_escaped_json(payload):
    """SiteGuard WAFを回避するJSON文字列を生成

    通常のjson.dumps()ではなく、< を \u003c にエスケープすることで
    WAFのHTMLコメント検知を回避する
    """
    json_str = json.dumps(payload, ensure_ascii=False)
    # < をunicodeエスケープに置換（JSONパーサーは \u003c を < として解釈する）
    json_str = json_str.replace('<', '\\u003c')
    return json_str.encode('utf-8')


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


def post_content_safe(post_id, content, env):
    """SiteGuard WAF対策付きコンテンツ投稿

    Step 1: WAFブロックキーワードを安全な形に変換
    Step 2: unicodeエスケープ付きJSONで投稿
    Step 3: ブロックされた場合は段階的投稿にフォールバック
    """
    wp_url = env['WP_URL']
    url = f"{wp_url}/wp-json/wp/v2/posts/{post_id}"

    # Step 1: WAFキーワードを変換
    safe_content, replacements = sanitize_for_waf(content)
    if replacements:
        print(f"  WAF対策: {len(replacements)}箇所のキーワードを変換", file=sys.stderr)
        for orig, repl in replacements.items():
            print(f"    '{orig}' → '{repl}'", file=sys.stderr)

    # Step 2: unicodeエスケープ付きで一括投稿を試みる
    payload_bytes = build_escaped_json({'content': safe_content})
    result, status = wp_api_request(url, env, data=payload_bytes, method='POST')

    if status == 200:
        print("  一括投稿: 成功", file=sys.stderr)
        return result

    # Step 3: 段階的投稿にフォールバック
    print(f"  一括投稿: ブロック（HTTP {status}）→ 段階的投稿に切り替え", file=sys.stderr)

    blocks = safe_content.split('\n\n')
    print(f"  ブロック数: {len(blocks)}", file=sys.stderr)

    # リセット
    reset_payload = build_escaped_json({'content': '<p>.</p>'})
    wp_api_request(url, env, data=reset_payload, method='POST')
    time.sleep(0.3)

    accumulated = ""
    failed_blocks = []

    for i, block in enumerate(blocks):
        candidate = accumulated + ("\n\n" if accumulated else "") + block
        test_payload = build_escaped_json({'content': candidate})
        result, status = wp_api_request(url, env, data=test_payload, method='POST')

        if status == 200:
            accumulated = candidate
        else:
            failed_blocks.append((i, block[:60]))
            print(f"  Block {i}: スキップ（WAFブロック）: {block[:40]}...", file=sys.stderr)

    if failed_blocks:
        print(f"  警告: {len(failed_blocks)}ブロックがスキップされました", file=sys.stderr)
        for idx, preview in failed_blocks:
            print(f"    Block {idx}: {preview}", file=sys.stderr)
    else:
        print(f"  段階的投稿: 全{len(blocks)}ブロック成功", file=sys.stderr)

    return result


def convert_md_to_wp(md_path):
    """Markdownファイルをmd-to-wp-blocks.pyで変換"""
    result = subprocess.run(
        [sys.executable, MD_TO_WP_SCRIPT, md_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"エラー: MD変換失敗: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def extract_metadata(md_path):
    """Markdownファイルからメタデータを抽出（YAMLフロントマター対応）"""
    meta = {}
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # YAMLフロントマター（---で囲まれたブロック）を優先パース
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip()
            val = val.strip().strip('"\'')
            if key == 'title':
                meta['title'] = val
            elif key == 'slug':
                meta['slug'] = val
            elif key == 'meta_description':
                meta['excerpt'] = val
        return meta

    # フォールバック: Markdown見出し形式
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('# ') and not line.startswith('## '):
            meta['title'] = line[2:]
        elif line.startswith('**メタディスクリプション**:'):
            meta['excerpt'] = line.split(':', 1)[1].strip()
        elif line.startswith('**スラッグ**:'):
            meta['slug'] = line.split(':', 1)[1].strip()
    return meta


def main():
    parser = argparse.ArgumentParser(description='WordPress記事投稿（SiteGuard WAF対策付き）')
    parser.add_argument('file', nargs='?', help='WPブロックHTMLまたはMarkdownファイル')
    parser.add_argument('--title', help='記事タイトル')
    parser.add_argument('--slug', help='スラッグ（ローマ字）')
    parser.add_argument('--excerpt', help='メタディスクリプション')
    parser.add_argument('--media', type=int, help='アイキャッチのmedia ID')
    parser.add_argument('--post-id', type=int, help='既存記事のID（更新時）')
    parser.add_argument('--publish', action='store_true', help='公開する')
    parser.add_argument('--auto', action='store_true', help='Markdownからメタデータ自動抽出')
    parser.add_argument('--dry-run', action='store_true', help='実行せずに確認のみ')

    args = parser.parse_args()

    # 環境変数読み込み
    env = load_wp_env()
    if 'WP_URL' not in env:
        print("エラー: WP環境変数が読み込めません", file=sys.stderr)
        sys.exit(1)

    wp_url = env['WP_URL']

    # 公開のみモード
    if args.publish and args.post_id and not args.file:
        payload = json.dumps({'status': 'publish'}).encode()
        result, status = wp_api_request(
            f"{wp_url}/wp-json/wp/v2/posts/{args.post_id}",
            env, data=payload, method='POST'
        )
        if status == 200:
            print(f"公開完了: {result['link']}")
        else:
            print(f"公開失敗: HTTP {status}", file=sys.stderr)
        return

    if not args.file:
        parser.print_help()
        sys.exit(1)

    # ファイル読み込み・変換
    file_path = args.file
    is_markdown = file_path.endswith('.md')

    if is_markdown:
        content = convert_md_to_wp(file_path)
        if args.auto:
            meta = extract_metadata(file_path)
            if not args.title:
                args.title = meta.get('title')
            if not args.excerpt:
                args.excerpt = meta.get('excerpt')
            if not args.slug:
                args.slug = meta.get('slug')
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

    # dry-run
    if args.dry_run:
        _, replacements = sanitize_for_waf(content)
        print("=== Dry Run ===")
        print(f"タイトル: {args.title}")
        print(f"スラッグ: {args.slug}")
        print(f"メタディスクリプション: {args.excerpt}")
        print(f"アイキャッチ: {args.media}")
        print(f"コンテンツサイズ: {len(content)} bytes")
        print(f"WAF変換箇所: {len(replacements)}")
        for orig, repl in replacements.items():
            print(f"  '{orig}' → '{repl}'")
        return

    # 新規投稿 or 更新
    if args.post_id:
        post_id = args.post_id
        print(f"既存記事を更新: post_id={post_id}", file=sys.stderr)
    else:
        # 新規作成（最小コンテンツで）
        create_payload = {'title': args.title or '', 'content': '<p>.</p>', 'status': 'draft'}
        if args.slug:
            create_payload['slug'] = args.slug
        if args.excerpt:
            create_payload['excerpt'] = args.excerpt
        if args.media:
            create_payload['featured_media'] = args.media

        result, status = wp_api_request(
            f"{wp_url}/wp-json/wp/v2/posts",
            env,
            data=json.dumps(create_payload, ensure_ascii=False).encode(),
            method='POST'
        )

        if status != 201:
            print(f"エラー: 記事作成失敗 HTTP {status}", file=sys.stderr)
            print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

        post_id = result['id']
        print(f"記事作成: post_id={post_id}, slug={result['slug']}", file=sys.stderr)

    # コンテンツ投稿（WAF対策付き）
    result = post_content_safe(post_id, content, env)

    # 公開
    if args.publish:
        pub_payload = json.dumps({'status': 'publish'}).encode()
        result, status = wp_api_request(
            f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
            env, data=pub_payload, method='POST'
        )
        if status == 200:
            print(f"\n公開完了: {result['link']}")
            # スラッグキャッシュ自動更新
            slug = result.get('slug', '')
            title = result.get('title', {}).get('rendered', '')
            if slug and title:
                list_slugs = os.path.join(SCRIPT_DIR, 'list-slugs.sh')
                subprocess.run(['bash', list_slugs, '--add', slug, title],
                               capture_output=True, text=True)
        else:
            print(f"公開失敗: HTTP {status}", file=sys.stderr)
    else:
        print(f"\n下書き保存: {wp_url}/?p={post_id}")

    # 結果サマリー
    verify, _ = wp_api_request(
        f"{wp_url}/wp-json/wp/v2/posts/{post_id}?context=edit", env
    )
    raw = verify.get('content', {}).get('raw', '')
    print(f"  スラッグ: {verify.get('slug')}", file=sys.stderr)
    print(f"  アイキャッチ: {verify.get('featured_media')}", file=sys.stderr)
    print(f"  ふきだし: {raw.count('loos/balloon')}ブロック", file=sys.stderr)
    print(f"  H2: {raw.count('<h2>')}個", file=sys.stderr)
    print(f"  内部リンク: {raw.count('dekataro.com/')}本", file=sys.stderr)


if __name__ == '__main__':
    main()
