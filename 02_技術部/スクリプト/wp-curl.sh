#!/bin/bash
# WordPress REST API用のcurlラッパー
# 使い方:
#   bash 02_技術部/スクリプト/wp-curl.sh upload <画像ファイルパス> [alt_text]
#   bash 02_技術部/スクリプト/wp-curl.sh get <endpoint>
#   bash 02_技術部/スクリプト/wp-curl.sh post <endpoint> <json_data>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# wp-env.shから認証情報を読み込む
eval "$(bash "$SCRIPT_DIR/wp-env.sh")"

if [ -z "${WP_USERNAME:-}" ] || [ -z "${WP_APP_PASSWORD:-}" ] || [ -z "${WP_URL:-}" ]; then
  echo '{"error":"WP認証情報が不足しています。.envにWP_URL, WP_USERNAME, WP_APP_PASSWORDを設定してください"}' >&2
  exit 1
fi

ACTION="${1:-}"
shift || true

case "$ACTION" in
  upload)
    FILE_PATH="${1:-}"
    ALT_TEXT="${2:-}"
    if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
      echo '{"error":"ファイルが見つかりません: '"$FILE_PATH"'"}' >&2
      exit 1
    fi
    CURL_ARGS=(-s -u "$WP_USERNAME:$WP_APP_PASSWORD" -F "file=@$FILE_PATH")
    if [ -n "$ALT_TEXT" ]; then
      CURL_ARGS+=(-F "alt_text=$ALT_TEXT")
    fi
    curl "${CURL_ARGS[@]}" "$WP_URL/wp-json/wp/v2/media"
    ;;
  get)
    ENDPOINT="${1:-}"
    curl -s -u "$WP_USERNAME:$WP_APP_PASSWORD" "$WP_URL/wp-json/wp/v2/$ENDPOINT"
    ;;
  post)
    ENDPOINT="${1:-}"
    JSON_DATA="${2:-}"
    curl -s -X POST -u "$WP_USERNAME:$WP_APP_PASSWORD" \
      -H "Content-Type: application/json" \
      -d "$JSON_DATA" \
      "$WP_URL/wp-json/wp/v2/$ENDPOINT"
    ;;
  *)
    echo "使い方:" >&2
    echo "  wp-curl.sh upload <画像パス> [alt_text]" >&2
    echo "  wp-curl.sh get <endpoint>" >&2
    echo "  wp-curl.sh post <endpoint> <json>" >&2
    exit 1
    ;;
esac
