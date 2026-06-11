import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# --- TAMPILAN ANTARMUKA WEB ---
st.set_page_config(page_title="LST Mapper Pro Lite", layout="wide", page_icon="🌍")

st.title("🌍 Proyek LST Mapper - Pemroses Suhu Landsat")
st.write("Versi Komputasi Ringan Aman Server Cloud. Dirancang untuk memproses citra tanpa merusak memori RAM.")

# Pilihan Satelit untuk Konstanta Kalibrasi
satelit = st.selectbox("Pilih Jenis Satelit Landsat:", ["Landsat 8", "Landsat 9", "Landsat 7"])

st.subheader("📥 Unggah Berkas Citra (Format .TIF)")
col1, col2, col3 = st.columns(3)

with col1:
    b10_file = st.file_uploader("Unggah Band 10 (Thermal) *Wajib*", type=["tif", "tiff"])
with col2:
    b4_file = st.file_uploader("Unggah Band 4 (Red) *Opsional*", type=["tif", "tiff"])
with col3:
    b5_file = st.file_uploader("Unggah Band 5 (NIR) *Opsional*", type=["tif", "tiff"])

# Tombol Eksekusi
if st.button("🔥 PROSES DATA LST", type="primary"):
    if b10_file is not None:
        with st.spinner("Mengompresi matriks piksel dan menghitung suhu..."):
            try:
                # --- MEMBACA FILE DENGAN METODE MEMORI AMAN (PILLOW) ---
                img10 = Image.open(b10_file)
                
                # Lakukan Downsampling instan (mengambil 1 sampel setiap 15 piksel)
                b10_full = np.array(img10, dtype=np.float64)
                b10 = b10_full[::15, ::15] 
                
                # Konstanta Kalibrasi Standar
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
                # 1. DN ke Radiance
                radiance = (M_L * b10) + A_L
                
                # Mencegah nilai nol atau negatif agar tidak terjadi error logaritma
                radiance[radiance <= 0] = 0.001 
                
                # 2. Radiance ke Brightness Temperature (Kelvin)
                kelvin = K2 / np.log((K1 / radiance) + 1)
                
                # 3. Proses NDVI & Emisivitas jika ada Band 4 & 5
                if b4_file is not None and b5_file is not None:
                    img4 = Image.open(b4_file)
                    img5 = Image.open(b5_file)
                    
                    b4 = np.array(img4, dtype=np.float64)[::15, ::15]
                    b5 = np.array(img5, dtype=np.float64)[::15, ::15]
                    
                    # Rumus Kerapatan Tanaman (NDVI)
                    ndvi = (b5 - b4) / (b5 + b4 + 1e-10)
                    ndvi_min, ndvi_max = np.nanmin(ndvi), np.nanmax(ndvi)
                    
                    # Rumus Proporsi Vegetasi & Emisivitas
                    Pv = ((ndvi - ndvi_min) / (ndvi_max - ndvi_min + 1e-10)) ** 2
                    emissivity = 0.004 * Pv + 0.986
                    
                    # Rumus LST Celcius Akhir
                    lambda_wave = 10.8
                    rho = 14388
                    lst_celcius = (kelvin / (1 + (lambda_wave * kelvin / rho) * np.log(emissivity))) - 273.15
                    metode_text = "Metode Koreksi Emisivitas NDVI"
                else:
                    # Tanpa vegetasi menggunakan konversi standar Celcius
                    lst_celcius = kelvin - 273.15
                    metode_text = "Metode Brightness Temperature Standar"
                
                # Pembersihan data anomali / tepi citra luar angkasa
                lst_celcius[lst_celcius < -10] = np.nan
                lst_celcius[lst_celcius > 60] = np.nan
                
                # --- OUTPUT STATISTIK ---
                st.success(f"Pemrosesan Sukses Menggunakan {metode_text}!")
                
                s_min = np.nanmin(lst_celcius)
                s_max = np.nanmax(lst_celcius)
                s_mean = np.nanmean(lst_celcius)
                s_med = np.nanmedian(lst_celcius)
                
                stat1, stat2, stat3, stat4 = st.columns(4)
                stat1.metric("Suhu Terendah", f"{s_min:.1f} °C")
                stat2.metric("Suhu Tertinggi", f"{s_max:.1f} °C")
                stat3.metric("Rata-rata", f"{s_mean:.1f} °C")
                stat4.metric("Nilai Tengah", f"{s_med:.1f} °C")
                
                # --- VISUALISASI GRAFIK ---
                out_col1, out_col2 = st.columns(2)
                
                with out_col1:
                    st.subheader("🗺️ Peta LST")
                    fig_map, ax_map = plt.subplots(figsize=(5, 4))
                    im = ax_map.imshow(lst_celcius, cmap='jet')
                    plt.colorbar(im, ax=ax_map, label="Suhu (°C)")
                    ax_map.axis('off')
                    st.pyplot(fig_map)
                    
                with out_col2:
                    st.subheader("📊 Histogram Piksel")
                    fig_hist, ax_hist = plt.subplots(figsize=(5, 3.5))
                    ax_hist.hist(lst_celcius[~np.isnan(lst_celcius)], bins=30, color='darkred', alpha=0.7)
                    ax_hist.set_xlabel("Suhu (°C)")
                    ax_hist.set_ylabel("Jumlah")
                    st.pyplot(fig_hist)
                    
            except Exception as e:
                st.error(f"Gagal memproses berkas citra: {e}")
    else:
        st.warning("⚠️ Silakan pilih berkas Band 10 terlebih dahulu!")
