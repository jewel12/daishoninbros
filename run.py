import threading
import time
from openai import OpenAI
import re
import base64
import io
from io import BytesIO
import streamlit as st
from streamlit_webrtc import webrtc_streamer

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

openai_client = OpenAI()
ctx = {
    "frame_img": None,
    "frame_img_lock": threading.Lock(),
}
brother_voices = {
    "アドン": "fable",
    "サムソン": "echo"
}

def camera_cb(frame):
    with ctx["frame_img_lock"]:
        ctx["frame_img"] = frame.to_image()
    return frame

def generate_praises(client, img):
    buf = BytesIO()
    img.save(buf, "jpeg")
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
    pt = r"(アドン|サムソン):(.+?)(?=\n|$)"
    matches = re.findall(pt, response.choices[0].message.content)
    return {name: speech for name, speech in matches}

def play_praise(client, voice, msg):
    adon_response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=msg,
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


def run_brothers():
    camera = webrtc_streamer(key="camera", video_frame_callback=camera_cb)
    while camera.state.playing:
        with ctx["frame_img_lock"]:
            img = ctx["frame_img"]
        if img is None:
            continue

        praises = generate_praises(openai_client, img)

        text_st = st.empty()

        for brother, msg in praises.items():
            with st.chat_message(brother):
                st.text(msg)
                play_praise(openai_client, brother_voices[brother], praises[brother])
                time.sleep(3) # 音声があんまり被らないように適当に待つ

        time.sleep(15)

if __name__ == "__main__":
    run_brothers()