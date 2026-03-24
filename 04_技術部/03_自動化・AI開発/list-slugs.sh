#!/bin/bash
# 公開済み記事のスラッグ一覧を取得するスクリプト
# 使い方: bash list-slugs.sh
# 内部リンクを張る前にスラッグを確認する用途

# .envからWP認証情報を読む（sourceは使わない）
WP_USERNAME=dinksadmin
WP_APP_PASSWORD="25BN Vx1K BjCm iFsD RIcl 0lhL"

echo "=== 公開済み記事スラッグ一覧 ==="
echo ""

curl -s -u "$WP_USERNAME:$WP_APP_PASSWORD" \
  "https://dinks-torisetsu.fun/wp-json/wp/v2/posts?status=publish&per_page=100&_fields=slug,title" \
  | python3 -c "
import json, sys
posts = json.load(sys.stdin)
for p in sorted(posts, key=lambda x: x['slug']):
    slug = p['slug']
    title = p['title']['rendered']
    print(f'  {slug}')
    print(f'    → {title}')
    print(f'    → https://www.dinks-torisetsu.fun/{slug}/')
    print()
"
