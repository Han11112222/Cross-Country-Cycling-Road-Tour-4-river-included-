# app.py — Cross-Country Cycling Road (국토종주 자전거길) 지도 시각화

import json
import pandas as pd
import streamlit as st
import pydeck as pdk

st.set_page_config(page_title="국토종주 자전거길 지도", layout="wide")


# -------------------- 데이터 로딩 --------------------
@st.cache_data(show_spinner=True)
def load_route_csv(csv_path: str) -> pd.DataFrame:
    """국토종주 자전거길 노선 좌표 CSV 로드 및 정리"""
    # 한글 파일이므로 cp949 우선
    df_local = pd.read_csv(csv_path, encoding="cp949")

    # 공백 제거
    df_local.columns = [c.strip() for c in df_local.columns]

    # 필요한 컬럼 이름 가정:
    # ["순서", "국토종주 자전거길", "위도(LINE_XP)", "경도(LINE_YP)"]
    # 숫자형으로 강제 변환
    if "순서" in df_local.columns:
        df_local["순서"] = pd.to_numeric(df_local["순서"], errors="coerce")

    if "국토종주 자전거길" in df_local.columns:
        df_local["국토종주 자전거길"] = pd.to_numeric(
            df_local["국토종주 자전거길"], errors="coerce"
        ).astype("Int64")

    df_local["위도(LINE_XP)"] = pd.to_numeric(
        df_local["위도(LINE_XP)"], errors="coerce"
    )
    df_local["경도(LINE_YP)"] = pd.to_numeric(
        df_local["경도(LINE_YP)"], errors="coerce"
    )

    # pydeck에서 쓰기 편하게 lat/lon 컬럼 추가
    df_local["lat"] = df_local["위도(LINE_XP)"]
    df_local["lon"] = df_local["경도(LINE_YP)"]

    # 위경도 없는 건 제거
    df_local = df_local.dropna(subset=["lat", "lon"])

    return df_local


def build_geojson(df: pd.DataFrame) -> dict:
    """
    각 '국토종주 자전거길' 코드별로 LineString GeoJSON 생성
    coordinates: [경도, 위도]
    """
    features = []

    for route_id, g in df.groupby("국토종주 자전거길"):
        g_sorted = g.sort_values("순서")
        coords = g_sorted[["lon", "lat"]].dropna().values.tolist()
        if len(coords) < 2:
            continue

        feature = {
            "type": "Feature",
            "properties": {
                "route_id": int(route_id)
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

if df.empty:
    st.error("CSV에서 데이터를 불러올 수 없었어. 컬럼 이름이나 인코딩을 한 번 확인해줘.")
    st.stop()

route_ids = sorted(df["국토종주 자전거길"].dropna().unique().tolist())
default_routes = route_ids  # 처음엔 전체 선택

selected_routes = st.sidebar.multiselect(
    "표시할 국토종주 자전거길 코드",
    options=route_ids,
    default=default_routes,
)

line_width = st.sidebar.slider("라인 두께", 1, 10, value=4)
zoom_level = st.sidebar.slider("초기 줌 레벨", 5, 12, value=7)


# -------------------- 데이터 필터링 / GeoJSON --------------------
if not selected_routes:
    st.warning("왼쪽에서 최소 한 개 이상의 자전거길 코드를 선택해줘.")
    st.stop()

filtered = df[df["국토종주 자전거길"].isin(selected_routes)].copy()

if filtered.empty:
    st.warning("선택한 자전거길 코드에 해당하는 좌표가 없어.")
    st.stop()

geojson_obj = build_geojson(filtered)

# 중심점 계산 (숫자로 변환된 lat/lon 기준)
valid_center = filtered[["lat", "lon"]].dropna()
if valid_center.empty:
    st.error("위도/경도 값이 모두 NaN이라 중심점을 계산할 수 없어.")
    st.stop()

center_lat = float(valid_center["lat"].mean())
center_lon = float(valid_center["lon"].mean())


# -------------------- pydeck 레이어 --------------------
geojson_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_obj,
    pickable=True,
    stroked=True,
    filled=False,
    get_line_color="[0, 128, 255]",
    get_line_width=line_width,
)

point_layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered,
    get_position='[lon, lat]',
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
    map_style="mapbox://styles/mapbox/outdoors-v12",
)

# -------------------- 화면 출력 --------------------
st.title("🚴‍♂️ 국토종주 자전거길 노선 지도")

st.caption(
    f"CSV 파일: `{data_path}` | 선택된 자전거길 코드: {', '.join(map(str, selected_routes))}"
)

st.pydeck_chart(deck, use_container_width=True)

# GeoJSON 다운로드
geojson_str = json.dumps(geojson_obj, ensure_ascii=False, indent=2)
st.download_button(
    "⬇️ 현재 선택된 노선 GeoJSON 다운로드",
    data=geojson_str,
    file_name="cross_country_routes.geojson",
    mime="application/geo+json",
)

# 원본 데이터 확인용
with st.expander("원본 좌표 데이터 보기"):
    st.dataframe(filtered.reset_index(drop=True), use_container_width=True)
