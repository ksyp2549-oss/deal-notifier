# deal-notifier

楽天市場・Amazonの激安商品をDiscordに通知するシステム。**GitHub Actionsで動かせば、自分のPCの電源が
切れていても自動で監視し続けます。**

## 仕組み

- `src/sources/rakuten.py`: 楽天市場商品検索API + ランキングAPIでキーワード/ジャンルを巡回
- `src/sources/amazon.py`: Amazon Creators API(旧PA-APIは2026年5月15日廃止)でキーワード検索
- `src/rules.py`: 取得した商品を以下のいずれかに該当したら「激安」と判定
  1. 定価に対する割引率が `config.yaml` の `min_discount_percent` 以上(Amazonなど定価情報がある場合)
  2. これまで観測した最安値からさらに `price_drop_from_history_percent` 以上値下がり(価格履歴はSQLiteに蓄積)
  3. 商品名に `sale_keywords` のいずれかを含む
- `src/notifier/discord.py`: 該当商品をDiscord Webhookへ埋め込みメッセージで通知(同一商品は`renotify_cooldown_hours`の間は再通知しない)
- `src/main.py`: エントリポイント。`--once` を付けると1回だけ巡回して終了(GitHub Actions向け)、付けなければAPSchedulerで内部的に定期実行し続ける(Docker/VPS向け)

## セットアップ

### 1. 楽天Web Service ID(すぐ使える)

1. https://webservice.rakuten.co.jp/ でアプリ登録(即時発行、無料)。「New App」→ Application type は
   **Web Application** を選び、Allowed websites に `github.com` を登録する(GitHub Actionsから
   呼び出すため。実行元IPが毎回変わるのでAPI/Backend Service(IP方式)は使えない)
2. 登録後、アプリの「Application ID」と、目のアイコンで表示できる「Access Key」の両方をコピーする
   (2026年のAPI改定でAccess Keyも必須になった)
3. アフィリエイトリンクにしたい場合は https://affiliate.rakuten.co.jp/ でアフィリエイトIDも取得

### 2. Discord Webhook

1. 通知したいチャンネルの「連携サービス」→「ウェブフックを作成」
2. Webhook URLをコピー

### 3. Amazon Creators API(任意・審査が必要、後回しでOK)

旧Product Advertising API(PA-API)は2026年5月15日に廃止済みです。Amazonアソシエイトの
管理画面(Associates Central)→ Tools → Creators API から Credential ID / Credential Secret を
発行してください。準備ができたら `config.yaml` の `amazon.enabled` を `true` にします。

### 4. 監視条件の調整

`config.yaml` でキーワード・ジャンル・割引率のしきい値などを調整します(後から何度でも変更可)。

## GitHub Actionsで自動運用(推奨・無料・PCの電源不要)

15分おき(`.github/workflows/notify.yml` の `cron` で調整可能)にGitHubのサーバー上でこのプログラムが
実行され、Discordに通知します。パソコンを開いている必要は一切ありません。

1. GitHubで新しいリポジトリを作成する(Public/Privateどちらでも可。APIキー等はコードに書かないので
   Publicでも問題ありませんが、気になる場合はPrivateを選ぶ)
2. このフォルダの中身をそのリポジトリにpushする
3. リポジトリの `Settings` → `Secrets and variables` → `Actions` → `New repository secret` で、
   手順1・2で取得した値を1つずつ登録する(名前は `.env.example` と同じにする):
   - `DISCORD_WEBHOOK_URL`
   - `RAKUTEN_APPLICATION_ID`
   - `RAKUTEN_ACCESS_KEY`(2026年のAPI改定で必須になった。アプリ管理画面の「Access Key」を目のアイコンで表示してコピー)
   - `RAKUTEN_AFFILIATE_ID`(未取得なら空でOK)
   - Amazonを使う場合は `AMAZON_CREDENTIAL_ID` / `AMAZON_CREDENTIAL_SECRET` / `AMAZON_PARTNER_TAG` も追加
4. リポジトリの `Actions` タブを開き、ワークフローが有効になっていることを確認
5. すぐに試したい場合は `Actions` タブ →「Deal Notifier」→「Run workflow」で手動実行できる
   (待たなくても即座に1回チェックが走る)

以降は自動で15分おきに実行され続けます。価格履歴・通知済み記録(`data/deals.db`)は実行のたびに
GitHub Actionsがリポジトリへ自動コミットして保存するので、次回実行時も引き継がれます。

> `config.yaml` の `poll_interval_minutes` はDocker/VPSで常時プロセスとして動かす場合の間隔設定です。
> GitHub Actionsを使う場合の実行間隔は `.github/workflows/notify.yml` の `cron` の方が優先されます。

## ローカルでテスト実行(任意)

```
pip install -r requirements.txt
cp .env.example .env
# .env を編集してAPIキー等を設定
python -m src.main --once
```

## 別の方法: Docker/VPSで常時プロセスを起動する

GitHub Actionsではなく、自前のサーバーで常時起動しておきたい場合はこちら。

```
docker compose up -d --build
```

- `data/deals.db` に価格履歴・通知履歴が永続化されます(ローカルDockerの場合)
- `config.yaml` を編集後は `docker compose restart` で反映
- Railway / Render / Fly.io / 任意のVPS(Docker対応)にそのままデプロイ可能。`.env` の内容を
  環境変数として設定し、`data/` ディレクトリ相当をボリュームとして永続化すること
