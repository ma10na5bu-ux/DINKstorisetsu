# NGワード・品質チェックルール

> 記事パイプラインの品質ゲート定義。生成→公開の間で必ず通す。

---

## パイプライン実行順序

```
1. 記事生成（Claude API）
      ↓
2. NGワードGrepチェック（ng-word-checker.js）
   - critical検出 → 停止・修正へ戻す
   - warningのみ → レポート付きで続行
      ↓
3. ファクトチェック（fact-checker.js）
   - LLMプロンプトにもNGルール組み込み済み
      ↓
4. 編集チェック（/editorial-check）
      ↓
5. WordPress公開
```

## 実行コマンド

```bash
cd 04_技術部/03_自動化・AI開発/fact-checker

# Step 1: NGワードチェック
node ng-word-checker.js <記事.md>

# Step 2: ファクトチェック（NGチェック通過後）
node fact-checker.js <記事.md>
```

---

## NGワードルール一覧

### ❌ Critical（検出=パイプライン停止）

| ID | カテゴリ | NGパターン | リスク | 置換方針 |
|---|---|---|---|---|
| DINKS-001 | ライフスタイル否定 | 子なしは可哀想/不完全/寂しい | DINKs否定 | DINKsの選択を尊重する表現に |
| FINANCE-001 | 金融リスク | 絶対に儲かる/必ず利益が出る | 誇大広告 | 「期待できます」「可能性があります」 |
| FINANCE-002 | 投資助言 | 具体的な銘柄・商品の購入指示 | 投資助言該当 | FPに相談を案内 |
| LEGAL-001 | 法律情報 | 税務・法律の具体的判断指示 | 専門家領域 | 税理士・弁護士に相談を案内 |

### ⚠️ Warning（検出=要確認・続行可）

| ID | カテゴリ | NGパターン | リスク | 置換方針 |
|---|---|---|---|---|
| LOGIC-001 | AI構文 | 矛盾する主張が同一記事内に共存 | 論理破綻 | 一貫性を確保 |
| TONE-001 | トーン | 「絶対に〜する」「100%効果」 | 信頼性 | 「期待できます」「役立つことが多い」 |
| COMPARE-001 | 比較表現 | 他のライフスタイルを否定する表現 | トーン違反 | ポジティブな表現に置換 |

---

## ルール追加方法

`ng-words.json` にルールを追加する：

```json
{
  "id": "DINKS-002",
  "category": "ライフスタイル否定",
  "severity": "critical",
  "pattern": "正規表現パターン",
  "description": "問題の説明",
  "replacement_guide": "置換方針"
}
```

LLMプロンプト側（`fact-checker.js` の `FACT_CHECKER_SYSTEM_PROMPT` / `REVISER_SYSTEM_PROMPT`）にも同時に反映すること。
