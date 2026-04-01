import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="DDD - 危機感ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ダークテーマCSS + レスポンシブ対応
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .metric-card {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        min-height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    /* カラムコンテナの高さを揃える */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    [data-testid="stColumn"] > div:first-child {
        height: 100%;
    }
    [data-testid="stColumn"] > div:first-child > div:first-child {
        height: 100%;
    }
    .summary-card {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 16px;
        text-align: left;
        min-height: 200px;
    }
    .metric-value {
        font-size: 48px;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 14px;
        color: #888;
        margin: 0;
    }
    .metric-sub {
        font-size: 11px;
        color: #555;
        margin: 4px 0 0 0;
    }
    .danger { color: #ff4444; }
    .warning { color: #ffaa00; }
    .info { color: #4488ff; }
    .neutral { color: #cccccc; }
    h1, h2, h3 { color: #ffffff !important; }
    .stMarkdown p { color: #cccccc; }
    .section-desc {
        color: #888;
        font-size: 13px;
        margin: 24px 0 2px 0 !important;
    }

    /* BIG3テーブル */
    .big3-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    .big3-table th {
        color: #888;
        font-size: 11px;
        font-weight: normal;
        text-align: center;
        padding: 8px 4px;
        border-bottom: 1px solid #333;
    }
    .big3-table td {
        color: #ccc;
        text-align: center;
        padding: 10px 4px;
        border-bottom: 1px solid #222;
    }
    .big3-table .exercise-name {
        text-align: left;
        font-weight: bold;
        color: #fff;
    }
    .big3-alert {
        background: #2a1a1a;
        border: 1px solid #ff4444;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 8px;
    }
    .big3-alert-ok {
        background: #1a2a1a;
        border: 1px solid #44ff44;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 8px;
    }

    /* === タブレット（900px以下：iPad縦向き含む） === */
    @media (max-width: 900px) {
        /* カラムを2列に強制 */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 45% !important;
            min-width: 45% !important;
        }
        .metric-value {
            font-size: 36px;
        }
        .metric-label {
            font-size: 12px;
        }
        .metric-card {
            padding: 14px;
        }
        .summary-card {
            min-height: auto;
        }
        h1 { font-size: 24px !important; }
        h3 { font-size: 18px !important; }
        .big3-table { font-size: 12px; }
        .big3-table th { font-size: 10px; padding: 6px 2px; }
        .big3-table td { padding: 8px 2px; }
    }

    /* === スマホ（480px以下） === */
    @media (max-width: 480px) {
        /* セクション間の余白 */
        .section-desc {
            margin: 20px 0 2px 0 !important;
        }
        .summary-card {
            margin-bottom: 8px;
        }
        .metric-card {
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 32px;
        }
        .metric-card .metric-value span {
            font-size: 16px !important;
        }
        .metric-label {
            font-size: 11px;
        }
        .metric-sub {
            font-size: 10px;
        }
        .metric-card {
            padding: 12px;
            margin-bottom: 4px;
        }
        .summary-card {
            min-height: auto;
            padding: 12px;
            margin-bottom: 4px;
        }
        .summary-card p {
            font-size: 13px !important;
        }
        .summary-card .summary-number {
            font-size: 24px !important;
        }
        .summary-card .summary-number span {
            font-size: 14px !important;
        }
        .summary-card p b {
            font-size: 14px !important;
        }
        h1 { font-size: 20px !important; }
        h3 { font-size: 16px !important; }
        .section-desc {
            font-size: 11px;
            margin: 20px 0 2px 0 !important;
        }
        /* Plotlyチャートのタッチ操作改善 */
        .js-plotly-plot .plotly .modebar {
            display: none !important;
        }
        .big3-table { font-size: 11px; }
        .big3-table th { font-size: 9px; padding: 6px 2px; }
        .big3-table td { padding: 6px 2px; }
    }
</style>
""", unsafe_allow_html=True)

# スプシ設定
SPREADSHEET_ID = "1fQOhLu66RDolsWM67qL17D6IZkbnW1x8wJB6Lf2dgK8"

from urllib.parse import quote

def get_sheet_url(sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"

# データ読み込み（スプシから直接）
@st.cache_data(ttl=60)
def load_data():
    url = get_sheet_url("シート1")
    df = pd.read_csv(url, usecols=["日付", "体重(kg)", "体脂肪率(%)", "基礎代謝(kcal)"])
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df = df.dropna(subset=["日付"]).reset_index(drop=True)
    # 計算列を追加
    df["7日移動平均(kg)"] = df["体重(kg)"].rolling(7, min_periods=1).mean()
    df["7日移動平均_体脂肪率(%)"] = df["体脂肪率(%)"].rolling(7, min_periods=1).mean()
    df["7日移動平均_基礎代謝(kcal)"] = df["基礎代謝(kcal)"].rolling(7, min_periods=1).mean()
    min_weight = df["体重(kg)"].expanding().min()
    df["最低体重からの差分(kg)"] = df["体重(kg)"] - min_weight
    return df

@st.cache_data(ttl=60)
def load_training_data():
    """トレーニングログを読み込み"""
    try:
        url = get_sheet_url("トレーニング")
        df = pd.read_csv(url)
        if df.empty or len(df.columns) < 5:
            return pd.DataFrame(columns=["日付", "種目", "重量(kg)", "回数", "セット番号", "消費kcal", "メモ"])
        df["日付"] = pd.to_datetime(df["日付"])
        df["重量(kg)"] = pd.to_numeric(df["重量(kg)"], errors="coerce")
        df["回数"] = pd.to_numeric(df["回数"], errors="coerce")
        df["セット番号"] = pd.to_numeric(df["セット番号"], errors="coerce")
        df["ボリューム"] = df["重量(kg)"] * df["回数"]
        return df
    except Exception:
        return pd.DataFrame(columns=["日付", "種目", "重量(kg)", "回数", "セット番号", "消費kcal", "メモ"])

@st.cache_data(ttl=60)
def load_exercise_master():
    """種目マスタを読み込み"""
    try:
        url = get_sheet_url("種目マスタ")
        df = pd.read_csv(url)
        return df
    except Exception:
        return pd.DataFrame(columns=["種目名", "カテゴリ", "METs", "備考"])

@st.cache_data(ttl=60)
def load_1rm_records():
    """1RM記録を読み込み"""
    try:
        url = get_sheet_url("1RM記録")
        df = pd.read_csv(url)
        if df.empty or len(df.columns) < 3:
            return pd.DataFrame(columns=["日付", "種目", "1RM(kg)"])
        df["日付"] = pd.to_datetime(df["日付"])
        df["1RM(kg)"] = pd.to_numeric(df["1RM(kg)"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=["日付", "種目", "1RM(kg)"])

# === gspread書き込み ===
def get_gspread_client():
    """Streamlit secretsからサービスアカウント認証してgspreadクライアントを取得"""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        return gspread.authorize(creds)
    except Exception:
        return None

def append_training_rows(rows):
    """トレーニングログをスプシに追記。rowsは[[日付, 種目, 重量, 回数, セット番号, 消費kcal, メモ], ...]"""
    gc = get_gspread_client()
    if gc is None:
        return False
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("トレーニング")
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return True

def append_1rm_rows(rows):
    """1RM記録をスプシに追記。rowsは[[日付, 種目, 1RM(kg)], ...]"""
    gc = get_gspread_client()
    if gc is None:
        return False
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("1RM記録")
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return True

@st.cache_data(ttl=60)
def load_nutrition_data():
    """栄養データを読み込み"""
    try:
        url = get_sheet_url("栄養")
        df = pd.read_csv(url)
        if df.empty or len(df.columns) < 7:
            return pd.DataFrame(columns=["日付", "摂取kcal", "P(g)", "F(g)", "C(g)", "安静時消費kcal", "アクティブkcal"])
        df["日付"] = pd.to_datetime(df["日付"])
        for col in ["摂取kcal", "P(g)", "F(g)", "C(g)", "安静時消費kcal", "アクティブkcal"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        # 合計消費kcal（TDEE）を算出
        df["消費kcal"] = df["安静時消費kcal"].fillna(0) + df["アクティブkcal"].fillna(0)
        df.loc[df["消費kcal"] == 0, "消費kcal"] = np.nan
        return df
    except Exception:
        return pd.DataFrame(columns=["日付", "摂取kcal", "P(g)", "F(g)", "C(g)", "安静時消費kcal", "アクティブkcal"])

def append_body_row(row):
    """体重データをスプシに追記。rowは[日付, 体重, 体脂肪率, 基礎代謝]"""
    gc = get_gspread_client()
    if gc is None:
        return False
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("シート1")
    # USER_ENTEREDで日付をシリアル値として保存（既存データと型を合わせる）
    ws.append_rows([row], value_input_option="USER_ENTERED")
    return True

def append_nutrition_row(row):
    """栄養データをスプシに追記。rowは[日付, 摂取kcal, P, F, C, 安静時消費kcal, アクティブkcal]"""
    gc = get_gspread_client()
    if gc is None:
        return False
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("栄養")
    ws.append_rows([row], value_input_option="USER_ENTERED")
    return True

# 更新ボタン
if st.button("🔄 データを更新"):
    st.cache_data.clear()
    st.rerun()

try:
    df = load_data()
except Exception as e:
    st.error(f"スプレッドシートの読み込みに失敗しました。共有設定を確認してください。\n{e}")
    st.stop()
latest = df.iloc[-1]
today = latest["日付"]

# 目標設定（スプシの「設定」シートから読み込み）
PAL_MAP = {
    "在宅ワーク・運動なし": 1.45,
    "座り仕事・軽い運動": 1.55,
    "座り仕事・週3-4回運動": 1.65,
    "活動的・週5回以上運動": 1.75,
}

@st.cache_data(ttl=300)  # 5分キャッシュ
def load_settings():
    try:
        settings_url = get_sheet_url("設定")
        settings_df = pd.read_csv(settings_url)
        latest_setting = settings_df.iloc[-1]
        return latest_setting
    except Exception:
        return None

settings = load_settings()
if settings is not None:
    TARGET_WEIGHT = float(settings.get("目標体重(kg)", 75.0))
    TARGET_FAT = float(settings.get("目標体脂肪率(%)", 15.0))
    TARGET_DATE = pd.to_datetime(settings.get("目標日", "2026/07/31"))
    ACTIVITY_FACTOR_SETTING = PAL_MAP.get(settings.get("活動レベル", ""), 1.45)
else:
    TARGET_WEIGHT = 75.0
    TARGET_FAT = 15.0
    TARGET_DATE = pd.to_datetime("2026/07/31")
    ACTIVITY_FACTOR_SETTING = 1.45
days_left = (TARGET_DATE - today).days

# === ヘッダー ===
st.markdown("# 📊 DataDrivenDiet")
st.markdown(f"<p style='color:#666; font-size:12px;'>最終更新: {today.strftime('%Y/%m/%d')} | データ: {len(df)}日分 | 目標: {TARGET_DATE.strftime('%Y/%m/%d')}まで（残り{days_left}日）</p>", unsafe_allow_html=True)

# === タブ構成 ===
tab_weight, tab_nutrition, tab_training = st.tabs(["⚖️ 体重管理", "🍽️ 栄養管理", "🏋️ トレーニング"])

# ============================================================
# 体重管理タブ
# ============================================================
with tab_weight:
    # === 体重記録フォーム ===
    with st.expander("📝 体重を記録", expanded=False):
        with st.form("body_form"):
            body_date = st.date_input("日付", value=datetime.now().date(), key="body_date")

            # 前回値をプリフィル
            prev_w = float(latest["体重(kg)"]) if pd.notna(latest["体重(kg)"]) else 0.0
            prev_fat = float(latest["体脂肪率(%)"]) if pd.notna(latest["体脂肪率(%)"]) else 0.0
            prev_bmr = float(latest["基礎代謝(kcal)"]) if pd.notna(latest["基礎代謝(kcal)"]) else 0.0

            col_w, col_fat, col_bmr = st.columns(3)
            body_w = col_w.number_input("体重(kg)", value=prev_w, step=0.1, min_value=0.0, format="%.1f", key="body_w")
            body_fat = col_fat.number_input("体脂肪率(%)", value=prev_fat, step=0.1, min_value=0.0, format="%.1f", key="body_fat")
            body_bmr = col_bmr.number_input("基礎代謝(kcal)", value=int(prev_bmr), step=10, min_value=0, key="body_bmr")

            body_submitted = st.form_submit_button("💾 体重データを保存", use_container_width=True)

            if body_submitted:
                date_str = body_date.strftime("%Y/%m/%d")
                row = [date_str, body_w, body_fat, body_bmr]
                try:
                    success = append_body_row(row)
                    if success:
                        st.success("✅ 体重データを保存しました！")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 書き込みに失敗しました。")
                except Exception as e:
                    st.error(f"❌ エラー: {e}")

    # === スコアカード（CSS Grid 2x2） ===
    weight = latest["体重(kg)"]
    diff_to_target = weight - TARGET_WEIGHT
    rebound = latest["最低体重からの差分(kg)"]
    rebound_color = "danger" if rebound > 10 else "warning" if rebound > 5 else "info"

    START_WEIGHT = 105.7
    # 直近30日の7日移動平均に対して線形回帰でトレンド算出（日次diff().mean()より安定）
    _trend_col = "7日移動平均(kg)"
    df_recent_trend = df[df["日付"] > (today - pd.Timedelta(days=30))]
    df_trend_valid = df_recent_trend[df_recent_trend[_trend_col].notna()]
    if len(df_trend_valid) >= 7:
        _x = (df_trend_valid["日付"] - df_trend_valid["日付"].iloc[0]).dt.days.values.astype(float)
        _y = df_trend_valid[_trend_col].values
        daily_trend = np.polyfit(_x, _y, 1)[0]  # 傾き（kg/日）
    else:
        daily_trend = 0

    min_weight = df["体重(kg)"].min()

    if daily_trend > 0.01:
        remaining_to_doom = START_WEIGHT - weight
        doom_days = int(remaining_to_doom / daily_trend)
        card3_color = "danger" if doom_days < 365 else "warning" if doom_days < 1000 else "info"
        card3_label = "破滅カウントダウン"
        card3_value = f'{doom_days}<span style="font-size:20px">日</span>'
        card3_sub = "105.7kgに届くまで"
    elif daily_trend < -0.01:
        remaining_to_min = weight - min_weight
        days_to_min = int(remaining_to_min / abs(daily_trend))
        card3_color = "info" if days_to_min < 90 else "warning" if days_to_min < 180 else "neutral"
        card3_label = "最低体重到達まで"
        card3_value = f'{days_to_min}<span style="font-size:20px">日</span>'
        card3_sub = f"{min_weight:.1f}kgに届くまで"
    else:
        card3_color = "warning"
        card3_label = "トレンド"
        card3_value = "横ばい ➡️"
        card3_sub = "変化なし。行動を変えろ。"

    last_30 = df[df["日付"] > (today - pd.Timedelta(days=30))]
    measured_days = last_30["体重(kg)"].notna().sum()
    skip_days = 30 - measured_days
    skip_rate = (skip_days / 30) * 100
    skip_color = "danger" if skip_rate > 30 else "warning" if skip_rate > 15 else "info"

    rebound_sign = "+" if rebound >= 0 else ""
    rebound_label = "増加" if rebound >= 0 else "減少"

    st.markdown(f"""
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
        <div class="metric-card" style="height:140px;">
            <p class="metric-label">現在の体重</p>
            <p class="metric-value neutral">{weight:.1f}<span style="font-size:20px">kg</span></p>
            <p class="metric-sub">目標体重まで<br>あと {diff_to_target:.1f}kg</p>
        </div>
        <div class="metric-card" style="height:140px;">
            <p class="metric-label">リバウンド</p>
            <p class="metric-value {rebound_color}">{rebound_sign}{rebound:.1f}<span style="font-size:20px">kg</span></p>
            <p class="metric-sub">最低{min_weight:.1f}kgからの<br>{rebound_label}</p>
        </div>
        <div class="metric-card" style="height:140px;">
            <p class="metric-label">{card3_label}</p>
            <p class="metric-value {card3_color}">{card3_value}</p>
            <p class="metric-sub">{card3_sub}</p>
        </div>
        <div class="metric-card" style="height:140px;">
            <p class="metric-label">測定サボり率</p>
            <p class="metric-value {skip_color}">{skip_rate:.0f}<span style="font-size:20px">%</span></p>
            <p class="metric-sub">直近30日中<br>{skip_days}日未測定</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # === 全体サマリー ===
    st.markdown("### 全体サマリー")

    # --- モンテカルロシミュレーション ---
    @st.cache_data
    def run_monte_carlo(weights_series, current_weight, target_weight, days_remaining, n_simulations=5000):
        """直近90日の体重変動パターンから目標達成確率を算出"""
        recent = weights_series.tail(90)
        daily_changes = recent.diff().dropna()
        daily_changes = daily_changes[daily_changes.between(-2, 2)]

        if len(daily_changes) < 14:
            return None, None, None

        mu = daily_changes.mean()
        sigma = daily_changes.std()

        np.random.seed(42)
        simulated_ends = []
        paths = []
        for _ in range(n_simulations):
            path = [current_weight]
            for d in range(days_remaining):
                change = np.random.normal(mu, sigma)
                path.append(path[-1] + change)
            simulated_ends.append(path[-1])
            if len(paths) < 100:
                paths.append(path)

        simulated_ends = np.array(simulated_ends)
        prob = (simulated_ends <= target_weight).mean() * 100
        median_end = np.median(simulated_ends)
        return prob, median_end, paths

    mc_prob, mc_median, mc_paths = run_monte_carlo(
        df["体重(kg)"].dropna(), weight, TARGET_WEIGHT, max(days_left, 1)
    )

    st.markdown("<p class='section-desc'>📌 現状と推移</p>", unsafe_allow_html=True)
    # 直近30日トレンド
    df_30 = df[df["日付"] > (today - pd.Timedelta(days=30))]
    if len(df_30) >= 7:
        trend_30 = df_30["体重(kg)"].dropna()
        weight_change_30 = trend_30.iloc[-1] - trend_30.iloc[0] if len(trend_30) >= 2 else 0
        trend_label = "増加中 📈" if weight_change_30 > 0.5 else "減少中 📉" if weight_change_30 < -0.5 else "横ばい ➡️"
        trend_color = "#ff4444" if weight_change_30 > 0.5 else "#00ff88" if weight_change_30 < -0.5 else "#ffaa00"
    else:
        weight_change_30 = 0
        trend_label = "データ不足"
        trend_color = "#888"

    current_fat = df[df["体脂肪率(%)"].notna()].iloc[-1]["体脂肪率(%)"] if df["体脂肪率(%)"].notna().any() else None
    fat_text = f"体脂肪率: {current_fat:.1f}% （目標{TARGET_FAT:.0f}%）" if current_fat else "体脂肪率: データなし"

    st.markdown(f"""
    <div class="summary-card">
        <p style="color:#ccc; font-size:14px; margin:0;">体重: <b style="color:#fff;">{weight:.1f}kg</b> → 目標 <b style="color:#00ff88;">{TARGET_WEIGHT:.0f}kg</b></p>
        <p style="color:#ccc; font-size:14px; margin:4px 0;">{fat_text}</p>
        <p style="color:#ccc; font-size:14px; margin:4px 0;">30日トレンド: <b style="color:{trend_color};">{weight_change_30:+.1f}kg（{trend_label}）</b></p>
        <p style="color:#ccc; font-size:14px; margin:4px 0;">最低体重からのリバウンド: <b style="color:#ff4444;">+{weight - min_weight:.1f}kg</b></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p class='section-desc'>🔮 予測</p>", unsafe_allow_html=True)
    if mc_median is not None:
        pred_color = "#00ff88" if mc_median <= TARGET_WEIGHT else "#ff4444" if mc_median > weight else "#ffaa00"
        st.markdown(f"""
        <div class="summary-card">
            <p style="color:#ccc; font-size:14px; margin:0;">今のペースが続いた場合</p>
            <p style="color:#ccc; font-size:14px; margin:4px 0;">{TARGET_DATE.strftime('%Y/%m/%d')}時点の予測体重:</p>
            <p class="summary-number" style="color:{pred_color}; font-size:36px; font-weight:bold; margin:8px 0;">{mc_median:.1f}<span style="font-size:16px;">kg</span></p>
            <p style="color:#888; font-size:11px; margin:0;">過去の変動パターンから5,000回シミュレーション</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="summary-card">
            <p style="color:#888;">予測に必要なデータが不足しています。14日以上の測定が必要です。</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<p class='section-desc'>🎯 目標達成確率</p>", unsafe_allow_html=True)
    if mc_prob is not None:
        prob_color = "#00ff88" if mc_prob >= 50 else "#ffaa00" if mc_prob >= 20 else "#ff4444"
        bar_width = max(mc_prob, 2)
        st.markdown(f"""
        <div class="summary-card">
            <p style="color:#ccc; font-size:14px; margin:0;">{TARGET_DATE.strftime('%Y/%m/%d')}までに{TARGET_WEIGHT:.0f}kg達成</p>
            <p class="summary-number" style="color:{prob_color}; font-size:48px; font-weight:bold; margin:8px 0;">{mc_prob:.1f}<span style="font-size:20px;">%</span></p>
            <div style="background:#333; border-radius:4px; height:8px; margin:8px 0;">
                <div style="background:{prob_color}; border-radius:4px; height:8px; width:{bar_width}%;"></div>
            </div>
            <p style="color:#888; font-size:11px; margin:0;">{"今のままでは厳しい。行動を変えろ。" if mc_prob < 20 else "可能性はある。ペースを上げろ。" if mc_prob < 50 else "いいペース。維持しろ。"}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="summary-card">
            <p style="color:#888;">確率算出に必要なデータが不足しています。</p>
        </div>
        """, unsafe_allow_html=True)

    # --- 目標達成に必要なアクション ---
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown("### 🎯 目標達成に必要なアクション")
    st.markdown("<p class='section-desc'>エビデンスベースの減量科学とあなたのデータから逆算。</p>", unsafe_allow_html=True)

    required_loss = weight - TARGET_WEIGHT
    required_weekly = required_loss / max(days_left / 7, 1)
    required_daily_deficit = (required_loss * 7200) / max(days_left, 1)

    current_bmr_val = df[df["基礎代謝(kcal)"].notna()].iloc[-1]["基礎代謝(kcal)"] if "基礎代謝(kcal)" in df.columns and df["基礎代謝(kcal)"].notna().any() else None
    current_fat = df[df["体脂肪率(%)"].notna()].iloc[-1]["体脂肪率(%)"] if df["体脂肪率(%)"].notna().any() else None

    # 体脂肪率に応じた安全減量ペース判定
    if current_fat and current_fat > 20:
        safe_weekly_pct = 0.85
    elif current_fat and current_fat > 15:
        safe_weekly_pct = 0.6
    else:
        safe_weekly_pct = 0.4
    safe_weekly_kg = weight * safe_weekly_pct / 100

    # --- データから優先度判定 ---
    ACTIVITY_FACTOR = ACTIVITY_FACTOR_SETTING
    df_recent_meas = df[df["日付"] > (today - pd.Timedelta(days=30))]
    meas_rate = df_recent_meas["体重(kg)"].notna().sum() / 30 * 100

    # 安全ペース判定
    if current_fat and current_fat > 20:
        safe_weekly_pct = 0.85
    elif current_fat and current_fat > 15:
        safe_weekly_pct = 0.6
    else:
        safe_weekly_pct = 0.4
    safe_weekly_kg = weight * safe_weekly_pct / 100
    pace_ok = required_weekly <= safe_weekly_kg

    # カロリー計算
    tdee, target_intake, actual_deficit, deficit_pct = None, None, None, None
    protein_g, fat_g, carb_g = None, None, None
    if current_bmr_val:
        tdee = current_bmr_val * ACTIVITY_FACTOR
        recommended_deficit = min(required_daily_deficit, tdee * 0.25)
        target_intake = max(tdee - recommended_deficit, current_bmr_val)
        actual_deficit = tdee - target_intake
        deficit_pct = actual_deficit / tdee * 100
        protein_g = weight * 2.2
        fat_g = target_intake * 0.27 / 9
        carb_g = (target_intake - protein_g * 4 - fat_g * 9) / 4

    # --- TOP 3 を動的に選出 ---
    top3 = []

    if meas_rate < 50:
        top3.append({
            "title": "毎朝、体重計に乗れ",
            "detail": f"直近30日で{meas_rate:.0f}%しか測れてない。現実を見ないと何も変わらない。",
        })

    df_30 = df[df["日付"] > (today - pd.Timedelta(days=30))]
    if len(df_30) >= 7:
        trend_30_vals = df_30["体重(kg)"].dropna()
        weight_change_30 = trend_30_vals.iloc[-1] - trend_30_vals.iloc[0] if len(trend_30_vals) >= 2 else 0
    else:
        weight_change_30 = 0

    if weight_change_30 > 0.5 and target_intake:
        top3.append({
            "title": f"1日{target_intake:.0f}kcal以内。それだけ守れ。",
            "detail": f"30日で+{weight_change_30:.1f}kg。食べすぎ。1日の消費は{tdee:.0f}kcal。食べていいのは{target_intake:.0f}kcal。差の{actual_deficit:.0f}kcalが脂肪を削る。",
        })

    if 50 <= meas_rate < 80 and len(top3) < 3:
        top3.append({
            "title": "毎朝、体重計に乗れ",
            "detail": f"測定率{meas_rate:.0f}%。歯抜けのデータでは正確な判断ができない。毎朝30秒でいい。",
        })

    if len(top3) < 3:
        top3.append({
            "title": "筋トレ週3回（火・木・土）。コミットメントを守れ。",
            "detail": "痩せながら筋肉を残す唯一の方法。走るだけでは筋肉も一緒に消える。サボったら週次頻度チャートに出る。",
        })

    if protein_g and len(top3) < 3:
        top3.append({
            "title": f"タンパク質1日{protein_g:.0f}g。鶏むね肉なら約{protein_g / 23:.0f}g。",
            "detail": "筋肉を守る生命線。4-5回に分けて摂れ。プロテインで補ってOK。",
        })

    if weight_change_30 <= 0.5 and target_intake and len(top3) < 3:
        top3.append({
            "title": f"1日{target_intake:.0f}kcal以内を守れ",
            "detail": f"消費{tdee:.0f}kcalに対して-{actual_deficit:.0f}kcal。これ以上削ると筋肉が落ちる。",
        })

    if len(top3) < 3:
        top3.append({
            "title": "7時間寝ろ。睡眠は最強のサプリ。",
            "detail": "同じ食事でも寝不足だと筋肉が60%多く落ちる。研究で証明済。",
        })

    top3_html = ""
    for i, item in enumerate(top3[:3]):
        num = i + 1
        top3_html += f"""
        <div style="background:linear-gradient(135deg, #1a1a2e, #16213e); border:1px solid #ff4444; border-radius:8px; padding:16px 20px; margin-bottom:10px;">
            <span style="color:#ff4444; font-size:24px; font-weight:bold; margin-right:12px;">#{num}</span>
            <span style="color:#fff; font-size:16px; font-weight:bold;">{item['title']}</span><br>
            <span style="color:#aaa; font-size:13px; margin-left:36px; display:inline-block; margin-top:4px;">{item['detail']}</span>
        </div>
        """

    st.markdown(top3_html, unsafe_allow_html=True)

    # --- その他のアクション（折りたたみ） ---
    other_items = []

    other_items.append({
        "icon": "⚖️",
        "title": f"必要ペース: 週-{required_weekly:.2f}kg（安全上限: 週-{safe_weekly_kg:.2f}kg）",
        "detail": f"残り{days_left}日で-{required_loss:.1f}kg。{'安全範囲内。' if pace_ok else '上限超え。筋肉ロスのリスクあり。'}",
        "color": "#00ff88" if pace_ok else "#ff4444",
    })

    if protein_g:
        other_items.append({
            "icon": "🍽️",
            "title": f"PFC: P{protein_g:.0f}g / F{fat_g:.0f}g / C{carb_g:.0f}g",
            "detail": "P=体重×2.2g（筋肉維持）、F=27%（ホルモン維持）、C=残り（筋トレ燃料）",
            "color": "#ffaa00",
        })

    if current_bmr_val:
        shortfall = required_daily_deficit - actual_deficit
        if shortfall > 0:
            other_items.append({
                "icon": "🏃",
                "title": f"有酸素で追加{shortfall:.0f}kcal/日消費",
                "detail": "低〜中強度、週2-3回。ランニングよりサイクリングが筋肉への干渉が少ない",
                "color": "#ffaa00",
            })

    other_items.append({
        "icon": "🥩",
        "title": "トレ前後の栄養摂取",
        "detail": "トレ2-3h前にP30g+C50g。トレ後2h以内にP30g+C40g。就寝前にカゼイン30g",
        "color": "#4488ff",
    })

    other_items.append({
        "icon": "😴",
        "title": "睡眠7時間以上",
        "detail": "コルチゾール抑制・MPS維持・インスリン感受性の維持に必須",
        "color": "#4488ff",
    })

    with st.expander("その他のアクション", expanded=False):
        other_html = ""
        for item in other_items:
            other_html += f"""
            <div style="background:#1a1a2e; border-left:3px solid {item['color']}; padding:10px 14px; border-radius:4px; margin-bottom:6px;">
                <span style="color:#fff; font-size:13px; font-weight:bold;">{item['icon']} {item['title']}</span><br>
                <span style="color:#888; font-size:11px;">{item['detail']}</span>
            </div>
            """
        st.markdown(other_html, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # === 共通期間切り替え ===
    period_options = {"全期間": None, "1年": 365, "半年": 180, "3ヶ月": 90, "1ヶ月": 30, "1週間": 7}
    selected_period = st.segmented_control("表示期間", options=list(period_options.keys()), default="全期間")
    period_days = period_options[selected_period]

    if period_days:
        cutoff = today - pd.Timedelta(days=period_days)
        df_view = df[df["日付"] >= cutoff]
    else:
        df_view = df

    # === 体重推移グラフ ===
    st.markdown("### 体重の推移")
    st.markdown("<p class='section-desc'>赤線が上がってたらアウト。緑の点線が目標。7月末までにここまで落とす。</p>", unsafe_allow_html=True)

    fig_weight = go.Figure()

    fig_weight.add_trace(go.Scatter(
        x=df_view["日付"], y=df_view["体重(kg)"],
        mode="lines",
        name="体重（日次）",
        line=dict(color="#aaaaaa", width=1),
        opacity=0.7,
    ))

    df_ma = df_view[df_view["7日移動平均(kg)"].notna()]
    fig_weight.add_trace(go.Scatter(
        x=df_ma["日付"], y=df_ma["7日移動平均(kg)"],
        mode="lines",
        name="7日移動平均",
        line=dict(color="#ff4444", width=2.5),
    ))

    fig_weight.add_trace(go.Scatter(
        x=[today, TARGET_DATE],
        y=[weight, TARGET_WEIGHT],
        mode="lines",
        name=f"目標ペース（→{TARGET_WEIGHT:.0f}kg）",
        line=dict(color="#00ff88", width=2, dash="dash"),
    ))

    fig_weight.add_hline(y=min_weight, line_dash="dot", line_color="#44ff44",
                          annotation_text=f"最低 {min_weight:.1f}kg", annotation_position="top left",
                          annotation_font_color="#44ff44")

    fig_weight.add_hline(y=TARGET_WEIGHT, line_dash="dot", line_color="#00ff88",
                          annotation_text=f"目標 {TARGET_WEIGHT:.0f}kg", annotation_position="top left",
                          annotation_font_color="#00ff88")

    if not period_days or period_days >= 365:
        fig_weight.add_hline(y=105.7, line_dash="dot", line_color="#ff4444",
                              annotation_text="破滅ライン 105.7kg", annotation_position="bottom left",
                              annotation_font_color="#ff4444")

    fig_weight.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=350,
        margin=dict(l=40, r=10, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#ffffff", size=11)),
        yaxis=dict(title="kg", gridcolor="#222"),
        xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
    )

    st.plotly_chart(fig_weight, use_container_width=True)

    # ネクストアクション（選択期間の直近トレンドで判定）
    period_label = selected_period if selected_period != "全期間" else "全期間"
    df_ma_view = df_view[df_view["7日移動平均(kg)"].notna()]
    if len(df_ma_view) >= 14:
        quarter_len = max(len(df_ma_view) // 4, 7)
        ma_recent = df_ma_view.tail(quarter_len)["7日移動平均(kg)"]
        ma_trend = ma_recent.iloc[-1] - ma_recent.iloc[0]
    elif len(df_ma_view) >= 3:
        ma_trend = df_ma_view["7日移動平均(kg)"].iloc[-1] - df_ma_view["7日移動平均(kg)"].iloc[0]
    else:
        ma_trend = 0

    if ma_trend > 0.5:
        action_text = f"{period_label}の直近トレンド: +{ma_trend:.1f}kg。増加中。食事を見直せ。"
        action_color = "#ff4444"
    elif ma_trend > -0.3:
        action_text = f"{period_label}の直近トレンド: {ma_trend:+.1f}kg。横ばい。運動量を上げろ。"
        action_color = "#ffaa00"
    else:
        action_text = f"{period_label}の直近トレンド: {ma_trend:.1f}kg。減少中。このペースを維持しろ。"
        action_color = "#00ff88"

    st.markdown(
        f"<div style='background:#1a1a2e; border-left:3px solid {action_color}; padding:12px 16px; border-radius:4px; margin-bottom:16px;'>"
        f"<span style='color:#888; font-size:12px;'>📋 FEEDBACK</span><br>"
        f"<span style='color:{action_color}; font-size:15px; font-weight:bold;'>{action_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # === 体脂肪率 + 基礎代謝推移（縦並び） ===
    st.markdown("### 体脂肪率の推移")

    df_fat = df_view[df_view["体脂肪率(%)"].notna()]

    fig_fat = go.Figure()
    fig_fat.add_trace(go.Scatter(
        x=df_fat["日付"], y=df_fat["体脂肪率(%)"],
        mode="lines",
        name="体脂肪率",
        line=dict(color="#ffaa00", width=1.5),
    ))
    fig_fat.add_hline(y=TARGET_FAT, line_dash="dot", line_color="#00ff88",
                       annotation_text=f"目標 {TARGET_FAT:.0f}%", annotation_position="top left",
                       annotation_font_color="#00ff88")
    fig_fat.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=280,
        margin=dict(l=40, r=10, t=20, b=30),
        yaxis=dict(title="%", gridcolor="#222"),
        xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
        showlegend=False,
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # 体脂肪率 FEEDBACK
    current_fat = df[df["体脂肪率(%)"].notna()].iloc[-1]["体脂肪率(%)"]
    fat_to_goal = current_fat - TARGET_FAT
    df_fat_ma = df_view[df_view["7日移動平均_体脂肪率(%)"].notna()]
    if len(df_fat_ma) >= 14:
        quarter_len = max(len(df_fat_ma) // 4, 7)
        fat_recent = df_fat_ma.tail(quarter_len)["7日移動平均_体脂肪率(%)"]
        fat_trend = fat_recent.iloc[-1] - fat_recent.iloc[0]
    elif len(df_fat_ma) >= 3:
        fat_trend = df_fat_ma["7日移動平均_体脂肪率(%)"].iloc[-1] - df_fat_ma["7日移動平均_体脂肪率(%)"].iloc[0]
    else:
        fat_trend = None

    if fat_trend is None:
        fb_fat_text = "データ不足。まず毎日測れ。"
        fb_fat_color = "#ff4444"
    elif fat_trend > 0.5:
        fb_fat_text = f"{period_label}の直近トレンド: +{fat_trend:.1f}%。増加中。"
        fb_fat_color = "#ff4444"
    elif fat_trend < -0.5:
        fb_fat_text = f"{period_label}の直近トレンド: {fat_trend:.1f}%。減少中。続けろ。"
        fb_fat_color = "#00ff88"
    else:
        fb_fat_text = f"{period_label}の直近トレンド: {fat_trend:+.1f}%。横ばい。目標{TARGET_FAT:.0f}%まであと{fat_to_goal:.1f}%。"
        fb_fat_color = "#ffaa00"

    st.markdown(
        f"<div style='background:#1a1a2e; border-left:3px solid {fb_fat_color}; padding:8px 12px; border-radius:4px;'>"
        f"<span style='color:#888; font-size:11px;'>📋 FEEDBACK</span><br>"
        f"<span style='color:{fb_fat_color}; font-size:13px; font-weight:bold;'>{fb_fat_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 基礎代謝の推移")

    df_bmr = df_view[df_view["基礎代謝(kcal)"].notna()] if "基礎代謝(kcal)" in df_view.columns else pd.DataFrame()

    if not df_bmr.empty:
        fig_bmr = go.Figure()
        fig_bmr.add_trace(go.Scatter(
            x=df_bmr["日付"], y=df_bmr["基礎代謝(kcal)"],
            mode="lines",
            name="基礎代謝",
            line=dict(color="#4488ff", width=1.5),
        ))
        fig_bmr.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            height=300,
            margin=dict(l=50, r=20, t=20, b=30),
            yaxis=dict(title="kcal", gridcolor="#222"),
            xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
            showlegend=False,
        )
        st.plotly_chart(fig_bmr, use_container_width=True)

        # 基礎代謝 FEEDBACK
        current_bmr = df_bmr["基礎代謝(kcal)"].iloc[-1]
        df_bmr_ma = df_view[df_view["7日移動平均_基礎代謝(kcal)"].notna()]
        if len(df_bmr_ma) >= 14:
            quarter_len = max(len(df_bmr_ma) // 4, 7)
            bmr_recent = df_bmr_ma.tail(quarter_len)["7日移動平均_基礎代謝(kcal)"]
            bmr_trend = bmr_recent.iloc[-1] - bmr_recent.iloc[0]
        elif len(df_bmr_ma) >= 3:
            bmr_trend = df_bmr_ma["7日移動平均_基礎代謝(kcal)"].iloc[-1] - df_bmr_ma["7日移動平均_基礎代謝(kcal)"].iloc[0]
        else:
            bmr_trend = None

        if bmr_trend is None:
            fb_bmr_text = "データ不足。まず毎日測れ。"
            fb_bmr_color = "#ff4444"
        elif bmr_trend > 10:
            fb_bmr_text = f"{period_label}の直近トレンド: +{bmr_trend:.0f}kcal。筋肉がついてきてる。現在{current_bmr:.0f}kcal。"
            fb_bmr_color = "#00ff88"
        elif bmr_trend < -10:
            fb_bmr_text = f"{period_label}の直近トレンド: {bmr_trend:.0f}kcal。筋肉が減ってる可能性あり。"
            fb_bmr_color = "#ff4444"
        else:
            fb_bmr_text = f"{period_label}の直近トレンド: {bmr_trend:+.0f}kcal。横ばい。現在{current_bmr:.0f}kcal。"
            fb_bmr_color = "#ffaa00"

        st.markdown(
            f"<div style='background:#1a1a2e; border-left:3px solid {fb_bmr_color}; padding:8px 12px; border-radius:4px;'>"
            f"<span style='color:#888; font-size:11px;'>📋 FEEDBACK</span><br>"
            f"<span style='color:{fb_bmr_color}; font-size:13px; font-weight:bold;'>{fb_bmr_text}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<p style='color:#555; text-align:center; padding:80px 0;'>基礎代謝データなし</p>", unsafe_allow_html=True)

    # === 月別サマリーテーブル ===
    st.markdown("### 月別サマリー")
    st.markdown("<p class='section-desc'>赤=太った月、緑=痩せた月。測定日数が少ない＝体重計に乗れなかった月。</p>", unsafe_allow_html=True)

    df_monthly = df.copy()
    df_monthly["年月"] = df_monthly["日付"].dt.to_period("M").astype(str)

    monthly_summary = df_monthly.groupby("年月").agg(
        平均体重=("体重(kg)", "mean"),
        最小体重=("体重(kg)", "min"),
        最大体重=("体重(kg)", "max"),
        平均体脂肪率=("体脂肪率(%)", "mean"),
        測定日数=("体重(kg)", "count"),
    ).round(1)

    monthly_summary["前月比(kg)"] = monthly_summary["平均体重"].diff().round(1)
    monthly_summary = monthly_summary.sort_index(ascending=False)

    st.dataframe(
        monthly_summary.style.map(
            lambda v: "color: #ff4444" if isinstance(v, (int, float)) and v > 0 else
                      "color: #44ff44" if isinstance(v, (int, float)) and v < 0 else "",
            subset=["前月比(kg)"]
        ).format("{:.1f}", subset=["平均体重", "最小体重", "最大体重", "平均体脂肪率", "前月比(kg)"]),
        use_container_width=True,
        height=400,
    )

# ============================================================
# 栄養管理タブ
# ============================================================
with tab_nutrition:
    df_nutr = load_nutrition_data()

    # --- 栄養入力フォーム ---
    with st.expander("📝 栄養を記録", expanded=False):
        with st.form("nutrition_form"):
            nutr_date = st.date_input("日付", value=datetime.now().date(), key="nutr_date")

            # 前回値をプリフィル
            prev_intake, prev_p, prev_f, prev_c, prev_rest, prev_active = 0, 0, 0, 0, 0, 0
            if not df_nutr.empty:
                last_nutr = df_nutr.iloc[-1]
                prev_intake = int(last_nutr["摂取kcal"]) if pd.notna(last_nutr["摂取kcal"]) else 0
                prev_p = int(last_nutr["P(g)"]) if pd.notna(last_nutr["P(g)"]) else 0
                prev_f = int(last_nutr["F(g)"]) if pd.notna(last_nutr["F(g)"]) else 0
                prev_c = int(last_nutr["C(g)"]) if pd.notna(last_nutr["C(g)"]) else 0
                prev_rest = int(last_nutr["安静時消費kcal"]) if pd.notna(last_nutr["安静時消費kcal"]) else 0
                prev_active = int(last_nutr["アクティブkcal"]) if pd.notna(last_nutr["アクティブkcal"]) else 0

            st.markdown("**あすけんから転記**")
            nutr_intake = st.number_input("摂取kcal", value=prev_intake, step=50, min_value=0, key="nutr_intake")

            st.markdown("**PFCマクロ**")
            col_p, col_f, col_c = st.columns(3)
            nutr_p = col_p.number_input("P タンパク質(g)", value=prev_p, step=5, min_value=0, key="nutr_p")
            nutr_f = col_f.number_input("F 脂質(g)", value=prev_f, step=5, min_value=0, key="nutr_f")
            nutr_c = col_c.number_input("C 炭水化物(g)", value=prev_c, step=5, min_value=0, key="nutr_c")

            st.markdown("**Apple Watch消費カロリー**")
            col_rest, col_active = st.columns(2)
            nutr_rest = col_rest.number_input("安静時消費エネルギー(kcal)", value=prev_rest, step=50, min_value=0, key="nutr_rest")
            nutr_active = col_active.number_input("アクティブエネルギー(kcal)", value=prev_active, step=50, min_value=0, key="nutr_active")

            nutr_submitted = st.form_submit_button("💾 栄養データを保存", use_container_width=True)

            if nutr_submitted:
                date_str = nutr_date.strftime("%Y/%m/%d")
                row = [date_str, nutr_intake, nutr_p, nutr_f, nutr_c, nutr_rest, nutr_active]
                try:
                    success = append_nutrition_row(row)
                    if success:
                        st.success("✅ 栄養データを保存しました！")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ 書き込みに失敗しました。")
                except Exception as e:
                    st.error(f"❌ エラー: {e}")

    # --- 栄養データの表示 ---
    if not df_nutr.empty and len(df_nutr) >= 1:
        # 期間フィルタ（栄養タブ独自）
        period_options_nutr = {"全期間": None, "1年": 365, "半年": 180, "3ヶ月": 90, "1ヶ月": 30, "2週間": 14, "1週間": 7}
        selected_period_nutr = st.segmented_control("表示期間", options=list(period_options_nutr.keys()), default="全期間", key="period_nutr")
        period_days_nutr = period_options_nutr[selected_period_nutr]

        if period_days_nutr:
            cutoff_nutr = today - pd.Timedelta(days=period_days_nutr)
            df_nutr_view = df_nutr[df_nutr["日付"] >= cutoff_nutr]
        else:
            df_nutr_view = df_nutr

        # 体重データのフィルタ済みビュー（基礎代謝ライン等で使用）
        if period_days_nutr:
            df_view_nutr = df[df["日付"] >= cutoff_nutr]
        else:
            df_view_nutr = df

        if not df_nutr_view.empty:
            # --- 逆算TDEE計算 ---
            # 体重データとマージして14日ローリングで算出
            df_merged = pd.merge(
                df[["日付", "体重(kg)"]],
                df_nutr[["日付", "摂取kcal", "消費kcal"]],
                on="日付", how="inner"
            ).sort_values("日付")

            reverse_tdee_series = pd.Series(dtype=float)
            if len(df_merged) >= 14:
                # 14日ローリング逆算TDEE
                weight_change_14d = df_merged["体重(kg)"].rolling(14).apply(
                    lambda x: x.iloc[-1] - x.iloc[0], raw=False
                )
                intake_sum_14d = df_merged["摂取kcal"].rolling(14).sum()
                # 体脂肪1kg ≈ 7,200kcal
                calorie_surplus_14d = weight_change_14d * 7200
                reverse_tdee_14d = (intake_sum_14d - calorie_surplus_14d) / 14
                reverse_tdee_series = pd.Series(reverse_tdee_14d.values, index=df_merged["日付"].values)

            # --- スコアカード ---
            st.markdown("### 栄養スコアカード")

            # 今週のデータ
            week_ago = today - pd.Timedelta(days=7)
            df_nutr_week = df_nutr[df_nutr["日付"] > week_ago]

            avg_balance = "---"
            balance_color = "info"
            if not df_nutr_week.empty and df_nutr_week["消費kcal"].notna().any() and df_nutr_week["摂取kcal"].notna().any():
                week_intake_avg = df_nutr_week["摂取kcal"].mean()
                week_burn_avg = df_nutr_week["消費kcal"].mean()
                bal = week_intake_avg - week_burn_avg
                avg_balance = f"{bal:+.0f}"
                balance_color = "danger" if bal > 0 else "success"

            # P/体重
            p_per_kg = "---"
            p_color = "info"
            if not df_nutr_week.empty and df_nutr_week["P(g)"].notna().any():
                avg_p = df_nutr_week["P(g)"].mean()
                p_ratio = avg_p / weight
                p_per_kg = f"{p_ratio:.1f}"
                p_color = "success" if p_ratio >= 2.0 else "warning" if p_ratio >= 1.6 else "danger"

            # 記録率
            days_in_week = min(7, (today - df_nutr["日付"].min()).days + 1)
            record_count = len(df_nutr_week)
            record_rate = record_count / days_in_week * 100 if days_in_week > 0 else 0
            record_color = "success" if record_rate >= 80 else "warning" if record_rate >= 50 else "danger"

            scorecard_html = f"""
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:20px;">
                <div class="metric-card">
                    <div style="color:#888; font-size:11px;">今週平均カロリー収支</div>
                    <div style="color:var(--{balance_color}); font-size:28px; font-weight:bold;">{avg_balance}</div>
                    <div style="color:#666; font-size:10px;">kcal/日（摂取−消費）</div>
                </div>
                <div class="metric-card">
                    <div style="color:#888; font-size:11px;">P / 体重</div>
                    <div style="color:var(--{p_color}); font-size:28px; font-weight:bold;">{p_per_kg}</div>
                    <div style="color:#666; font-size:10px;">g/kg（目標: 2.0以上）</div>
                </div>
                <div class="metric-card">
                    <div style="color:#888; font-size:11px;">今週の記録率</div>
                    <div style="color:var(--{record_color}); font-size:28px; font-weight:bold;">{record_rate:.0f}%</div>
                    <div style="color:#666; font-size:10px;">{record_count}/{days_in_week}日</div>
                </div>
            </div>
            """
            st.markdown(scorecard_html, unsafe_allow_html=True)

            # --- カロリー収支チャート（ローソク足） ---
            st.markdown("### カロリー収支")
            st.markdown("<p class='section-desc'>緑=痩せた日、赤=太った日。ヒゲの長さが摂取と消費の振れ幅。</p>", unsafe_allow_html=True)

            # 日次収支データ作成
            df_bal = df_nutr_view[
                df_nutr_view["摂取kcal"].notna() & df_nutr_view["消費kcal"].notna() & (df_nutr_view["消費kcal"] > 0)
            ].copy()

            if not df_bal.empty:
                df_bal["収支"] = df_bal["摂取kcal"] - df_bal["消費kcal"]
                df_bal["累積収支"] = df_bal["収支"].cumsum()
                # 表示期間の初日を基準(0)にする
                baseline = df_bal["累積収支"].iloc[0] - df_bal["収支"].iloc[0]  # 初日のopen=0
                df_bal["累積_adj"] = df_bal["累積収支"] - baseline
                df_bal["累積_kg"] = df_bal["累積_adj"] / 7200

                # 累積収支がそのまま「上=太る、下=痩せる」
                df_bal["close"] = df_bal["累積_adj"]
                df_bal["open"] = df_bal["close"].shift(1).fillna(0)
                # ヒゲ: 摂取・消費の平均からの振れ幅
                intake_dev = (df_bal["摂取kcal"] - df_bal["摂取kcal"].mean()).clip(lower=0) * 0.5
                burn_dev = (df_bal["消費kcal"] - df_bal["消費kcal"].mean()).clip(lower=0) * 0.5
                df_bal["high"] = df_bal[["open", "close"]].max(axis=1) + intake_dev
                df_bal["low"] = df_bal[["open", "close"]].min(axis=1) - burn_dev

                fig_cal = make_subplots(specs=[[{"secondary_y": True}]])

                # ローソク足（上がる=太る=赤、下がる=痩せる=緑）
                fig_cal.add_trace(go.Candlestick(
                    x=df_bal["日付"],
                    open=df_bal["open"],
                    high=df_bal["high"],
                    low=df_bal["low"],
                    close=df_bal["close"],
                    increasing_line_color="#ff4444",
                    increasing_fillcolor="#ff4444",
                    decreasing_line_color="#00ff88",
                    decreasing_fillcolor="#00ff88",
                    name="カロリー収支",
                    whiskerwidth=0.5,
                ), secondary_y=False)

                # 体重変動（初日基準=0の累積差分、第2Y軸）
                df_weight_period = df[["日付", "体重(kg)"]].dropna()
                df_weight_period = df_weight_period[
                    df_weight_period["日付"].isin(df_bal["日付"])
                ].sort_values("日付")
                if len(df_weight_period) >= 2:
                    first_weight = df_weight_period["体重(kg)"].iloc[0]
                    df_weight_period["体重変動"] = df_weight_period["体重(kg)"] - first_weight
                    fig_cal.add_trace(go.Scatter(
                        x=df_weight_period["日付"],
                        y=df_weight_period["体重変動"],
                        mode="lines+markers",
                        name="体重変動",
                        line=dict(color="#ffffff", width=2),
                        marker=dict(size=4),
                        hovertemplate="%{x|%m/%d}<br>体重変動: %{y:+.1f} kg<extra></extra>",
                    ), secondary_y=True)

                # ゼロライン
                fig_cal.add_hline(y=0, line_dash="solid", line_color="#555", line_width=1, secondary_y=False)

                # 体脂肪換算アノテーション
                last_cum = df_bal["累積_kg"].iloc[-1]
                last_close = df_bal["close"].iloc[-1]
                cum_sign = "+" if last_cum > 0 else ""
                cum_color = "#ff4444" if last_cum > 0 else "#00ff88"
                fig_cal.add_annotation(
                    x=df_bal["日付"].iloc[-1],
                    y=last_close,
                    text=f"<b>{cum_sign}{last_cum:.2f} kg</b>",
                    showarrow=True, arrowhead=2, arrowcolor=cum_color,
                    font=dict(color=cum_color, size=13),
                    bgcolor="rgba(14,17,23,0.8)",
                    bordercolor=cum_color,
                    borderwidth=1,
                    secondary_y=False,
                )

                fig_cal.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                    height=420,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(
                        gridcolor="#222", tickformat="%m/%d",
                        rangeslider=dict(visible=False),
                    ),
                    legend=dict(orientation="h", y=-0.12),
                    hovermode="x unified",
                )
                # 左Y軸: カロリー収支（0中心対称）
                y_abs_max = max(abs(df_bal["high"].max()), abs(df_bal["low"].min()), 500)
                y_margin = y_abs_max * 1.15
                fig_cal.update_yaxes(
                    title_text="累積カロリー収支 (kcal)", gridcolor="#222",
                    zeroline=True, zerolinecolor="#444",
                    range=[-y_margin, y_margin],
                    secondary_y=False,
                )
                # 右Y軸: 体重変動（0中心対称）
                if len(df_weight_period) >= 2:
                    w_abs_max = max(abs(df_weight_period["体重変動"].max()), abs(df_weight_period["体重変動"].min()), 0.5)
                    w_margin = w_abs_max * 1.15
                    fig_cal.update_yaxes(
                        title_text="体重変動 (kg)", gridcolor="rgba(0,0,0,0)",
                        showgrid=False,
                        zeroline=True, zerolinecolor="#444",
                        range=[-w_margin, w_margin],
                        secondary_y=True,
                    )
                st.plotly_chart(fig_cal, use_container_width=True)

            # --- 摂取 vs 消費 詳細 ---
            st.markdown("### 摂取 vs 消費")
            st.markdown("<p class='section-desc'>オレンジが青を超えたら食いすぎ。基礎代謝を割ったら筋肉が溶ける。</p>", unsafe_allow_html=True)

            fig_detail = go.Figure()

            # 摂取kcal
            fig_detail.add_trace(go.Scatter(
                x=df_nutr_view["日付"], y=df_nutr_view["摂取kcal"],
                mode="lines+markers",
                name="摂取kcal",
                line=dict(color="#ffaa00", width=2),
                marker=dict(size=4),
                fill="tozeroy",
                fillcolor="rgba(255,170,0,0.08)",
            ))

            # Apple Watch消費kcal
            df_burn = df_nutr_view[df_nutr_view["消費kcal"].notna() & (df_nutr_view["消費kcal"] > 0)]
            if not df_burn.empty:
                fig_detail.add_trace(go.Scatter(
                    x=df_burn["日付"], y=df_burn["消費kcal"],
                    mode="lines+markers",
                    name="消費kcal（Apple Watch）",
                    line=dict(color="#4488ff", width=2),
                    marker=dict(size=4),
                    fill="tozeroy",
                    fillcolor="rgba(68,136,255,0.08)",
                ))

            # 逆算TDEE
            if not reverse_tdee_series.empty:
                rt_dates = pd.to_datetime(reverse_tdee_series.index)
                if period_days_nutr:
                    mask = rt_dates >= cutoff_nutr
                    rt_filtered = reverse_tdee_series[mask]
                else:
                    rt_filtered = reverse_tdee_series
                rt_valid = rt_filtered.dropna()
                if not rt_valid.empty:
                    fig_detail.add_trace(go.Scatter(
                        x=pd.to_datetime(rt_valid.index),
                        y=rt_valid.values,
                        mode="lines",
                        name="逆算TDEE（14日）",
                        line=dict(color="#00ff88", width=2, dash="dash"),
                    ))

            # 基礎代謝ライン
            if df_view_nutr["基礎代謝(kcal)"].notna().any():
                latest_bmr = df["基礎代謝(kcal)"].dropna().iloc[-1]
                fig_detail.add_hline(
                    y=latest_bmr, line_dash="dot", line_color="#ff4444",
                    annotation_text=f"基礎代謝 {latest_bmr:.0f}kcal",
                    annotation_position="top left",
                    annotation_font_color="#ff4444",
                )

            fig_detail.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                height=320,
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
                yaxis=dict(gridcolor="#222", title="kcal"),
                legend=dict(orientation="h", y=-0.15),
                hovermode="x unified",
            )
            st.plotly_chart(fig_detail, use_container_width=True)

            # --- PFCバランス推移 ---
            st.markdown("### PFCバランス推移")
            st.markdown("<p class='section-desc'>タンパク質（青）が薄いと筋肉が減る。脂質（赤）が厚いと太る。</p>", unsafe_allow_html=True)

            df_pfc = df_nutr_view[df_nutr_view[["P(g)", "F(g)", "C(g)"]].notna().all(axis=1)].copy()
            if not df_pfc.empty:
                # kcal換算
                df_pfc = df_pfc.copy()
                df_pfc["P_kcal"] = df_pfc["P(g)"] * 4
                df_pfc["F_kcal"] = df_pfc["F(g)"] * 9
                df_pfc["C_kcal"] = df_pfc["C(g)"] * 4

                fig_pfc = go.Figure()
                fig_pfc.add_trace(go.Bar(x=df_pfc["日付"], y=df_pfc["P_kcal"], name="P（タンパク質）", marker_color="#4488ff"))
                fig_pfc.add_trace(go.Bar(x=df_pfc["日付"], y=df_pfc["F_kcal"], name="F（脂質）", marker_color="#ff4444"))
                fig_pfc.add_trace(go.Bar(x=df_pfc["日付"], y=df_pfc["C_kcal"], name="C（炭水化物）", marker_color="#ffaa00"))

                fig_pfc.update_layout(
                    barmode="stack",
                    template="plotly_dark",
                    paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                    height=300,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
                    yaxis=dict(gridcolor="#222", title="kcal"),
                    legend=dict(orientation="h", y=-0.15),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_pfc, use_container_width=True)

            # --- タンパク質/体重 推移 ---
            st.markdown("### タンパク質 / 体重")
            st.markdown("<p class='section-desc'>2.0g/kg以上で筋肉維持。下回ったら赤ゾーン。</p>", unsafe_allow_html=True)

            df_p_ratio = pd.merge(
                df_nutr_view[["日付", "P(g)"]].dropna(),
                df[["日付", "体重(kg)"]],
                on="日付", how="left"
            )
            # 体重がない日は直近値で補完
            df_p_ratio["体重(kg)"] = df_p_ratio["体重(kg)"].ffill().bfill()
            df_p_ratio = df_p_ratio.dropna(subset=["P(g)", "体重(kg)"])

            if not df_p_ratio.empty:
                df_p_ratio["P/体重"] = df_p_ratio["P(g)"] / df_p_ratio["体重(kg)"]

                fig_p = go.Figure()
                fig_p.add_trace(go.Scatter(
                    x=df_p_ratio["日付"], y=df_p_ratio["P/体重"],
                    mode="lines+markers",
                    name="P/体重 (g/kg)",
                    line=dict(color="#4488ff", width=2),
                    marker=dict(size=5),
                ))

                # 目標ライン
                fig_p.add_hline(y=2.0, line_dash="dash", line_color="#00ff88",
                                annotation_text="目標 2.0g/kg", annotation_position="top left",
                                annotation_font_color="#00ff88")
                # 危険ライン
                fig_p.add_hline(y=1.6, line_dash="dot", line_color="#ff4444",
                                annotation_text="最低限 1.6g/kg", annotation_position="bottom left",
                                annotation_font_color="#ff4444")

                # 赤ゾーン（1.6以下）
                fig_p.add_hrect(y0=0, y1=1.6, fillcolor="rgba(255,68,68,0.08)", line_width=0)

                fig_p.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                    height=280,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
                    yaxis=dict(gridcolor="#222", title="g/kg"),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_p, use_container_width=True)

            # --- 体重 vs カロリー収支 ---
            st.markdown("### 体重 vs カロリー収支")
            st.markdown("<p class='section-desc'>食べすぎた週に体重が増える因果関係を見る。7日移動平均で比較。</p>", unsafe_allow_html=True)

            df_weight_cal = pd.merge(
                df[["日付", "7日移動平均(kg)"]],
                df_nutr[["日付", "摂取kcal", "消費kcal"]],
                on="日付", how="inner"
            ).sort_values("日付")

            if not df_weight_cal.empty and len(df_weight_cal) >= 7:
                df_weight_cal["カロリー収支"] = df_weight_cal["摂取kcal"] - df_weight_cal["消費kcal"].fillna(0)
                df_weight_cal["収支_7日MA"] = df_weight_cal["カロリー収支"].rolling(7, min_periods=3).mean()

                if period_days_nutr:
                    df_weight_cal = df_weight_cal[df_weight_cal["日付"] >= cutoff_nutr]

                if not df_weight_cal.empty:
                    fig_wc = make_subplots(specs=[[{"secondary_y": True}]])

                    fig_wc.add_trace(go.Scatter(
                        x=df_weight_cal["日付"], y=df_weight_cal["7日移動平均(kg)"],
                        mode="lines", name="体重（7日MA）",
                        line=dict(color="#ff4444", width=2),
                    ), secondary_y=False)

                    fig_wc.add_trace(go.Bar(
                        x=df_weight_cal["日付"], y=df_weight_cal["収支_7日MA"],
                        name="カロリー収支（7日MA）",
                        marker_color=["#ff4444" if v > 0 else "#44ff44" for v in df_weight_cal["収支_7日MA"].fillna(0)],
                        opacity=0.6,
                    ), secondary_y=True)

                    fig_wc.add_hline(y=0, line_dash="dot", line_color="#666", secondary_y=True)

                    fig_wc.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                        height=350,
                        margin=dict(l=20, r=20, t=30, b=20),
                        xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
                        legend=dict(orientation="h", y=-0.15),
                        hovermode="x unified",
                    )
                    fig_wc.update_yaxes(title_text="体重 (kg)", gridcolor="#222", secondary_y=False)
                    fig_wc.update_yaxes(title_text="カロリー収支 (kcal)", gridcolor="#222", secondary_y=True)
                    st.plotly_chart(fig_wc, use_container_width=True)

    elif df_nutr.empty:
        st.markdown("<p style='color:#555; text-align:center; padding:40px 0;'>栄養データなし。上の「📝 栄養を記録」から入力を開始してください。</p>", unsafe_allow_html=True)

# ============================================================
# トレーニングタブ
# ============================================================
with tab_training:
    df_train = load_training_data()
    df_master = load_exercise_master()
    df_1rm = load_1rm_records()

    BIG3 = ["スクワット", "デッドリフト", "ベンチプレス"]
    # 推奨ウェイト係数（rep数に応じた1RMの割合）
    RM_PERCENT = {6: 0.80, 8: 0.75, 10: 0.70}

    # 種目定義（順番, 種目名, デフォルトrep数）
    EXERCISES = [
        ("スクワット", 8),
        ("デッドリフト", 6),
        ("ベンチプレス", 8),
        ("ラットプルダウン", 10),
        ("ダンベルショルダープレス", 10),
        ("サイドレイズ", 15),
        ("EZバーカール", 10),
        ("EZバーエクステンション", 10),
        ("ハンギングレッグレイズ", 20),
        ("ロシアンツイスト", 20),
    ]

    def get_last_session_data(df_t):
        """直近セッションのデータを種目別に取得。{種目名: {重量, reps: [s1,s2,s3]}}"""
        if df_t.empty:
            return {}
        last_date = df_t["日付"].max()
        last = df_t[df_t["日付"] == last_date]
        result = {}
        for ex_name, group in last.groupby("種目"):
            group_sorted = group.sort_values("セット番号")
            w = group_sorted["重量(kg)"].iloc[0] if not group_sorted.empty else 0
            reps = group_sorted["回数"].tolist()
            weights = group_sorted["重量(kg)"].tolist()
            result[ex_name] = {"重量": weights, "reps": reps}
        return result

    # === 入力フォーム ===
    with st.expander("📝 トレーニングを記録", expanded=False):
        last_data = get_last_session_data(df_train)

        form_tab_log, form_tab_1rm = st.tabs(["トレーニングログ", "1RM記録（月末）"])

        # --- トレーニングログフォーム ---
        with form_tab_log:
            with st.form("training_form"):
                train_date = st.date_input("日付", value=datetime.now().date())

                st.markdown("<p style='color:#888; font-size:12px;'>各種目のセットごとに重量とrep数を入力。前回値がデフォルトで入っています。</p>", unsafe_allow_html=True)

                form_data = {}
                for ex_name, default_reps in EXERCISES:
                    prev = last_data.get(ex_name, {})
                    prev_weights = prev.get("重量", [0, 0, 0])
                    prev_reps = prev.get("reps", [default_reps] * 3)
                    while len(prev_weights) < 3:
                        prev_weights.append(prev_weights[-1] if prev_weights else 0)
                    while len(prev_reps) < 3:
                        prev_reps.append(default_reps)

                    st.markdown(f"**{ex_name}**")
                    sets = []
                    for s in range(3):
                        c1, c2 = st.columns(2)
                        w = c1.number_input(
                            f"S{s+1} kg", value=float(prev_weights[s]), step=2.5, min_value=0.0,
                            key=f"{ex_name}_w{s}"
                        )
                        r = c2.number_input(
                            f"S{s+1} rep", value=int(prev_reps[s]), step=1, min_value=0,
                            key=f"{ex_name}_r{s}"
                        )
                        sets.append((w, r))
                    form_data[ex_name] = sets

                submitted = st.form_submit_button("💾 記録を保存", use_container_width=True)

                if submitted:
                    rows = []
                    date_str = train_date.strftime("%Y/%m/%d")
                    for ex_name, sets in form_data.items():
                        for s_idx, (w, r) in enumerate(sets):
                            if r > 0:  # rep数が0のセットはスキップ
                                rows.append([date_str, ex_name, w, r, s_idx + 1, "", ""])

                    if rows:
                        try:
                            success = append_training_rows(rows)
                            if success:
                                st.success(f"✅ {len(rows)}セット分のデータを保存しました！")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ 書き込みに失敗しました。Secrets設定を確認してください。")
                        except Exception as e:
                            st.error(f"❌ エラー: {e}")
                    else:
                        st.warning("保存するデータがありません。")

        # --- 1RM記録フォーム ---
        with form_tab_1rm:
            with st.form("rm_form"):
                rm_date = st.date_input("測定日", value=datetime.now().date(), key="rm_date")
                st.markdown("<p style='color:#888; font-size:12px;'>BIG3の1RM実測値を入力。</p>", unsafe_allow_html=True)

                rm_data = {}
                for ex in BIG3:
                    # 前回の1RM値をデフォルトに
                    prev_1rm = 0.0
                    if not df_1rm.empty:
                        ex_records = df_1rm[df_1rm["種目"] == ex].sort_values("日付", ascending=False)
                        if not ex_records.empty and ex_records["1RM(kg)"].notna().any():
                            prev_1rm = float(ex_records.iloc[0]["1RM(kg)"])
                    rm_data[ex] = st.number_input(
                        f"{ex} (kg)", value=prev_1rm, step=2.5, min_value=0.0, key=f"rm_{ex}"
                    )

                rm_submitted = st.form_submit_button("💾 1RMを保存", use_container_width=True)

                if rm_submitted:
                    rm_rows = []
                    date_str = rm_date.strftime("%Y/%m/%d")
                    for ex, val in rm_data.items():
                        if val > 0:
                            rm_rows.append([date_str, ex, val])
                    if rm_rows:
                        try:
                            success = append_1rm_rows(rm_rows)
                            if success:
                                st.success(f"✅ BIG3の1RM記録を保存しました！")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ 書き込みに失敗しました。")
                        except Exception as e:
                            st.error(f"❌ エラー: {e}")

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    def estimate_1rm(weight_kg, reps):
        """Epley式で推定1RMを算出"""
        if reps <= 0 or weight_kg <= 0:
            return 0
        if reps == 1:
            return weight_kg
        return weight_kg * (1 + reps / 30)

    has_training_data = not df_train.empty and df_train["重量(kg)"].notna().any()

    if not has_training_data:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px;">
            <p style="color:#888; font-size:18px;">🏋️ トレーニングデータがまだありません</p>
            <p style="color:#555; font-size:14px;">Google Sheetsの「トレーニング」シートにデータを入力してください。</p>
            <p style="color:#555; font-size:13px; margin-top:16px;">
                <b style="color:#aaa;">入力形式:</b> 日付 | 種目 | 重量(kg) | 回数 | セット番号 | 消費kcal | メモ<br>
                <b style="color:#aaa;">例:</b> 2026/03/27 | スクワット | 80 | 8 | 1 | | ウォームアップ後
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 1RM記録があれば表示
        if not df_1rm.empty and df_1rm["1RM(kg)"].notna().any():
            st.markdown("### 🏆 BIG3 1RM記録")
            for ex in BIG3:
                ex_1rm = df_1rm[df_1rm["種目"] == ex].sort_values("日付", ascending=False)
                if not ex_1rm.empty:
                    latest_1rm = ex_1rm.iloc[0]
                    default_reps = 6 if ex == "デッドリフト" else 8
                    rec_weight = latest_1rm["1RM(kg)"] * RM_PERCENT.get(default_reps, 0.75)
                    st.markdown(f"""
                    <div class="metric-card" style="height:auto; margin-bottom:8px;">
                        <p class="metric-label">{ex}</p>
                        <p class="metric-value info">{latest_1rm['1RM(kg)']:.0f}<span style="font-size:20px">kg</span></p>
                        <p class="metric-sub">推奨: {rec_weight:.1f}kg × {default_reps}rep</p>
                    </div>
                    """, unsafe_allow_html=True)

            # BIG3合計 + 体重比（トレーニングデータなし時）
            big3_total = 0
            for ex in BIG3:
                ex_1rm_df = df_1rm[df_1rm["種目"] == ex].sort_values("日付", ascending=False)
                if not ex_1rm_df.empty and ex_1rm_df["1RM(kg)"].notna().any():
                    big3_total += ex_1rm_df.iloc[0]["1RM(kg)"]
            if big3_total > 0:
                current_weight = df["体重(kg)"].dropna().iloc[-1] if not df.empty else 0
                ratio = big3_total / current_weight if current_weight > 0 else 0
                target_ratio = big3_total / 75.0
                st.markdown(f"""
                <div class="metric-card" style="height:auto; margin-bottom:8px; margin-top:16px;">
                    <p class="metric-label">BIG3合計</p>
                    <p class="metric-value info">{big3_total:.0f}<span style="font-size:20px">kg</span></p>
                    <p class="metric-sub">現在: 体重比 <b style="color:#00ff88;">{ratio:.1f}倍</b>（{current_weight:.1f}kg）</p>
                    <p class="metric-sub">目標: 体重比 <b style="color:#ff8800;">{target_ratio:.1f}倍</b>（75kg時）</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        # === スコアカード ===
        now = pd.Timestamp.now()
        week_start = now - pd.Timedelta(days=now.weekday())
        df_this_week = df_train[df_train["日付"] >= week_start]
        weekly_sessions = df_this_week["日付"].dt.date.nunique()
        weekly_volume = df_this_week["ボリューム"].sum()

        # 前週比較
        prev_week_start = week_start - pd.Timedelta(days=7)
        df_prev_week = df_train[(df_train["日付"] >= prev_week_start) & (df_train["日付"] < week_start)]
        prev_weekly_volume = df_prev_week["ボリューム"].sum()
        vol_diff = weekly_volume - prev_weekly_volume if prev_weekly_volume > 0 else 0
        vol_diff_pct = (vol_diff / prev_weekly_volume * 100) if prev_weekly_volume > 0 else 0

        session_color = "info" if weekly_sessions >= 2 else "warning" if weekly_sessions >= 1 else "danger"
        vol_color = "info" if vol_diff >= 0 else "warning"

        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div class="metric-card" style="height:140px;">
                <p class="metric-label">今週のトレーニング</p>
                <p class="metric-value {session_color}">{weekly_sessions}<span style="font-size:20px">回</span></p>
                <p class="metric-sub">目標: 2〜3回/週</p>
            </div>
            <div class="metric-card" style="height:140px;">
                <p class="metric-label">今週の総ボリューム</p>
                <p class="metric-value {vol_color}">{weekly_volume:,.0f}<span style="font-size:16px">kg</span></p>
                <p class="metric-sub">{'前週比: ' + f'{vol_diff:+,.0f}kg ({vol_diff_pct:+.0f}%)' if prev_weekly_volume > 0 else 'まだ前週データなし'}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # === BIG3 1RM テーブル ===
        st.markdown("### 🏆 BIG3 パフォーマンス")
        st.markdown("<p class='section-desc'>実測1RM → 推奨ウェイト → ログからの推定1RM。推定が実測を超えたら重量を上げろ。</p>", unsafe_allow_html=True)

        big3_rows = []
        alerts = []
        for ex in BIG3:
            default_reps = 6 if ex == "デッドリフト" else 8

            # 実測1RM（最新）
            ex_1rm = df_1rm[df_1rm["種目"] == ex].sort_values("日付", ascending=False) if not df_1rm.empty else pd.DataFrame()
            actual_1rm = ex_1rm.iloc[0]["1RM(kg)"] if not ex_1rm.empty and ex_1rm["1RM(kg)"].notna().any() else None
            actual_1rm_date = ex_1rm.iloc[0]["日付"].strftime("%m/%d") if actual_1rm else "-"

            # 推奨ウェイト
            rec_weight = actual_1rm * RM_PERCENT.get(default_reps, 0.75) if actual_1rm else None

            # ログからの推定1RM（直近30日のベストセットから）
            ex_logs = df_train[(df_train["種目"] == ex) & (df_train["日付"] > (now - pd.Timedelta(days=30)))]
            estimated_1rm = None
            if not ex_logs.empty:
                ex_logs = ex_logs.copy()
                ex_logs["推定1RM"] = ex_logs.apply(lambda r: estimate_1rm(r["重量(kg)"], r["回数"]), axis=1)
                best_row = ex_logs.loc[ex_logs["推定1RM"].idxmax()]
                estimated_1rm = best_row["推定1RM"]

            # アラート判定
            if actual_1rm and estimated_1rm and estimated_1rm > actual_1rm:
                alerts.append(f"💪 {ex}: 推定1RM ({estimated_1rm:.0f}kg) が実測 ({actual_1rm:.0f}kg) を超えた。重量を上げろ。")

            big3_rows.append({
                "種目": ex,
                "reps": default_reps,
                "actual_1rm": f"{actual_1rm:.0f}kg" if actual_1rm else "-",
                "actual_date": actual_1rm_date,
                "rec_weight": f"{rec_weight:.1f}kg" if rec_weight else "-",
                "estimated_1rm": f"{estimated_1rm:.0f}kg" if estimated_1rm else "-",
                "has_alert": actual_1rm is not None and estimated_1rm is not None and estimated_1rm > actual_1rm,
            })

        # BIG3テーブル（Streamlit native）
        for row in big3_rows:
            est_color = "#ff4444" if row["has_alert"] else "#ccc"
            st.markdown(f"""
<div class="metric-card" style="height:auto; padding:14px 16px; margin-bottom:8px;">
<p style="color:#fff; font-size:16px; font-weight:bold; margin:0 0 8px 0;">{row['種目']}</p>
<p style="color:#888; font-size:11px; margin:0;">実測1RM: <b style="color:#ccc; font-size:14px;">{row['actual_1rm']}</b> <span style="color:#555;">({row['actual_date']})</span></p>
<p style="color:#888; font-size:11px; margin:4px 0;">推奨: <b style="color:#00ff88; font-size:14px;">{row['rec_weight']}</b> <span style="color:#555;">×{row['reps']}rep</span></p>
<p style="color:#888; font-size:11px; margin:4px 0;">推定1RM: <b style="color:{est_color}; font-size:14px;">{row['estimated_1rm']}</b></p>
</div>
""", unsafe_allow_html=True)

        # アラート表示
        for alert in alerts:
            st.markdown(f'<div class="big3-alert"><span style="color:#ff4444; font-size:13px; font-weight:bold;">{alert}</span></div>', unsafe_allow_html=True)

        if not alerts and any(r["actual_1rm"] != "-" and r["estimated_1rm"] != "-" for r in big3_rows):
            st.markdown('<div class="big3-alert-ok"><span style="color:#44ff44; font-size:13px;">現在の重量設定は適切。このまま続けろ。</span></div>', unsafe_allow_html=True)

        # BIG3合計 + 体重比
        big3_total = 0
        for ex in BIG3:
            ex_1rm_df = df_1rm[df_1rm["種目"] == ex].sort_values("日付", ascending=False)
            if not ex_1rm_df.empty and ex_1rm_df["1RM(kg)"].notna().any():
                big3_total += ex_1rm_df.iloc[0]["1RM(kg)"]
        if big3_total > 0:
            current_weight = df["体重(kg)"].dropna().iloc[-1] if not df.empty else 0
            ratio = big3_total / current_weight if current_weight > 0 else 0
            target_ratio = big3_total / 75.0
            st.markdown(f"""
            <div class="metric-card" style="height:auto; margin-bottom:8px; margin-top:16px;">
                <p class="metric-label">BIG3合計</p>
                <p class="metric-value info">{big3_total:.0f}<span style="font-size:20px">kg</span></p>
                <p class="metric-sub">現在: 体重比 <b style="color:#00ff88;">{ratio:.1f}倍</b>（{current_weight:.1f}kg）</p>
                <p class="metric-sub">目標: 体重比 <b style="color:#ff8800;">{target_ratio:.1f}倍</b>（75kg時）</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # === 期間切り替え ===
        t_period_options = {"全期間": None, "1年": 365, "半年": 180, "3ヶ月": 90, "1ヶ月": 30, "2週間": 14}
        t_selected_period = st.segmented_control("表示期間 ", options=list(t_period_options.keys()), default="全期間")
        t_period_days = t_period_options.get(t_selected_period) if t_selected_period else None

        if t_period_days:
            t_cutoff = pd.Timestamp.now() - pd.Timedelta(days=t_period_days)
            df_train_view = df_train[df_train["日付"] >= t_cutoff]
            df_weight_view = df[df["日付"] >= t_cutoff]
        else:
            df_train_view = df_train
            df_weight_view = df

        # === 体重 vs 総ボリューム 2軸チャート ===
        st.markdown("### 体重 vs トレーニングボリューム")
        st.markdown("<p class='section-desc'>体重が減ってもボリュームが維持できていれば筋肉は守れている。</p>", unsafe_allow_html=True)

        # セッション単位の総ボリュームを算出
        df_session_vol = df_train_view.groupby(df_train_view["日付"].dt.date).agg(
            総ボリューム=("ボリューム", "sum")
        ).reset_index()
        df_session_vol.columns = ["日付", "総ボリューム"]
        df_session_vol["日付"] = pd.to_datetime(df_session_vol["日付"])

        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

        # 体重（左Y軸）
        fig_dual.add_trace(go.Scatter(
            x=df_weight_view["日付"], y=df_weight_view["7日移動平均(kg)"],
            mode="lines",
            name="体重(7日MA)",
            line=dict(color="#ff4444", width=2),
        ), secondary_y=False)

        # 総ボリューム（右Y軸）
        fig_dual.add_trace(go.Scatter(
            x=df_session_vol["日付"], y=df_session_vol["総ボリューム"],
            mode="lines+markers",
            name="セッション総ボリューム",
            line=dict(color="#4488ff", width=1.5),
            marker=dict(size=5),
        ), secondary_y=True)

        fig_dual.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            height=350,
            margin=dict(l=50, r=50, t=30, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#ffffff", size=11)),
            xaxis=dict(gridcolor="#222", tickformat="%m/%d"),
        )
        fig_dual.update_yaxes(title_text="体重(kg)", title_font_color="#ff4444", tickfont_color="#ff4444", gridcolor="#222", secondary_y=False)
        fig_dual.update_yaxes(title_text="ボリューム(kg)", title_font_color="#4488ff", tickfont_color="#4488ff", gridcolor="rgba(0,0,0,0)", secondary_y=True)

        st.plotly_chart(fig_dual, use_container_width=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # === 1RM推移チャート（BIG3） ===
        if not df_1rm.empty and df_1rm["1RM(kg)"].notna().any():
            st.markdown("### 1RM推移（BIG3）")
            st.markdown("<p class='section-desc'>実測（実線）と推定（破線）。推定が実測を追い越したら成長のサイン。</p>", unsafe_allow_html=True)

            colors_1rm = {"スクワット": "#ff4444", "デッドリフト": "#ffaa00", "ベンチプレス": "#4488ff"}
            fig_1rm = go.Figure()

            for ex in BIG3:
                color = colors_1rm[ex]

                # 実測1RM
                ex_actual = df_1rm[df_1rm["種目"] == ex].sort_values("日付")
                if not ex_actual.empty:
                    fig_1rm.add_trace(go.Scatter(
                        x=ex_actual["日付"], y=ex_actual["1RM(kg)"],
                        mode="lines+markers",
                        name=f"{ex}（実測）",
                        line=dict(color=color, width=2),
                        marker=dict(size=8),
                    ))

                # 推定1RM（ログからセッションごとのベスト）
                ex_logs = df_train_view[df_train_view["種目"] == ex].copy()
                if not ex_logs.empty:
                    ex_logs["推定1RM"] = ex_logs.apply(lambda r: estimate_1rm(r["重量(kg)"], r["回数"]), axis=1)
                    ex_est = ex_logs.groupby(ex_logs["日付"].dt.date)["推定1RM"].max().reset_index()
                    ex_est.columns = ["日付", "推定1RM"]
                    ex_est["日付"] = pd.to_datetime(ex_est["日付"])
                    fig_1rm.add_trace(go.Scatter(
                        x=ex_est["日付"], y=ex_est["推定1RM"],
                        mode="lines+markers",
                        name=f"{ex}（推定）",
                        line=dict(color=color, width=1.5, dash="dash"),
                        marker=dict(size=4),
                        opacity=0.7,
                    ))

            fig_1rm.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0E1117",
                plot_bgcolor="#0E1117",
                height=350,
                margin=dict(l=40, r=10, t=30, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#ffffff", size=10)),
                yaxis=dict(title="kg", gridcolor="#222"),
                xaxis=dict(gridcolor="#222", dtick="D1", tickformat="%Y-%m-%d"),
            )

            st.plotly_chart(fig_1rm, use_container_width=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # === 週次トレーニング頻度 ===
        st.markdown("### 週次トレーニング頻度")
        st.markdown("<p class='section-desc'>週2〜3回がコミットメント。赤い点線を下回ったらサボり。</p>", unsafe_allow_html=True)

        df_train_dates = df_train_view.copy()
        df_train_dates["週"] = df_train_dates["日付"].dt.isocalendar().week.astype(int)
        df_train_dates["年"] = df_train_dates["日付"].dt.isocalendar().year.astype(int)
        df_train_dates["年週"] = df_train_dates["年"].astype(str) + "-W" + df_train_dates["週"].astype(str).str.zfill(2)

        weekly_freq = df_train_dates.groupby("年週")["日付"].apply(lambda x: x.dt.date.nunique()).reset_index()
        weekly_freq.columns = ["年週", "回数"]

        fig_freq = go.Figure()
        bar_colors = ["#ff4444" if r < 2 else "#ffaa00" if r < 3 else "#00ff88" for r in weekly_freq["回数"]]

        fig_freq.add_trace(go.Bar(
            x=weekly_freq["年週"], y=weekly_freq["回数"],
            marker_color=bar_colors,
            name="トレーニング回数",
        ))

        fig_freq.add_hline(y=2, line_dash="dot", line_color="#ff4444",
                           annotation_text="最低ライン", annotation_position="top left",
                           annotation_font_color="#ff4444")

        fig_freq.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            height=300,
            margin=dict(l=40, r=10, t=30, b=30),
            yaxis=dict(title="回数", gridcolor="#222", dtick=1),
            xaxis=dict(gridcolor="#222", type="category"),
            showlegend=False,
        )

        st.plotly_chart(fig_freq, use_container_width=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        # === 種目別ボリューム推移 ===
        st.markdown("### 種目別ボリューム推移")
        st.markdown("<p class='section-desc'>漸進性過負荷（Progressive Overload）を確認。右肩上がりなら成長中。</p>", unsafe_allow_html=True)

        all_exercises = sorted(df_train_view["種目"].dropna().unique().tolist())
        selected_exercises = st.multiselect(
            "種目を選択",
            options=all_exercises,
            default=BIG3 if all(ex in all_exercises for ex in BIG3) else all_exercises[:3],
        )

        if selected_exercises:
            fig_vol = go.Figure()
            colors_vol = ["#ff4444", "#ffaa00", "#4488ff", "#00ff88", "#ff88ff", "#88ffff", "#ffff88", "#ff8844", "#8844ff", "#44ff88"]

            for i, ex in enumerate(selected_exercises):
                ex_data = df_train_view[df_train_view["種目"] == ex].copy()
                ex_daily = ex_data.groupby(ex_data["日付"].dt.date)["ボリューム"].sum().reset_index()
                ex_daily.columns = ["日付", "ボリューム"]
                ex_daily["日付"] = pd.to_datetime(ex_daily["日付"])

                fig_vol.add_trace(go.Scatter(
                    x=ex_daily["日付"], y=ex_daily["ボリューム"],
                    mode="lines+markers",
                    name=ex,
                    line=dict(color=colors_vol[i % len(colors_vol)], width=2),
                    marker=dict(size=5),
                ))

            fig_vol.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0E1117",
                plot_bgcolor="#0E1117",
                height=350,
                margin=dict(l=40, r=10, t=30, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#ffffff", size=11)),
                yaxis=dict(title="ボリューム(kg)", gridcolor="#222"),
                xaxis=dict(gridcolor="#222", dtick="D1", tickformat="%Y-%m-%d"),
            )

            st.plotly_chart(fig_vol, use_container_width=True)

# === フッター ===
st.markdown("---")
st.markdown("<p style='text-align:center; color:#444; font-size:11px;'>DDD - Data Driven Diet | 褒めない。事実を見せる。</p>", unsafe_allow_html=True)
