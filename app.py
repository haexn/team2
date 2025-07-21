# app.py (메인 Streamlit 앱 파일)

import streamlit as st
import pyaudio
import wave
from google.cloud import speech_v1p1beta1 as speech # 뉘앙스 분석을 위해 v1p1beta1 사용 고려
from google.cloud.speech_v1p1beta1 import enums
import os
import io

# Google Cloud 인증 정보 설정 (환경 변수 또는 직접 파일 경로 지정)
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/your/google_cloud_key.json"

# --- 1. Streamlit UI 설정 ---
st.set_page_config(page_title="실시간 대화 도우미", layout="wide")
st.title("🗣️ 실시간 대화 도우미")
st.write("상대방의 말을 실시간 자막으로 보고 뉘앙스까지 확인하세요.")

# --- 2. 오디오 스트림 설정 (PyAudio) ---
# PyAudio 설정 (샘플 레이트, 채널 등)
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000 # 음성 인식에 적합한 샘플 레이트

# --- 3. Google Cloud Speech-to-Text 클라이언트 초기화 ---
client = speech.SpeechClient()

# 스트리밍 요청 설정 (뉘앙스 분석을 위해 enable_automatic_punctuation, enable_word_time_offsets, language_code_override 등 활용)
config = speech.RecognitionConfig(
    encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=RATE,
    language_code="ko-KR", # 한국어 설정
    enable_automatic_punctuation=True, # 자동 구두점 추가
    enable_word_time_offsets=True, # 단어별 시간 오프셋 (뉘앙스 분석에 활용 가능)
    # model="default", # 또는 "enhanced" 모델 사용 고려
    use_enhanced=True, # 향상된 모델 사용
)

streaming_config = speech.StreamingRecognitionConfig(
    config=config,
    interim_results=True, # 중간 결과 표시
)

# --- 4. 실시간 음성 인식 및 뉘앙스 분석 함수 ---
def listen_and_transcribe():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    st.info("말씀해주세요...")
    placeholder = st.empty() # 실시간 자막을 업데이트할 placeholder

    requests = (speech.StreamingRecognizeRequest(audio_content=audio_chunk)
                for audio_chunk in generate_audio_chunks(stream))
    responses = client.streaming_recognize(streaming_config, requests)

    # 뉘앙스 분석을 위한 간단한 로직 (예시)
    def analyze_nuance(text, words_info):
        # 여기에 뉘앙스를 분석하는 복잡한 로직을 추가합니다.
        # 예를 들어, 특정 단어의 억양(pitch), 음량(volume) 변화,
        # 문장 끝의 구두점 등을 분석하여 뉘앙스를 추론할 수 있습니다.
        # '응?'과 '응!'을 구분하는 예시:
        if text.endswith("?"):
            return f"**{text}** (질문)"
        elif text.endswith("!"):
            return f"**{text}** (확신/동의)"
        elif "응" in text:
            # '응'이라는 단어가 포함되었을 때 추가적인 분석 필요
            # Google Cloud Speech-to-Text의 억양/감정 정보는 직접 제공되지 않으므로,
            # 별도의 NLP 라이브러리(예: KoBERT 기반 감성 분석 모델)를 연동해야 합니다.
            return f"**{text}** (뉘앙스 분석 필요)"
        return text # 기본 텍스트 반환

    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript
        words_info = result.alternatives[0].words # 단어별 정보 (시간 오프셋 등)

        display_text = analyze_nuance(transcript, words_info)
        placeholder.markdown(f"### {display_text}") # 자막 업데이트

        if result.is_final:
            st.success(f"최종 결과: {display_text}")
            # 여기에 최종 결과에 대한 추가 처리 로직을 넣을 수 있습니다.

    stream.stop_stream()
    stream.close()
    p.terminate()

def generate_audio_chunks(stream):
    while True:
        data = stream.read(CHUNK)
        yield data

# --- 5. 앱 실행 버튼 ---
if st.button("실시간 대화 시작"):
    listen_and_transcribe()
