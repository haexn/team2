import streamlit as st
import random

# 가상의 감정 데이터셋 정의
# 실제 AI 모델이 없는 상태에서 데모를 위해 특정 텍스트에 대해 미리 정의된 감정 점수를 사용합니다.
virtual_emotion_data = {
    "나는 오늘 정말 행복해!": {"행복": 0.9, "놀람": 0.05, "중립": 0.05},
    "정말 지루한 회의였어.": {"지루함": 0.7, "짜증": 0.2, "중립": 0.1},
    "이거 정말 좋아.": {"행복": 0.7, "중립": 0.2, "놀람": 0.1}, # 진심인 경우
    "이거 정말 좋아. (비꼬는 말투)": {"비꼬는": 0.8, "짜증": 0.1, "중립": 0.1}, # 비꼬는 경우
    "아, 정말 짜증나!": {"분노": 0.8, "짜증": 0.15, "슬픔": 0.05},
    "믿을 수가 없어!": {"놀람": 0.85, "기쁨": 0.1, "중립": 0.05},
    "너무 슬퍼.": {"슬픔": 0.9, "중립": 0.1},
    "오늘 날씨가 좋네요.": {"중립": 0.9, "행복": 0.1},
    "그는 정말 잘했어.": {"칭찬": 0.8, "행복": 0.1, "중립": 0.1},
    "정말 끔찍했어.": {"혐오": 0.7, "슬픔": 0.2, "분노": 0.1},
    "나는 아무렇지도 않아.": {"중립": 0.95, "슬픔": 0.05},
    "이건 완벽해!": {"행복": 0.85, "놀람": 0.1, "칭찬": 0.05},
    "제발 그만해.": {"짜증": 0.7, "분노": 0.2, "슬픔": 0.1},
}

def analyze_emotion(text):
    """
    가상의 감정 데이터셋을 사용하여 감정을 분석하는 함수.
    실제 AI 모델 대신 미리 정의된 데이터를 사용합니다.
    """
    if not text.strip():
        return {}

    # 입력 텍스트가 가상 데이터셋에 있는지 확인
    for key, emotions in virtual_emotion_data.items():
        if text.strip().lower() == key.lower():
            return dict(sorted(emotions.items(), key=lambda item: item[1], reverse=True))

    # 가상 데이터셋에 없는 경우, 일반적인 중립 또는 무작위 감정 반환 (선택 사항)
    # 여기서는 "중립"을 기본으로 하되, 약간의 무작위성을 추가합니다.
    st.warning("입력된 텍스트에 대한 가상의 감정 데이터가 없습니다. '중립' 감정으로 처리됩니다.")
    
    # 더 많은 감정 유형을 포함하고 싶다면 아래 리스트를 확장하세요.
    all_possible_emotions = ["행복", "슬픔", "분노", "놀람", "혐오", "두려움", "중립", "비꼬는", "지루함", "짜증", "칭찬"]
    
    # 중립 감정 위주로 무작위 점수 생성
    simulated_emotions = {"중립": 0.7 + random.random() * 0.2} # 0.7 ~ 0.9
    remaining_score = 1.0 - simulated_emotions["중립"]
    
    other_emotions = [e for e in all_possible_emotions if e != "중립"]
    if other_emotions:
        num_other_emotions = min(len(other_emotions), 3) # 최대 3가지 다른 감정 추가
        random.shuffle(other_emotions)
        
        scores_for_others = [random.random() for _ in range(num_other_emotions)]
        total_other_scores = sum(scores_for_others)
        
        for i in range(num_other_emotions):
            emotion = other_emotions[i]
            simulated_emotions[emotion] = scores_for_others[i] / total_other_scores * remaining_score
            
    return dict(sorted(simulated_emotions.items(), key=lambda item: item[1], reverse=True))


st.set_page_config(page_title="AI 기반 감정 분석 문자 번역기", layout="centered")

st.markdown("""
<style>
.main-header {
    font-size: 2.5em;
    color: #4CAF50;
    text-align: center;
    margin-bottom: 20px;
}
.subheader {
    font-size: 1.2em;
    color: #555;
    text-align: center;
    margin-bottom: 30px;
}
.emotion-score {
    font-weight: bold;
    color: #333;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🧠 AI 기반 감정 분석 문자 번역기</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">상대방의 표정이나 말투를 AI가 분석해 감정을 텍스트로 표시합니다.</p>', unsafe_allow_html=True)

st.write("---")

st.header("텍스트 입력 및 감정 분석")
user_input = st.text_area(
    "분석할 텍스트를 입력하세요 (가상 데이터 예시를 참고하세요):",
    height=150,
    placeholder="예: '나는 오늘 정말 행복해!', '이거 정말 좋아.', '이거 정말 좋아. (비꼬는 말투)', '정말 지루한 회의였어.'"
)

if st.button("감정 분석하기"):
    if user_input:
        st.info("분석 중입니다...")
        emotions = analyze_emotion(user_input)

        if emotions:
            st.subheader("분석 결과:")
            st.write("입력된 텍스트의 주요 감정:")
            
            # Display primary emotion
            primary_emotion = list(emotions.keys())[0]
            primary_score = emotions[primary_emotion]
            st.success(f"**{primary_emotion}**: {primary_score:.2f}")

            st.write("---")
            st.write("모든 감정 점수:")
            for emotion, score in emotions.items():
                st.write(f"- <span class='emotion-score'>{emotion}</span>: {score:.2f}", unsafe_allow_html=True)
        else:
            st.warning("분석할 텍스트가 없습니다. 텍스트를 입력해주세요.")
    else:
        st.warning("텍스트를 입력하고 '감정 분석하기' 버튼을 눌러주세요.")

st.write("---")

st.markdown("""
### 🌟 주요 기능 및 특징:
* **기능:** 상대방의 표정이나 말투를 AI가 분석해 감정을 텍스트로 표시합니다.
* **기술:** 음성 톤 분석, 표정 인식, 감정 분석 NLP (이 데모에서는 텍스트 NLP만 시뮬레이션).
* **특징:**
    * 상대의 '기분'이나 '뉘앙스'를 이해하는 데 도움을 줍니다.
    * 예: "좋아"라는 말이 '진심'인지, '비꼬는지' 등 해석.
* **유용성:** 청각뿐 아니라 감정 이해의 어려움을 보완합니다.
""")

st.markdown("---")
st.caption("이 웹 앱은 AI 기반 감정 분석 문자 번역기의 개념을 보여주기 위한 데모입니다. 실제 AI 모델 통합이 필요하며, 현재는 가상의 데이터로 작동합니다.")
