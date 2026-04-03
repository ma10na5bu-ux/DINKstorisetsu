#!/bin/bash
# 公開済み記事のスラッグ一覧を取得するスクリプト
# 使い方:
#   bash list-slugs.sh          # キャッシュがあればキャッシュ表示、なければAPI取得
#   bash list-slugs.sh --refresh # 強制的にAPIから再取得してキャッシュ更新
#   bash list-slugs.sh --add <slug> <title>  # キャッシュに1件追加（公開時用）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CACHE_FILE="$PROJECT_DIR/02_技術部/スクリプト/.slug-cache.txt"

# --add モード: キャッシュに1件追加（wp-post.pyから呼ばれる）
if [ "$1" = "--add" ] && [ -n "$2" ] && [ -n "$3" ]; then
    SLUG="$2"
    TITLE="$3"
    # キャッシュがなければ先にrefresh
    if [ ! -f "$CACHE_FILE" ]; then
        bash "$0" --refresh > /dev/null 2>&1
    fi
    # 重複チェックして追加
    if ! grep -q "^$SLUG	" "$CACHE_FILE" 2>/dev/null; then
        echo "$SLUG	$TITLE" >> "$CACHE_FILE"
        sort -o "$CACHE_FILE" "$CACHE_FILE"
    fi
    echo "キャッシュ追加: $SLUG"
    exit 0
fi

# --refresh モード or キャッシュがない場合: APIから取得
if [ "$1" = "--refresh" ] || [ ! -f "$CACHE_FILE" ]; then
    eval "$(bash "$SCRIPT_DIR/wp-env.sh")"

    curl -s -u "$WP_USERNAME:$WP_APP_PASSWORD" \
      "https://dinks-torisetsu.fun/wp-json/wp/v2/posts?status=publish&per_page=100&_fields=slug,title" \
      | python3 -c "
import json, sys
posts = json.load(sys.stdin)
for p in sorted(posts, key=lambda x: x['slug']):
    slug = p['slug']
    title = p['title']['rendered']
    print(f'{slug}\t{title}')
" > "$CACHE_FILE"

    echo "=== スラッグキャッシュ更新完了（$(wc -l < "$CACHE_FILE" | tr -d ' ')件） ==="
    echo ""
fi

# 表示
echo "=== 公開済み記事スラッグ一覧 ==="
echo ""
while IFS=$'\t' read -r slug title; do
    echo "  $slug"
    echo "    → $title"
    echo "    → https://www.dinks-torisetsu.fun/$slug/"
    echo ""
done < "$CACHE_FILE"
