#!/bin/bash
# .envからWordPress認証情報を安全に読み込むヘルパー
# 使い方: eval "$(bash 02_技術部/スクリプト/wp-env.sh)"
#
# スペース入りのAPP_PASSWORDを正しくexportする

# プロジェクトルートの.envを探す（フォルダ深さに依存しない）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE=""
CHECK_DIR="$SCRIPT_DIR"
while [ "$CHECK_DIR" != "/" ]; do
  if [ -f "$CHECK_DIR/.env" ]; then
    ENV_FILE="$CHECK_DIR/.env"
    break
  fi
  CHECK_DIR="$(dirname "$CHECK_DIR")"
done

if [ -z "$ENV_FILE" ] || [ ! -f "$ENV_FILE" ]; then
  echo "echo 'ERROR: .env not found'" >&2
  exit 1
fi

# .envをパースしてexport文を出力
while IFS='=' read -r key value; do
  # コメント行・空行をスキップ
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  # 値の前後の空白とクォートを除去
  value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//;s/^"//;s/"$//')
  echo "export $key=\"$value\""
done < "$ENV_FILE"
