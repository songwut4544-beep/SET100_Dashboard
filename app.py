import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from datetime import datetime
import time
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os 

st.set_page_config(page_title="Ultimate Trading Dashboard", layout="wide")
st.title("🦅 Eagle All-In-One Trading Dashboard")

DEFAULT_CHART_SETTINGS = {"show_volume": True, "show_bb": False, "show_ema": True, "show_trendline": False, "show_fibo": False, "show_rsi": False, "show_macd": False}

# ========================================================
# 📥 DATA CENTER (ศูนย์ข้อมูล) - อัปโหลดไฟล์ NVDR (รองรับหลายไฟล์พร้อมกัน)
# ========================================================
with st.sidebar:
    st.markdown("### 📥 Data Center (ศูนย์ข้อมูล)")
    # 🌟 เพิ่ม accept_multiple_files=True เพื่อให้เลือกหลายไฟล์ได้พร้อมกัน
    uploaded_files = st.file_uploader("📥 อัปโหลดไฟล์ NVDR จาก SET (.csv)", type=["csv"], accept_multiple_files=True)
    
    if uploaded_files: # ถ้ามีการอัปโหลดไฟล์เข้ามา (ไม่ว่าจะ 1 หรือหลายไฟล์)
        with st.spinner(f"กำลังประมวลผลข้อมูล {len(uploaded_files)} ไฟล์ และอัปเดตฐานข้อมูล..."):
            try:
                import re
                from datetime import datetime
                import os
                import pandas as pd
                
                df_all_new = [] # ตัวแปรชั่วคราวสำหรับเก็บข้อมูลจากทุกไฟล์ที่อัปโหลดเข้ามารอบนี้
                
                for uploaded_file in uploaded_files:
                    # 1. อ่านไฟล์และดึง "วันที่" จาก Header ด้านบน ของแต่ละไฟล์
                    raw_lines = uploaded_file.getvalue().decode("utf-8", errors="replace").splitlines()
                    file_date = None
                    for line in raw_lines[:5]:
                        match = re.search(r'As of (\d{1,2}\s+[a-zA-Z]{3}\s+\d{4})', line)
                        if match:
                            parsed_date = datetime.strptime(match.group(1), "%d %b %Y")
                            file_date = parsed_date.strftime('%Y-%m-%d')
                            break
                    
                    if not file_date:
                        file_date = datetime.today().strftime('%Y-%m-%d')
                    
                    # 2. อ่านข้อมูลตาราง (ข้าม 6 บรรทัดแรก)
                    uploaded_file.seek(0)
                    df_single = pd.read_csv(uploaded_file, skiprows=6)
                    
                    if 'Unnamed: 0' in df_single.columns:
                        df_single = df_single.rename(columns={
                            'Unnamed: 0': 'Symbol',
                            'Buy.1': 'ปริมาณซื้อ',
                            'Sell.1': 'ปริมาณขาย',
                            'Net.1': 'สุทธิ (Net)'
                        })
                    
                    df_single['วันที่'] = file_date
                    df_single['Symbol'] = df_single['Symbol'].astype(str).str.strip()
                    
                    for col in ['ปริมาณซื้อ', 'ปริมาณขาย', 'สุทธิ (Net)']:
                        if col in df_single.columns:
                            df_single[col] = pd.to_numeric(df_single[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    
                    df_single = df_single[['วันที่', 'Symbol', 'ปริมาณซื้อ', 'ปริมาณขาย', 'สุทธิ (Net)']]
                    df_single = df_single[df_single['Symbol'] != 'nan']
                    df_single = df_single[df_single['Symbol'] != '']
                    
                    df_all_new.append(df_single)
                
                # รวมข้อมูลไฟล์ใหม่ทั้งหมดเข้าด้วยกัน
                if df_all_new:
                    df_new_combined = pd.concat(df_all_new, ignore_index=True)
                    
                    # 3. รวมเข้ากับฐานข้อมูลหลักในเครื่อง (NVDR_Data_History.csv)
                    file_path = 'NVDR_Data_History.csv'
                    if os.path.exists(file_path):
                        df_old = pd.read_csv(file_path)
                        df_final_combined = pd.concat([df_old, df_new_combined], ignore_index=True)
                    else:
                        df_final_combined = df_new_combined.copy()
                    
                    # ลบข้อมูลซ้ำ (กรณีมีไฟล์วันที่ซ้ำกัน)
                    df_final_combined['วันที่'] = pd.to_datetime(df_final_combined['วันที่']).dt.strftime('%Y-%m-%d')
                    df_final_combined = df_final_combined.drop_duplicates(subset=['วันที่', 'Symbol'], keep='last')
                    
                    # 🎯 4. กฎเหล็ก: จำกัดข้อมูล 60 วันล่าสุด (Purge ของเก่าทิ้งอัตโนมัติ)
                    unique_dates = sorted(df_final_combined['วันที่'].unique(), reverse=True)
                    keep_dates = unique_dates[:60]
                    df_final_combined = df_final_combined[df_final_combined['วันที่'].isin(keep_dates)]
                    
                    # 5. บันทึกผลลัพธ์
                    df_final_combined.to_csv(file_path, index=False)
                    st.cache_data.clear() # ล้าง Cache เพื่อบังคับให้ตารางโหลดใหม่ทันที
                    st.success(f"✅ อัปเดตสำเร็จทั้งหมด {len(uploaded_files)} ไฟล์! (ปัจจุบันมีข้อมูลสะสมย้อนหลัง {len(keep_dates)} วันทำการ)")
                
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
    st.divider()

# --------------------------------------------------------
# 📌 ฐานข้อมูล SET100 (อัปเดตล่าสุด 100 ตัว)
# --------------------------------------------------------
SET100_SECTORS = {
    "Energy & Utilities": ['BANPU', 'BCP', 'BCPG', 'BGRIM', 'EA', 'EGCO', 'GPSC', 'GULF', 'GUNKUL', 'IRPC', 'OR', 'PTG', 'PTT', 'PTTEP', 'RATCH', 'SPRC', 'TOP', 'WHAUP'],
    "Banking": ['BBL', 'KBANK', 'KKP', 'KTB', 'SCB', 'TCAP', 'TISCO', 'TTB'],
    "Commerce": ['AURA', 'BJC', 'COM7', 'CPALL', 'CRC', 'DOHOME', 'GLOBAL', 'HMPRO', 'MEGA', 'MOSHI', 'MRDIYT'],
    "Finance & Securities": ['AEONTS', 'BAM', 'BLA', 'JMT', 'KTC', 'MTC', 'SAWAD', 'TIDLOR', 'TLI'],
    "Property & Construction": ['AMATA', 'AP', 'AWC', 'CK', 'CPN', 'LH', 'QH', 'SIRI', 'SPALI', 'STECON', 'TOA', 'WHA'],
    "Transportation & Logistics": ['AAV', 'AOT', 'BA', 'BEM', 'BTS', 'PRM', 'RCL', 'THAI'],
    "ICT & Media": ['ADVANC', 'JMART', 'PLANB', 'THCOM', 'TRUE', 'VGI'],
    "Health Care Services": ['BCH', 'BDMS', 'BH', 'CHG', 'PR9'],
    "Food & Beverage": ['BTG', 'CBG', 'CPF', 'GFPT', 'ICHI', 'M', 'OSP', 'TFG', 'TU'],
    "Petro, Materials & Agri": ['IVL', 'PTTGC', 'SCC', 'SCGP', 'STA', 'STGT', 'TASCO'],
    "Tourism & Leisure": ['CENTEL', 'ERW', 'MINT'],
    "Electronics": ['CCET', 'DELTA', 'HANA', 'KCE']
}

THAI_NAMES = {
    # Energy & Utilities
    'BANPU': 'บ้านปู', 'BCP': 'บางจาก', 'BCPG': 'บีซีพีจี', 'BGRIM': 'บี.กริม', 'EA': 'พลังงานบริสุทธิ์', 'EGCO': 'เอ็กโก', 'GPSC': 'โกลบอล เพาเวอร์', 'GULF': 'กัลฟ์', 'GUNKUL': 'กันกุล', 'IRPC': 'ไออาร์พีซี', 'OR': 'โออาร์', 'PTG': 'พีทีจี', 'PTT': 'ปตท.', 'PTTEP': 'ปตท.สผ.', 'RATCH': 'ราช กรุ๊ป', 'SPRC': 'สตาร์ ปิโตรเลียม', 'TOP': 'ไทยออยล์', 'WHAUP': 'ดับบลิวเอชเอ ยูทิลิตี้ส์',
    # Banking
    'BBL': 'แบงก์กรุงเทพ', 'KBANK': 'กสิกรไทย', 'KKP': 'เกียรตินาคินภัทร', 'KTB': 'กรุงไทย', 'SCB': 'เอสซีบี เอกซ์', 'TCAP': 'ทุนธนชาต', 'TISCO': 'ทิสโก้', 'TTB': 'ทีเอ็มบีธนชาต',
    # Commerce
    'AURA': 'ออโรร่า', 'BJC': 'เบอร์ลี่ ยุคเกอร์', 'COM7': 'คอมเซเว่น', 'CPALL': 'ซีพี ออลล์', 'CRC': 'เซ็นทรัล รีเทล', 'DOHOME': 'ดูโฮม', 'GLOBAL': 'สยามโกลบอล', 'HMPRO': 'โฮมโปร', 'MEGA': 'เมก้า ไลฟ์ไซแอ็นซ์', 'MOSHI': 'โมชิ โมชิ', 'MRDIYT': 'มิสเตอร์ ดี.ไอ.วาย.',
    # Finance & Securities
    'AEONTS': 'อิออน ธนสินทรัพย์', 'BAM': 'บริหารสินทรัพย์', 'BLA': 'กรุงเทพประกันชีวิต', 'JMT': 'เจเอ็มที', 'KTC': 'บัตรกรุงไทย', 'MTC': 'เมืองไทย แคปปิตอล', 'SAWAD': 'ศรีสวัสดิ์', 'TIDLOR': 'ติดล้อ', 'TLI': 'ไทยประกันชีวิต',
    # Property & Construction
    'AMATA': 'อมตะ', 'AP': 'เอพี', 'AWC': 'แอสเสท เวิรด์', 'CK': 'ช.การช่าง', 'CPN': 'เซ็นทรัลพัฒนา', 'LH': 'แลนด์แอนด์เฮ้าส์', 'QH': 'ควอลิตี้เฮ้าส์', 'SIRI': 'แสนสิริ', 'SPALI': 'ศุภาลัย', 'STECON': 'ซิโน-ไทย', 'TOA': 'ทีโอเอ เพ้นท์', 'WHA': 'ดับบลิวเอชเอ',
    # Transportation & Logistics
    'AAV': 'เอเชีย เอวิเอชั่น', 'AOT': 'ท่าอากาศยานไทย', 'BA': 'การบินกรุงเทพ', 'BEM': 'ทางด่วนและรถไฟฟ้า', 'BTS': 'บีทีเอส', 'PRM': 'พริมา มารีน', 'RCL': 'อาร์ ซี แอล', 'THAI': 'การบินไทย',
    # ICT & Media
    'ADVANC': 'แอดวานซ์', 'JMART': 'เจมาร์ท กรุ๊ป', 'PLANB': 'แพลน บี มีเดีย', 'THCOM': 'ไทยคม', 'TRUE': 'ทรู', 'VGI': 'วีจีไอ',
    # Health Care Services
    'BCH': 'บางกอก เชน', 'BDMS': 'กรุงเทพดุสิตเวชการ', 'BH': 'บำรุงราษฎร์', 'CHG': 'จุฬารัตน์', 'PR9': 'พระรามเก้า',
    # Food & Beverage
    'BTG': 'เบทาโกร', 'CBG': 'คาราบาว', 'CPF': 'เจริญโภคภัณฑ์อาหาร', 'GFPT': 'จีเอฟพีที', 'ICHI': 'อิชิตัน', 'M': 'เอ็มเค สุกี้', 'OSP': 'โอสถสภา', 'TFG': 'ไทยฟู้ดส์', 'TU': 'ไทยยูเนี่ยน',
    # Petro, Materials & Agri
    'IVL': 'อินโดรามา', 'PTTGC': 'พีทีที โกลบอล', 'SCC': 'ปูนซิเมนต์ไทย', 'SCGP': 'เอสซีจี แพคเกจจิ้ง', 'STA': 'ศรีตรังแอโกร', 'STGT': 'ศรีตรังโกลฟส์', 'TASCO': 'ทิปโก้แอสฟัลท์',
    # Tourism & Leisure
    'CENTEL': 'เซ็นทรัลพลาซา', 'ERW': 'ดิ เอราวัณ', 'MINT': 'ไมเนอร์',
    # Electronics
    'CCET': 'แคล-คอมพ์', 'DELTA': 'เดลต้า', 'HANA': 'ฮานา', 'KCE': 'เคซีอี'
}

ticker_to_sector = {}
all_set100_tickers = []
for sector, tickers in SET100_SECTORS.items():
    for t in tickers:
        ticker_to_sector[t] = sector
        all_set100_tickers.append(t)
all_tickers_bk = [t + ".BK" for t in all_set100_tickers]

@st.cache_data(ttl=3600)
def get_nvdr_smart_money(valid_tickers):
    file_path = 'NVDR_Data_History.csv'
    if not os.path.exists(file_path): return pd.DataFrame(), []
    df = pd.read_csv(file_path)
    df['วันที่'] = pd.to_datetime(df['วันที่'])
    pivot_df = df.pivot(index='Symbol', columns='วันที่', values='สุทธิ (Net)').fillna(0)
    pivot_df = pivot_df[pivot_df.index.isin(valid_tickers)] / 1000000.0
    dates_sorted = sorted(pivot_df.columns, reverse=True)
    pivot_df = pivot_df[dates_sorted]

    # 📌 คำนวณยอดสะสม (เพิ่ม 50D และ 60D)
    pivot_df['Net 5D'] = pivot_df[dates_sorted[0:min(5, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 10D'] = pivot_df[dates_sorted[0:min(10, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 15D'] = pivot_df[dates_sorted[0:min(15, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 20D'] = pivot_df[dates_sorted[0:min(20, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 25D'] = pivot_df[dates_sorted[0:min(25, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 30D'] = pivot_df[dates_sorted[0:min(30, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 40D'] = pivot_df[dates_sorted[0:min(40, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 50D'] = pivot_df[dates_sorted[0:min(50, len(dates_sorted))]].sum(axis=1)
    pivot_df['Net 60D'] = pivot_df[dates_sorted[0:min(60, len(dates_sorted))]].sum(axis=1)

    try:
        hist = yf.download([f"{s}.BK" for s in pivot_df.index], period="3mo", progress=False)
        hist_close = hist['Close'] if isinstance(hist.columns, pd.MultiIndex) else hist[['Close']]
        hist_high = hist['High'] if isinstance(hist.columns, pd.MultiIndex) else hist[['High']]

        # 📌 เพิ่ม 50D, 60D ในลูปคำนวณราคา %
        for d in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
            pct_series = pd.Series(index=pivot_df.index, dtype=float)
            for s in pivot_df.index:
                try:
                    c = hist_close[f"{s}.BK"].dropna()
                    if len(c) > d: first = float(c.iloc[-(d+1)])
                    elif len(c) > 0: first = float(c.iloc[0])
                    else: continue
                    last = float(c.iloc[-1])
                    pct_series[s] = ((last - first) / first) * 100
                except: pct_series[s] = 0.0
            pivot_df[f'ราคาเปลี่ยน % {d}D'] = pct_series

        pivot_df['ห่าง High 3M (%)'] = 0.0
        for s in pivot_df.index:
            try:
                c = hist_close[f"{s}.BK"].dropna()
                h = hist_high[f"{s}.BK"].dropna()
                if len(c) > 0 and len(h) > 0:
                    curr_c = float(c.iloc[-1])
                    max_h = float(h.max())
                    pivot_df.at[s, 'ห่าง High 3M (%)'] = max(0.0, ((max_h - curr_c) / curr_c) * 100)
            except: pass
    except:
        for d in [5, 10, 15, 20, 25, 30, 40, 50, 60]: pivot_df[f'ราคาเปลี่ยน % {d}D'] = 0.0
        pivot_df['ห่าง High 3M (%)'] = 0.0

    def analyze_nvdr_stage(row):
        n, p = row['Net 30D'], row['ราคาเปลี่ยน % 30D']
        return "ขาขึ้นหนุนชัด (Markup)" if n > 0 and p > 0 else "สะสมเก็บของ (Accumulation)" if n > 0 and p <= 0 else "รินขายไล่ราคา (Distribution)" if n <= 0 and p > 0 else "ขาลงรายใหญ่เท (Markdown)"
    pivot_df['NVDR Stage'] = pivot_df.apply(analyze_nvdr_stage, axis=1)

    pivot_df = pivot_df.reset_index()
    date_cols_str = [f"{d.strftime('%Y-%m-%d')} (D{i+1})" for i, d in enumerate(dates_sorted)]
    pivot_df = pivot_df.rename(columns=dict(zip(dates_sorted, date_cols_str)))

    def count_consecutive_buys(row):
        c = 0
        for d in date_cols_str:
            if row[d] > 0: c += 1
            else: break
        return c
    pivot_df['ซื้อต่อเนื่อง (Days)'] = pivot_df.apply(count_consecutive_buys, axis=1)

    # 📌 คำนวณ %พุ่ง(5D) - เทียบยอดล่าสุดกับค่าเฉลี่ย 5 วัน
    if len(dates_sorted) > 0:
        avg_5d = pivot_df[date_cols_str[0:min(5, len(date_cols_str))]].mean(axis=1)
        latest_val = pivot_df[date_cols_str[0]]
        pivot_df['% เทียบเฉลี่ย 5D'] = np.where(avg_5d != 0, ((latest_val - avg_5d) / avg_5d.abs()) * 100, 0.0)
    else:
        pivot_df['% เทียบเฉลี่ย 5D'] = 0.0

    # 📌 จัดเรียงคอลัมน์โดยเพิ่ม 50D, 60D และ %พุ่ง(5D) และ Sort จาก 60D
    cols_order = ['Symbol', 'NVDR Stage', 'ห่าง High 3M (%)', 'Net 60D', 'ราคาเปลี่ยน % 60D', 'Net 50D', 'ราคาเปลี่ยน % 50D', 'Net 40D', 'ราคาเปลี่ยน % 40D', 'Net 30D', 'ราคาเปลี่ยน % 30D', 'Net 25D', 'ราคาเปลี่ยน % 25D', 'Net 20D', 'ราคาเปลี่ยน % 20D', 'Net 15D', 'ราคาเปลี่ยน % 15D', 'Net 10D', 'ราคาเปลี่ยน % 10D', 'Net 5D', 'ราคาเปลี่ยน % 5D', '% เทียบเฉลี่ย 5D', 'ซื้อต่อเนื่อง (Days)'] + date_cols_str
    return pivot_df[cols_order].sort_values(by='Net 60D', ascending=False), date_cols_str

# ========================================================
# 🧠 ENGINE: ฟังก์ชันดึงข้อมูลหุ้น (Technical Indicators)
# ========================================================
@st.cache_data(ttl=3600) # แคชข้อมูล 1 ชั่วโมงเพื่อป้องกันการดึงใหม่ซ้ำซ้อน
def fetch_stock_data(ticker, period="1y"):
    import time
    # ใส่ตัวหน่วงเวลาเล็กน้อยเพื่อป้องกัน Yahoo Finance บล็อก
    time.sleep(0.3)
    
    try:
        df = yf.download(f"{ticker}.BK", period=period, progress=False)
        if df.empty or len(df) < 20: 
            return None
        
        # จัดการข้อมูลที่เป็น MultiIndex (กรณี Yahoo ส่งข้อมูลมาแบบกลุ่ม)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
            
        # คำนวณ Technical Indicators
        df['EMA_15'] = EMAIndicator(close=df['Close'], window=15).ema_indicator()
        df['EMA_50'] = EMAIndicator(close=df['Close'], window=50).ema_indicator()
        df['EMA_200'] = EMAIndicator(close=df['Close'], window=200).ema_indicator()
        
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()
        
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_High'] = bb.bollinger_hband()
        df['BB_Low'] = bb.bollinger_lband()
        
        # คำนวณ % ห่าง High เดิม 60 วัน
        rolling_high = df['High'].rolling(window=60, min_periods=1).max()
        df['Dist to High %'] = ((df['Close'] - rolling_high) / rolling_high) * 100
        
        return df.dropna()
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_advanced_stock_data(tickers):
    data_list = []
    df_history = yf.download(tickers, period="1y", group_by='ticker', progress=False)
    df_history_h1 = yf.download(tickers, period="5d", interval="1h", group_by='ticker', progress=False)
    progress_bar = st.progress(0)
    status_text = st.empty()
    now_ts = time.time()
    today_date = datetime.today().date()
    
    for i, ticker in enumerate(tickers):
        symbol = ticker.replace('.BK', '')
        status_text.text(f"กำลังสแกนเรดาร์ตลาดหุ้นไทยและข้อมูลการเงิน: {symbol} ({i+1}/{len(tickers)})")
        progress_bar.progress((i + 1) / len(tickers))
        try:
            df = df_history[ticker].dropna() if len(tickers) > 1 else df_history.dropna()
            df = df[df['Volume'] > 0] 
            if df.empty or len(df) < 30: continue
            close_prices, volumes = df['Close'].squeeze(), df['Volume'].squeeze()
            vol_mb = (volumes * close_prices) / 1000000 
            curr_close, prev_close = float(close_prices.iloc[-1]), float(close_prices.iloc[-2])
            p_change = ((curr_close - prev_close) / prev_close) * 100
            try: dist_to_high_pct = max(0.0, ((float(df['High'].tail(60).max()) - curr_close) / curr_close) * 100)
            except: dist_to_high_pct = 0.0

            alert_vol_price_up, alert_vol_price_sideway = "-", "-"
            try:
                df_h1 = df_history_h1[ticker].dropna() if len(tickers) > 1 else df_history_h1.dropna()
                if not df_h1.empty and len(df_h1) > 10:
                    df_h1['Vol_MA'] = df_h1['Volume'].rolling(window=10).mean()
                    for idx, row in df_h1.iterrows():
                        if pd.isna(row['Vol_MA']): continue
                        if row['Volume'] > (row['Vol_MA'] * 2.0):
                            price_change_h1 = ((row['Close'] - row['Open']) / row['Open']) * 100
                            days_ago = (today_date - idx.date()).days
                            day_str = "วันนี้!" if days_ago <= 0 else f"{days_ago} วันก่อน"
                            if price_change_h1 >= 1.5 and (days_ago > 0 or p_change >= 0) and (curr_close >= row['Close']): alert_vol_price_up = f"🚀 {day_str}"
                            elif abs(price_change_h1) < 1.0 and curr_close >= row['Low']: alert_vol_price_sideway = f"👀 {day_str}"
            except: pass

            vol_tail_6 = volumes.tail(6)
            v_values = list((vol_tail_6.pct_change().dropna() * 100).values) if len(vol_tail_6) > 1 else []
            while len(v_values) < 5: v_values.insert(0, 0.0)
            
            last_5_vol_diffs = volumes.diff().tail(5).dropna().values
            if len(last_5_vol_diffs) > 0:
                is_up = last_5_vol_diffs[-1] > 0
                c = 0
                for v in reversed(last_5_vol_diffs):
                    if (v > 0) == is_up: c += 1
                    else: break
                v_trend = f"เพิ่มขึ้น ({c}D)" if is_up else f"ลดลง ({c}D)"
            else: v_trend = "-"

            ema20 = EMAIndicator(close=close_prices, window=20).ema_indicator().iloc[-1]
            ema50 = EMAIndicator(close=close_prices, window=50).ema_indicator().iloc[-1]
            try: ema200 = EMAIndicator(close=close_prices, window=200).ema_indicator().iloc[-1]
            except: ema200 = close_prices.mean()
            trend_status = "Up (ขาขึ้น)" if ema20 > ema50 else "Down (ขาลง)" if ema20 < ema50 else "Sideway"
            stage_status = "ขาขึ้น (Markup)" if curr_close > ema200 and ema50 > ema200 and curr_close > ema50 else "ย่อพักตัว (Pullback)" if curr_close > ema200 and ema50 > ema200 else "รีบาวด์ (Rebound)" if curr_close < ema200 and ema50 < ema200 and curr_close > ema50 else "ขาลง (Markdown)" if curr_close < ema200 and ema50 < ema200 else "สะสม (Accumulation)" if curr_close > ema200 and ema50 < ema200 else "เทขาย (Distribution)" if curr_close < ema200 and ema50 > ema200 else "ไร้ทิศทาง (Sideway)"

            macd_ind = MACD(close=close_prices)
            macd_diff = (macd_ind.macd() - macd_ind.macd_signal()).dropna()
            curr_macd = float(macd_ind.macd().dropna().iloc[-1]) if not macd_ind.macd().dropna().empty else 0
            if not macd_diff.empty:
                is_up = macd_diff.iloc[-1] > 0
                c = 0
                for v in reversed(macd_diff.values):
                    if (v > 0) == is_up: c += 1
                    else: break
                macd_status = f"ตัดขึ้น ({c}D)" if is_up else f"ตัดลง ({c}D)"
            else: macd_status = "-"

            rsi_line = RSIIndicator(close=close_prices).rsi().dropna()
            curr_rsi = float(rsi_line.iloc[-1]) if not rsi_line.empty else 0
            rsi_diff = rsi_line - 50
            if not rsi_diff.empty:
                is_up = rsi_diff.iloc[-1] > 0
                c = 0
                for v in reversed(rsi_diff.values):
                    if (v > 0) == is_up: c += 1
                    else: break
                rsi_status = f"ตัดขึ้น 50 ({c}D)" if is_up else f"ตัดลง 50 ({c}D)"
            else: rsi_status = "-"

            tk = yf.Ticker(ticker)
            info = tk.info
            div_yield = info.get('dividendYield', 0) or 0
            ex_div_timestamp = info.get('exDividendDate', None)
            market_cap = info.get('marketCap', 0) or 0
            pbv = info.get('priceToBook', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            roa = info.get('returnOnAssets', 0) or 0
            
            data_list.append({
                "Symbol": symbol, "Thai Name": THAI_NAMES.get(symbol, "-"), "Sector": ticker_to_sector.get(symbol, "Others"), "Sign": "XD" if ex_div_timestamp and ex_div_timestamp > now_ts else "", 
                "Prev Close": prev_close, "Change %": p_change, "Close": curr_close, "Dist to High %": dist_to_high_pct,                 
                "Vol In Up": alert_vol_price_up, "Vol In Sideway": alert_vol_price_sideway, "Vol (MB)": float(vol_mb.iloc[-1]), 
                "Price (5D)": close_prices.tail(5).tolist(), "Vol (5D)": vol_mb.tail(5).tolist(),
                "V-5%": v_values[0], "V-4%": v_values[1], "V-3%": v_values[2], "V-2%": v_values[3], "V-1%": v_values[4],
                "Vol Trend (5D)": v_trend, "Trend": trend_status, "Stage": stage_status,
                "MACD": curr_macd, "MACD Trend": macd_status, "RSI": curr_rsi, "RSI Trend": rsi_status, 
                "Market Cap (M)": market_cap / 1000000.0,
                "PE": info.get('trailingPE', 0) or 0, 
                "PBV": pbv,
                "ROE %": roe * 100,
                "ROA %": roa * 100,
                "Div Yield %": div_yield if div_yield > 1 else div_yield * 100
            })
        except Exception: continue
    progress_bar.empty(); status_text.empty()
    return pd.DataFrame(data_list)

@st.cache_data(ttl=900)
def get_global_indices():
    # จัดกลุ่มดัชนีระดับโลกให้ครอบคลุมทุกทวีปและสินทรัพย์สำคัญ
    indices_groups = {
        "🇺🇸 อเมริกา (US)": {'^DJI': 'Dow Jones', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ'},
        "🇪🇺 ยุโรป (Europe)": {'^FTSE': 'FTSE 100 (UK)', '^GDAXI': 'DAX (GER)', '^FCHI': 'CAC 40 (FRA)'},
        "🌏 เอเชีย (Asia)": {'^N225': 'Nikkei 225 (JPN)', '^HSI': 'Hang Seng (HK)', '000001.SS': 'Shanghai (CHN)'},
        "🛢️ โภคภัณฑ์ (Commodities)": {'GC=F': 'Gold (ทองคำ)', 'CL=F': 'WTI Crude (น้ำมัน)', 'HG=F': 'Copper (ทองแดง)'},
        "₿ คริปโต & ความเสี่ยง": {'BTC-USD': 'Bitcoin (BTC)', '^VIX': 'VIX (ดัชนีความกลัว)', '^TNX': 'US 10Y Yield'}
    }
    
    grouped_data = {}
    # รวบรวม ticker ทั้งหมดเพื่อดึงข้อมูลทีเดียว
    all_tickers = [t for group in indices_groups.values() for t in group.keys()]
    
    try:
        hist = yf.download(all_tickers, period="5d", group_by='ticker', progress=False)
        for group_name, tickers in indices_groups.items():
            group_list = []
            for ticker, name in tickers.items():
                try:
                    df = hist[ticker].dropna() if len(all_tickers) > 1 else hist.dropna()
                    if not df.empty and len(df) >= 2:
                        curr = float(df['Close'].iloc[-1])
                        prev = float(df['Close'].iloc[-2])
                        chg = ((curr - prev) / prev) * 100
                        group_list.append({"Name": name, "Price": curr, "Change": chg, "Ticker": ticker})
                except: continue
            if group_list:
                grouped_data[group_name] = group_list
    except: pass
    return grouped_data

# --- ดึงข้อมูลหลัก ---
with st.spinner('กำลังประมวลผลข้อมูลตลาดดึงตรงระบบ...'):
    df_stocks = get_advanced_stock_data(all_tickers_bk)

if not df_stocks.empty:
    st.sidebar.header("🔍 ระบบค้นหาหลัก")
    search_symbol = st.sidebar.text_input("ค้นหาชื่อหุ้น/ETF (เช่น BGRIM, QQQ):").upper().strip()
    selected_sectors = st.sidebar.multiselect("เลือกกลุ่มอุตสาหกรรม (หุ้นไทย)", options=list(SET100_SECTORS.keys()), default=list(SET100_SECTORS.keys()))
    rsi_range = st.sidebar.slider("ช่วง RSI", 0, 100, (0, 100))
    macd_signal_filter = st.sidebar.radio("สถานะ MACD", ["ทั้งหมด", "อยู่ในเทรนด์ตัดขึ้น", "อยู่ในเทรนด์ตัดลง"])

    filtered_df = df_stocks[(df_stocks['Sector'].isin(selected_sectors)) & (df_stocks['RSI'] >= rsi_range[0]) & (df_stocks['RSI'] <= rsi_range[1])]
    if macd_signal_filter == "อยู่ในเทรนด์ตัดขึ้น": filtered_df = filtered_df[filtered_df['MACD Trend'].str.contains("ตัดขึ้น", na=False)]
    elif macd_signal_filter == "อยู่ในเทรนด์ตัดลง": filtered_df = filtered_df[filtered_df['MACD Trend'].str.contains("ตัดลง", na=False)]

    tab1, tab2, tab5 = st.tabs(["🚀 Thai Stocks Scanner", "👽 NVDR Smart Money Flow", "🧠 AI Market Brain & Overview"])

    # ========================================================
    # 🚀 TAB 1: หุ้นไทย (SET100) + งบการเงิน
    # ========================================================
    with tab1:
        st.subheader("📊 ตารางสรุปสัญญาณเทคนิคอลสั้นกระชับ และข้อมูลอัตราส่วนงบการเงิน")

        # ========================================================
        # 🎯 ชุดโค้ด AI เรดาร์ต้นน้ำ (แทรกก่อนดึงข้อมูลโชว์ในตาราง)
        # ========================================================
        nvdr_df, _ = get_nvdr_smart_money(all_set100_tickers)
        if 'Net 5D' not in filtered_df.columns and not nvdr_df.empty:
            filtered_df = pd.merge(filtered_df, nvdr_df[['Symbol', 'Net 5D']], on='Symbol', how='left')
            filtered_df['Net 5D'] = filtered_df['Net 5D'].fillna(0)

        is_price_up = (filtered_df['Change %'] > 0.5) 
        is_nvdr_in = (filtered_df['Net 5D'] > 20.0) 
        cond_breakout = (filtered_df['Dist to High %'] >= -10.0) & (filtered_df['Dist to High %'] <= -5.0) & is_price_up & is_nvdr_in
        cond_early_flow = (filtered_df['Dist to High %'] >= -25.0) & (filtered_df['Dist to High %'] < -10.0) & is_price_up & is_nvdr_in

        conditions = [cond_breakout, cond_early_flow]
        choices = ["🚀 จ่อทะลุฟ้า", "🔥 พลังต้นน้ำ"]
        filtered_df['🎯 เรดาร์ต้นน้ำ'] = np.select(conditions, choices, default="-")

        display_df = filtered_df[['Sign', 'Symbol', '🎯 เรดาร์ต้นน้ำ', 'Thai Name', 'Prev Close', 'Change %', 'Close', 'Vol (MB)', 'Dist to High %', 'Vol In Up', 'Vol In Sideway', 'Price (5D)', 'Vol (5D)', 'V-5%', 'V-4%', 'V-3%', 'V-2%', 'V-1%', 'Vol Trend (5D)', 'Trend', 'Stage', 'MACD', 'MACD Trend', 'RSI', 'RSI Trend', 'Market Cap (M)', 'PE', 'PBV', 'ROE %', 'ROA %', 'Div Yield %']]
        if search_symbol and search_symbol != "AUDJPY" and not any(x in search_symbol for x in GLOBAL_ASSET_GROUPS.keys()): display_df = display_df[display_df['Symbol'].str.contains(search_symbol, na=False)]

        display_df = display_df.rename(columns={
            'Symbol': 'หุ้น', 'Thai Name': 'ชื่อไทย', 'Prev Close': 'ปิดก่อน', 'Change %': 'เปลี่ยน%', 'Close': 'ล่าสุด', 
            'Vol (MB)': 'มูลค่า(ลบ.)', 'Dist to High %': 'ห่างHighเดิม(%)', 'Vol In Up': 'Volเข้าราคาไป', 'Vol In Sideway': 'Volเข้าราคาไม่ไป', 
            'Price (5D)': 'กราฟราคา', 'Vol (5D)': 'กราฟVol', 'Vol Trend (5D)': 'เทรนด์Vol', 'Trend': 'แนวโน้ม', 'Stage': 'ระยะหุ้น', 
            'MACD Trend': 'เทรนด์MACD', 'RSI Trend': 'เทรนด์RSI',
            'Market Cap (M)': 'Market Cap(ลบ.)', 'PE': 'P/E', 'PBV': 'P/BV', 'ROE %': 'ROE%', 'ROA %': 'ROA%', 'Div Yield %': 'ปันผล%'
        })

        styled_df = display_df.style.map(lambda v: 'color: #00C853; font-weight: bold;' if isinstance(v, str) and ("ตัดขึ้น" in v or "Up" in v or "เพิ่มขึ้น" in v) else 'color: #FF1744; font-weight: bold;' if isinstance(v, str) and ("ตัดลง" in v or "Down" in v or "ลดลง" in v) else '', subset=['เทรนด์Vol', 'แนวโน้ม', 'เทรนด์MACD', 'เทรนด์RSI'])\
                                  .map(lambda v: 'color: #00C853; font-weight: bold;' if isinstance(v, str) and ("สะสม" in v or "ขาขึ้น" in v or "รีบาวด์" in v) else 'color: #FF1744; font-weight: bold;' if isinstance(v, str) and ("เทขาย" in v or "ขาลง" in v) else 'color: #FF9800; font-weight: bold;' if isinstance(v, str) and "ย่อพักตัว" in v else '', subset=['ระยะหุ้น'])\
                                  .map(lambda v: 'background-color: #FFD600; color: black; font-weight: bold;' if v == "XD" else '', subset=['Sign'])\
                                  .map(lambda v: 'background-color: #00C853; color: black; font-weight: bold;' if isinstance(v, float) and v <= 5.0 else '', subset=['ห่างHighเดิม(%)'])\
                                  .map(lambda v: 'color: #00E676; font-weight: bold;' if isinstance(v, str) and "🚀" in v else '', subset=['Volเข้าราคาไป'])\
                                  .map(lambda v: 'color: #FFEA00; font-weight: bold;' if isinstance(v, str) and "👀" in v else '', subset=['Volเข้าราคาไม่ไป'])\
                                  .map(lambda val: 'color: #00E676; font-weight: bold; background-color: rgba(0, 230, 118, 0.1);' if val == "🚀 จ่อทะลุฟ้า" else 'color: #FF6D00; font-weight: bold; background-color: rgba(255, 109, 0, 0.1);' if val == "🔥 พลังต้นน้ำ" else '', subset=['🎯 เรดาร์ต้นน้ำ'])

        selection_event = st.dataframe(
            styled_df,
            column_config={
                "ปิดก่อน": st.column_config.NumberColumn("ปิดก่อน", format="%.2f"), 
                "เปลี่ยน%": st.column_config.NumberColumn("เปลี่ยน%", format="%.2f"), 
                "ล่าสุด": st.column_config.NumberColumn("ล่าสุด", format="%.2f"), 
                "มูลค่า(ลบ.)": st.column_config.NumberColumn("มูลค่า(ลบ.)", format="%.1f"), 
                "ห่างHighเดิม(%)": st.column_config.NumberColumn("ห่างHighเดิม", format="%.2f%%"), 
                "V-5%": st.column_config.NumberColumn("V-5%", format="%d"),
                "V-4%": st.column_config.NumberColumn("V-4%", format="%d"),
                "V-3%": st.column_config.NumberColumn("V-3%", format="%d"),
                "V-2%": st.column_config.NumberColumn("V-2%", format="%d"),
                "V-1%": st.column_config.NumberColumn("V-1%", format="%d"),
                "กราฟราคา": st.column_config.LineChartColumn("กราฟราคา"), 
                "กราฟVol": st.column_config.BarChartColumn("กราฟVol"), 
                "MACD": st.column_config.NumberColumn("MACD", format="%.2f"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.2f"),
                "Market Cap(ลบ.)": st.column_config.NumberColumn("Market Cap(ลบ.)", format="%,.0f"),
                "P/E": st.column_config.NumberColumn("P/E", format="%.2f"),
                "P/BV": st.column_config.NumberColumn("P/BV", format="%.2f"),
                "ROE%": st.column_config.NumberColumn("ROE%", format="%.2f%%"),
                "ROA%": st.column_config.NumberColumn("ROA%", format="%.2f%%"),
                "ปันผล%": st.column_config.NumberColumn("ปันผล%", format="%.2f")
            },
            width='stretch', height=330, hide_index=True, on_select="rerun", selection_mode="single-row"
        )

        active_stock = display_df.iloc[selection_event.selection.rows[0]]['หุ้น'] if selection_event.selection.rows else None

        st.markdown("---")
        st.subheader("📈 หน้าจอกราฟเทคนิคอลและประวัติข้อมูล")
        col_chart1, col_chart2 = st.columns([1, 4])
        with col_chart1:
            st.info("ควบคุมกราฟ ⚙️")
            tf_options = {"Day (D)": {"interval": "1d", "period": "6mo"}, "Week (W)": {"interval": "1wk", "period": "2y"}}
            selected_tf = st.radio("เลือกกรอบเวลา (Timeframe)", list(tf_options.keys()), key="tf_thai")
            st.divider()
            show_vol = st.checkbox("แสดง Volume", value=DEFAULT_CHART_SETTINGS["show_volume"], key="v_thai")
            show_bb = st.checkbox("Bollinger Bands", value=DEFAULT_CHART_SETTINGS["show_bb"], key="bb_thai")
            show_ema = st.checkbox("EMA (20, 50, 200)", value=DEFAULT_CHART_SETTINGS["show_ema"], key="ema_thai")
            show_fibo = st.checkbox("🎯 เปิดเส้น Fibonacci", value=DEFAULT_CHART_SETTINGS["show_fibo"], key="fibo_thai")
            show_rsi = st.checkbox("แสดง RSI (14)", value=DEFAULT_CHART_SETTINGS["show_rsi"], key="rsi_thai")
            show_macd = st.checkbox("แสดง MACD", value=DEFAULT_CHART_SETTINGS["show_macd"], key="macd_thai")

        with col_chart2:
            if active_stock:
                with st.spinner(f'กำลังโหลดความละเอียดข้อมูลหุ้น {active_stock}...'):
                    tf_params = tf_options[selected_tf]
                    df_chart = yf.Ticker(f"{active_stock}.BK").history(period=tf_params["period"], interval=tf_params["interval"])
                    if df_chart.empty: st.error(f"⚠️ ไม่สามารถดึงข้อมูลกราฟของ {active_stock} ได้")
                    else:
                        df_chart.index = df_chart.index.tz_localize(None)
                        df_chart = df_chart[df_chart['Volume'] > 0]
                        close_s = df_chart['Close'].squeeze()
                        
                        rows = 1
                        row_heights = [0.6] if show_vol or show_rsi or show_macd else [1.0]
                        if show_vol: rows += 1; row_heights.append(0.2)
                        if show_rsi: rows += 1; row_heights.append(0.2)
                        if show_macd: rows += 1; row_heights.append(0.2)
                        row_heights = [h/sum(row_heights) for h in row_heights]

                        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
                        fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=close_s, name="Price"), row=1, col=1)
                        
                        if show_fibo:
                            max_p, min_p = float(df_chart['High'].max()), float(df_chart['Low'].min())
                            diff = max_p - min_p
                            for lvl, val, col in zip(["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"], [min_p, max_p - 0.764 * diff, max_p - 0.618 * diff, max_p - 0.5 * diff, max_p - 0.382 * diff, max_p - 0.214 * diff, max_p], ['#f44336', '#ff9800', '#ffeb3b', '#4caf50', '#2196f3', '#9c27b0', '#f44336']):
                                fig.add_hline(y=val, line_dash="dash", line_color=col, annotation_text=f"Fibo {lvl} ({val:.2f})", annotation_position="top left", row=1, col=1)

                        if show_bb:
                            bb = BollingerBands(close=close_s, window=20, window_dev=2)
                            fig.add_trace(go.Scatter(x=df_chart.index, y=bb.bollinger_hband(), line=dict(color='rgba(173,216,230,0.5)', width=1), name="BB Upper"), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_chart.index, y=bb.bollinger_lband(), line=dict(color='rgba(173,216,230,0.5)', width=1), name="BB Lower", fill='tonexty'), row=1, col=1)

                        if show_ema:
                            fig.add_trace(go.Scatter(x=df_chart.index, y=EMAIndicator(close_s, 20).ema_indicator(), line=dict(color='#2962FF', width=1.5), name="EMA 20"), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_chart.index, y=EMAIndicator(close_s, 50).ema_indicator(), line=dict(color='#FF6D00', width=1.5), name="EMA 50"), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_chart.index, y=EMAIndicator(close_s, 200).ema_indicator(), line=dict(color='#00C853', width=2), name="EMA 200"), row=1, col=1)

                        current_row = 2
                        if show_vol:
                            fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=['#00C853' if c >= o else '#D50000' for o, c in zip(df_chart['Open'], close_s)], name="Volume"), row=current_row, col=1)
                            current_row += 1

                        if show_rsi:
                            fig.add_trace(go.Scatter(x=df_chart.index, y=RSIIndicator(close_s).rsi(), line=dict(color='purple', width=2), name="RSI"), row=current_row, col=1)
                            fig.add_hline(y=70, line_dash="dot", line_color="red", row=current_row, col=1)
                            fig.add_hline(y=30, line_dash="dot", line_color="green", row=current_row, col=1)
                            current_row += 1
                            
                        if show_macd:
                            macd_ind = MACD(close=close_s)
                            m_hist = macd_ind.macd_diff().dropna()
                            fig.add_trace(go.Scatter(x=df_chart.index, y=macd_ind.macd(), line=dict(color='blue', width=2), name="MACD"), row=current_row, col=1)
                            fig.add_trace(go.Scatter(x=df_chart.index, y=macd_ind.macd_signal(), line=dict(color='orange', width=2), name="Signal"), row=current_row, col=1)
                            fig.add_trace(go.Bar(x=m_hist.index, y=m_hist, marker_color=['#00C853' if val >= 0 else '#D50000' for val in m_hist], name="Histogram"), row=current_row, col=1)

                        dt_all = pd.date_range(start=df_chart.index.min(), end=df_chart.index.max(), freq='D')
                        fig.update_xaxes(rangebreaks=[dict(values=dt_all.difference(df_chart.index.normalize().unique()).strftime("%Y-%m-%d").tolist())])
                        fig.update_layout(title=f"กราฟ {active_stock} [{selected_tf}]", xaxis_rangeslider_visible=False, height=320 + (rows * 100), margin=dict(l=20, r=20, t=40, b=20), showlegend=False, hovermode='x unified')
                        st.plotly_chart(fig, use_container_width=True)

                    # ---------------------------------------------------------
                    # 🌟 เพิ่มข้อมูลงบการเงิน (กำไรสุทธิ) ใต้กราฟ ก่อนข้อมูล NVDR
                    # ---------------------------------------------------------
                    st.divider()
                    st.markdown(f"### 💰 สรุปกำไรสุทธิ (Net Profit): {active_stock}")
                    with st.spinner("กำลังดึงข้อมูลงบการเงิน..."):
                        try:
                            tk_fin = yf.Ticker(f"{active_stock}.BK")
                            inc_y = tk_fin.income_stmt
                            inc_q = tk_fin.quarterly_income_stmt
                            
                            col_fin1, col_fin2 = st.columns(2)
                            
                            with col_fin1:
                                st.markdown("**📅 กำไรสุทธิรายปี (3 ปีย้อนหลัง)**")
                                if not inc_y.empty and 'Net Income' in inc_y.index:
                                    net_y = inc_y.loc['Net Income'].dropna().head(3)
                                    df_y = pd.DataFrame(net_y).reset_index()
                                    df_y.columns = ['ปี', 'กำไรสุทธิ (ล้านบาท)']
                                    df_y['ปี'] = df_y['ปี'].dt.year.astype(str)
                                    df_y['กำไรสุทธิ (ล้านบาท)'] = df_y['กำไรสุทธิ (ล้านบาท)'] / 1000000.0
                                    st.dataframe(df_y.style.format({"กำไรสุทธิ (ล้านบาท)": "{:,.2f}"}), hide_index=True, use_container_width=True)
                                else:
                                    st.info("ไม่มีข้อมูลกำไรรายปี")

                            with col_fin2:
                                st.markdown("**📊 กำไรสุทธิรายไตรมาส (ล่าสุด)**")
                                if not inc_q.empty and 'Net Income' in inc_q.index:
                                    net_q = inc_q.loc['Net Income'].dropna().head(4)
                                    df_q = pd.DataFrame(net_q).reset_index()
                                    df_q.columns = ['ไตรมาส', 'กำไรสุทธิ (ล้านบาท)']
                                    df_q['ไตรมาส'] = df_q['ไตรมาส'].dt.to_period('Q').astype(str)
                                    df_q['กำไรสุทธิ (ล้านบาท)'] = df_q['กำไรสุทธิ (ล้านบาท)'] / 1000000.0
                                    st.dataframe(df_q.style.format({"กำไรสุทธิ (ล้านบาท)": "{:,.2f}"}), hide_index=True, use_container_width=True)
                                else:
                                    st.info("ไม่มีข้อมูลกำไรรายไตรมาส")
                        except Exception as e:
                            st.warning("ไม่สามารถดึงข้อมูลงบการเงินได้ในขณะนี้")

                    st.divider()
                    st.markdown(f"### 👽 ยอดซื้อขาย NVDR รายวันย้อนหลัง: {active_stock}")
                    if os.path.exists('NVDR_Data_History.csv'):
                        df_all_nvdr = pd.read_csv('NVDR_Data_History.csv')
                        df_stock_nvdr = df_all_nvdr[df_all_nvdr['Symbol'].astype(str).str.strip() == active_stock.strip()].sort_values(by='วันที่', ascending=False)
                        
                        if not df_stock_nvdr.empty:
                            df_stock_nvdr = df_stock_nvdr.copy()
                            df_stock_nvdr['วันที่'] = pd.to_datetime(df_stock_nvdr['วันที่'])
                            
                            try:
                                # ดึงข้อมูลรายวันของหุ้นตัวนั้น
                                hist_daily = yf.Ticker(f"{active_stock}.BK").history(period="3mo", interval="1d")
                                hist_daily.index = hist_daily.index.tz_localize(None).normalize()
                                
                                # คำนวณมูลค่าตลาดรวมดั้งเดิม (Volume x Close) เพื่อใช้เป็นฐานคำนวณ Net % 
                                hist_daily['Original_Market_Value'] = hist_daily['Volume'] * hist_daily['Close']
                                
                                # ข้อ 4: ยอดซื้อขายรวมตลาด (แก้ไขเป็น x2 เพื่อรวมฝั่งซื้อและขาย)
                                hist_daily['Market_Total_Value_x2'] = hist_daily['Original_Market_Value'] * 2
                                df_stock_nvdr['ยอดซื้อขายรวมตลาด (x2)'] = df_stock_nvdr['วันที่'].map(hist_daily['Market_Total_Value_x2']).fillna(0)
                                df_stock_nvdr['Original_Market_Value'] = df_stock_nvdr['วันที่'].map(hist_daily['Original_Market_Value']).fillna(0)
                                
                                # ข้อ 5: ยอดซื้อขาย NVDR (รวม) = มูลค่าซื้อ + มูลค่าขาย
                                df_stock_nvdr['ยอดซื้อขาย NVDR (รวม)'] = df_stock_nvdr['ปริมาณซื้อ'] + df_stock_nvdr['ปริมาณขาย']
                                
                                # ข้อ 6: สัดส่วน Net NVDR % (คงเดิม = สุทธิ / มูลค่าตลาดรวมเดิมฝั่งเดียว)
                                df_stock_nvdr['สัดส่วน Net NVDR (%)'] = np.where(
                                    df_stock_nvdr['Original_Market_Value'] != 0, 
                                    (df_stock_nvdr['สุทธิ (Net)'] / df_stock_nvdr['Original_Market_Value']) * 100, 
                                    0.0
                                )
                                
                                # ข้อ 7: Participation Rate % = (ยอดซื้อขาย NVDR รวม / ยอดซื้อขายรวมตลาด x2) * 100
                                df_stock_nvdr['Participation Rate (%)'] = np.where(
                                    df_stock_nvdr['ยอดซื้อขายรวมตลาด (x2)'] != 0, 
                                    (df_stock_nvdr['ยอดซื้อขาย NVDR (รวม)'] / df_stock_nvdr['ยอดซื้อขายรวมตลาด (x2)']) * 100, 
                                    0.0
                                )
                            except:
                                df_stock_nvdr['ยอดซื้อขายรวมตลาด (x2)'] = 0.0
                                df_stock_nvdr['ยอดซื้อขาย NVDR (รวม)'] = 0.0
                                df_stock_nvdr['สัดส่วน Net NVDR (%)'] = 0.0
                                df_stock_nvdr['Participation Rate (%)'] = 0.0

                            df_stock_nvdr['วันที่'] = df_stock_nvdr['วันที่'].dt.strftime('%Y-%m-%d')
                            
                            # จัด Format การแสดงผลทั้งหมด
                            styled_nvdr_hist = df_stock_nvdr.drop(columns=['Symbol', 'Original_Market_Value'], errors='ignore').style.format({
                                "ปริมาณซื้อ": "{:,.0f}", 
                                "ปริมาณขาย": "{:,.0f}", 
                                "สุทธิ (Net)": "{:,.0f}",
                                "ยอดซื้อขายรวมตลาด (x2)": "{:,.0f}",
                                "ยอดซื้อขาย NVDR (รวม)": "{:,.0f}",
                                "สัดส่วน Net NVDR (%)": "{:+.2f}%",
                                "Participation Rate (%)": "{:.2f}%"
                            }).map(
                                lambda val: 'color: #00C853; font-weight: bold;' if val > 0 else 'color: #FF1744; font-weight: bold;' if val < 0 else '', 
                                subset=['สุทธิ (Net)', 'สัดส่วน Net NVDR (%)']
                            ).map(
                                # ไฮไลท์สีน้ำเงินเข้ม ถ้าต่างชาติมีส่วนร่วมคุมกระดานเกิน 15%
                                lambda val: 'color: #2962FF; font-weight: bold;' if val >= 15.0 else '', 
                                subset=['Participation Rate (%)']
                            )

                            st.dataframe(styled_nvdr_hist, use_container_width=True, hide_index=True)
            else: st.info("👆 คลิกเลือกแถวชื่อหุ้นที่ตารางด้านบน เพื่อดึงข้อมูลกราฟและข้อมูลจำเพาะ")

    # ========================================================
    # 👽 TAB 2: เม็ดเงินต่างชาติ NVDR
    # ========================================================
    with tab2:
        st.subheader("👽 เรดาร์ตรวจจับเม็ดเงินต่างชาติสะสมแบ่งช่วงเวลา (SET100)")
        
        with st.spinner("กำลังประกอบตารางสรุปเม็ดเงินย้อนหลัง..."):
            nvdr_df, date_cols = get_nvdr_smart_money(all_set100_tickers)
            if not nvdr_df.empty:
                nvdr_df = nvdr_df.copy()
                if search_symbol and search_symbol != "AUDJPY": nvdr_df = nvdr_df[nvdr_df['Symbol'].str.contains(search_symbol, na=False)]
                
                nvdr_df.insert(1, 'Thai Name', nvdr_df['Symbol'].map(lambda x: THAI_NAMES.get(x, "-")))
                # 1. เปลี่ยนชื่อคอลัมน์ (เพิ่ม 50D, 60D และ %พุ่ง(5D))
                nvdr_display = nvdr_df.rename(columns={'Symbol': 'หุ้น', 'Thai Name': 'ชื่อไทย', 'NVDR Stage': 'สภาพสถานะ', 'ห่าง High 3M (%)': 'ห่างHighเดิม(%)', 'Net 60D': 'สะสม60D(ลบ.)', 'ราคาเปลี่ยน % 60D': 'ราคา%60D', 'Net 50D': 'สะสม50D(ลบ.)', 'ราคาเปลี่ยน % 50D': 'ราคา%50D', 'Net 40D': 'สะสม40D(ลบ.)', 'ราคาเปลี่ยน % 40D': 'ราคา%40D', 'Net 30D': 'สะสม30D(ลบ.)', 'ราคาเปลี่ยน % 30D': 'ราคา%30D', 'Net 25D': 'สะสม25D(ลบ.)', 'ราคาเปลี่ยน % 25D': 'ราคา%25D', 'Net 20D': 'สะสม20D(ลบ.)', 'ราคาเปลี่ยน % 20D': 'ราคา%20D', 'Net 15D': 'สะสม15D(ลบ.)', 'ราคาเปลี่ยน % 15D': 'ราคา%15D', 'Net 10D': 'สะสม10D(ลบ.)', 'ราคาเปลี่ยน % 10D': 'ราคา%10D', 'Net 5D': 'สะสม5D(ลบ.)', 'ราคาเปลี่ยน % 5D': 'ราคา%5D', '% เทียบเฉลี่ย 5D': '%พุ่ง(5D)', 'ซื้อต่อเนื่อง (Days)': 'ซื้อติดกัน'})

                # 2. จัด Format ตัวเลข (รวมคอลัมน์ใหม่เข้าในระบบปัดเศษเดิม)
                format_dict = {col: '{:,.0f}' for col in date_cols + ['สะสม60D(ลบ.)', 'สะสม50D(ลบ.)', 'สะสม40D(ลบ.)', 'สะสม30D(ลบ.)', 'สะสม25D(ลบ.)', 'สะสม20D(ลบ.)', 'สะสม15D(ลบ.)', 'สะสม10D(ลบ.)', 'สะสม5D(ลบ.)']}
                format_dict.update({col: '{:+.2f}%' for col in ['ราคา%60D', 'ราคา%50D', 'ราคา%40D', 'ราคา%30D', 'ราคา%25D', 'ราคา%20D', 'ราคา%15D', 'ราคา%10D', 'ราคา%5D', '%พุ่ง(5D)']})
                format_dict.update({'ห่างHighเดิม(%)': '{:.2f}%'})

                # 3. ใส่พื้นหลังไล่สี (Gradient)
                styled = nvdr_display.style.format(format_dict).background_gradient(subset=date_cols, cmap='RdYlGn', axis=None).background_gradient(subset=['สะสม60D(ลบ.)', 'สะสม50D(ลบ.)', 'สะสม40D(ลบ.)', 'สะสม30D(ลบ.)', 'สะสม25D(ลบ.)', 'สะสม20D(ลบ.)', 'สะสม15D(ลบ.)', 'สะสม10D(ลบ.)', 'สะสม5D(ลบ.)'], cmap='RdYlGn', axis=None)
                
                # 4. ใส่สีตัวหนังสือ (เขียว/แดง)
                for col in ['ราคา%60D', 'ราคา%50D', 'ราคา%40D', 'ราคา%30D', 'ราคา%25D', 'ราคา%20D', 'ราคา%15D', 'ราคา%10D', 'ราคา%5D', '%พุ่ง(5D)']: 
                    styled = styled.map(lambda val: 'color: #00C853; font-weight: bold;' if val > 0 else 'color: #FF1744; font-weight: bold;' if val < 0 else '', subset=[col])

                # 5. ใส่สีไฮไลท์เงื่อนไขพิเศษ (ของเดิมที่ดึงกลับมาครบ 100%)
                styled = styled.map(lambda val: 'background-color: #00C853; color: black; font-weight: bold;' if val >= 3 else '', subset=['ซื้อติดกัน'])\
                               .map(lambda val: 'color: #00C853; font-weight: bold;' if isinstance(val, str) and ("สะสม" in val or "ขาขึ้น" in val) else 'color: #FF1744; font-weight: bold;' if isinstance(val, str) and ("เทขาย" in val or "ขาลง" in val or "รินขาย" in val) else '', subset=['สภาพสถานะ'])\
                               .map(lambda val: 'background-color: #00C853; color: black; font-weight: bold;' if isinstance(val, (int, float)) and pd.notna(val) and val <= 5.0 else '', subset=['ห่างHighเดิม(%)'])
                
                selection_nvdr = st.dataframe(
                    styled, width='stretch', height=350, hide_index=True, on_select="rerun", selection_mode="single-row", key="nvdr_table",
                    column_config={"ชื่อไทย": st.column_config.TextColumn("ชื่อไทย", width="small")}
                )
                active_nvdr_stock = nvdr_display.iloc[selection_nvdr.selection.rows[0]]['หุ้น'] if selection_nvdr.selection.rows and selection_nvdr.selection.rows[0] < len(nvdr_display) else None

                st.markdown("---")
                st.subheader("📈 หน้าจอกราฟเทคนิคอล (วิเคราะห์แรงซื้อ/ขาย NVDR เทียบกราฟ)")
                col_n_c1, col_n_c2 = st.columns([1, 4])
                with col_n_c1:
                    st.info("ควบคุมกราฟ ⚙️")
                    selected_tf_n = st.radio("เลือกกรอบเวลา (Timeframe)", list(tf_options.keys()), key="tf_nvdr")
                    st.divider()
                    show_vol_n = st.checkbox("แสดง Volume", value=True, key="v_nvdr")
                    show_bb_n = st.checkbox("Bollinger Bands", value=False, key="bb_nvdr")
                    show_ema_n = st.checkbox("EMA (20, 50, 200)", value=True, key="ema_nvdr")
                    show_fibo_n = st.checkbox("🎯 เปิดเส้น Fibonacci", value=False, key="fibo_nvdr")
                    show_rsi_n = st.checkbox("แสดง RSI (14)", value=False, key="rsi_nvdr")
                    show_macd_n = st.checkbox("แสดง MACD", value=False, key="macd_nvdr")

                with col_n_c2:
                    if active_nvdr_stock:
                        with st.spinner(f'กำลังโหลดความละเอียดข้อมูลกราฟ {active_nvdr_stock}...'):
                            df_chart = yf.Ticker(f"{active_nvdr_stock}.BK").history(period=tf_options[selected_tf_n]["period"], interval=tf_options[selected_tf_n]["interval"])
                            if not df_chart.empty:
                                df_chart.index = df_chart.index.tz_localize(None)
                                df_chart = df_chart[df_chart['Volume'] > 0]
                                close_s = df_chart['Close'].squeeze()
                                
                                rows = 1
                                row_heights = [0.6] if show_vol_n or show_rsi_n or show_macd_n else [1.0]
                                if show_vol_n: rows += 1; row_heights.append(0.2)
                                if show_rsi_n: rows += 1; row_heights.append(0.2)
                                if show_macd_n: rows += 1; row_heights.append(0.2)
                                row_heights = [h/sum(row_heights) for h in row_heights]

                                fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
                                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=close_s, name="Price"), row=1, col=1)
                                
                                if show_fibo_n:
                                    max_p, min_p = float(df_chart['High'].max()), float(df_chart['Low'].min())
                                    diff = max_p - min_p
                                    for lvl, val, col in zip(["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"], [min_p, max_p - 0.764 * diff, max_p - 0.618 * diff, max_p - 0.5 * diff, max_p - 0.382 * diff, max_p - 0.214 * diff, max_p], ['#f44336', '#ff9800', '#ffeb3b', '#4caf50', '#2196f3', '#9c27b0', '#f44336']):
                                        fig.add_hline(y=val, line_dash="dash", line_color=col, annotation_text=f"Fibo {lvl} ({val:.2f})", annotation_position="top left", row=1, col=1)

                                if show_bb_n:
                                    bb = BollingerBands(close=close_s, window=20, window_dev=2)
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=bb.bollinger_hband(), line=dict(color='rgba(173,216,230,0.5)', width=1), name="BB Upper"), row=1, col=1)
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=bb.bollinger_lband(), line=dict(color='rgba(173,216,230,0.5)', width=1), name="BB Lower", fill='tonexty'), row=1, col=1)

                                if show_ema_n:
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=EMAIndicator(close_s, 20).ema_indicator(), line=dict(color='#2962FF', width=1.5), name="EMA 20"), row=1, col=1)
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=EMAIndicator(close_s, 50).ema_indicator(), line=dict(color='#FF6D00', width=1.5), name="EMA 50"), row=1, col=1)
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=EMAIndicator(close_s, 200).ema_indicator(), line=dict(color='#00C853', width=2), name="EMA 200"), row=1, col=1)

                                current_row = 2
                                if show_vol_n:
                                    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=['#00C853' if c >= o else '#D50000' for o, c in zip(df_chart['Open'], close_s)], name="Volume"), row=current_row, col=1)
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Volume'].rolling(window=20).mean(), line=dict(color='#FF9800', width=1.5), name="Vol MA(20)"), row=current_row, col=1)
                                    current_row += 1

                                if show_rsi_n:
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=RSIIndicator(close_s).rsi(), line=dict(color='purple', width=2), name="RSI"), row=current_row, col=1)
                                    fig.add_hline(y=70, line_dash="dot", line_color="red", row=current_row, col=1)
                                    fig.add_hline(y=30, line_dash="dot", line_color="green", row=current_row, col=1)
                                    current_row += 1
                                    
                                if show_macd_n:
                                    macd_ind = MACD(close=close_s)
                                    m_hist = macd_ind.macd_diff().dropna()
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=macd_ind.macd(), line=dict(color='blue', width=2), name="MACD"), row=current_row, col=1)
                                    fig.add_trace(go.Scatter(x=df_chart.index, y=macd_ind.macd_signal(), line=dict(color='orange', width=2), name="Signal"), row=current_row, col=1)
                                    fig.add_trace(go.Bar(x=m_hist.index, y=m_hist, marker_color=['#00C853' if val >= 0 else '#D50000' for val in m_hist], name="Histogram"), row=current_row, col=1)

                                dt_all = pd.date_range(start=df_chart.index.min(), end=df_chart.index.max(), freq='D')
                                fig.update_xaxes(rangebreaks=[dict(values=dt_all.difference(df_chart.index.normalize().unique()).strftime("%Y-%m-%d").tolist())])
                                fig.update_layout(title=f"กราฟ {active_nvdr_stock} [{selected_tf_n}]", xaxis_rangeslider_visible=False, height=320 + (rows * 100), margin=dict(l=20, r=20, t=40, b=20), showlegend=False, hovermode='x unified')
                                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("⚠️ ยังไม่พบฐานข้อมูล NVDR_Data_History.csv")


    # ========================================================
    # 🧠 TAB 5: AI Market Brain & Predictive Overview
    # ========================================================
    with tab5:
        st.subheader("🧠 ศูนย์บัญชาการตลาด และ AI พยากรณ์แนวโน้ม (Advanced Market Brain)")
        
        # --- 1. Global Overview (จัดกลุ่มครอบคลุมทั่วโลก) ---
        st.markdown("### 🌍 1. Global Macro Overview (ดัชนีชี้วัดระดับโลก)")
        global_groups = get_global_indices()
        if global_groups:
            cols_global = st.columns(len(global_groups))
            for i, (group_name, items) in enumerate(global_groups.items()):
                with cols_global[i]:
                    st.markdown(f"**{group_name}**")
                    for item in items:
                        st.metric(label=item["Name"], value=f"{item['Price']:,.2f}", delta=f"{item['Change']:+.2f}%", delta_color="inverse" if "VIX" in item["Name"] else "normal")
        st.divider()

        # --- 2. SET Market Flow ---
        st.markdown("### 🏦 2. ภาพรวมกระแสเงินทุนและอุตสาหกรรม (SET Market Flow)")
        flow_file = 'Investor_Flow.csv'
        if os.path.exists(flow_file):
            flow_df = pd.read_csv(flow_file)
            flow_df.columns = flow_df.columns.str.strip() 
            flow_df['วันที่'] = pd.to_datetime(flow_df['วันที่'], format='%y-%m-%d', errors='coerce')
            flow_df = flow_df.sort_values('วันที่', ascending=True).reset_index(drop=True)
            
            # --- ตารางสรุป 1D ถึง 12 เดือน (เพิ่ม 1-4 วันแล้ว) ---
            st.markdown("**📊 ตารางสรุปยอดซื้อขายสุทธิสะสม (Fund Flow Accumulation)**")
            periods = {"1 วัน": 1, "2 วัน": 2, "3 วัน": 3, "4 วัน": 4, "5 วัน": 5, "15 วัน": 15, "1 เดือน": 20, "2 เดือน": 40, "3 เดือน": 60, "4 เดือน": 80, "5 เดือน": 100, "6 เดือน": 120, "7 เดือน": 140, "8 เดือน": 160, "9 เดือน": 180, "10 เดือน": 200, "11 เดือน": 220, "12 เดือน": 240}
            summary_data = []
            
            for p_name, days in periods.items():
                slice_df = flow_df.tail(days) if len(flow_df) >= days else flow_df
                summary_data.append({
                    "ระยะเวลา": p_name,
                    "ต่างชาติ (MB)": slice_df['ต่างชาติ'].sum(),
                    "กองทุน+โบรก (MB)": slice_df['กองทุนและโบรกเกอร์'].sum(),
                    "รายย่อย (MB)": slice_df['รายย่อย'].sum()
                })
            
            st.dataframe(pd.DataFrame(summary_data).style.format({"ต่างชาติ (MB)": "{:,.2f}", "กองทุน+โบรก (MB)": "{:,.2f}", "รายย่อย (MB)": "{:,.2f}"}).map(lambda val: 'color: #00C853; font-weight: bold;' if val > 0 else 'color: #FF1744; font-weight: bold;' if val < 0 else '', subset=["ต่างชาติ (MB)", "กองทุน+โบรก (MB)", "รายย่อย (MB)"]), use_container_width=True, hide_index=True)
            
            # --- กราฟซ้อนทับ (Shared X-axis) ---
            st.markdown("**📈 กราฟความสัมพันธ์ SET Index และ ยอดเงินทุนสะสม (Cumulative Fund Flow)**")
            
            # คำนวณยอดสะสม (Cumulative Sum) ของแต่ละกลุ่ม
            flow_df['ต่างชาติ_สะสม'] = flow_df['ต่างชาติ'].cumsum()
            flow_df['กองทุนและปอบ_สะสม'] = flow_df['กองทุนและโบรกเกอร์'].cumsum()
            flow_df['รายย่อย_สะสม'] = flow_df['รายย่อย'].cumsum()

            fig_combined = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08,
                row_heights=[0.5, 0.5],
                subplot_titles=("ดัชนีตลาดหลักทรัพย์ (SET Index)", "ยอดซื้อขายสุทธิสะสม (Cumulative Fund Flow)")
            )
            
            # กราฟบน: SET Index
            fig_combined.add_trace(go.Scatter(
                x=flow_df['วันที่'], y=flow_df['SET'], name="SET Index", 
                line=dict(color='#FFD600', width=3), mode='lines', 
                fill='tozeroy', fillcolor='rgba(255, 214, 0, 0.1)'
            ), row=1, col=1)
            
            # กราฟล่าง: Fund Flow (เปลี่ยนเป็นกราฟเส้นสะสม)
            fig_combined.add_trace(go.Scatter(x=flow_df['วันที่'], y=flow_df['ต่างชาติ_สะสม'], name='ต่างชาติสะสม', line=dict(color='#2962FF', width=2), mode='lines'), row=2, col=1)
            fig_combined.add_trace(go.Scatter(x=flow_df['วันที่'], y=flow_df['กองทุนและปอบ_สะสม'], name='กองทุน+ปอบสะสม', line=dict(color='#FF6D00', width=2), mode='lines'), row=2, col=1)
            fig_combined.add_trace(go.Scatter(x=flow_df['วันที่'], y=flow_df['รายย่อย_สะสม'], name='รายย่อยสะสม', line=dict(color='#00C853', width=2), mode='lines'), row=2, col=1)
            
            fig_combined.update_layout(
                height=650, 
                margin=dict(l=20, r=20, t=40, b=20),
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
            )
            # เพิ่มเส้น 0 (Zero Line) ในกราฟล่างเพื่อให้ดูง่ายขึ้น
            fig_combined.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

            st.plotly_chart(fig_combined, use_container_width=True)
                
            # --- สรุปราย Sector ประจำวัน ---
            if not df_stocks.empty:
                st.markdown("**ดัชนีและแนวโน้มกลุ่มอุตสาหกรรมวันนี้ (Sector Performance)**")
                sector_perf = df_stocks.groupby('Sector').agg({'Change %': 'mean', 'Vol (MB)': 'sum'}).reset_index().sort_values('Change %', ascending=False)
                sector_perf.columns = ['กลุ่มอุตสาหกรรม', 'เปลี่ยนแปลงเฉลี่ย (%)', 'มูลค่าซื้อขาย (MB)']
                st.dataframe(sector_perf.style.format({'เปลี่ยนแปลงเฉลี่ย (%)': '{:+.2f}%', 'มูลค่าซื้อขาย (MB)': '{:,.1f}'}).map(lambda val: 'color: #00C853; font-weight: bold;' if val > 0 else 'color: #FF1744; font-weight: bold;' if val < 0 else '', subset=['เปลี่ยนแปลงเฉลี่ย (%)']), use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ ไม่พบไฟล์ Investor_Flow.csv")
        st.divider()

       # --- 3. เรดาร์ตรวจจับเม็ดเงินต่างชาติ (NVDR Flow Analysis) ---
        st.markdown("### 📊 3. เรดาร์ตรวจจับเม็ดเงินต่างชาติ (NVDR Flow Analysis)")
        
        # กล่องเลือกช่วงเวลา (เวอร์ชันเดิม เริ่มที่ 5 วัน)
        period_options = {"5 วัน": "Net 5D", "10 วัน": "Net 10D", "15 วัน": "Net 15D", "20 วัน (1 เดือน)": "Net 20D", "25 วัน": "Net 25D", "30 วัน": "Net 30D", "40 วัน (2 เดือน)": "Net 40D"}
        selected_period_label = st.selectbox("🗓️ เลือกระยะเวลาสะสมของ NVDR ที่ต้องการวิเคราะห์:", list(period_options.keys()), key="nvdr_select")
        col_net = period_options[selected_period_label]
        
        nvdr_df, _ = get_nvdr_smart_money(all_set100_tickers)
        if not nvdr_df.empty:
            nvdr_df['Sector'] = nvdr_df['Symbol'].map(ticker_to_sector).fillna("Others")
            
            # ภาพรวม Sector NVDR
            st.markdown(f"**แผนที่เงินทุนต่างชาติแยกตามอุตสาหกรรม (ยอดสะสม {selected_period_label})**")
            sector_flow = nvdr_df.groupby('Sector')[col_net].sum().reset_index().sort_values(col_net, ascending=True)
            
            fig_sec_flow = go.Figure(go.Bar(
                x=sector_flow[col_net], y=sector_flow['Sector'], orientation='h',
                marker_color=['#FF1744' if val < 0 else '#00C853' for val in sector_flow[col_net]],
                text=[f"{val:,.0f} MB" for val in sector_flow[col_net]], textposition='auto'
            ))
            fig_sec_flow.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=f"NVDR {col_net} (ล้านบาท)")
            st.plotly_chart(fig_sec_flow, use_container_width=True)
            
            # ภาพรวมรายหุ้น NVDR
            st.markdown(f"**อันดับหุ้นที่ต่างชาติซื้อ/ขาย มากที่สุด (ยอดสะสม {selected_period_label})**")
            col_buy, col_sell = st.columns(2)
            top10_buy = nvdr_df.nlargest(10, col_net).sort_values(col_net, ascending=True)
            top10_sell = nvdr_df.nsmallest(10, col_net).sort_values(col_net, ascending=False)
            
            with col_buy:
                fig_buy = go.Figure(go.Bar(x=top10_buy[col_net], y=top10_buy['Symbol'], orientation='h', marker_color='#00C853', text=[f"{val:,.0f}" for val in top10_buy[col_net]], textposition='auto'))
                fig_buy.update_layout(title="🟢 Top 10 Net BUY", height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_buy, use_container_width=True)
                
            with col_sell:
                fig_sell = go.Figure(go.Bar(x=top10_sell[col_net], y=top10_sell['Symbol'], orientation='h', marker_color='#FF1744', text=[f"{val:,.0f}" for val in top10_sell[col_net]], textposition='auto'))
                fig_sell.update_layout(title="🔴 Top 10 Net SELL", height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_sell, use_container_width=True)
        else:
            st.warning("⚠️ ไม่พบไฟล์ NVDR_Data_History.csv")
        st.divider()

        # --- 4. AI Predictive Analytics (พยากรณ์ล่วงหน้า) ---
        st.markdown("### 🔮 4. AI Predictive Analytics (สถิติพยากรณ์และจุดกลับตัว)")
        
        # 4.1 Seasonality 1-12 เดือน
        st.markdown("**🗓️ สถิติฤดูกาล (Seasonality Playbook 1-12 เดือน)**")
        st.info("""
        **AI สรุปสถิติรอบปี (อ้างอิงจากพฤติกรรม SET Index และ Fund Flow ในอดีต 10 ปี):**
        - **ม.ค. (January Effect):** มักมีแรงซื้อกลับจากกองทุน หุ้น Mid-Small Cap และกลุ่มธนาคาร (เก็งงบ Q4) มักจะเด่น
        - **ก.พ. - มี.ค. (Dividend Season):** หุ้นปันผลสูง (High Dividend) และกลุ่มสื่อสารมักจะ Outperform เตรียมรับปันผล
        - **เม.ย. (Pre-Sell in May):** ตลาดมักทรงตัว กลุ่มท่องเที่ยวและค้าปลีกมักได้รับอานิสงส์จากเทศกาลสงกรานต์
        - **พ.ค. (Sell in May):** *สถิติมักเป็นขาลง* ต่างชาติและกองทุนมักปรับพอร์ต ควรเน้นหุ้น Defensive (โรงพยาบาล, สาธารณูปโภค)
        - **มิ.ย. - ก.ค. (Q2 Earnings):** ตลาดเริ่มฟื้นตัว เลือกเล่นเป็นรายตัว (Stock Selection) กลุ่มพลังงานมักจะผันผวนตามราคาน้ำมัน
        - **ส.ค. - ก.ย. (Low Season):** ตลาดซึมและผันผวนสูง เป็นช่วงพักฐาน กลุ่มส่งออกและอิเล็กทรอนิกส์มักทำได้ดีหากบาทอ่อน
        - **ต.ค. (Rebound Month):** ตลาดมักสร้างจุดต่ำสุดและเริ่มเด้งกลับ (Q4 Rally)
        - **พ.ย. - ธ.ค. (Window Dressing & LTF/SSF):** *สถิติมักเป็นขาขึ้น* เม็ดเงินกองทุนลดหย่อนภาษีไหลเข้า หุ้น Big Cap (SET50) จะนำตลาด
        """)
        
        if not df_stocks.empty:
            col_up, col_down = st.columns(2)
            # 4.2 Predict หุ้นกำลังจะกลับเป็น "ขาขึ้น"
            with col_up:
                st.markdown("**🚀 หุ้นมีโอกาสกลับเป็น 'ขาขึ้น' (Bullish Reversal)**")
                st.caption("เงื่อนไข: MACD เพิ่งตัดขึ้น (1-2 วัน) หรือ RSI กำลังฟื้นตัวจากโซนล่าง")
                predict_up = df_stocks[(df_stocks['MACD Trend'].str.contains(r"ตัดขึ้น \(1D\)|ตัดขึ้น \(2D\)", na=False)) | ((df_stocks['Stage'].isin(["สะสม (Accumulation)", "รีบาวด์ (Rebound)"])) & (df_stocks['Change %'] > 0))].sort_values('Vol (MB)', ascending=False).head(10)
                if not predict_up.empty:
                    st.dataframe(predict_up[['Symbol', 'Close', 'Change %', 'MACD Trend', 'Stage']].style.format({'Close': '{:.2f}', 'Change %': '{:+.2f}%'}).map(lambda _: 'color: #00C853; font-weight: bold;', subset=['Change %', 'MACD Trend']), hide_index=True, use_container_width=True)
                else:
                    st.write("ยังไม่พบสัญญาณหุ้นกลับตัวขึ้นชัดเจนในวันนี้")

            # 4.3 Predict หุ้นกำลังจะกลับเป็น "ขาลง"
            with col_down:
                st.markdown("**⚠️ หุ้นมีโอกาสกลับเป็น 'ขาลง' (Bearish Reversal)**")
                st.caption("เงื่อนไข: MACD เพิ่งตัดลง (1-2 วัน) หรือราคาหลุดแนวรับสำคัญ")
                predict_down = df_stocks[(df_stocks['MACD Trend'].str.contains(r"ตัดลง \(1D\)|ตัดลง \(2D\)", na=False)) | ((df_stocks['Stage'].isin(["เทขาย (Distribution)", "ย่อพักตัว (Pullback)"])) & (df_stocks['Change %'] < -1))].sort_values('Vol (MB)', ascending=False).head(10)
                if not predict_down.empty:
                    st.dataframe(predict_down[['Symbol', 'Close', 'Change %', 'MACD Trend', 'Stage']].style.format({'Close': '{:.2f}', 'Change %': '{:+.2f}%'}).map(lambda _: 'color: #FF1744; font-weight: bold;', subset=['Change %', 'MACD Trend']), hide_index=True, use_container_width=True)
                else:
                    st.write("ยังไม่พบสัญญาณหุ้นกลับตัวลงชัดเจนในวันนี้")
        st.divider()






