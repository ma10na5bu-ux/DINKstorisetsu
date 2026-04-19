# CLAUDE.md — デカ太郎メディア統合プロジェクト指示書

## プロジェクト概要

デカ太郎が運営する2つのメディアを一元管理するプロジェクト。

| | デカログ（ブログ） |
|---|---|
| **URL** | https://dekataro.com |
| **目的** | 収益化（SEO → アフィリエイト） |
| **記事の主語** | 読者（ハウツー・レビュー・比較） |
| **テーマ** | 柴犬・DINKs暮らし・お金・レビュー・おでかけ |
| **想定読者** | 検索流入（20〜40代夫婦・柴犬オーナー） |
| **文字数** | 2,000〜3,000字 |
| **公開方法** | wp-post.py（自動投稿） |
| **成功指標** | PV・収益 |

### 運営方針
- ブログのみ運営。note は2026-04-14廃止
- 詳細は `メディア運用方針.md` を参照

### ブログ技術スタック
- WordPress（SWELL）/ ConoHa WING / Claude Code / Gemini Advanced / AquaVoice Pro
- GitHub: https://github.com/ma10na5bu-ux/DINKstorisetsu（※リポ名変更予定）
- Slack: #dinksトリセツ（Shibamediaワークスペース）

### ネタ帳
- ローカルファイルで管理: `01_編集部/ネタ帳.md`
- Notionは参照しない（2026-04-13移行済み）

### Gemini MCP連携
- テキスト系（レビュー・校正）: Gemini MCP or curl直接（gemini-2.5-flash）
- 画像生成: Geminiチャット画面（手動）
- レビュープロンプト: `01_編集部/ガイドライン/Geminiレビュープロンプト.md`

---

## フォルダ構成

```
dekataro/
├── CLAUDE.md
├── メディア運用方針.md    ← ブログとnoteの棲み分けルール
├── 01_編集部/
│   ├── 原稿/              ← ブログ記事Markdown
│   ├── 画像/              ← ブログ・アイキャッチ・プロンプト（ローカル保管）
│   ├── ガイドライン/       ← 編集・デザイン・CSS
│   ├── knowledge/          ← 文体リファレンス用の高品質過去記事（執筆時に参照）
│   └── ネタ帳.md           ← 記事アイデア管理
├── 02_技術部/
│   └── スクリプト/         ← wp-post.py, trim-eyecatch.py 等
├── migration_data/         ← サイト統合時の移行データ（アーカイブ）
├── .env                   ← WP認証・APIキー（.gitignore済み）
└── .mcp.json              ← Notion・Gemini MCP設定
```

---

## 編集方針

### コンセプト
「30代夫婦と豆柴の暮らし」を発信するメディア。柴犬・DINKs暮らし・おでかけ・お金の4軸。

### トーンの3原則
1. ポジティブであること：暮らしの楽しさを伝える
2. クスッと笑えること：日常のおかしみ、読んでて口角が上がる文章
3. なるべく誰も傷つかないこと：他のライフスタイルを否定しない

### NGルール
- **他のライフスタイルとの比較をしない**（子育て世帯 vs DINKs 等）
- **他人や他のものを否定しない**
- DINKsを正当化・弁明するトーンにしない
- 「DINKsの方が勝ち組」的な表現は絶対NG
- 子どもがいる人を「大変そう」と見下す表現もNG
- **医療・健康に関する記事は対象外**（獣医師に相談を案内するにとどめる）

### 記事の判断基準
「この記事を読んだ人が、思わずスクショしてパートナーに送りたくなるか？」

### コンテンツタイプと比率
| タイプ | 目標比率 | 内容 |
|---|---|---|
| 笑い・あるある | 50%以上 | 柴犬あるある、夫婦あるある、笑える実体験 |
| 体験記事 | 30% | 実用情報を体験ストーリーで包んだ記事 |
| 知識記事 | 20%以下 | SEO入口記事。体験エピソードを冒頭に入れる |

### カテゴリ（9分類）
※ slug はWordPress実態に合わせた正確な値。記事YAMLの`category:`にはこのslugを使う。

| カテゴリ | slug | WP ID | 内容 |
|---|---|---|---|
| 柴犬 | shiba | 2 | 柴犬の基本・しつけ・あるある・柴犬との暮らし・犬グッズ |
| 夫婦 | couple | 10 | 夫婦の日常・暮らし・住まい・旅行・DINKs向けグッズ・家電 |
| お金 | money | 5 | 家計管理・資産形成・投資 |
| 仕事 | work | 1 | 転職・副業・働き方・キャリア・ツール・効率化 |
| ゴルフ | golf | 11 | ゴルフ体験・コース・ギア |
| キャンプ | camp | 12 | キャンプ体験・ギア・スポット |
| 筋トレ | training | 13 | トレーニング・習慣化・ギア |
| 趣味 | hobby | 15 | ライフスタイル系趣味・ランキング・始め方 |
| コラム | column | ※WP未作成 | データ・研究・エッセイ・雑感（特定カテゴリに収まらないもの） |

### 文章スタイル
- 書き手（デカ太郎）の一人称視点
- ヨメ氏（妻）・ハチ（豆柴）も登場
- 読者に語りかける文体（「〜ですよね」「〜ありませんか？」）
- ストーリーの中に情報を織り込む
- 読者層：20〜40代の夫婦・柴犬オーナー・柴犬に興味がある人

### 夫婦のキャラクター
| | デカ太郎（夫・書き手） | ヨメ氏（妻） |
|---|---|---|
| 性格 | 自由奔放・ポジティブ | 優しい・おだやか |
| 役割 | ボケ・突っ走る側 | ツッコミ・見守る側 |

### 呼び名ルール（全メディア統一）
| 対象 | 呼び名 | 旧名（使用禁止） |
|---|---|---|
| 自分 | デカ太郎 | まーくん |
| 妻 | ヨメ氏 | はるさん |
| 犬 | ハチ | えいちゃん |

- SWELLの「ふきだし」で会話形式を表現
- デカ太郎がやらかす → ヨメ氏の冷静なツッコミ、が基本パターン

### ふきだしブロック形式
```html
<!-- デカ太郎（左・グリーン） -->
<!-- wp:loos/balloon {"balloonIcon":"https://dekataro.com/wp-content/uploads/2026/04/dekataro-icon.png","balloonName":"デカ太郎","balloonCol":"green"} -->
<p>セリフ</p>
<!-- /wp:loos/balloon -->

<!-- ヨメ氏（右・レッド） -->
<!-- wp:loos/balloon {"balloonIcon":"https://dekataro.com/wp-content/uploads/2026/04/yomeshi-icon.png","balloonName":"ヨメ氏","balloonCol":"red","balloonAlign":"right"} -->
<p>セリフ</p>
<!-- /wp:loos/balloon -->
```

### 黄色ハイライト記法
原稿Markdownでは `<mark>` タグを使う。wp-post.py が自動的にSWELLネイティブマーカーに変換する。

```
<mark>ここに強調したいテキスト</mark>
```

→ WordPressには `<span class="swl-marker mark_yellow">テキスト</span>` として投稿される。

### タイトル
- **40文字以内**
- 感情や好奇心を刺激しつつ検索キーワードを含める
- 商品名・サービス名・地域名・具体的な状況を入れる

### 記事構成
- 文字数：2,000〜3,000字
- 構成：書き出し → 実用情報（地の文） → 本文（H2×3〜5） → まとめ
- 冒頭の実用情報はまとめボックス・囲み枠禁止。地の文に自然に溶け込ませる
- メタディスクリプション：120文字以内
- 内部リンク：最低2本
- 画像alt属性は必ず設定

### アイキャッチ画像
- 生成: generate-eyecatch.py（gemini-3-pro-image-preview → 1200×630 JPEG を自動出力）
- trim-eyecatch.py は不要（ウォーターマークなし・リサイズはスクリプト内で完結）
- 出力ファイル: `01_編集部/画像/{slug}_eyecatch.jpg`
- プロンプトファイルは `01_編集部/画像/{slug}_eyecatch_prompt.md` に保存
- `アイキャッチ画像プロンプト集.md` は読み込み不要。以下のテンプレートを使う:

```
Draw a wide illustration (16:9 aspect ratio, 1200×630px).

【Scene】
{{記事の場面を英語で。夫婦30代・豆柴を自然に配置。右下15%は重要要素を置かない}}

【Art Style】
- Flat vector illustration style, NOT anime
- Minimal line work, soft rounded shapes
- Similar to modern web/app illustration (like Notion or Slack illustrations)

【Color Palette — STRICT】
- Background: soft warm gray
- Primary: muted sage green
- Secondary: warm beige
- Accent (minimal use): soft coral
- Skin tones: warm natural tones
- NO bright red, NO bright blue, NO vivid yellow, NO saturated colors

【Composition】
- Clean and simple, lots of white space / Key elements centered
- IMPORTANT: Do NOT place any important elements in the bottom-right corner (the bottom-right 15% of the image will be cropped)
- Magazine editorial feel, calm and sophisticated

【Rules】
- No text, no watermarks, no logos, no color swatches, no labels, no annotations
- Keep all important elements within the center 60% of the image
- Overall tone: calm, warm, minimal
```

### 収益化
- アフィリエイト（ドッグフード、ペット保険、時短家電、旅行、VOD、キャンプギア、家計管理サービス）
- 集客: SEO（Google検索）、将来的にPinterest追加
- 棲み分け: noteは「自分」が主語（日記・エッセイ）。ブログは「読者」が主語（ハウツー・レビュー・比較）

---

## 制作フロー

### Phase 1: ネタ選び＋ヒアリング（✅承認①）
1. プリフライトチェック（`.env` の WP認証キー存在確認のみ。Notionチェック不要）
2. `01_編集部/ネタ帳.md` を読み込んで💡アイデア欄から候補を抽出（ファイル1回読むだけ）
3. 候補＋ヒアリングテンプレートをセットで提示
4. デカ太郎が選択＋回答（1往復で完結）

### Phase 2: リサーチ＋構成（✅承認②）
5. **競合・検索意図分析**（承認①で選定したテーマに対して実施）
   - 対策キーワードで検索上位3〜5サイトの構成を確認（WebSearch/WebFetch）
   - 競合が扱っていない独自要素（体験・データ）を特定
6. H2・H3の見出し構成案を作成し、デカ太郎に提示
7. デカ太郎が構成を承認（修正があればここで反映）

### Phase 3: 執筆＋レビュー＋監修（✅承認③）
8. 執筆（Markdown形式）
   - `01_編集部/knowledge/` 内の過去記事を参照し、文体・ふきだしのリズムを踏襲する
   - 内部リンク候補は Phase 1 で読んだネタ帳.mdの公開済み一覧から選ぶ（追加コスト0）
   - **分割執筆ルール**: H2が5つ以上の記事はH2単位で生成・確認を繰り返す（後半の品質劣化防止）
9. 並列実行: editorial-check + fact-check + アイキャッチプロンプト生成
10. デカ太郎に監修依頼（体験の嘘チェック・面白いか・fact-checkの🔍人間確認項目）

### Phase 4: アイキャッチ画像（全自動）
11. generate-eyecatch.py でアイキャッチ生成・リサイズ（自動）
    ```
    python3 02_技術部/スクリプト/generate-eyecatch.py {slug}
    ```
    → `01_編集部/画像/{slug}_eyecatch.jpg` が出力される

### Phase 5: 公開（全自動）
14. 画像アップロード（curl -F multipart形式。--data-binaryはWAF 403）
15. wp-post.py で記事投稿（**必ず `--auto --publish --media <ID>` を付ける**）
    ```
    python3 02_技術部/スクリプト/wp-post.py "原稿ファイル.md" --auto --publish --media <画像ID>
    ```
    - `--auto`: YAMLフロントマターからtitle・slug・meta_descriptionを自動読み込み（必須）
    - `--media`: アイキャッチのmedia ID（`--eyecatch-id`は存在しない）
16. wp-post.pyの出力でslug・title・linkを確認。スラッグが`{id}-2`等の場合のみAPIで修正
17. `01_編集部/ネタ帳.md` を更新（アイデア欄から削除→公開済み欄に追記）
18. git commit + push

### 派生記事
- 1体験→複数記事に切り出し、相互リンク
- トーン：デカ太郎一人称、日記より情報寄り。「友達に教えてあげる」距離感

---

## 品質チェック

### チェック体制
- **editorial-check**: 構成・SEO（KW密度1.5〜2%）・論理整合・AI特有エラー・医療情報混入チェック（必須）
- **fact-check**: 数値データ・固有名詞・研究引用の検証（必須。editorial-checkと並列実行）
- **Geminiレビュー**: 任意。デカ太郎が「Geminiにも見せて」と指示した場合のみ実行

### 文体リファレンス
- `01_編集部/knowledge/` に高品質な過去記事5本を収録
- 執筆時に文体・ふきだし配置・構成リズムの参照元として使用

### 文章品質ルール
- 一文60文字以内
- 同じ語尾が3回連続しない
- 体言止め3つ以上連続しない
- 数値の一貫性（タイトル・リード・本文・まとめで矛盾しない）

### 表現NG
- 「好きです」（ヨメ氏への直接的愛情表現）→「感謝です」「ありがたい」
- 「必ず」「絶対」等の断言 →「〜の場合が多い」
- 症状→具体的対処指示 → 獣医師に相談を案内

---

## 自律実行ルール

**基本原則：コスト（課金）が発生しない作業はすべて承認不要で自動実行。完了まで自律的に進行する。**

### 承認必須（これだけ）
- 外部の有料APIへの新規接続
- WordPressの設定変更（テーマ・プラグイン等）
- サイト全体に影響する一括変更
- 不可逆な本番環境の操作

### 共通制約
- 個人情報・APIキーをコードに直書きしない
- `.env`の内容をログに出力しない
- 記事は必ず /editorial-check + /fact-check を通してから投稿する

### 報告ルール
- 承認不要の作業 → 完了後に1行で事後報告
- エラー → 内容と対処を1行で報告、解決できたら続行
- 解決できないエラーのみ → 詳細を報告して指示を仰ぐ
- 作業完了時は git commit + push でGitHubを最新に保つ

