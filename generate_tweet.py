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
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# ====== 短縮URL作成関数 ======
def shorten_url(long_url):
    try:
        res = requests.get(f"https://tinyurl.com/api-create.php?url={long_url}")
        if res.status_code == 200:
            return res.text
    except Exception as e:
        print("⚠️ URL短縮失敗:", e)
    return long_url

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
    print("🔁 トークン更新レスポンス:", res.status_code, res.text)
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
print("🧠 キーワード選出:", kw1, kw2)

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
print("📝 ツイート内容:", tweet_text)

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
print("🖼️ 画像生成完了、サイズ:", len(image_data), "bytes")

# ====== 画像保存（圧縮） ======
today = datetime.now().strftime("%Y%m%d%H%M%S")
os.makedirs("images", exist_ok=True)
image_path = f"images/image_{today}.jpg"
image = Image.open(BytesIO(image_data)).convert("RGB")
image = image.resize((512, 512), Image.LANCZOS)
image.save(image_path, "JPEG", quality=85, optimize=True)
print("💾 画像保存済み:", image_path)

# ====== OGP付きHTML生成 ======
os.makedirs("posts", exist_ok=True)
html_path = f"posts/{today}.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(f"""
<!DOCTYPE html>
<html lang=\"ja\">
<head>
  <meta charset=\"UTF-8\">
  <meta property=\"og:title\" content=\"AI学級委員長ちゃんからの応援\" />
  <meta property=\"og:description\" content=\"{tweet_text}\" />
  <meta property=\"og:image\" content=\"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/images/image_{today}.jpg\" />
  <meta name=\"twitter:card\" content=\"summary_large_image\" />
  <title>AI学級委員長ちゃん</title>
</head>
<body>
  <h1>AI学級委員長ちゃんからの応援</h1>
  <img src=\"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/images/image_{today}.jpg\" alt=\"AI学級委員長ちゃん\" style=\"width:100%;\">
</body>
</html>
    """)
print("📝 HTML生成完了:", html_path)

# ====== GitHub Pagesにpush ======
repo_https = REPO_URL.replace("https://github.com", f"https://x-access-token:{GH_PAT}@github.com")
subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"])
subprocess.run(["git", "config", "--global", "user.name", "AI Class Bot"])
subprocess.run(["git", "remote", "remove", "origin"], check=False)
subprocess.run(["git", "remote", "add", "origin", repo_https])
subprocess.run(["git", "add", image_path, html_path])
subprocess.run(["git", "commit", "-m", f"Add image and HTML for {today}"], check=False)
push_result = subprocess.run(["git", "push", "origin", "HEAD"], capture_output=True, text=True)
print("🚀 GitHubへpush結果:", push_result.returncode)
print(push_result.stdout)
print(push_result.stderr)

# ====== Twitter投稿 ======
html_url = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}/posts/{today}.html"
short_url = shorten_url(html_url)
tweet_with_url = f"{tweet_text}\n{short_url}"

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
