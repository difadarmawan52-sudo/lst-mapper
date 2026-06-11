import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.enums import Resampling
import io

# --- PENGATURAN HALAMAN ---
st.set_page_config(page_title="LST Mapper Pro Lite", layout="wide", page_icon="🌍")

# --- MENYUNTIKKAN CSS KUSTOM (HTML/CSS) ---
st.markdown("""
    <style>
    /* Mengubah font dan latar belakang utama */
    @import url('https://googleapis.com');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc;
    }
    
    /* Desain Header Utama Bergradasi */
    .header-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #0d9488 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #ffffff !important;
    }
    .header-subtitle {
        font-size: 1.1rem;
        font-weight: 300;
        opacity: 0.9;
    }
    
    /* Desain Kartu (Cards) untuk Input dan Output */
    .custom-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
    }
    
    /* Label Judul Section */
    .section-title {
        color: #0f172a;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER WEB (HTML + CSS GRADIENT) ---
st.markdown("""
    <div class="header-container">
        <div class="header-title">🌍 LST Mapper Pro — Cloud Edition</div>
        <div class="header-subtitle">Sistem Komputasi Spasial Ekstraksi Land Surface Temperature (LST) Berbasis Citra Satelit Landsat Level-1</div>
    </div>
""", unsafe_allow_html=True)

# --- AREA INPUT DATA (KARTU PUTIH CSS) ---
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📥 Konfigurasi Sensor & Unggah Berkas Citra</div>', unsafe_allow_html=True)

# Pilihan Satelit untuk Konstanta Kalibrasi
satelit = st.selectbox("Pilih Jenis Satelit Landsat:", ["Landsat 8", "Landsat 9", "Landsat 7"])

col1, col2, col3 = st.columns(3)
with col1:
    b10_file = st.file_uploader("Unggah Band 10 (Thermal) *Wajib*", type=["tif", "tiff"])
with col2:
    b4_file = st.file_uploader("Unggah Band 4 (Red) *Opsional untuk NDVI*", type=["tif", "tiff"])
with col3:
    b5_file = st.file_uploader("Unggah Band 5 (NIR) *Opsional untuk NDVI*", type=["tif", "tiff"])

st.markdown('</div>', unsafe_allow_html=True)

# --- TOMBOL EKSEKUSI ---
if st.button("🔥 PROSES DATA LST", type="primary", use_container_width=True):
    if b10_file is not None:
        with st.spinner("Menjalankan komputasi matriks piksel aman RAM..."):
            try:
                # --- MEMBACA FILE DENGAN RASTERIO DOWNSAMPLING ---
                with rasterio.open(b10_file) as src_meta:
                    meta_asli = src_meta.meta.copy()
                    t_height = int(src_meta.height / 15)
                    t_width = int(src_meta.width / 15)
                    
                    b10 = src_meta.read(
                        1,
                        out_shape=(t_height, t_width),
                        resampling=Resampling.bilinear
                    ).astype('float64')
                
                # Konstanta Kalibrasi Standar Satelit
                if satelit in ["Landsat 8", "Landsat 9"]:
                    M_L = 0.0003342
                    A_L = 0.1
                    K1 = 774.89
                    K2 = 1321.07
                else:  # Landsat 7
                    M_L = 0.055375
                    A_L = 1.18243
                    K1 = 666.09
                    K2 = 1282.71
                
                # --- PROSES RUMUS MATEMATIKA ---
                radiance = (M_L * b10) + A_L
                radiance[radiance <= 0] = 0.001 
                kelvin = K2 / np.log((K1 / radiance) + 1)
                
                if b4_file is not None and b5_file is not None:
                    with rasterio.open(b4_file) as src4:
                        b4 = src4.read(1, out_shape=(t_height, t_width), resampling=Resampling.bilinear).astype('float64')
                    with rasterio.open(b5_file) as src5:
                        b5 = src5.read(1, out_shape=(t_height, t_width), resampling=Resampling.bilinear).astype('float64')
                    
                    ndvi = (b5 - b4) / (b5 + b4 + 1e-10)
                    ndvi_min, ndvi_max = np.nanmin(ndvi), np.nanmax(ndvi)
                    
                    Pv = ((ndvi - ndvi_min) / (ndvi_max - ndvi_min + 1e-10)) ** 2
                    emissivity = 0.004 * Pv + 0.986
                    
                    lambda_wave = 10.8
                    rho = 14388
                    lst_celcius = (kelvin / (1 + (lambda_wave * kelvin / rho) * np.log(emissivity))) - 273.15
                    metode_text = "Metode Koreksi Emisivitas NDVI (Sobrino 2004)"
                else:
                    lst_celcius = kelvin - 273.15
                    metode_text = "Metode Brightness Temperature Standar"
                
                # Data Cleaning
                lst_celcius[lst_celcius < -10] = np.nan
                lst_celcius[lst_celcius > 60] = np.nan
                
                # --- AREA OUTPUT DATA ---
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.success(f"Pemrosesan Sukses Menggunakan {metode_text}!")
                
                # Tampilkan Angka Statistik
                s_min, s_max = np.nanmin(lst_celcius), np.nanmax(lst_celcius)
                s_mean, s_med = np.nanmean(lst_celcius), np.nanmedian(lst_celcius)
                
                stat1, stat2, stat3, stat4 = st.columns(4)
                stat1.metric("Suhu Minimum", f"{s_min:.1f} °C")
                stat2.metric("Suhu Maksimum", f"{s_max:.1f} °C")
                stat3.metric("Rata-rata Wilayah", f"{s_mean:.1f} °C")
                stat4.metric("Nilai Tengah (Median)", f"{s_med:.1f} °C")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Tampilkan Visualisasi Grafik
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                out_col1, out_col2 = st.columns(2)
                
                with out_col1:
                    st.markdown('<div class="section-title">🗺️ Visualisasi Spasial Peta LST</div>', unsafe_allow_html=True)
                    fig_map, ax_map = plt.subplots(figsize=(6, 4.5))
                    fig_map.patch.set_facecolor('#ffffff')
                    im = ax_map.imshow(lst_celcius, cmap='jet')
                    cb = plt.colorbar(im, ax=ax_map, orientation='horizontal', pad=0.05)
                    cb.set_label("Suhu Permukaan Bumi (°C)", fontsize=10)
                    ax_map.axis('off')
                    st.pyplot(fig_map)
                    
                with out_col2:
                    st.markdown('<div class="section-title">📊 Grafik Distribusi Frekuensi Piksel</div>', unsafe_allow_html=True)
                    fig_hist, ax_hist = plt.subplots(figsize=(6, 4.2))
                    fig_hist.patch.set_facecolor('#ffffff')
                    ax_hist.hist(lst_celcius[~np.isnan(lst_celcius)], bins=35, color='#0d9488', alpha=0.8, edgecolor='#ffffff')
                    ax_hist.set_xlabel("Rentang Suhu (°C)", fontsize=10)
                    ax_hist.set_ylabel("Jumlah Piksel Terdeteksi", fontsize=10)
                    ax_hist.grid(axis='y', linestyle='--', alpha=0.5)
                    st.pyplot(fig_hist)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # --- BUTTON DOWNLOAD GEOTIFF ---
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">💾 Ekspor Hasil Analisis Spasial</div>', unsafe_allow_html=True)
                st.write("Unduh data hasil pemrosesan LST ini dalam format GeoTIFF berkoordinat agar dapat dianalisis lanjut di ArcGIS/QGIS tanpa merubah posisi geografis asli.")
                
                meta_asli.update({
                    "driver": "GTiff",
                    "height": lst_celcius.shape[0],
                    "width": lst_celcius.shape[1],
                    "dtype": "float32",
                    "count": 1,
                    "transform": meta_asli["transform"] * meta_asli["transform"].scale(15, 15)
                })
                
                mem_file = io.BytesIO()
                with rasterio.open(mem_file, 'w', **meta_asli) as dst:
                    dst.write(lst_celcius.astype('float32'), 1)
                
                st.download_button(
                    label="🌍 UNDUH DATA LST (GEOTIFF .TIF)",
                    data=mem_file.getvalue(),
                    file_name="Hasil_LST_Berkoordinat.tif",
                    mime="image/tiff",
                    use_container_width=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"Gagal memproses berkas citra: {e}")
    else:
        st.warning("⚠️ Silakan pilih berkas Band 10 terlebih dahulu!")
