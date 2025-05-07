import openai
import tweepy
import base64
import json
import os
import random

# 設定読み込み
with open("prompt_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# ランダムな話題キーワードを選出
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

# ChatGPTでツイート生成
openai.api_key = os.getenv("OPENAI_API_KEY")
chat_response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": CHARACTER_PROMPT},
        {"role": "user", "content": "今日のツイートを作って"}
    ]
)
tweet_text = chat_response["choices"][0]["message"]["content"]

# DALL·Eプロンプト生成
dalle_prompt = (
    f"前髪あり＋サイドに結んだ黒髪ポニーテール、太めの眼鏡、"
    f"切り抜き文字型のAI髪飾り、赤いリボンの制服姿のAI学級委員長のデフォルメアニメ風イラスト。"
    f"今日のテーマは「{kw1}」と「{kw2}」。それを反映したイメージを描いてください。"
)

# DALL·E画像生成（base64デコード）
image_response = openai.Image.create(
    prompt=dalle_prompt,
    n=1,
    size="1024x1024",
    response_format="b64_json"
)

image_b64 = image_response["data"][0]["b64_json"]
image_data = base64.b64decode(image_b64)
with open("image.png", "wb") as f:
    f.write(image_data)

print("🖼️ image.png のサイズ:", os.path.getsize("image.png"), "bytes")

# Twitter(X) API認証
auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET")
)
api = tweepy.API(auth)

# ツイート投稿
media = api.media_upload("image.png")
api.update_status(status=tweet_text, media_ids=[media.media_id])

print("✅ 投稿完了")
