import openai
import base64
import json
import os
import random
from datetime import datetime
from PIL import Image
from io import BytesIO
import subprocess
import requests

# 設定読み込み
with open("prompt_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# キーワード選出
with open("keywords1.json", "r", encoding="utf-8") as f1, open("keywords2.json", "r", encoding="utf-8") as f2:
    kw1 = random.choice(json.load(f1))
    kw2 = random.choice(json.load(f2))
    topic_prompt = f"今日の話題は「{kw1}」と「{kw2}」です。"

CHARACTER_PROMPT = f"""
あなたは{config['character']}です。
特徴: {', '.join(config['traits'])}
絵柄: {config['style_hint']}
感情表現: {config['mood']}
このキャラクターとして、140文字以内で今日も頑張るフォロワーに優しく声をかけてください。
{topic_prompt}
"""

# ツイート文生成
openai.api_key = os.getenv("OPENAI_API_KEY")
chat_response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": CHARACTER_PROMPT},
        {"role": "user", "content": "今日のツイートを作って"}
    ]
)
tweet_text = chat_response["choices"][0]["message"]["content"]

# 画像生成
dalle_prompt = (
    f"前髪あり＋サイドに結んだ黒髪ポニーテール、太めの眼鏡、"
    f"切り抜き文字型のAI髪飾り、赤いリボンの制服姿のAI学級委員長のデフォルメアニメ風イラスト。"
    f"今日のテーマは「{kw1}」と「{kw2}」。それを反映したイメージを描いてください。"
)
image_response = openai.Image.create(
    prompt=dalle_prompt,
    n=1,
    size="512x512",
    response_format="b64_json"
)
image_b64 = image_response["data"][0]["b64_json"]
image_data = base64.b64decode(image_b64)

# 保存
today = datetime.now().strftime("%Y%m%d%H%M%S")
image_path = f"images/image_{today}.jpg"
image = Image.open(BytesIO(image_data)).convert("RGB")
image.save(image_path, "JPEG", quality=85)

# GitHub Pagesへ追加コミット
subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"])
subprocess.run(["git", "config", "--global", "user.name", "AI Class Bot"])
subprocess.run(["git", "add", image_path])
subprocess.run(["git", "commit", "-m", f"Add image {image_path}"])
subprocess.run(["git", "push"])

# 投稿用URL付きツイート作成
repo_url = os.getenv("REPO_URL")
image_url = f"{repo_url}/images/image_{today}.jpg"
tweet_with_url = f"{tweet_text}
{image_url}"

# POST /2/tweets
bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
}
payload = { "text": tweet_with_url }
response = requests.post("https://api.twitter.com/2/tweets", headers=headers, json=payload)

if response.status_code in (200, 201):
    print("✅ ツイート投稿成功")
else:
    print("❌ ツイート投稿失敗:", response.status_code, response.text)
