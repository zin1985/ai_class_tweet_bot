# ✅ 完全なトークン更新＆投稿スクリプト（OAuth 2.0 User Context + refresh_token + OpenAI + GitHub push修正済み）

import os
import json
import base64
import random
from datetime import datetime
from io import BytesIO
import subprocess
import requests
from PIL import Image
from openai import OpenAI

# ====== 環境変数読み込み ======
CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("TWITTER_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO_URL = os.getenv("REPO_URL")
GH_PAT = os.getenv("GH_PAT")

# ====== アクセストークン更新関数（OAuth2） ======
def refresh_access_token():
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        print("❌ CLIENT_ID, CLIENT_SECRET または REFRESH_TOKEN が未設定です")
        exit(1)

    token_url = "https://api.twitter.com/2/oauth2/token"
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    basic_token = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {basic_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }
    res = requests.post(token_url, headers=headers, data=data)
    if res.status_code == 200:
        return res.json()["access_token"]
    else:
        print("❌ アクセストークン更新失敗:", res.status_code, res.text)
        exit(1)

# ====== アクセストークン取得 ======
TWITTER_ACCESS_TOKEN_V2 = refresh_access_token()

# ====== OpenAI 初期化 ======
client = OpenAI(api_key=OPENAI_API_KEY)

# ====== 設定読み込みとキーワード選出 ======
with open("prompt_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
with open("keywords1.json", "r", encoding="utf-8") as f1, open("keywords2.json", "r", encoding="utf-8") as f2:
    kw1 = random.choice(json.load(f1))
    kw2 = random.choice(json.load(f2))
    topic_prompt = f"今日の話題は「{kw1}」と「{kw2}」です。"

# ====== プロンプト生成 ======
CHARACTER_PROMPT = f"""
あなたは{config['character']}です。
特徴: {', '.join(config['traits'])}
絵柄: {config['style_hint']}
感情表現: {config['mood']}
このキャラクターとして、140文字以内で今日も頑張るフォロワーに優しく声をかけてください。
{topic_prompt}
"""

# ====== ツイート本文生成 ======
chat_response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": CHARACTER_PROMPT},
        {"role": "user", "content": "今日のツイートを作って"}
    ]
)
tweet_text = chat_response.choices[0].message.content.strip()

# ====== DALL·E画像生成 ======
dalle_prompt = (
    f"前髪あり＋サイドに結んだ黒髪ポニーテール、太めの眼鏡、"
    f"切り抜き文字型のAI髪飾り、赤いリボンの制服姿のAI学級委員長のデフォルメアニメ風イラスト。"
    f"今日のテーマは「{kw1}」と「{kw2}」。それを反映したイメージを描いてください。"
)
image_response = client.images.generate(
    model="dall-e-3",
    prompt=dalle_prompt,
    size="1024x1024",
    quality="standard",
    n=1,
    response_format="b64_json"
)
image_b64 = image_response.data[0].b64_json
image_data = base64.b64decode(image_b64)

# ====== 画像保存（軽量化） ======
today = datetime.now().strftime("%Y%m%d%H%M%S")
os.makedirs("images", exist_ok=True)
image_path = f"images/image_{today}.jpg"
image = Image.open(BytesIO(image_data)).convert("RGB")
image = image.resize((512, 512), Image.LANCZOS)
image.save(image_path, "JPEG", quality=85, optimize=True)

# ====== GitHub Pagesに画像をPush（リモート明示設定） ======
repo_https = REPO_URL.replace("https://github.com", f"https://x-access-token:{GH_PAT}@github.com")
subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"])
subprocess.run(["git", "config", "--global", "user.name", "AI Class Bot"])
subprocess.run(["git", "remote", "remove", "origin"], check=False)
subprocess.run(["git", "remote", "add", "origin", repo_https])
subprocess.run(["git", "add", image_path])
subprocess.run(["git", "commit", "-m", f"Add image {image_path}"])
subprocess.run(["git", "push", "origin", "HEAD"])

# ====== Twitter投稿（v2） ======
page_url = REPO_URL.replace("https://github.com", "https://").replace(".git", "")
image_url = f"{page_url}/images/image_{today}.jpg"
tweet_with_url = f"{tweet_text}\n{image_url}"

headers = {
    "Authorization": f"Bearer {TWITTER_ACCESS_TOKEN_V2}",
    "Content-Type": "application/json"
}
payload = {"text": tweet_with_url}
res = requests.post("https://api.twitter.com/2/tweets", headers=headers, json=payload)

if res.status_code in [200, 201]:
    print("✅ ツイート投稿成功（OAuth2 + refreshトークン）")
else:
    print("❌ ツイート失敗:", res.status_code, res.text)
