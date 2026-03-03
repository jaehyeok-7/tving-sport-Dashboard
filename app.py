import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정 (요청한 2줄로만 수정)
st.set_page_config(page_title="스포츠 이탈 위험 조기탐지 대시보드", layout="wide")
st.title("스포츠 이탈 위험 조기탐지 대시보드")

# ----------------------------------------------------------------
# 1. 컬럼 매핑 설정 (내 CSV 컬럼명에 맞춰 여기만 수정하세요)
# ----------------------------------------------------------------
COLMAP = {
    "user_id": "user_id",
    "timestamp": "match_end_time",
    "league": "league",
    "team": "team",
    "match_id": "match_id",
    "watch_time": "watch_time",
    "is_live": "is_live",
    "segment": "segment",
    "risk_label": "risk_label",  # 1: 이탈위험, 0: 유지
    "revisit_24h": "revisit_24h",
    "revisit_72h": "revisit_72h",
    "week_num": "week_num"
}

# ----------------------------------------------------------------
# 2. 샘플 데이터 생성 함수 (CSV 없을 때 실행)
# ----------------------------------------------------------------
@st.cache_data
def generate_sample_data(weeks=20):
    np.random.seed(42)
    data = []

    leagues = ["K-League", "EPL", "NBA", "KBO"]
    teams = {
        "K-League": ["Ulsan", "Jeonbuk", "Seoul"],
        "EPL": ["ManCity", "Arsenal", "Liverpool"],
        "NBA": ["Lakers", "Warriors", "Celtics"],
        "KBO": ["KIA", "삼성", "두산", "롯데"],
    }
    segments = ["열성팬", "가끔보는층", "하이라이트위주", "라이브위주", "시즌만", "이탈위험"]

    start_date = datetime.now() - timedelta(weeks=weeks)

    for w in range(weeks):
        current_week_start = start_date + timedelta(weeks=w)
        # 시즌 여부 결정 (가운데 8주는 비시즌으로 가정)
        is_offseason = 8 <= w <= 12
        num_users = 800 if is_offseason else 1200

        for _ in range(num_users):
            user_id = f"user_{np.random.randint(1, 3000)}"
            league = np.random.choice(leagues)
            team = np.random.choice(teams[league])

            # 비시즌에는 시청시간과 재방문율이 낮아짐
            watch_time = (
                np.random.gamma(shape=2.0, scale=15.0)
                if not is_offseason
                else np.random.gamma(shape=1.0, scale=10.0)
            )
            risk_prob = 0.4 if is_offseason else 0.15
            risk_label = 1 if np.random.random() < risk_prob else 0

            data.append(
                {
                    COLMAP["user_id"]: user_id,
                    COLMAP["timestamp"]: current_week_start + timedelta(days=np.random.randint(0, 7)),
                    COLMAP["league"]: league,
                    COLMAP["team"]: team,
                    COLMAP["match_id"]: f"m_{w}_{np.random.randint(1, 50)}",
                    COLMAP["watch_time"]: watch_time,
                    COLMAP["is_live"]: np.random.choice([1, 0], p=[0.7, 0.3]),
                    COLMAP["segment"]: np.random.choice(segments),
                    COLMAP["risk_label"]: risk_label,
                    COLMAP["revisit_24h"]: 1 if (np.random.random() > 0.6 and not is_offseason) else 0,
                    COLMAP["revisit_72h"]: 1 if (np.random.random() > 0.4 and not is_offseason) else 0,
                    COLMAP["week_num"]: w,
                }
            )

    df = pd.DataFrame(data)
    return df

# 데이터 로드
df = generate_sample_data()

# ----------------------------------------------------------------
# 3. 사이드바 필터
# ----------------------------------------------------------------
st.sidebar.title("🔍 분석 필터")

selected_weeks = st.sidebar.slider("분석 기간 (최근 n주)", 4, 20, 12)
current_week = df[COLMAP["week_num"]].max()
ref_week = st.sidebar.selectbox(
    "기준 주차 선택(최근 1주)",
    options=range(current_week, current_week - selected_weeks, -1)
)

league_filter = st.sidebar.multiselect(
    "리그 선택",
    options=df[COLMAP["league"]].unique(),
    default=df[COLMAP["league"]].unique()
)
team_filter = st.sidebar.multiselect(
    "팀 선택",
    options=df[df[COLMAP["league"]].isin(league_filter)][COLMAP["team"]].unique()
)

# 데이터 필터링 적용
filtered_df = df[
    (df[COLMAP["week_num"]] > (ref_week - selected_weeks)) &
    (df[COLMAP["week_num"]] <= ref_week) &
    (df[COLMAP["league"]].isin(league_filter))
]
if team_filter:
    filtered_df = filtered_df[filtered_df[COLMAP["team"]].isin(team_filter)]

# ----------------------------------------------------------------
# 4. 메인 대시보드 탭 구성
# ----------------------------------------------------------------
tabs = st.tabs(["📊 Overview", "👥 상태분류", "📉 이탈구간", "⏱️ 타이밍", "🧪 액션실험"])

# --- Tab 1: Overview ---
with tabs[0]:
    st.header("스포츠 이탈 위험 조기탐지 대시보드")

    # 상단 KPI
    this_week_df = filtered_df[filtered_df[COLMAP["week_num"]] == ref_week]
    prev_week_df = filtered_df[filtered_df[COLMAP["week_num"]] == ref_week - 1]

    risk_rate = this_week_df[COLMAP["risk_label"]].mean()
    prev_risk_rate = prev_week_df[COLMAP["risk_label"]].mean() if not prev_week_df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("위험군 비율", f"{risk_rate:.1%}", f"{(risk_rate - prev_risk_rate):.1%}", delta_color="inverse")
    col2.metric("24h 재방문율", f"{this_week_df[COLMAP['revisit_24h']].mean():.1%}")
    col3.metric("72h 재방문율", f"{this_week_df[COLMAP['revisit_72h']].mean():.1%}")
    col4.metric("평균 시청 시간", f"{this_week_df[COLMAP['watch_time']].mean():.1f}분")

    # 위험군 추이 라인 차트
    trend_df = filtered_df.groupby(COLMAP["week_num"])[COLMAP["risk_label"]].mean().reset_index()
    fig_trend = px.line(
        trend_df,
        x=COLMAP["week_num"],
        y=COLMAP["risk_label"],
        title="주차별 위험군 비율 추이 (시즌/비시즌)"
    )
    # 비시즌 하이라이트 (8~12주차 예시)
    fig_trend.add_vrect(
        x0=8, x1=12,
        fillcolor="gray", opacity=0.2,
        annotation_text="OFF-SEASON",
        annotation_position="top left"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# --- Tab 2: 상태분류 ---
with tabs[1]:
    st.header("세그먼트별 상세 분석")

    seg_stats = filtered_df.groupby(COLMAP["segment"]).agg({
        COLMAP["user_id"]: "nunique",
        COLMAP["watch_time"]: "mean",
        COLMAP["revisit_24h"]: "mean",
        COLMAP["risk_label"]: "mean"
    }).rename(columns={
        COLMAP["user_id"]: "사용자수",
        COLMAP["watch_time"]: "평균시청시간",
        COLMAP["revisit_24h"]: "24h재방문",
        COLMAP["risk_label"]: "이탈위험도"
    })

    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        fig_pie = px.pie(
            seg_stats.reset_index(),
            values="사용자수",
            names=COLMAP["segment"],
            title="세그먼트 비율"
        )
        st.plotly_chart(fig_pie)

    with col_s2:
        st.dataframe(seg_stats.style.background_gradient(cmap="RdYlGn_r", subset=["이탈위험도"]))

# --- Tab 3: 이탈구간 (Funnel) ---
with tabs[2]:
    st.header("사용자 여정 퍼널 분석")
    st.caption("위험군과 유지군이 어느 단계에서 가장 큰 차이가 나는지 확인합니다.")

    funnel_data = pd.DataFrame({
        "stage": ["유입", "경기진입", "시청(1분+)", "경기종료", "후속탐색", "재방문"],
        "count": [1000, 850, 600, 550, 300, 150],
        "group": "전체"
    })
    funnel_risk = pd.DataFrame({
        "stage": ["유입", "경기진입", "시청(1분+)", "경기종료", "후속탐색", "재방문"],
        "count": [1000, 700, 400, 350, 100, 20],
        "group": "위험군"
    })
    df_funnel = pd.concat([funnel_data, funnel_risk])

    fig_funnel = px.funnel(
        df_funnel,
        x="count",
        y="stage",
        color="group",
        title="유지군 vs 위험군 여정 비교"
    )
    st.plotly_chart(fig_funnel, use_container_width=True)
    st.info("예시 기준으로는 경기 종료 이후 후속 탐색 단계에서 이탈이 크게 나타납니다.")

# --- Tab 4: 타이밍 ---
with tabs[3]:
    st.header("개입 골든타임 분석")
    st.caption("마지막 시청 이후 경과 시간 구간별로 재방문 가능성이 어떻게 달라지는지 확인합니다.")

    timing_data = pd.DataFrame({
        "경과시간": ["0-6h", "6-24h", "24-72h", "72h+"],
        "재방문확률": [0.65, 0.40, 0.15, 0.05]
    })

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        fig_time = px.bar(
            timing_data,
            x="경과시간",
            y="재방문확률",
            color="재방문확률",
            title="마지막 시청 후 경과시간별 재방문 확률"
        )
        st.plotly_chart(fig_time)

    with t_col2:
        heatmap_data = np.random.rand(6, 4)
        fig_heat = px.imshow(
            heatmap_data,
            labels=dict(x="경과시간", y="세그먼트", color="이탈위험"),
            x=["0-6h", "6-24h", "24-72h", "72h+"],
            y=df[COLMAP["segment"]].unique(),
            title="세그먼트별 이탈 피크 타이밍"
        )
        st.plotly_chart(fig_heat)

# --- Tab 5: 액션실험 ---
with tabs[4]:
    st.header("액션 실험 결과")

    st.subheader("A/B 테스트 결과 (Push 알림 유형별)")
    exp_data = pd.DataFrame({
        "실험그룹": ["Control", "통계 기반 알림", "개인화 추천 알림"],
        "클릭률(CTR)": ["2.1%", "3.5%", "5.8%"],
        "72h 재방문율": ["10.2%", "12.5%", "15.8%"]
    })
    st.table(exp_data)

    st.subheader("세그먼트별 액션 가이드(주요 streamlit run app.pyKPI 포함)")

    seg_kpi = (
        filtered_df.groupby(COLMAP["segment"])
        .agg(
            사용자수=(COLMAP["user_id"], "nunique"),
            평균시청시간=(COLMAP["watch_time"], "mean"),
            재방문24h=(COLMAP["revisit_24h"], "mean"),
            재방문72h=(COLMAP["revisit_72h"], "mean"),
            이탈위험도=(COLMAP["risk_label"], "mean"),
        )
        .reset_index()
    )

    action_guide = pd.DataFrame(
        [
            {
                "세그먼트": "열성팬",
                "추천 액션": "개인화 푸시(팀/선수/다음 경기) + 경기 종료 후 6~24h",
                "1차 KPI": "24h 재방문율",
                "2차 KPI": "72h 재방문율, 시청시간",
                "가드레일": "푸시 거부/해지율, 앱 이탈",
            },
            {
                "세그먼트": "가끔보는층",
                "추천 액션": "스포츠 홈 상단 노출 강화 + 하이라이트 묶음 고정",
                "1차 KPI": "클릭률(CTR) 또는 진입률",
                "2차 KPI": "24h 재방문율",
                "가드레일": "홈 이탈률, 세션 길이",
            },
            {
                "세그먼트": "하이라이트위주",
                "추천 액션": "하이라이트 자동재생/연속시청 추천",
                "1차 KPI": "시청시간, 다음 콘텐츠 진입률",
                "2차 KPI": "24h 재방문율",
                "가드레일": "조기 이탈(1~3분 이탈) 증가 여부",
            },
            {
                "세그먼트": "라이브위주",
                "추천 액션": "경기 종료 직후 연관 라이브/리플레이 추천 + 알림 설정 유도",
                "1차 KPI": "알림 설정 전환율",
                "2차 KPI": "72h 재방문율",
                "가드레일": "알림 피로도(차단율)",
            },
            {
                "세그먼트": "시즌만",
                "추천 액션": "비시즌 대체 동선(예능/다큐/선수 콘텐츠) + 주간 리마인드",
                "1차 KPI": "주간 활성(WAU)",
                "2차 KPI": "72h 재방문율",
                "가드레일": "프로모션 비용 대비 효과",
            },
            {
                "세그먼트": "이탈위험",
                "추천 액션": "72h 내 트리거 푸시 + 개인화 추천(가장 좋아한 팀/리그)",
                "1차 KPI": "72h 재방문율",
                "2차 KPI": "이탈위험도 감소",
                "가드레일": "푸시 차단/구독 해지",
            },
        ]
    )

    merged = action_guide.merge(
        seg_kpi,
        left_on="세그먼트",
        right_on=COLMAP["segment"],
        how="left",
    ).drop(columns=[COLMAP["segment"]])

    st.dataframe(merged, use_container_width=True)