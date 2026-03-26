import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

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
        margin: -8px 0 8px 0;
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
    }

    /* === スマホ（480px以下） === */
    @media (max-width: 480px) {
        /* セクション間の余白 */
        .section-desc {
            margin-top: 16px !important;
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
        .metric-value span {
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
            font-size: 12px !important;
        }
        .summary-card p b {
            font-size: 14px !important;
        }
        h1 { font-size: 20px !important; }
        h3 { font-size: 16px !important; }
        .section-desc {
            font-size: 11px;
        }
        /* Plotlyチャートのタッチ操作改善 */
        .js-plotly-plot .plotly .modebar {
            display: none !important;
        }
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
    df = pd.read_csv(url)
    df["日付"] = pd.to_datetime(df["日付"])
    # 計算列を追加
    df["7日移動平均(kg)"] = df["体重(kg)"].rolling(7, min_periods=1).mean()
    df["7日移動平均_体脂肪率(%)"] = df["体脂肪率(%)"].rolling(7, min_periods=1).mean()
    df["7日移動平均_基礎代謝(kcal)"] = df["基礎代謝(kcal)"].rolling(7, min_periods=1).mean()
    min_weight = df["体重(kg)"].expanding().min()
    df["最低体重からの差分(kg)"] = df["体重(kg)"] - min_weight
    return df

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

# === スコアカード（CSS Grid 2x2） ===
weight = latest["体重(kg)"]
diff_to_target = weight - TARGET_WEIGHT
rebound = latest["最低体重からの差分(kg)"]
rebound_color = "danger" if rebound > 10 else "warning" if rebound > 5 else "info"

START_WEIGHT = 105.7
df_recent_trend = df[df["日付"] > (today - pd.Timedelta(days=30))]
daily_trend = df_recent_trend["体重(kg)"].dropna().diff().mean() if len(df_recent_trend) >= 7 else 0

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

st.markdown(f"""
<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
    <div class="metric-card" style="height:140px;">
        <p class="metric-label">現在の体重</p>
        <p class="metric-value neutral">{weight:.1f}<span style="font-size:20px">kg</span></p>
        <p class="metric-sub">目標{TARGET_WEIGHT:.0f}kgまで あと{diff_to_target:.1f}kg</p>
    </div>
    <div class="metric-card" style="height:140px;">
        <p class="metric-label">リバウンド</p>
        <p class="metric-value {rebound_color}">+{rebound:.1f}<span style="font-size:20px">kg</span></p>
        <p class="metric-sub">最低72.4kgからの増加</p>
    </div>
    <div class="metric-card" style="height:140px;">
        <p class="metric-label">{card3_label}</p>
        <p class="metric-value {card3_color}">{card3_value}</p>
        <p class="metric-sub">{card3_sub}</p>
    </div>
    <div class="metric-card" style="height:140px;">
        <p class="metric-label">サボり率</p>
        <p class="metric-value {skip_color}">{skip_rate:.0f}<span style="font-size:20px">%</span></p>
        <p class="metric-sub">直近30日中 {skip_days}日未測定</p>
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
    # 直近90日のみ使う（「今のペース」を正しく反映するため）
    recent = weights_series.tail(90)
    daily_changes = recent.diff().dropna()
    daily_changes = daily_changes[daily_changes.between(-2, 2)]  # 異常値除去

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

summary_col1, summary_col2, summary_col3 = st.columns(3)

with summary_col1:
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
        <p style="color:#ccc; font-size:14px; margin:4px 0;">最低体重からのリバウンド: <b style="color:#ff4444;">+{weight - df['体重(kg)'].min():.1f}kg</b></p>
    </div>
    """, unsafe_allow_html=True)

with summary_col2:
    st.markdown("<p class='section-desc'>🔮 予測</p>", unsafe_allow_html=True)
    if mc_median is not None:
        pred_color = "#00ff88" if mc_median <= TARGET_WEIGHT else "#ff4444" if mc_median > weight else "#ffaa00"
        st.markdown(f"""
        <div class="summary-card">
            <p style="color:#ccc; font-size:14px; margin:0;">今のペースが続いた場合</p>
            <p style="color:#ccc; font-size:14px; margin:4px 0;">{TARGET_DATE.strftime('%Y/%m/%d')}時点の予測体重:</p>
            <p style="color:{pred_color}; font-size:36px; font-weight:bold; margin:8px 0;">{mc_median:.1f}<span style="font-size:16px;">kg</span></p>
            <p style="color:#888; font-size:11px; margin:0;">過去の変動パターンから5,000回シミュレーション</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="summary-card">
            <p style="color:#888;">予測に必要なデータが不足しています。14日以上の測定が必要です。</p>
        </div>
        """, unsafe_allow_html=True)

with summary_col3:
    st.markdown("<p class='section-desc'>🎯 目標達成確率</p>", unsafe_allow_html=True)
    if mc_prob is not None:
        prob_color = "#00ff88" if mc_prob >= 50 else "#ffaa00" if mc_prob >= 20 else "#ff4444"
        bar_width = max(mc_prob, 2)
        st.markdown(f"""
        <div class="summary-card">
            <p style="color:#ccc; font-size:14px; margin:0;">{TARGET_DATE.strftime('%Y/%m/%d')}までに{TARGET_WEIGHT:.0f}kg達成</p>
            <p style="color:{prob_color}; font-size:48px; font-weight:bold; margin:8px 0;">{mc_prob:.1f}<span style="font-size:20px;">%</span></p>
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
required_daily_deficit = (required_loss * 7200) / max(days_left, 1)  # 脂肪1kg=7200kcal

current_bmr_val = df[df["基礎代謝(kcal)"].notna()].iloc[-1]["基礎代謝(kcal)"] if "基礎代謝(kcal)" in df.columns and df["基礎代謝(kcal)"].notna().any() else None
current_fat = df[df["体脂肪率(%)"].notna()].iloc[-1]["体脂肪率(%)"] if df["体脂肪率(%)"].notna().any() else None

# 体脂肪率に応じた安全減量ペース判定
if current_fat and current_fat > 20:
    safe_weekly_pct = 0.85  # 体重の0.7-1.0%
elif current_fat and current_fat > 15:
    safe_weekly_pct = 0.6   # 体重の0.5-0.7%
else:
    safe_weekly_pct = 0.4   # 体重の0.3-0.5%
safe_weekly_kg = weight * safe_weekly_pct / 100

# --- データから優先度判定 ---
ACTIVITY_FACTOR = ACTIVITY_FACTOR_SETTING  # スプシ設定シートから読み込み
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

# 最優先判定：測定サボりがひどいなら何より先
if meas_rate < 50:
    top3.append({
        "title": "毎朝、体重計に乗れ",
        "detail": f"直近30日で{meas_rate:.0f}%しか測れてない。現実を見ないと何も変わらない。",
    })

# 30日トレンドが増加中なら食事が最優先
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

# 測定率が50-80%ならTOP3に入れる
if 50 <= meas_rate < 80 and len(top3) < 3:
    top3.append({
        "title": "毎朝、体重計に乗れ",
        "detail": f"測定率{meas_rate:.0f}%。歯抜けのデータでは正確な判断ができない。毎朝30秒でいい。",
    })

# 筋トレは常にTOP3候補
if len(top3) < 3:
    top3.append({
        "title": "筋トレ週4回。有酸素より先。",
        "detail": "痩せながら筋肉を残す唯一の方法。走るだけでは筋肉も一緒に消える。",
    })

# タンパク質
if protein_g and len(top3) < 3:
    top3.append({
        "title": f"タンパク質1日{protein_g:.0f}g。鶏むね肉なら約{protein_g / 23:.0f}g。",
        "detail": "筋肉を守る生命線。4-5回に分けて摂れ。プロテインで補ってOK。",
    })

# カロリー（増加中でない場合）
if weight_change_30 <= 0.5 and target_intake and len(top3) < 3:
    top3.append({
        "title": f"1日{target_intake:.0f}kcal以内を守れ",
        "detail": f"消費{tdee:.0f}kcalに対して-{actual_deficit:.0f}kcal。これ以上削ると筋肉が落ちる。",
    })

# 睡眠
if len(top3) < 3:
    top3.append({
        "title": "7時間寝ろ。睡眠は最強のサプリ。",
        "detail": "同じ食事でも寝不足だと筋肉が60%多く落ちる。研究で証明済。",
    })

# --- TOP 3 表示 ---
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

# 実測値
fig_weight.add_trace(go.Scatter(
    x=df_view["日付"], y=df_view["体重(kg)"],
    mode="lines",
    name="体重（日次）",
    line=dict(color="#aaaaaa", width=1),
    opacity=0.7,
))

# 7日移動平均
df_ma = df_view[df_view["7日移動平均(kg)"].notna()]
fig_weight.add_trace(go.Scatter(
    x=df_ma["日付"], y=df_ma["7日移動平均(kg)"],
    mode="lines",
    name="7日移動平均",
    line=dict(color="#ff4444", width=2.5),
))

# 目標ライン（今日→7月末の直線）
fig_weight.add_trace(go.Scatter(
    x=[today, TARGET_DATE],
    y=[weight, TARGET_WEIGHT],
    mode="lines",
    name=f"目標ペース（→{TARGET_WEIGHT:.0f}kg）",
    line=dict(color="#00ff88", width=2, dash="dash"),
))

# 最低体重ライン
min_weight = df["体重(kg)"].min()
fig_weight.add_hline(y=min_weight, line_dash="dot", line_color="#44ff44",
                      annotation_text=f"最低 {min_weight:.1f}kg", annotation_position="top left",
                      annotation_font_color="#44ff44")

# 目標体重ライン
fig_weight.add_hline(y=TARGET_WEIGHT, line_dash="dot", line_color="#00ff88",
                      annotation_text=f"目標 {TARGET_WEIGHT:.0f}kg", annotation_position="top left",
                      annotation_font_color="#00ff88")

# 破滅ライン（全期間・1年の時だけ表示）
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
    xaxis=dict(gridcolor="#222"),
)

st.plotly_chart(fig_weight, use_container_width=True)

# ネクストアクション（選択期間の直近トレンドで判定）
period_label = selected_period if selected_period != "全期間" else "全期間"
df_ma_view = df_view[df_view["7日移動平均(kg)"].notna()]
if len(df_ma_view) >= 14:
    # 期間の後半1/4の移動平均トレンドで判定
    quarter_len = max(len(df_ma_view) // 4, 7)
    ma_recent = df_ma_view.tail(quarter_len)["7日移動平均(kg)"]
    ma_trend = ma_recent.iloc[-1] - ma_recent.iloc[0]
elif len(df_ma_view) >= 3:
    ma_trend = df_ma_view["7日移動平均(kg)"].iloc[-1] - df_ma_view["7日移動平均(kg)"].iloc[0]
else:
    ma_trend = 0

# 優先度順に1つだけ表示
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

# === 2列レイアウト: 体脂肪率 + 基礎代謝推移 ===
left_col, right_col = st.columns(2)

with left_col:
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
        xaxis=dict(gridcolor="#222"),
        showlegend=False,
    )
    st.plotly_chart(fig_fat, use_container_width=True)

    # 体脂肪率 FEEDBACK（選択期間の後半1/4の7日移動平均で判定）
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

with right_col:
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
            xaxis=dict(gridcolor="#222"),
            showlegend=False,
        )
        st.plotly_chart(fig_bmr, use_container_width=True)

        # 基礎代謝 FEEDBACK（選択期間の後半1/4の7日移動平均で判定）
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
    monthly_summary.style.applymap(
        lambda v: "color: #ff4444" if isinstance(v, (int, float)) and v > 0 else
                  "color: #44ff44" if isinstance(v, (int, float)) and v < 0 else "",
        subset=["前月比(kg)"]
    ).format("{:.1f}", subset=["平均体重", "最小体重", "最大体重", "平均体脂肪率", "前月比(kg)"]),
    use_container_width=True,
    height=400,
)

# === フッター ===
st.markdown("---")
st.markdown("<p style='text-align:center; color:#444; font-size:11px;'>DDD - Data Driven Diet | 褒めない。事実を見せる。</p>", unsafe_allow_html=True)
