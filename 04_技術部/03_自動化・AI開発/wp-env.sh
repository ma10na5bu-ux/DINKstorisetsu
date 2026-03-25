#!/bin/bash
# .envからWordPress認証情報を安全に読み込むヘルパー
# 使い方: eval "$(bash 04_技術部/03_自動化・AI開発/wp-env.sh)"
#
# スペース入りのAPP_PASSWORDを正しくexportする

ENV_FILE="$(dirname "$0")/../../.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "echo 'ERROR: .env not found at $ENV_FILE'" >&2
  exit 1
fi

# .envをパースしてexport文を出力
while IFS='=' read -r key value; do
  # コメント行・空行をスキップ
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  # 値の前後の空白を除去
  value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  echo "export $key=\"$value\""
done < "$ENV_FILE"
