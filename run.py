import threading
import time
from openai import OpenAI
import requests
import re
import base64
import io
import sys
import os
from io import BytesIO
import streamlit as st
from streamlit_webrtc import webrtc_streamer

client = OpenAI()
frame_img_container= {"img": None}
img_lock = threading.Lock()

def camera_cb(frame):
    with img_lock:
        frame_img_container["img"] = frame.to_image()
    return frame

camera_ctx = webrtc_streamer(key="camera", video_frame_callback=camera_cb)

old_img = None

system_msgs = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": """
あなたはアドンとサムソンという２人のキャラクターを演じます。
アドンとサムソンは入力された画像にいる人物について非常にポジティブな褒め言葉をかけてください。

# キャラクターの特徴について

アドンは語尾に「だぜぇ！！！！」をつけることが多いです。
サムソンは「ですね！！！！」を語尾につけることが多いです。

# 褒め言葉の内容について

日本のボディービルダーへの掛け声のようにユニークな褒め言葉にしてください。勢い重視で、あんまり意味が通らなくても良いです。

ボディービルダーへの掛け声にはいくつかパターンがあります。
- 食べ物に例えるパターン
  - 例: 腹筋板チョコ！
  - 例: プロテインにイースト菌混ざってんのかい！
- 場所に例えるパターン
  - 例: 上腕二頭筋ナイス！チョモランマ！
  - 例: 筋肉国宝！ルーブル美術館に展示したい
- 動物に例えるパターン
  - 例: 背中がカブトムシの腹みたい！
  - 例: リクガメかと思ったら大胸筋かい！
- 文化的なものが由来のパターン
  - 例: 筋肉縄文杉！
  - 例: ノーベル筋肉賞！

他にもいろんなものに例えたり、そこに至ったプロセスを勝手に想像して過剰に褒めたりします。あくまでボディービルダーへの掛け声を参考にするだけで、無理やり筋肉に結び付けなくていいです。

# 褒め言葉の出力について

それぞれの褒め言葉は以下のように「名前:褒め言葉」という形式で出力してください。

アドン:背中がカブトムシの腹みたいだぜぇ！！！！
サムソン:リクガメと思ったら大胸筋ですね！！！！
             """
            }
        ]
    }
]

def parse_msg(msg):
    pt = r"(アドン|サムソン):(.+?)(?=\n|$)"
    matches = re.findall(pt, msg)
    return {name: speech for name, speech in matches}

while camera_ctx.state.playing:
    with img_lock:
        img = frame_img_container["img"]
    if img is None:
        continue

    buf = BytesIO()
    img.save(buf, "jpeg")
    container = st.empty()
    base64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
    response = client.chat.completions.create(
        model = "gpt-4-vision-preview",
        messages=[
            *system_msgs,
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_img}"
                        }
                    }
                ]
            }],
        max_tokens=200,
    )
    msg = response.choices[0].message.content
    print(msg)
    praises = parse_msg(msg)
    print(praises)

    text_st = st.empty()

    adon_response = client.audio.speech.create(
        model="tts-1",
        voice="fable",
        input=praises["アドン"],
    )
    b64audio = base64.b64encode(io.BytesIO(adon_response.content).getvalue()).decode("utf-8")
    adon_audio_st = st.empty()
    md = f"""
        <audio controls autoplay="true">
        <source src="data:audio/mp3;base64,{b64audio}" type="audio/mp3">
        </audio>
    """
    adon_audio_st.markdown(
        md,
        unsafe_allow_html=True,
    )

    samson_response = client.audio.speech.create(
        model="tts-1",
        voice="echo",
        input=praises["サムソン"],
    )
    b64audio = base64.b64encode(io.BytesIO(samson_response.content).getvalue()).decode("utf-8")

    time.sleep(3)
    samson_audio_st = st.empty()
    md = f"""
        <audio controls autoplay="true">
        <source src="data:audio/mp3;base64,{b64audio}" type="audio/mp3">
        </audio>
    """
    samson_audio_st.markdown(
        md,
        unsafe_allow_html=True,
    )

    text_st.text(praises)
    time.sleep(15)