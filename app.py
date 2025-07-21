import streamlit as st
from streamlit_webrtc import webrtc_stream, WebRtcMode, RTCConfiguration
from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
import os
import collections
import time

# --- Google Cloud 인증 정보 설정 ---
# 1. 로컬에서 실행할 경우: 다운로드 받은 서비스 계정 JSON 키 파일 경로 지정
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/your/google_cloud_key.json"

# 2. Streamlit Cloud에 배포할 경우: Streamlit Secrets를 사용하여 설정
#    (secrets.toml 파일에 google_credentials_json = '{"type": "service_account", ...}' 형태로 저장)
#    st.secrets["google_credentials_json"] 값을 사용하여 인증합니다.
try:
    if "google_credentials_json" in st.secrets:
        # Streamlit Secrets에서 인증 정보 로드
        import json
        credentials_json = json.dumps(st.secrets["google_credentials_json"])
        with open("google_credentials.json", "w") as f:
            f.write(credentials_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"
    elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        st.error("Google Cloud 인증 정보가 설정되지 않았습니다. "
                 "Streamlit Secrets 또는 환경 변수를 확인해주세요.")
        st.stop() # 앱 실행 중단
except Exception as e:
    st.error(f"Google Cloud 인증 정보 로드 중 오류 발생: {e}")
    st.stop()

# --- Streamlit UI 설정 ---
st.set_page_config(page_title="실시간 대화 도우미", layout="wide")
st.title("🗣️ 실시간 대화 도우미")
st.markdown("상대방의 말을 실시간 자막으로 보고 뉘앙스까지 확인하세요.")

# --- Google Cloud Speech-to-Text 클라이언트 초기화 ---
client = speech.SpeechClient()

# 스트리밍 요청 설정
# 샘플 레이트는 streamlit-webrtc의 기본값인 16000Hz에 맞춰줍니다.
config = speech.RecognitionConfig(
    encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,
    language_code="ko-KR",  # 한국어 설정
    enable_automatic_punctuation=True,  # 자동 구두점 추가
    enable_word_time_offsets=True,  # 단어별 시간 오프셋 (뉘앙스 분석에 활용 가능)
    use_enhanced=True,  # 향상된 모델 사용 (정확도 향상)
)

streaming_config = speech.StreamingRecognitionConfig(
    config=config,
    interim_results=True,  # 중간 결과 표시
)

# --- 뉘앙스 분석 함수 ---
def analyze_nuance(text, words_info):
    # 간단한 규칙 기반 뉘앙스 분석 (개선 필요)
    if text.endswith("?"):
        return f"<span style='background-color:#FFFACD;'>**{text}** (질문)</span>"
    elif text.endswith("!"):
        return f"<span style='background-color:#E0FFFF;'>**{text}** (확신/동의)</span>"
    elif "응" in text and text.strip() == "응": # '응' 단독 사용 시
        # 더 복잡한 뉘앙스 분석 (예: 이전 대화 맥락, 음성 특징)이 필요하지만,
        # 여기서는 구두점 기반으로만 처리합니다.
        return f"**{text}** (뉘앙스 파악 중)"
    return text

# --- 실시간 자막 및 뉘앙스 표시 영역 ---
st.markdown("---")
st.subheader("실시간 대화 자막")
current_transcript_placeholder = st.empty()  # 중간 결과를 표시할 영역
final_transcript_container = st.container()  # 최종 결과를 누적 표시할 영역

# 이전 최종 결과들을 저장할 리스트
final_transcripts = collections.deque(maxlen=10) # 최근 10개만 저장

# --- Streamlit WebRTC 스트림 처리 ---
# WebRTC 설정 (STUN 서버는 NAT traversal을 위해 필요)
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

st.info("시작 버튼을 클릭하고 마이크 권한을 허용해주세요.")
st.caption("참고: Chrome 브라우저에서 가장 잘 작동합니다.")

webrtc_ctx = webrtc_stream(
    key="speech-to-text-stream",
    mode=WebRtcMode.SENDONLY,  # 오디오만 전송
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": False, "audio": True},  # 비디오 비활성화, 오디오 활성화
    audio_receiver_size=2048,  # 오디오 버퍼 크기
    desired_playing_state={"playing": True}, # 시작과 동시에 오디오 스트림 재생 시도
)

# 오디오 수신 및 STT 처리
if webrtc_ctx.audio_receiver:
    st.success("마이크에서 음성 데이터를 수신 중입니다. 말씀해주세요...")

    # Google Speech-to-Text API의 스트리밍 요청을 위한 제너레이터
    # 오디오 프레임을 받아서 API로 전송하는 역할
    def request_generator(audio_receiver):
        # API 스트리밍 세션 유지 시간
        # Google Speech-to-Text API는 단일 스트리밍 요청당 약 60초의 제한이 있습니다.
        # 이를 초과하면 새 스트리밍 세션을 시작해야 합니다.
        # 여기서는 계속해서 오디오를 받아서 보내는 방식으로 처리합니다.
        
        while webrtc_ctx.state.playing: # 웹캠이 활성화되어 있는 동안 계속 실행
            try:
                # audio_receiver에서 오디오 프레임을 가져옵니다.
                # get_queued_frames()는 pydub.AudioSegment 객체 리스트를 반환합니다.
                audio_frames = audio_receiver.get_queued_frames(timeout=1) # 1초 대기

                if audio_frames:
                    # pydub AudioSegment 리스트를 LINEAR16 (RAW) 오디오 바이트로 변환
                    # Google Speech-to-Text API는 16-bit signed, little-endian, mono 오디오를 기대합니다.
                    # streamlit-webrtc는 기본적으로 16KHz, 1채널, 16bit 인코딩을 사용합니다.
                    audio_bytes = b"".join([frame.to_ndarray().tobytes() for frame in audio_frames])
                    
                    yield speech.StreamingRecognizeRequest(audio_content=audio_bytes)
                else:
                    # 오디오 프레임이 없으면 잠시 대기하여 CPU 사용량 줄임
                    time.sleep(0.01)

            except Exception as e:
                st.warning(f"오디오 프레임 처리 중 오류 발생: {e}")
                break # 오류 발생 시 루프 종료

    while webrtc_ctx.state.playing:
        try:
            # 새로운 스트리밍 세션 시작 (60초 제한 고려)
            requests = request_generator(webrtc_ctx.audio_receiver)
            responses = client.streaming_recognize(streaming_config, requests)

            for response in responses:
                if not response.results:
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript
                words_info = result.alternatives[0].words

                # 뉘앙스 분석 및 표시
                display_text = analyze_nuance(transcript, words_info)
                current_transcript_placeholder.markdown(f"### {display_text}")

                if result.is_final:
                    # 최종 결과를 final_transcripts에 추가하고 표시 업데이트
                    final_transcripts.appendleft(f"- {display_text}")
                    with final_transcript_container:
                        st.markdown("<hr>", unsafe_allow_html=True) # 구분선
                        for t in final_transcripts:
                            st.markdown(t, unsafe_allow_html=True)
                    current_transcript_placeholder.empty() # 최종 결과 표시 후 임시 자막 초기화
                    break # 현재 스트리밍 세션의 최종 결과가 나오면 새 세션을 시작
        except Exception as e:
            st.error(f"음성 인식 스트림 오류: {e}")
            st.warning("잠시 후 다시 시도합니다...")
            time.sleep(2) # 오류 발생 시 잠시 대기 후 재시도

else:
    st.warning("마이크 스트림을 시작할 수 없습니다. 브라우저 권한을 확인해주세요.")
