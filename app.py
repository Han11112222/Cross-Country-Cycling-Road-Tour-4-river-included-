import pandas as pd
import numpy as np
import streamlit as st
import pydeck as pdk

st.set_page_config(page_title="국토종주 자전거길 지도", layout="wide")

# ---------------- 데이터 로드 ----------------
@st.cache_data
def load_data():
    # 같은 폴더에 있는 CSV 사용
    df = pd.read_csv("★국토종주 자전거길 노선좌표.csv", encoding="cp949")

    # 위도/경도 숫자로 변환 (문자 섞여 있어도 에러 나지 않게)
    df["위도"] = pd.to_numeric(df["위도(LINE_XP)"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도(LINE_YP)"], errors="coerce")

    # 위도/경도 없는 행은 제거
    df = df.dropna(subset=["위도", "경도"]).copy()

    # 노선코드 + 순서 기준 정렬
    df = df.sort_values(["국토종주 자전거길", "순서"])
    return df

df = load_data()

# ---------------- 노선 계층 구조 ----------------
# 지금은 CSV에 이름 정보가 없으니, 예시 이름으로만 구성
# -> 실제로는 여기 이름을 "낙동강길", "안동댐~상주상풍교" 등으로 바꾸면 됨
ROUTE_HIERARCHY = {
    "국토종주길": {
        "노선 1": {"전체 구간": [1]},
        "노선 2": {"전체 구간": [2]},
        "노선 3": {"전체 구간": [3]},
        "노선 4": {"전체 구간": [4]},
        "노선 5": {"전체 구간": [5]},
        "노선 6": {"전체 구간": [6]},
        "노선 7": {"전체 구간": [7]},
        "노선 8": {"전체 구간": [8]},
    }
}

# ---------------- 사이드바 UI ----------------
st.sidebar.header("설정")

# 대분류
big_options = list(ROUTE_HIERARCHY.keys())
big_choice = st.sidebar.selectbox("대분류", big_options, index=0)

# 중분류(노선)
mid_options = list(ROUTE_HIERARCHY[big_choice].keys())
mid_choice = st.sidebar.selectbox("중분류 (노선 선택)", mid_options)

# 소분류(구간)
small_options = list(ROUTE_HIERARCHY[big_choice][mid_choice].keys())
small_choice = st.sidebar.selectbox("소분류 (구간 선택)", small_options)

# 선택된 항목이 포함하는 노선 코드들
selected_codes = set(ROUTE_HIERARCHY[big_choice][mid_choice][small_choice])

# 스타일 조절
line_width = st.sidebar.slider("라인 두께(선택 노선)", 1, 20, 8)
zoom_level = st.sidebar.slider("초기 줌 레벨", 4, 16, 7)

# ---------------- PathLayer용 데이터 만들기 ----------------
def make_paths(_df: pd.DataFrame) -> pd.DataFrame:
    paths = (
        _df.groupby("국토종주 자전거길")
        .apply(lambda g: g[["경도", "위도"]].to_numpy().tolist())
        .reset_index(name="path")
    )
    return paths

paths_all = make_paths(df)
paths_selected = paths_all[paths_all["국토종주 자전거길"].isin(selected_codes)].copy()

# 지도 중심은 전체 데이터 평균 위치로
center_lat = float(df["위도"].mean())
center_lon = float(df["경도"].mean())

# ---------------- 레이어 정의 ----------------
# 전체 노선(연한 회색)
base_layer = pdk.Layer(
    "PathLayer",
    data=paths_all,
    get_path="path",
    get_color=[180, 180, 180, 80],  # 연한 회색
    width_scale=1,
    width_min_pixels=1,
    pickable=False,
)

# 선택한 노선(진하게 표시)
highlight_layer = pdk.Layer(
    "PathLayer",
    data=paths_selected,
    get_path="path",
    get_color=[255, 69, 0, 200],  # 진한 주황/빨강
    width_scale=1,
    width_min_pixels=line_width,
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=zoom_level,
    pitch=40,
    bearing=0,
)

deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/outdoors-v12",
    initial_view_state=view_state,
    layers=[base_layer, highlight_layer],
    tooltip={"text": "노선 코드: {국토종주 자전거길}"},
)

# ---------------- 메인 화면 ----------------
st.title("국토종주 자전거길 지도 시각화")
st.caption("회색: 전체 국토종주 노선 / 주황색: 선택한 노선(대·중·소분류 선택 결과)")

st.pydeck_chart(deck)
