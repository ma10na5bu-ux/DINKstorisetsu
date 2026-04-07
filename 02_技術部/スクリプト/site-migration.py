#!/usr/bin/env python3
"""
サイト統合移行スクリプト — デカ太郎ラボ

shiba-with.com + dinks-torisetsu.fun → dekataro.com

使い方:
  # Phase 1: カテゴリ作成
  python3 site-migration.py --phase categories

  # Phase 2: 旧サイトから全記事エクスポート（ローカルJSON保存）
  python3 site-migration.py --phase export

  # Phase 3: dekataro.comに記事インポート
  python3 site-migration.py --phase import

  # Phase 4: 内部リンク書き換え + 旧キャラ名置換
  python3 site-migration.py --phase fix-content

  # Phase 5: 301リダイレクト用 .htaccess 生成
  python3 site-migration.py --phase redirects

  # 全フェーズ一括実行
  python3 site-migration.py --phase all

  # ドライラン（実際には書き込まない）
  python3 site-migration.py --phase all --dry-run
"""

import sys
import os
import json
import re
import urllib.request
import urllib.error
import base64
import time
import argparse
from datetime import datetime

# ============================================================
# 設定
# ============================================================

# サイト認証情報
SITES = {
    'shiba': {
        'url': 'https://shiba-with.com',
        'username': 'shibaadmin',
        'password': 'sY0R lO1v XIzD bYrX KGcG r75O',
    },
    'dinks': {
        'url': 'https://dinks-torisetsu.fun',
        'username': 'dinksadmin',
        'password': '25BN Vx1K BjCm iFsD RIcl 0lhL',
    },
    'new': {
        'url': 'https://dekataro.com',
        'username': 'dekataro',
        'password': 'YUgf TK04 RqBo mO3j d7Xi luiB',
    },
}

# 新サイトのカテゴリ
NEW_CATEGORIES = [
    {'name': '柴犬', 'slug': 'shiba'},
    {'name': 'おでかけ', 'slug': 'outing'},
    {'name': '暮らし', 'slug': 'life'},
    {'name': 'お金', 'slug': 'money'},
    {'name': 'グッズ・レビュー', 'slug': 'goods-review'},
    {'name': 'コラム', 'slug': 'column'},
]

# カテゴリマッピング（旧カテゴリ名 → 新カテゴリslug）
CATEGORY_MAP_SHIBA = {
    '柴犬の基本': 'shiba',
    'しつけ・育て方': 'shiba',
    'お散歩・お出かけ': 'outing',
    'グッズ・ごはん': 'goods-review',
    '季節・イベント': 'column',
    '柴犬あるある': 'shiba',
    '柴犬ライフ': 'shiba',
}

CATEGORY_MAP_DINKS = {
    'お金のリアル': 'money',
    '暮らしと時間': 'life',
    '夫婦のこと': 'life',
    '趣味・おでかけ': 'outing',
    'ペットとDINKs': 'shiba',
}

# 旧キャラ名 → 新キャラ名
CHARACTER_REPLACEMENTS = {
    'まーくん': 'デカ太郎',
    'はるさん': 'ヨメ氏',
    'えいちゃん': 'ハチ',
}

# WAF対策キーワード
WAF_BLOCKED_KEYWORDS = ['and', 'or', 'select', 'union', 'drop', 'insert', 'update', 'delete']

# エクスポート先ディレクトリ
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'migration_data')

# ============================================================
# REST API ヘルパー
# ============================================================

def api_request(site_key, endpoint, data=None, method='GET', waf_safe=False):
    """WordPress REST API リクエスト"""
    site = SITES[site_key]
    url = f"{site['url']}/wp-json/wp/v2/{endpoint}"
    credentials = base64.b64encode(
        f"{site['username']}:{site['password']}".encode()
    ).decode()

    if data is not None:
        if waf_safe:
            # SiteGuard WAF回避: < を \u003c にエスケープ
            body = json.dumps(data, ensure_ascii=False)
            body = body.replace('<', '\\u003c')
            body = body.encode('utf-8')
        else:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    else:
        body = None

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Authorization', f'Basic {credentials}')
    if body:
        req.add_header('Content-Type', 'application/json; charset=utf-8')

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            total = resp.headers.get('X-WP-Total')
            total_pages = resp.headers.get('X-WP-TotalPages')
            return result, resp.status, {'total': total, 'total_pages': total_pages}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        return {'error': body_text, 'code': e.code}, e.code, {}


def get_all_posts(site_key):
    """全記事を取得（ページネーション対応）"""
    all_posts = []
    page = 1
    while True:
        result, status, headers = api_request(
            site_key, f'posts?per_page=100&page={page}&context=edit&status=publish,draft'
        )
        if status != 200 or not result:
            break
        all_posts.extend(result)
        total_pages = int(headers.get('total_pages', 1))
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)
    return all_posts


def get_all_categories(site_key):
    """全カテゴリを取得"""
    result, status, _ = api_request(site_key, 'categories?per_page=100')
    if status == 200:
        return result
    return []


def get_media(site_key, media_id):
    """メディア情報を取得"""
    if not media_id:
        return None
    result, status, _ = api_request(site_key, f'media/{media_id}')
    if status == 200:
        return result
    return None


def download_media(url, save_path):
    """メディアファイルをダウンロード（日本語URL対応）"""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    # URLの日本語部分をエンコード
    from urllib.parse import urlparse, quote
    parsed = urlparse(url)
    encoded_path = quote(parsed.path, safe='/')
    encoded_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
    req = urllib.request.Request(encoded_url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req) as resp:
        with open(save_path, 'wb') as f:
            f.write(resp.read())
    return save_path


def upload_media(site_key, file_path, filename=None, alt_text=''):
    """メディアファイルをアップロード"""
    site = SITES[site_key]
    url = f"{site['url']}/wp-json/wp/v2/media"
    credentials = base64.b64encode(
        f"{site['username']}:{site['password']}".encode()
    ).decode()

    if filename is None:
        filename = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        file_data = f.read()

    # Content-Type推定
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif',
        '.webp': 'image/webp', '.svg': 'image/svg+xml',
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    req = urllib.request.Request(url, data=file_data, method='POST')
    req.add_header('Authorization', f'Basic {credentials}')
    req.add_header('Content-Type', content_type)
    # 日本語ファイル名対応: RFC 5987 形式
    from urllib.parse import quote as url_quote
    ascii_safe = filename.encode('ascii', errors='ignore').decode()
    if ascii_safe == filename:
        req.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    else:
        encoded_fn = url_quote(filename, safe='')
        req.add_header('Content-Disposition', f"attachment; filename*=UTF-8''{encoded_fn}")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            # alt属性設定
            if alt_text:
                api_request(site_key, f"media/{result['id']}",
                           data={'alt_text': alt_text}, method='POST')
            return result
    except urllib.error.HTTPError as e:
        print(f"  メディアアップロード失敗: {filename} (HTTP {e.code})", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  メディアアップロード失敗: {filename} ({e})", file=sys.stderr)
        return None


# ============================================================
# Phase 1: カテゴリ作成
# ============================================================

def phase_categories(dry_run=False):
    """dekataro.comに6カテゴリを作成"""
    print("\n=== Phase 1: カテゴリ作成 ===")

    existing = get_all_categories('new')
    existing_slugs = {c['slug'] for c in existing}

    for cat in NEW_CATEGORIES:
        if cat['slug'] in existing_slugs:
            print(f"  スキップ（既存）: {cat['name']} ({cat['slug']})")
            continue

        if dry_run:
            print(f"  [DRY] 作成予定: {cat['name']} ({cat['slug']})")
            continue

        result, status, _ = api_request('new', 'categories', data={
            'name': cat['name'],
            'slug': cat['slug'],
        }, method='POST')

        if status == 201:
            print(f"  作成: {cat['name']} (ID: {result['id']})")
        else:
            print(f"  エラー: {cat['name']} — {result}", file=sys.stderr)

    # 「未分類」カテゴリの確認
    for c in existing:
        if c['slug'] == 'uncategorized':
            print(f"  ※「未分類」カテゴリ (ID: {c['id']}) は後で削除してください")

    print("  完了")


# ============================================================
# Phase 2: エクスポート
# ============================================================

def phase_export(dry_run=False):
    """旧2サイトから全記事をエクスポート"""
    print("\n=== Phase 2: 記事エクスポート ===")
    os.makedirs(EXPORT_DIR, exist_ok=True)

    for site_key, site_name in [('shiba', '柴犬ブログ'), ('dinks', 'DINKsブログ')]:
        print(f"\n--- {site_name} ({SITES[site_key]['url']}) ---")

        # 記事取得
        posts = get_all_posts(site_key)
        print(f"  記事数: {len(posts)}")

        # カテゴリ取得（IDと名前のマッピング用）
        categories = get_all_categories(site_key)
        cat_id_to_name = {c['id']: c['name'] for c in categories}

        # 各記事の処理
        export_data = []
        for post in posts:
            cat_names = [cat_id_to_name.get(cid, '未分類') for cid in post.get('categories', [])]
            entry = {
                'id': post['id'],
                'title': post['title']['raw'] if isinstance(post['title'], dict) else post['title'],
                'slug': post['slug'],
                'content': post['content']['raw'] if isinstance(post['content'], dict) else post['content'],
                'excerpt': post['excerpt']['raw'] if isinstance(post['excerpt'], dict) else post.get('excerpt', ''),
                'date': post['date'],
                'status': post['status'],
                'categories': cat_names,
                'featured_media': post.get('featured_media', 0),
                'source_site': site_key,
                'source_url': f"{SITES[site_key]['url']}/{post['slug']}/",
            }

            # アイキャッチ画像情報
            if entry['featured_media']:
                media = get_media(site_key, entry['featured_media'])
                if media:
                    entry['featured_media_url'] = media.get('source_url', '')
                    entry['featured_media_alt'] = media.get('alt_text', '')
                    entry['featured_media_filename'] = os.path.basename(
                        media.get('source_url', '').split('?')[0]
                    )

            export_data.append(entry)
            print(f"  [{post['status']}] {entry['title']} ({entry['slug']})")
            print(f"         カテゴリ: {', '.join(cat_names)}")
            time.sleep(0.2)

        # JSON保存
        export_path = os.path.join(EXPORT_DIR, f'{site_key}_posts.json')
        if not dry_run:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(f"\n  保存: {export_path}")
        else:
            print(f"\n  [DRY] 保存先: {export_path}")

        # アイキャッチ画像ダウンロード
        media_dir = os.path.join(EXPORT_DIR, f'{site_key}_media')
        for entry in export_data:
            if entry.get('featured_media_url'):
                fname = entry['featured_media_filename']
                save_path = os.path.join(media_dir, fname)
                if dry_run:
                    print(f"  [DRY] DL予定: {fname}")
                    continue
                if os.path.exists(save_path):
                    print(f"  スキップ（DL済）: {fname}")
                    continue
                try:
                    download_media(entry['featured_media_url'], save_path)
                    print(f"  DL: {fname}")
                    time.sleep(0.3)
                except Exception as e:
                    print(f"  DL失敗: {fname} — {e}", file=sys.stderr)

    print("\n  エクスポート完了")


# ============================================================
# Phase 3: インポート
# ============================================================

def phase_import(dry_run=False):
    """dekataro.comに記事をインポート"""
    print("\n=== Phase 3: 記事インポート ===")

    # 新サイトのカテゴリID取得
    new_cats = get_all_categories('new')
    cat_slug_to_id = {c['slug']: c['id'] for c in new_cats}

    if not cat_slug_to_id:
        print("  エラー: 新サイトにカテゴリがありません。Phase 1を先に実行してください", file=sys.stderr)
        return

    cat_list = ', '.join(f"{c['name']}(ID:{c['id']})" for c in new_cats)
    print(f"  新サイトカテゴリ: {cat_list}")

    # 既存記事のスラッグを取得（重複防止）
    existing_posts = get_all_posts('new')
    existing_slugs = {p['slug'] for p in existing_posts}

    # 除外スラッグ
    EXCLUDE_SLUGS = {'test-balloon-delete-me', 'hello-world', 'shiba-dog-food-guide'}

    # マッピング結果保存用（リダイレクト生成に使う）
    migration_map = []

    for site_key, cat_map in [('shiba', CATEGORY_MAP_SHIBA), ('dinks', CATEGORY_MAP_DINKS)]:
        export_path = os.path.join(EXPORT_DIR, f'{site_key}_posts.json')
        if not os.path.exists(export_path):
            print(f"  スキップ: {export_path} が見つかりません", file=sys.stderr)
            continue

        with open(export_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        media_dir = os.path.join(EXPORT_DIR, f'{site_key}_media')
        print(f"\n--- {site_key} ({len(posts)}記事) ---")

        for post in posts:
            slug = post['slug']

            # 除外チェック
            if slug in EXCLUDE_SLUGS:
                print(f"  除外: {post['title']} ({slug})")
                continue

            # 重複チェック
            if slug in existing_slugs:
                print(f"  スキップ（既存）: {post['title']} ({slug})")
                migration_map.append({
                    'source_url': post['source_url'],
                    'new_url': f"https://dekataro.com/{slug}/",
                    'status': 'skipped_duplicate',
                })
                continue

            # カテゴリマッピング
            new_cat_slugs = set()
            for old_cat_name in post['categories']:
                mapped = cat_map.get(old_cat_name)
                if mapped:
                    new_cat_slugs.add(mapped)
            if not new_cat_slugs:
                new_cat_slugs.add('column')  # フォールバック

            new_cat_ids = [cat_slug_to_id[s] for s in new_cat_slugs if s in cat_slug_to_id]

            if dry_run:
                print(f"  [DRY] {post['title']} ({slug})")
                print(f"         → カテゴリ: {', '.join(new_cat_slugs)}")
                migration_map.append({
                    'source_url': post['source_url'],
                    'new_url': f"https://dekataro.com/{slug}/",
                    'status': 'dry_run',
                })
                continue

            # アイキャッチ画像アップロード
            new_media_id = 0
            if post.get('featured_media_filename'):
                media_path = os.path.join(media_dir, post['featured_media_filename'])
                if os.path.exists(media_path):
                    media_result = upload_media(
                        'new', media_path,
                        filename=post['featured_media_filename'],
                        alt_text=post.get('featured_media_alt', ''),
                    )
                    if media_result:
                        new_media_id = media_result['id']
                        print(f"  画像UP: {post['featured_media_filename']} (ID: {new_media_id})")
                    time.sleep(0.5)

            # 記事作成（まず最小限で作成）
            create_data = {
                'title': post['title'],
                'slug': slug,
                'excerpt': post.get('excerpt', ''),
                'date': post['date'],
                'status': post.get('status', 'draft'),
                'categories': new_cat_ids,
                'content': '<p>.</p>',  # 仮コンテンツ
            }
            if new_media_id:
                create_data['featured_media'] = new_media_id

            result, status, _ = api_request('new', 'posts', data=create_data, method='POST')

            if status != 201:
                print(f"  エラー: {post['title']} — HTTP {status}", file=sys.stderr)
                migration_map.append({
                    'source_url': post['source_url'],
                    'new_url': '',
                    'status': f'error_{status}',
                })
                continue

            new_post_id = result['id']

            # コンテンツ投稿（WAF対策付き）
            content = post['content']
            content_data = {'content': content}
            result2, status2, _ = api_request(
                'new', f'posts/{new_post_id}',
                data=content_data, method='POST', waf_safe=True,
            )

            if status2 == 200:
                print(f"  投稿: {post['title']} (ID: {new_post_id}, slug: {slug})")
            else:
                print(f"  コンテンツ投稿エラー: {post['title']} — HTTP {status2}", file=sys.stderr)
                # 段階的投稿にフォールバック
                fallback_result = post_content_staged(new_post_id, content)
                if fallback_result:
                    print(f"  段階的投稿で復旧: {post['title']}")

            existing_slugs.add(slug)
            migration_map.append({
                'source_url': post['source_url'],
                'new_url': f"https://dekataro.com/{slug}/",
                'new_post_id': new_post_id,
                'status': 'imported',
            })
            time.sleep(0.5)

    # マッピング保存
    map_path = os.path.join(EXPORT_DIR, 'migration_map.json')
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(migration_map, f, ensure_ascii=False, indent=2)
    print(f"\n  マッピング保存: {map_path}")
    print("  インポート完了")


def post_content_staged(post_id, content):
    """WAFブロック時の段階的投稿フォールバック"""
    blocks = content.split('\n\n')
    accumulated = ""

    for i, block in enumerate(blocks):
        candidate = accumulated + ("\n\n" if accumulated else "") + block
        result, status, _ = api_request(
            'new', f'posts/{post_id}',
            data={'content': candidate}, method='POST', waf_safe=True,
        )
        if status == 200:
            accumulated = candidate
        else:
            print(f"    Block {i} スキップ: {block[:40]}...", file=sys.stderr)

    return accumulated != ""


# ============================================================
# Phase 4: コンテンツ修正（内部リンク + キャラ名）
# ============================================================

def phase_fix_content(dry_run=False):
    """dekataro.comの全記事の内部リンク書き換え + キャラ名置換"""
    print("\n=== Phase 4: コンテンツ修正 ===")

    posts = get_all_posts('new')
    print(f"  対象記事数: {len(posts)}")

    # URL置換パターン
    url_patterns = [
        (r'https?://shiba-with\.com', 'https://dekataro.com'),
        (r'https?://dinks-torisetsu\.fun', 'https://dekataro.com'),
        (r'https?://www\.dinks-torisetsu\.fun', 'https://dekataro.com'),
    ]

    fixed_count = 0
    for post in posts:
        content = post['content']['raw'] if isinstance(post['content'], dict) else post['content']
        original_content = content
        changes = []

        # URL置換
        for pattern, replacement in url_patterns:
            matches = re.findall(pattern, content)
            if matches:
                changes.append(f"URL置換: {len(matches)}箇所 ({pattern})")
                content = re.sub(pattern, replacement, content)

        # キャラ名置換
        for old_name, new_name in CHARACTER_REPLACEMENTS.items():
            count = content.count(old_name)
            if count > 0:
                changes.append(f"キャラ名: {old_name}→{new_name} ({count}箇所)")
                content = content.replace(old_name, new_name)

        if content == original_content:
            continue

        title = post['title']['raw'] if isinstance(post['title'], dict) else post['title']
        print(f"\n  {title} (ID: {post['id']})")
        for change in changes:
            print(f"    {change}")

        if dry_run:
            print(f"    [DRY] 更新スキップ")
            continue

        result, status, _ = api_request(
            'new', f"posts/{post['id']}",
            data={'content': content}, method='POST', waf_safe=True,
        )

        if status == 200:
            print(f"    更新完了")
            fixed_count += 1
        else:
            print(f"    更新エラー: HTTP {status}", file=sys.stderr)
        time.sleep(0.3)

    print(f"\n  修正完了: {fixed_count}記事")


# ============================================================
# Phase 5: 301リダイレクト .htaccess 生成
# ============================================================

def phase_redirects(dry_run=False):
    """旧サイト用の .htaccess リダイレクトルールを生成"""
    print("\n=== Phase 5: リダイレクト生成 ===")

    # マッピングデータ読み込み
    map_path = os.path.join(EXPORT_DIR, 'migration_map.json')
    if os.path.exists(map_path):
        with open(map_path, 'r', encoding='utf-8') as f:
            migration_map = json.load(f)
    else:
        # マッピングがない場合、新サイトの記事から生成
        print("  migration_map.json がないため、新サイトの記事から生成します")
        posts = get_all_posts('new')
        migration_map = []
        for post in posts:
            slug = post['slug']
            migration_map.extend([
                {
                    'source_url': f"https://shiba-with.com/{slug}/",
                    'new_url': f"https://dekataro.com/{slug}/",
                },
                {
                    'source_url': f"https://dinks-torisetsu.fun/{slug}/",
                    'new_url': f"https://dekataro.com/{slug}/",
                },
            ])

    # shiba-with.com 用
    shiba_rules = []
    dinks_rules = []

    for entry in migration_map:
        source = entry.get('source_url', '')
        target = entry.get('new_url', '')
        if not target:
            continue

        slug = target.rstrip('/').split('/')[-1]

        if 'shiba-with.com' in source:
            shiba_rules.append(f'RedirectPermanent /{slug}/ https://dekataro.com/{slug}/')
        elif 'dinks-torisetsu' in source:
            dinks_rules.append(f'RedirectPermanent /{slug}/ https://dekataro.com/{slug}/')

    # shiba-with.com 用 .htaccess
    shiba_htaccess = f"""# === 301リダイレクト: shiba-with.com → dekataro.com ===
# 生成日: {datetime.now().strftime('%Y-%m-%d %H:%M')}
# 設置場所: shiba-with.com のドキュメントルート

# トップページ
RedirectPermanent / https://dekataro.com/

# 個別記事
{chr(10).join(shiba_rules)}
"""

    # dinks-torisetsu.fun 用 .htaccess
    dinks_htaccess = f"""# === 301リダイレクト: dinks-torisetsu.fun → dekataro.com ===
# 生成日: {datetime.now().strftime('%Y-%m-%d %H:%M')}
# 設置場所: dinks-torisetsu.fun のドキュメントルート

# トップページ
RedirectPermanent / https://dekataro.com/

# 個別記事
{chr(10).join(dinks_rules)}
"""

    # 保存
    for name, content in [('shiba-with_htaccess.txt', shiba_htaccess),
                          ('dinks-torisetsu_htaccess.txt', dinks_htaccess)]:
        path = os.path.join(EXPORT_DIR, name)
        if dry_run:
            print(f"\n  [DRY] {name}:")
            print(content)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  保存: {path}")

    print(f"\n  shiba-with.com: {len(shiba_rules)}ルール")
    print(f"  dinks-torisetsu.fun: {len(dinks_rules)}ルール")
    print("  リダイレクト生成完了")


# ============================================================
# メイン
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='サイト統合移行スクリプト')
    parser.add_argument('--phase', required=True,
                       choices=['categories', 'export', 'import', 'fix-content', 'redirects', 'all'],
                       help='実行するフェーズ')
    parser.add_argument('--dry-run', action='store_true', help='実際には書き込まない')
    args = parser.parse_args()

    print(f"{'='*50}")
    print(f"  デカ太郎ラボ サイト統合移行")
    print(f"  フェーズ: {args.phase}")
    print(f"  ドライラン: {'YES' if args.dry_run else 'NO'}")
    print(f"{'='*50}")

    phases = {
        'categories': [phase_categories],
        'export': [phase_export],
        'import': [phase_import],
        'fix-content': [phase_fix_content],
        'redirects': [phase_redirects],
        'all': [phase_categories, phase_export, phase_import, phase_fix_content, phase_redirects],
    }

    for fn in phases[args.phase]:
        fn(dry_run=args.dry_run)

    print(f"\n{'='*50}")
    print("  全フェーズ完了")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
