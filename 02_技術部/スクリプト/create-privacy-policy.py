#!/usr/bin/env python3
"""プライバシーポリシーページをWordPressに作成するスクリプト"""

import json
import urllib.request
import base64
import os

WP_URL = "https://dekataro.com"
WP_USERNAME = "dekataro"
WP_APP_PASSWORD = "YUgf TK04 RqBo mO3j d7Xi luiB"

content = """<!-- wp:heading -->
<h2 class="wp-block-heading">プライバシーポリシー</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>ふたり暮らしアップデート（運営者：がく、以下「当サイト」）は、訪問者のプライバシーを尊重し、個人情報の適切な管理に努めています。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">広告について</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトは、以下のアフィリエイトプログラムに参加しています。</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><li>Amazonアソシエイト・プログラム</li><li>バリューコマース、A8.net、その他アフィリエイトサービス</li></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>Amazonのアソシエイトとして、ふたり暮らしアップデート（運営者：がく）は適格販売により収入を得ています。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>記事内のリンクから商品・サービスを購入された場合、当サイトに紹介料が発生することがあります。ただし、紹介料の発生の有無によって記事内容が変わることはありません。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">アクセス解析ツールについて</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトでは、Googleアナリティクスを使用してアクセス状況を分析しています。Googleアナリティクスはデータ収集のためにCookieを使用しますが、個人を特定する情報は収集されません。Cookieの使用はブラウザの設定で無効にできます。詳細は<a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer noopener">Googleのプライバシーポリシー</a>をご参照ください。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">個人情報の取り扱いについて</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトのお問い合わせフォームから送信された情報（お名前・メールアドレス・メッセージ）は、お問い合わせへの回答のみに使用します。第三者への提供はいたしません。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">免責事項</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトの情報はできる限り正確を期していますが、内容の完全性・正確性を保証するものではありません。当サイトの情報をもとに行動した結果について、当サイトは一切の責任を負いかねます。</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">著作権について</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>当サイトのテキスト・画像等の著作権は運営者（がく）に帰属します。無断転載・複製はご遠慮ください。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>制定日：2026年4月29日</p>
<!-- /wp:paragraph -->"""

auth = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()

data = json.dumps({
    "title": "プライバシーポリシー",
    "slug": "privacy-policy",
    "content": content,
    "status": "publish",
    "type": "page"
}).encode("utf-8")

req = urllib.request.Request(
    f"{WP_URL}/wp-json/wp/v2/pages",
    data=data,
    headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json; charset=utf-8",
    },
    method="POST"
)

with urllib.request.urlopen(req) as res:
    result = json.loads(res.read().decode())
    print(f"ID: {result['id']}")
    print(f"URL: {result['link']}")
    print(f"Status: {result['status']}")
