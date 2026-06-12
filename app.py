import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.enums import Resampling
import io

# --- PENGATURAN HALAMAN (MANDATORY) ---
st.set_page_config(page_title="LST Mapper GeoEnterprise", layout="wide", page_icon="🌍")

# --- CSS CUSTOM UNTUK TAMPILAN SUPER PREMIUM ---
st.markdown("""
    <style>
    @import url('https://googleapis.com');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #f8fafc;
    }
    
    /* Header Utama */
    .hero-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #0d9488 100%);
        padding: 3rem 2.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2.5rem;
        box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.15);
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -0.05em;
        color: #ffffff !important;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        font-weight: 300;
        opacity: 0.9;
    }
    
    /* Desain Kartu (Cards) */
    .premium-card {
        background: #ffffff;
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 10px 15px -3px rgba(0, 0, 0, 0.03);
        margin-bottom: 2rem;
    }
    
    /* Judul Bagian */
    .card-title {
        color: #0f172a;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        border-left: 5px solid #3b82f6;
        padding-left: 12px;
    }
    
    /* Kartu Statistik Berwarna (Metrik Kustom) */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    .metric-box {
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .m-blue { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
    .m-red { background: linear-gradient(135deg, #dc2626, #b91c1c); }
    .m-teal { background: linear-gradient(135deg, #0d9488, #0f766e); }
    .m-purple { background: linear-gradient(135deg, #7c3aed, #6d28d9); }
    
    .metric-label { font-size: 0.9rem; font-weight: 500; opacity: 0.85; text-transform: uppercase; letter-spacing: 0.05em;}
    .metric-val { font-size: 1.8rem; font-weight: 700; margin-top: 0.25rem; }
    
    /* Tabel Teori */
    .teori-table {
        width: 100%; border-collapse: collapse; margin-top: 1rem;
    }
    .teori-table th {
        background-color: #1e3a8a; color: white; text-align: left; padding: 12px; font-weight: 600;
    }
    .teori-table td {
        padding: 12px; border-bottom: 1px solid #e2e8f0; font-size: 0.95rem; color: #334155;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGASI (MULTI-HALAMAN) ---
with st.sidebar:
    st.markdown("### 🏢 MENU NAVIGASI")
    menu = st.radio(
        "Pilih Halaman Proyek:",
        ["🖥️ Dashboard Utama", "📚 Teori Perhitungan LST"]
    )
    st.markdown("---")
    st.markdown("**Satelit Didukung:**\n- Landsat 7 (ETM+)\n- Landsat 8 (OLI/TIRS)\n- Landsat 9 (OLI-2/TIRS-2)")
    st.markdown("**Format Input:**\n- GeoTIFF Level-1 (`.TIF`)")

# ==============================================================================
# MENU 1: DASHBOARD UTAMA
# ==============================================================================
if menu == "🖥️ Dashboard Utama":
    
    # Hero Header HTML/CSS
    st.markdown("""
        <div class="hero-container">
            <div class="hero-title">🌍 LST Mapper GeoEnterprise</div>
            <div class="hero-subtitle">Platform Analisis Spasial Ekstraksi Land Surface Temperature (LST) Otomatis &amp; Bebas Crash Memori</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Kartu Input Data
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📥 Konfigurasi Sensor &amp; Unggah File Landsat Level-1</div>', unsafe_allow_html=True)
    
    satelit = st.selectbox("Pilih Jenis Satelit Rekaman:", ["Landsat 8", "Landsat 9", "Landsat 7"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        b10_file = st.file_uploader("Unggah Band 10 (Thermal) *Wajib*", type=["tif", "tiff"])
    with col2:
        b4_file = st.file_uploader("Unggah Band 4 (Red) *Opsional untuk NDVI*", type=["tif", "tiff"])
    with col3:
        b5_file = st.file_uploader("Unggah Band 5 (NIR) *Opsional untuk NDVI*", type=["tif", "tiff"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tombol Eksekusi Panjang Penuh (Full Width)
    if st.button("🔥 JALANKAN EKSTRAKSI DATA SPASIAL LST", type="primary", use_container_width=True):
        if b10_file is not None:
            with st.spinner("Sedang memproses algoritma downsampling spasial dan hukum fisika LST..."):
                try:
                    # Membaca Berkas dengan Rasterio Downsampling Aman RAM
                    with rasterio.open(b10_file) as src_meta:
                        meta_asli = src_meta.meta.copy()
                        t_height = int(src_meta.height / 15)
                        t_width = int(src_meta.width / 15)
                        
                        b10 = src_meta.read(
                            1, out_shape=(t_height, t_width), resampling=Resampling.bilinear
                        ).astype('float64')
                    
                    # Logika Pemilihan Konstanta Kalibrasi Satelit
                    if satelit in ["Landsat 8", "Landsat 9"]:
                        M_L, A_L, K1, K2 = 0.0003342, 0.1, 774.89, 1321.07
                    else:
                        M_L, A_L, K1, K2 = 0.055375, 1.18243, 666.09, 1282.71
                    
                    # Hitung Radiance & Brightness Temperature
                    radiance = (M_L * b10) + A_L
                    radiance[radiance <= 0] = 0.001
                    kelvin = K2 / np.log((K1 / radiance) + 1)
                    
                    # Hitung Koreksi Emisivitas Menggunakan NDVI
                    if b4_file is not None and b5_file is not None:
                        with rasterio.open(b4_file) as src4:
                            b4 = src4.read(1, out_shape=(t_height, t_width), resampling=Resampling.bilinear).astype('float64')
                        with rasterio.open(b5_file) as src5:
                            b5 = src5.read(1, out_shape=(t_height, t_width), resampling=Resampling.bilinear).astype('float64')
                        
                        ndvi = (b5 - b4) / (b5 + b4 + 1e-10)
                        ndvi_min, ndvi_max = np.nanmin(ndvi), np.nanmax(ndvi)
                        
                        Pv = ((ndvi - ndvi_min) / (ndvi_max - ndvi_min + 1e-10)) ** 2
                        emissivity = 0.004 * Pv + 0.986
                        
                        lst_celcius = (kelvin / (1 + (10.8 * kelvin / 14388) * np.log(emissivity))) - 273.15
                        metode_text = "Metode Split-Window dengan Koreksi Emisivitas Permukaan Bumi (NDVI Sobrino 2004)"
                    else:
                        lst_celcius = kelvin - 273.15
                        metode_text = "Metode At-Sensor Brightness Temperature Standar (Asumsi Blackbody)"
                    
                    # Data Cleaning Piksel Liar / Gangguan Awan
                    lst_celcius[lst_celcius < -5] = np.nan
                    lst_celcius[lst_celcius > 55] = np.nan
                    
                    # Nilai Statistik deskriptif
                    s_min, s_max = np.nanmin(lst_celcius), np.nanmax(lst_celcius)
                    s_mean, s_med = np.nanmean(lst_celcius), np.nanmedian(lst_celcius)
                    
                    # TAMPILKAN METRIK KUSTOM BERWARNA (HTML/CSS)
                    st.success(f"Proses Berhasil! Digunakan: {metode_text}")
                    
                    st.markdown(f"""
                        <div class="metric-grid">
                            <div class="metric-box m-blue">
                                <div class="metric-label">❄️ Suhu Terendah</div>
                                <div class="metric-val">{s_min:.1f} °C</div>
                            </div>
                            <div class="metric-box m-red">
                                <div class="metric-label">🔥 Suhu Tertinggi</div>
                                <div class="metric-val">{s_max:.1f} °C</div>
                            </div>
                            <div class="metric-box m-teal">
                                <div class="metric-label">📊 Rata-rata Spasial</div>
                                <div class="metric-val">{s_mean:.1f} °C</div>
                            </div>
                            <div class="metric-box m-purple">
                                <div class="metric-label">🎯 Nilai Tengah (Median)</div>
                                <div class="metric-val">{s_med:.1f} °C</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Peta dan Histogram dalam Kartu Putih
                    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                    g_col1, g_col2 = st.columns(2)
                    
                    with g_col1:
                        st.markdown('<div class="card-title">🗺️ Peta Zonasi Suhu Permukaan Bumi (LST)</div>', unsafe_allow_html=True)
                        fig_map, ax_map = plt.subplots(figsize=(6, 4.5))
                        fig_map.patch.set_facecolor('#ffffff')
                        im = ax_map.imshow(lst_celcius, cmap='jet')
                        fig_map.colorbar(im, ax=ax_map, label='Suhu (°C)')
