import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import os

# --- TAMPILAN WEB ANTMUKA ---
st.set_page_config(page_title="LST Mapper Pro", layout="wide", page_icon="🌍")

st.title("🌍 Proyek LST Mapper - Pemroses Suhu Landsat")
st.write("Unggah data citra Landsat Collection 2 Level-1 Anda untuk menghitung Suhu Permukaan Bumi (LST) secara otomatis.")

# Input Pilihan Satelit untuk Menentukan Konstanta K1 & K2
satelit = st.selectbox("Pilih Jenis Satelit Landsat:", ["Landsat 8", "Landsat 9", "Landsat 7"])

# Kolom Unggah File
st.subheader("📥 Unggah Berkas Citra (Format .TIF)")
col1, col2, col3 = st.columns(3)

with col1:
    b10_file = st.file_uploader("Unggah Band 10 (Thermal) *Wajib*", type=["tif", "tiff"])
with col2:
    b4_file = st.file_uploader("Unggah Band 4 (Red) *Opsional untuk NDVI*", type=["tif", "tiff"])
with col3:
    b5_file = st.file_uploader("Unggah Band 5 (NIR) *Opsional untuk NDVI*", type=["tif", "tiff"])

# Tombol Eksekusi
if st.button("🔥 PROSES DATA LST", type="primary"):
    if b10_file is not None:
        with st.spinner("Sedang memproses data citra... Mohon tunggu..."):
            try:
                # 1. MEMBACA FILE BAND 10 THERMAL
                with rasterio.open(b10_file) as src:
                    b10 = src.read(1).astype('float64')
                
                # 2. PROSES KONVERSI DN KE RADIANCE & BRIGHTNESS TEMPERATURE
                # Menentukan konstanta kalibrasi berdasarkan jenis satelit
                if satelit in ["Landsat 8", "Landsat 9"]:
                    M_L = 0.0003342
                    A_L = 0.1
                    K1 = 774.89
                    K2 = 1321.07
                else: # Landsat 7
                    M_L = 0.055375
                    A_L = 1.18243
                    K1 = 666.09
                    K2 = 1282.71
                
                # Rumus Radiance
                radiance = (M_L * b10) + A_L
                # Rumus Brightness Temperature (Kelvin)
                kelvin = K2 / np.log((K1 / radiance) + 1)
                
                # 3. PROSES NDVI & EMISSIVITY (Jika Band 4 & 5 Diunggah)
                if b4_file is not None and b5_file is not None:
                    with rasterio.open(b4_file) as src4:
                        b4 = src4.read(1).astype('float64')
                    with rasterio.open(b5_file) as src5:
                        b5 = src5.read(1).astype('float64')
                    
                    # Rumus Kerapatan Vegetasi (NDVI)
                    ndvi = (b5 - b4) / (b5 + b4 + 1e-10)
                    ndvi_min, ndvi_max = np.nanmin(ndvi), np.nanmax(ndvi)
                    
                    # Rumus Fractional Vegetation (Pv) & Emisivitas (E)
                    Pv = ((ndvi - ndvi_min) / (ndvi_max - ndvi_min + 1e-10)) ** 2
                    emissivity = 0.004 * Pv + 0.986
                    
                    # Rumus Akhir LST (Celcius) dengan koreksi Emisivitas
                    lambda_wave = 10.8 # Panjang gelombang rata-rata Band 10
                    rho = 14388 # Konstanta boltzmann
                    lst_celcius = (kelvin / (1 + (lambda_wave * kelvin / rho) * np.log(emissivity))) - 273.15
                    metode_text = "Metode Split-Window / Emisivitas NDVI Koreksi"
                else:
                    # Jika hanya Band 10, pakai konversi suhu standar Celcius
                    lst_celcius = kelvin - 273.15
                    metode_text = "Metode Brightness Temperature Standar (Tanpa Koreksi Vegetasi)"

                # Membersihkan data dari nilai error/blank (NoData)
                lst_celcius[lst_celcius < -50] = np.nan
                lst_celcius[lst_celcius > 100] = np.nan
                
                # 4. TAMPILKAN HASIL STATISTIK
                st.success(f"Pemrosesan Berhasil Menggunakan {metode_text}!")
                
                stat1, stat2, stat3, stat4 = st.columns(4)
                stat1.metric("Suhu Minimum", f"{np.nanmin(lst_celcius):.2f} °C")
                stat2.metric("Suhu Maksimum", f"{np.nanmax(lst_celcius):.2f} °C")
                stat3.metric("Rata-rata Suhu", f"{np.nanmean(lst_celcius):.2f} °C")
                stat4.metric("Nilai Tengah (Median)", f"{np.nanmedian(lst_celcius):.2f} °C")
                
                # 5. VISUALISASI PETA DAN HISTOGRAM
                out_col1, out_col2 = st.columns(2)
                
                with out_col1:
                    st.subheader("🗺️ Peta Distribusi Suhu (LST)")
                    fig_map, ax_map = plt.subplots(figsize=(6, 5))
                    im = ax_map.imshow(lst_celcius, cmap='jet')
                    plt.colorbar(im, ax=ax_map, label="Suhu (°C)")
                    ax_map.axis('off')
                    st.pyplot(fig_map)
                    
                with out_col2:
                    st.subheader("📊 Grafik Sebaran Piksel")
                    fig_hist, ax_hist = plt.subplots(figsize=(6, 4.3))
                    ax_hist.hist(lst_celcius[~np.isnan(lst_celcius)], bins=40, color='crimson', alpha=0.7)
                    ax_hist.set_xlabel("Suhu (°C)")
                    ax_hist.set_ylabel("Jumlah Piksel")
                    st.pyplot(fig_hist)
                    
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses gambar: {e}")
    else:
        st.warning("⚠️ Mohon unggah file Band 10 (.TIF) terlebih dahulu!")
