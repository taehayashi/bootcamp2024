# [Hands-on] Cloud Run x AlloyDB via Direct VPC egress

## ハンズオンの概要

本ハンズオンでは、**Cloud Run** と **AlloyDB** を使ったアプリケーション構築の流れを体験します。

ただし、Cloud Run から AlloyDB へのアクセスは、セキュリティポリシーにより プライベート IP アドレスを経由する必要があると仮定し、**Direct VPC Egress** を活用して、これを実現します。

### このラボの内容
* VPC, サブネットを作成する
* AlloyDB を作成する
* Artifact Registry にリポジトリを作成し、コンテナをビルド・プッシュする
* Cloud Run Service を構成する
* 接続をテストする


## Google Cloud プロジェクトの設定
次に、ターミナルの環境変数にプロジェクトIDやリージョンを設定します。
```bash
export PROJECT_ID=$(gcloud config list --format 'value(core.project)')
export REGION=asia-northeast1
export NETWORK_NAME=qwiklabs-handson-network
export SUBNET_NAME=asia-northeast1
export ALLOY_CLUSTER_NAME=primary
export ALLOY_INSTANCE_ID=qwiklabs-handson
```
<walkthrough-info-message>**Tips:** コードボックスの横にあるボタンをクリックすることで、クリップボードへのコピーおよび Cloud Shell へのコピーが簡単に行えます。</walkthrough-info-message>

次に、このハンズオンで利用するAPIを有効化します。

```bash
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable servicenetworking.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable alloydb.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```



## **[STEP1] VPC, サブネット を作成する**

<walkthrough-tutorial-duration duration=10></walkthrough-tutorial-duration>

このステップでは、Virtual Private Cloud (VPC) および サブネットを作成します。

1. 次のコマンドを実行して、VPC を作成します。
```bash
gcloud compute networks create $NETWORK_NAME --subnet-mode=custom
```

2.  続いて、作成した VPC にサブネットを作成します。
```bash
gcloud compute networks subnets create $SUBNET_NAME --network=$NETWORK_NAME --range="172.16.0.0/12" --region=$REGION
```

リソースが作成されたことをコンソール画面でも確認します。

3. ナビゲーションメニュー <walkthrough-nav-menu-icon></walkthrough-nav-menu-icon> から [**VPC ネットワーク**] に移動し、一覧に 作成した VPC `qwiklabs-handson-network` があることを確認します。

4. 続いて、VPC `qwiklabs-handson-network` をクリックし、VPC ネットワークの詳細画面を開きます。
[**サブネット**] タブをクリックし、一覧に作成したサブネット `asia-northeast1` があることを確認します。

以上で、VPC および サブネットを作成することができました。

## **[STEP2] Private Service Access の作成**

<walkthrough-tutorial-duration duration=5></walkthrough-tutorial-duration>

ここでは、Private Service Access を作成し、STEP1 で作成した VPC および Google Cloud が管理する VPC 間をプライベート接続できるように準備します。

1. 次のコマンドを実行して、STEP1 で作成した VPC および Google Cloud が管理する VPC 間をプライベート接続するための VPC ピアリング を作成します。

```bash
gcloud compute addresses create allocated-address-range \
    --global \
    --purpose=VPC_PEERING \
    --addresses=192.168.0.0 \
    --prefix-length=16 \
    --network=$NETWORK_NAME
```

```bash
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=allocated-address-range \
    --network=$NETWORK_NAME
```


## **[STEP3-1] AlloyDB クラスタを作成する**

<walkthrough-tutorial-duration duration=10></walkthrough-tutorial-duration>

ここでは、Cloud Run からアクセスするデータベースである AlloyDB のクラスタを作成します。

1.  次のコマンドを実行して、AlloyDB クラスタを作成します。
```bash
gcloud alloydb clusters create $ALLOY_CLUSTER_NAME \
    --database-version=POSTGRES_16 \
    --password=postgres \
    --region=$REGION \
    --project=$PROJECT_ID \
    --network=$NETWORK_NAME
```

リソースが作成されたことをコンソール画面でも確認します。

2. コンソール画面上部にある [**スラッシュ（/）を使用してリソース、ドキュメント、プロダクトなどを検索**] をクリックし、「AlloyDB」と入力し、Enter します。

3. 検索結果から「**AlloyDB**」を選択します。

4. AlloyDB クラスタの一覧に、作成した AlloyDB クラスタ `primary` があることを確認します。

以上で、AlloyDB クラスタを作成することができました。


## **[STEP3-2] AlloyDB インスタンスを作成する**

<walkthrough-tutorial-duration duration=15></walkthrough-tutorial-duration>

次に、AlloyDB のインスタンスを作成していきます。

1.  次のコマンドを実行して、AlloyDB インスタンスを作成します。

<walkthrough-info-message>**注:** インスタンスの作成には時間がかかる可能性があります。</walkthrough-info-message>

```bash
gcloud alloydb instances create $ALLOY_INSTANCE_ID \
    --instance-type=PRIMARY \
    --cpu-count=2 \
    --region=$REGION \
    --cluster=$ALLOY_CLUSTER_NAME \
    --assign-inbound-public-ip=ASSIGN_IPV4 \
    --ssl-mode=ALLOW_UNENCRYPTED_AND_ENCRYPTED \
    --database-flags password.enforce_complexity=on \
    --project=$PROJECT_ID
```

リソースが作成されたことをコンソール画面でも確認します。

2. AlloyDB クラスタの画面をリロードし、 AlloyDB クラスタ `primary` 配下に `qwiklabs-handson` があることを確認します。

以上で、AlloyDB インスタンスを作成することができました。

## **[STEP4] AlloyDB にデータを設定する**

<walkthrough-tutorial-duration duration=15></walkthrough-tutorial-duration>

このステップでは、AlloyDB に Auth Proxy 経由でアクセスし、データベース・テーブルの作成、およびデータの挿入を行います。

1. 次のコマンドを実行し、AlloyDB Auth Proxy をインストールします。

```bash
wget https://storage.googleapis.com/alloydb-auth-proxy/v1.11.3/alloydb-auth-proxy.linux.amd64 -O alloydb-auth-proxy
chmod +x alloydb-auth-proxy
```

2. 続いて、AlloyDB Auth Proxy を起動します。

```bash
./alloydb-auth-proxy projects/$PROJECT_ID/locations/asia-northeast1/clusters/primary/instances/$ALLOY_INSTANCE_ID \
    --port 5432 \
    --address 127.0.0.1 \
    --auto-iam-authn \
    --public-ip
```

3. Cloud Shell ターミナルのタブで「**＋**」ボタンをクリックし、新たなターミナルを開きます。

4. 新しく開いたターミナルタブで、次のコマンドを実行し、AlloyDB インスタンスへ接続します。

<walkthrough-info-message>パスワードを聞かれたら `postgres` を入力して Enter します。</walkthrough-info-message>

```bash
psql -h 127.0.0.1 -U postgres
```

5. 続いて、次の SQL を実行し、database と table の作成及び、データを挿入します。

```sql
CREATE DATABASE guestbook;
\connect guestbook
CREATE TABLE entries (guestname VARCHAR(255),
                      content VARCHAR(255),
                      entryid SERIAL PRIMARY KEY);
INSERT INTO entries (guestname, content) values ('Alex', 'I got here!');
INSERT INTO entries (guestname, content) values ('Kai', 'Me too!');
```

6. 次のコマンドを実行し、AlloyDB への接続を終了します。

```sql
quit
```
<walkthrough-info-message>接続を終了したら、SQL を実行していたターミナルのタブは閉じて構いません。</walkthrough-info-message>


7. 元の Cloud Shell ターミナルのタブに戻り、 `Ctrl` + `C` を実行し、Auth Proxy を終了します。

以上でデータの準備は完了です。


## **[STEP5] Artifact Registry を構築する**

<walkthrough-tutorial-duration duration=10></walkthrough-tutorial-duration>


このステップでは、Cloud Run にデプロイするコンテナアプリケーションを Artifact Registry に登録していきます。

1. 次のコマンドを実行し、Artifact Registry リポジトリを作成します。

```bash
gcloud artifacts repositories create qwiklabs-apps --repository-format=docker --location=$REGION
```

コンソール画面でも Artifact Registry にリポジトリが作成されたことを確認します。

2. コンソール画面上部にある [**スラッシュ（/）を使用してリソース、ドキュメント、プロダクトなどを検索**] をクリックし、「Artifact Registry」と入力し、Enter します。

3. 検索結果から「**Artifact Registry**」を選択します。

4. リポジトリの一覧に `qwiklabs-apps` があることを確認します。

5. 続いて、次のコマンドを実行し、サンプルアプリケーションのコンテナをビルドし、作成した Artifact Registry リポジトリへのプッシュします。

```bash
cd cloudrun-app
```

```bash
docker build -t asia-northeast1-docker.pkg.dev/$PROJECT_ID/qwiklabs-apps/inquiry-guestbook:v1.0 .
docker push asia-northeast1-docker.pkg.dev/$PROJECT_ID/qwiklabs-apps/inquiry-guestbook:v1.0
```

最後に、コンソール画面でも サンプルアプリケーションが  Artifact Registry リポジトリにプッシュされていることを確認します。

6. リポジトリの一覧から `qwiklabs-apps` をクリックします。リポジトリの詳細画面に `inquiry-guestbook` があることを確認します。

以上で Artifact Registry の設定は完了です。


## **[STEP6] Cloud Run を構築する**

<walkthrough-tutorial-duration duration=15></walkthrough-tutorial-duration>

このステップでは、サンプルアプリケーションを Cloud Run へデプロイします。

1. まず始めに、Cloud Run からの Alloy DB アクセス時に使用するプライベート IP アドレスを環境変数へ設定しておきます。

```bash
export IP_ADDRESS=$(gcloud alloydb instances describe $ALLOY_INSTANCE_ID --cluster=$ALLOY_CLUSTER_NAME --region=$REGION --format="value(ipAddress)")
```

2. 続いて、Cloud Run の構成情報にプロジェクト ID や AlloyDB のプライベート IP アドレス情報を反映するため、yaml ファイルを修正します。

```bash
sed -i -e s/PROJECT_ID/$PROJECT_ID/ cloudrun.yaml
sed -i -e s/IP_ADDRESS/$IP_ADDRESS/ cloudrun.yaml
```

3. 次のコマンドを実行し、修正した Cloud Run の構成情報 (yaml ファイル) を元に、Cloud Run サービスを作成します。

```bash
gcloud run services replace cloudrun.yaml --project=$PROJECT_ID
```

コンソール画面でも Cloud Run サービス が作成されたことを確認します。

4. コンソール画面上部にある [**スラッシュ（/）を使用してリソース、ドキュメント、プロダクトなどを検索**] をクリックし、「Cloud Run」と入力し、Enter します。

5. 検索結果から「**Cloud Run**」を選択します。

6. サービスのの一覧に `inquiry-guestbook` があることを確認します。

7. 最後に、Cloud Run にインターネットからアクセスができるように、エンドポイントをパブリック公開にします。

```bash
gcloud run services add-iam-policy-binding inquiry-guestbook --member=allUsers --role=roles/run.invoker --region=$REGION
```


## **[STEP6] 接続をテストする**

<walkthrough-tutorial-duration duration=15></walkthrough-tutorial-duration>

本ステップでは、Cloud Run から AlloyDB への接続をテストします。

1. Cloud Run から AlloyDB へのアクセスを許可するための Firewall ルールを VPC に設定します。

```bash
gcloud compute firewall-rules create allow-ingress-run --allow=tcp --source-ranges="172.16.0.0/12" --network=$NETWORK_NAME --source-tags=run-direct-egress
```

2. Cloud Run のパブリックエンドポイントを環境変数へ設定します。

```bash
export ENDPOINT=$(gcloud run services describe inquiry-guestbook --format 'value(status.url)' --region=$REGION)
```

3. Cloud Run のパブリックエンドポイントにアクセスします。

```bash
curl $ENDPOINT/entries
```

<walkthrough-info-message> [{"content":"I got here!","entryID":1,"guestName":"Alex"},{"content":"Me too!","entryID":2,"guestName":"Kai"}] がコマンド結果として応答されていれば成功です。</walkthrough-info-message>


## Congratulations!
<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

おめでとうございます！ハンズオンはこれで完了です。ご参加ありがとうございました。