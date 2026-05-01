#!/usr/bin/env python3
"""
カテゴリー再設計スクリプト
- 新親/子カテゴリー作成
- 既存カテゴリーの親付け替え
- 全記事の新カテゴリーへ移行
- タグ作成・付与
- 旧カテゴリー削除
"""

import os, sys, json, urllib.request, urllib.error, base64, time

# .env 読み込み
env = {}
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

WP_URL = env['WP_URL'].rstrip('/')
auth = base64.b64encode(f"{env['WP_USERNAME']}:{env['WP_APP_PASSWORD']}".encode()).decode()
HEADERS = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}


def wp_get(path, params=''):
    url = f"{WP_URL}/wp-json/wp/v2/{path}{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def wp_req(path, data, method='POST'):
    url = f"{WP_URL}/wp-json/wp/v2/{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print(f"  ERROR {e.code}: {msg[:200]}")
        return None

def get_all_posts():
    """ページネーション対応で全記事取得"""
    posts = []
    page = 1
    while True:
        batch = wp_get('posts', f'?per_page=100&page={page}&status=publish,draft')
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


# ============================================================
# Phase 1: 新しい親カテゴリーを作成
# ============================================================
print("=== Phase 1: 新しい親カテゴリーを作成 ===")
new_parents = [
    {'name': '食事の時短',   'slug': 'food-time-saving'},
    {'name': '家事の効率化', 'slug': 'home-efficiency'},
    {'name': 'DINKsの暮らし','slug': 'dinks-life'},
    {'name': '大人の趣味',   'slug': 'adult-hobbies'},
]
parent_ids = {}  # slug → ID
for p in new_parents:
    r = wp_req('categories', {'name': p['name'], 'slug': p['slug']})
    if r:
        parent_ids[p['slug']] = r['id']
        print(f"  作成: {p['name']} ID={r['id']}")
    else:
        # 既存の場合はslugsで取得
        existing = wp_get('categories', f"?slug={p['slug']}")
        if existing:
            parent_ids[p['slug']] = existing[0]['id']
            print(f"  既存: {p['name']} ID={existing[0]['id']}")

print(f"親カテゴリーIDs: {parent_ids}")

# ============================================================
# Phase 2: 新しい子カテゴリーを作成
# ============================================================
print("\n=== Phase 2: 新しい子カテゴリーを作成 ===")
new_children = [
    {'name': '宅配弁当・宅食',        'slug': 'food-delivery',  'parent': 'food-time-saving'},
    {'name': '朝食の時短・完全栄養食', 'slug': 'morning-routine','parent': 'food-time-saving'},
    {'name': 'ラクする自炊・レシピ',   'slug': 'cooking-hack',   'parent': 'food-time-saving'},
    {'name': '家事代行サービス',        'slug': 'housekeeping',   'parent': 'home-efficiency'},
    {'name': '時短家電・アイテム',      'slug': 'appliances',     'parent': 'home-efficiency'},
    {'name': 'お金とキャリア',          'slug': 'money-career',   'parent': 'dinks-life'},
    {'name': '夫婦のルール',            'slug': 'couple-rules',   'parent': 'dinks-life'},
]
child_ids = {}  # slug → ID
for c in new_children:
    data = {'name': c['name'], 'slug': c['slug'], 'parent': parent_ids[c['parent']]}
    r = wp_req('categories', data)
    if r:
        child_ids[c['slug']] = r['id']
        print(f"  作成: {c['name']} ID={r['id']}")
    else:
        existing = wp_get('categories', f"?slug={c['slug']}")
        if existing:
            child_ids[c['slug']] = existing[0]['id']
            print(f"  既存: {c['name']} ID={existing[0]['id']}")

print(f"子カテゴリーIDs: {child_ids}")

# ============================================================
# Phase 3: 既存カテゴリーの親を付け替え
# ============================================================
print("\n=== Phase 3: 既存カテゴリーの親付け替え ===")

# 柴犬との暮らし (ID:20, slug:shiba-life) → DINKsの暮らし の子
r = wp_req('categories/20', {'parent': parent_ids['dinks-life']})
if r: print(f"  柴犬との暮らし (ID:20) → DINKsの暮らし の子 OK")

# キャンプ (ID:12) → 大人の趣味 の子
r = wp_req('categories/12', {'parent': parent_ids['adult-hobbies']})
if r: print(f"  キャンプ (ID:12) → 大人の趣味 の子 OK")

# ゴルフ (ID:11) → 大人の趣味 の子
r = wp_req('categories/11', {'parent': parent_ids['adult-hobbies']})
if r: print(f"  ゴルフ (ID:11) → 大人の趣味 の子 OK")

# 筋トレ (ID:13) → 大人の趣味 の子（名前も「筋トレ・健康」に変更）
r = wp_req('categories/13', {'parent': parent_ids['adult-hobbies'], 'name': '筋トレ・健康'})
if r: print(f"  筋トレ→筋トレ・健康 (ID:13) → 大人の趣味 の子 OK")

# child_ids に既存カテゴリーのIDも追加（記事マッピング用）
child_ids['shiba-life'] = 20
child_ids['camp'] = 12
child_ids['golf'] = 11
child_ids['training'] = 13

# ============================================================
# Phase 4: 全記事を新カテゴリーに移行
# ============================================================
print("\n=== Phase 4: 全記事を新カテゴリーに移行 ===")

# 記事ID → 新カテゴリーslug のマッピング
POST_CATEGORY_MAP = {
    # 食事の時短 > 宅配弁当・宅食
    1302: 'food-delivery',   # nosh-fuufu-review

    # 食事の時短 > 朝食の時短・完全栄養食
    1183: 'morning-routine', # basefood-morning-routine

    # 食事の時短 > ラクする自炊・レシピ
    188:  'cooking-hack',    # dinks-shokuji-kaizen-ganbaranai

    # 家事の効率化 > 時短家電・アイテム
    194:  'appliances',      # dinks-kaji-hosanai (ドラム式・食洗機・ロボット掃除機)

    # 家事の効率化 > 家事代行サービス（現時点は記事なし、将来用）

    # DINKsの暮らし > お金とキャリア
    170:  'money-career',    # dinks-fire-file-hatarakikata
    165:  'money-career',    # dinks-buttoku-zero-taiken
    167:  'money-career',    # dinks-okane-stress-zero
    190:  'money-career',    # fuufu-kaikei-kanzen-seppu
    939:  'money-career',    # tomobataraki-fuufu-kaikei-kanri
    900:  'money-career',    # pair-loan-wariai-mochibu
    858:  'money-career',    # 30dai-yaritai-shigoto-nai
    734:  'money-career',    # kaigo-shigoto-imi-kawatta

    # DINKsの暮らし > 夫婦のルール
    1370: 'couple-rules',    # dinks-koukai-4nenme-honme
    1362: 'couple-rules',    # dinks-koukai-4nenme-honme-prev
    212:  'couple-rules',    # 4ldk-shumi-beya
    209:  'couple-rules',    # fuufu-drama-kaiwa
    172:  'couple-rules',    # dinks-suimin-mezamashi-nashi
    186:  'couple-rules',    # dinks-renai-kanjou-chousa
    204:  'couple-rules',    # dinks-kyujitsu-nanmonai
    175:  'couple-rules',    # dinks-jiyuu-jikan-real
    207:  'couple-rules',    # fuufu-kyorikan
    201:  'couple-rules',    # fuufu-telework-shigotobeya
    197:  'couple-rules',    # dinks-kuruma-shumi-bakuhatsu
    183:  'couple-rules',    # dinks-ryokou-shishutsu-2bai
    950:  'couple-rules',    # kyodoteki-fuufu-kajibuntan (家事分担ルール)
    856:  'couple-rules',    # 30dai-kekkon
    712:  'couple-rules',    # dinks-koukai-4nenme-honme-old
    455:  'couple-rules',    # dinks-wariai-nihon
    718:  'couple-rules',    # dinks-rikon-ritsu-data
    873:  'couple-rules',    # dinks-toha-merit-demerit
    881:  'couple-rules',    # dinks-koukai-shinai-sonae
    895:  'couple-rules',    # dinks-kibou-konkatsu

    # DINKsの暮らし > 柴犬との暮らし（主にshiba→shiba-lifeへ移行）
    163:  'shiba-life',      # dinks-juutaku-kounyu-inu (犬が飼いたいで家を買った)
    # 他の柴犬記事は下のループで一括処理

    # 大人の趣味 > キャンプ
    192:  'camp',            # fuufu-camp-youtube

    # 大人の趣味 > ゴルフ
    743:  'golf',            # fuufu-golf-kyotsu-shumi
    199:  'golf',            # fuufu-golf-hamatta

    # 大人の趣味 > 筋トレ・健康
    790:  'training',        # 30dai-kintore-keizoku-zasetsu

    # 大人の趣味 （親カテゴリー直接）
    778:  None,  # 30dai-shumi-osusume-ranking → adult-hobbies 親に配置
}

# 全記事取得
print("  全記事取得中...")
all_posts = get_all_posts()
print(f"  総記事数: {len(all_posts)}")

# cat 2 (旧shiba) の記事IDを収集
OLD_SHIBA_CAT = 2
shiba_post_ids = [p['id'] for p in all_posts if OLD_SHIBA_CAT in p.get('categories', [])]
print(f"  柴犬カテゴリー記事数: {len(shiba_post_ids)}")

success_count = 0
for post in all_posts:
    post_id = post['id']
    current_cats = post.get('categories', [])

    # POST_CATEGORY_MAP にある記事
    if post_id in POST_CATEGORY_MAP:
        new_slug = POST_CATEGORY_MAP[post_id]
        if new_slug is None:
            # 大人の趣味 親カテゴリー直接
            new_cat_id = parent_ids['adult-hobbies']
        else:
            new_cat_id = child_ids[new_slug]
        r = wp_req(f'posts/{post_id}', {'categories': [new_cat_id]})
        if r:
            print(f"  [{post_id}] {post['slug'][:40]} → {new_slug or 'adult-hobbies'}")
            success_count += 1

    # 旧 shiba (cat 2) 記事で POST_CATEGORY_MAP にないもの → shiba-life (ID:20) へ
    elif OLD_SHIBA_CAT in current_cats and post_id not in POST_CATEGORY_MAP:
        r = wp_req(f'posts/{post_id}', {'categories': [child_ids['shiba-life']]})
        if r:
            success_count += 1
            # 冗長なので個別ログ省略

print(f"  移行完了: {success_count}件")

# ============================================================
# Phase 5: タグ作成・付与
# ============================================================
print("\n=== Phase 5: タグ作成・付与 ===")

tags_to_create = [
    'nosh', 'ナッシュ',
    'BASE FOOD', 'ベースフード',
    'CaSy', 'カジー',
    '時短家電', 'ホットクック',
]
tag_ids = {}
for tag_name in tags_to_create:
    r = wp_req('tags', {'name': tag_name})
    if r:
        tag_ids[tag_name] = r['id']
        print(f"  タグ作成: {tag_name} ID={r['id']}")
    else:
        existing = wp_get('tags', f'?search={urllib.parse.quote(tag_name)}') if False else []
        # slugで検索
        slug = tag_name.lower().replace(' ', '-')
        existing = wp_get('tags', f'?slug={slug}')
        if existing:
            tag_ids[tag_name] = existing[0]['id']
            print(f"  タグ既存: {tag_name} ID={existing[0]['id']}")

# タグ付与マッピング
POST_TAG_MAP = {
    1302: ['nosh', 'ナッシュ'],
    1183: ['BASE FOOD', 'ベースフード'],
}
for post_id, tag_names in POST_TAG_MAP.items():
    ids = [tag_ids[t] for t in tag_names if t in tag_ids]
    if ids:
        # 既存タグと統合
        post_data = next((p for p in all_posts if p['id'] == post_id), None)
        existing_tags = post_data.get('tags', []) if post_data else []
        merged = list(set(existing_tags + ids))
        r = wp_req(f'posts/{post_id}', {'tags': merged})
        if r:
            print(f"  [{post_id}] タグ付与: {tag_names}")

# ============================================================
# Phase 6: 旧カテゴリー削除（記事0件になったもののみ）
# ============================================================
print("\n=== Phase 6: 旧カテゴリー削除 ===")

# 削除対象（旧構造の親・子カテゴリー）
OLD_CATS_TO_DELETE = [
    (17, 'money-home',      'お金と住まい'),
    (5,  'money',           'お金'),
    (19, 'work-future',     '働き方とこれから'),
    (1,  'work',            '仕事'),
    (16, 'dinks-couple',    '夫婦とDINKs'),
    (10, 'couple',          '夫婦'),
    (18, 'hobbies-weekend', '趣味と休日'),
    (15, 'hobby',           '趣味'),
    (2,  'shiba',           '柴犬'),
]

for cat_id, slug, name in OLD_CATS_TO_DELETE:
    # 削除前に記事数確認
    cat_info = wp_get('categories', f'/{cat_id}')
    count = cat_info.get('count', 0) if cat_info else 0
    if count > 0:
        print(f"  スキップ: {name} (ID:{cat_id}) - まだ{count}件記事あり")
        continue
    # force_delete=true で削除
    url = f"{WP_URL}/wp-json/wp/v2/categories/{cat_id}?force=true"
    req = urllib.request.Request(url, headers=HEADERS, method='DELETE')
    try:
        with urllib.request.urlopen(req) as r:
            print(f"  削除: {name} (ID:{cat_id}) OK")
    except urllib.error.HTTPError as e:
        print(f"  削除失敗: {name} (ID:{cat_id}) → {e.code}: {e.read().decode()[:100]}")

print("\n=== 完了 ===")
print("※ グローバルナビゲーションは WordPress 管理画面 > 外観 > メニュー で手動更新が必要")
