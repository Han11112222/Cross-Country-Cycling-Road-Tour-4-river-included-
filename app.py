# app.py  ─ Cross-Country Cycling Road (국토종주 자전거길) 지도 시각화

import json
import pandas as pd
import streamlit as st
import pydeck as pdk

st.set_page_config(page_title="국토종주 자전거길 지도", layout="wide")


# -------------------- 데이터 로딩 --------------------
@st.cache_data(show_spinner=True)
def load_route_csv(csv_path: str) -> pd.DataFrame:
    """국토종주 자전거길 노선 좌표 CSV 로드 (cp949 한글 인코딩)"""
    # 필요하면 utf-8 시도 후 실패 시 cp949로 다시 시도해도 됨
    df_local = pd.read_csv(csv_path, encoding="cp949")
    # 기본 컬럼 이름: 순서, 국토종주 자전거길, 위도(LINE_XP), 경도(LINE_YP)
    # 혹시 공백이 있으면 정리
    df_local.columns = [c.strip() for c in df_local.columns]
    return df_local


def build_geojson(df: pd.DataFrame) -> dict:
    """
    각 '국토종주 자전거길' 코드별로 LineString GeoJSON 생성
    - coordinates: [경도, 위도] 순서
    """
    features = []
    for route_id, g in df.groupby("국토종주 자전거길"):
        g_sorted = g.sort_values("순서")
        coords = g_sorted[["경도(LINE_YP)", "위도(LINE_XP)"]].values.tolist()
        if len(coords) < 2:
            continue

        feature = {
            "type": "Feature",
            "properties": {
                "route_id": int(route_id),
                # 필요하면 여기에 "name": "낙동강 자전거길" 같은 이름 매핑을 나중에 추가
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


# -------------------- 사이드바 UI --------------------
st.sidebar.title("⚙️ 설정")

data_path = "★국토종주 자전거길 노선좌표.csv"
df = load_route_csv(data_path)

route_ids = sorted(df["국토종주 자전거길"].unique().tolist())
default_routes = route_ids  # 처음에는 전부 켜기

selected_routes = st.sidebar.multiselect(
    "표시할 국토종주 자전거길 코드",
    options=route_ids,
    default=default_routes,
    help="나중에 코드 ↔ 실제 노선 이름 매핑을 넣으면 더 보기 좋아져.",
)

line_width = st.sidebar.slider("라인 두께", 1, 10, value=4)
zoom_level = st.sidebar.slider("초기 줌 레벨", 5, 12, value=7)


# -------------------- 데이터 필터링 / GeoJSON 생성 --------------------
if not selected_routes:
    st.warning("왼쪽에서 최소 한 개 이상의 자전거길 코드를 선택해줘.")
    st.stop()

filtered = df[df["국토종주 자전거길"].isin(selected_routes)].copy()

geojson_obj = build_geojson(filtered)

# 중심점 계산 (필터된 데이터 기준)
center_lat = float(filtered["위도(LINE_XP)"].mean())
center_lon = float(filtered["경도(LINE_YP)"].mean())


# -------------------- 지도 레이어 구성 (pydeck) --------------------
geojson_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_obj,
    pickable=True,
    stroked=True,
    filled=False,
    get_line_color="[0, 128, 255]",   # 파란색 계열
    get_line_width=line_width,
)

# 포인트(노선 좌표)도 보고 싶으면 ScatterplotLayer 추가
point_layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered,
    get_position='[`경도(LINE_YP)`, `위도(LINE_XP)`]',
    get_radius=30,
    get_fill_color="[255, 0, 0, 140]",
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=zoom_level,
    pitch=0,
    bearing=0,
)

deck = pdk.Deck(
    layers=[geojson_layer, point_layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>Route ID:</b> {route_id}",
        "style": {"color": "white"},
    },
    map_style="mapbox://styles/mapbox/outdoors-v12",  # 기본 야외 스타일
)

# -------------------- 화면 출력 --------------------
st.title("🚴‍♂️ 국토종주 자전거길 노선 지도 (CSV → GeoJSON 라인시각화)")

st.caption(
    f"CSV 파일: `{data_path}` | 선택된 자전거길 코드: {', '.join(map(str, selected_routes))}"
)

st.pydeck_chart(deck, use_container_width=True)

# GeoJSON 다운받기 (원하면)
geojson_str = json.dumps(geojson_obj, ensure_ascii=False, indent=2)
st.download_button(
    "⬇️ 현재 선택된 노선 GeoJSON 다운로드",
    data=geojson_str,
    file_name="cross_country_routes.geojson",
    mime="application/geo+json",
)

# 원본 데이터 테이블도 하단에 참고용으로 표시
with st.expander("원본 좌표 데이터 보기"):
    st.dataframe(filtered.reset_index(drop=True), use_container_width=True)
