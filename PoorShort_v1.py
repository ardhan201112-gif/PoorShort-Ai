import os
import asyncio
import requests
import streamlit as st
import edge_tts
from moviepy import *

# Directory Setup
OUTPUT_DIR = "poorshort_v2_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Voice Models
MALE_VOICES = {
    "🇮🇩 Indonesia - Pria (Ardi Neural)": "id-ID-ArdiNeural",
    "🇺🇸 English (US) - Male (Guy Neural)": "en-US-GuyNeural",
    "🇬🇧 English (UK) - Male (Ryan Neural)": "en-GB-RyanNeural"
}

# Aspect Ratios
ASPECT_RATIOS = {
    "9:16 (YouTube Shorts / TikTok / Reels)": (1080, 1920),
    "1:1 (Square - Feed IG)": (1080, 1080),
    "4:5 (Portrait - Post IG)": (1080, 1350)
}

def generate_hashtags(topic_keyword: str) -> str:
    base_tags = ["#Shorts", "#FYP", "#Trending", "#Edukasi", "#FaktaUnik", "#Viral"]
    clean_keyword = "".join(e for e in topic_keyword.title() if e.isalnum())
    custom_tags = [f"#{clean_keyword}", f"#Fakta{clean_keyword}", f"#Info{clean_keyword}"]
    return " ".join(list(set(base_tags + custom_tags)))

def fetch_pexels_video(query: str, orientation: str = "portrait", api_key: str = None) -> str:
    default_key = "563492ad6f9170000100000180a370b3d81b498cb0ec18d7bc86e4bc"
    active_key = api_key if api_key else default_key
    headers = {"Authorization": active_key}
    url = f"https://api.pexels.com/videos/search?query={query}&orientation={orientation}&per_page=3"
    
    try:
        response = requests.get(url, headers=headers, timeout=10).json()
        if response.get('videos'):
            video_files = response['videos'][0]['video_files']
            best_video = max(video_files, key=lambda x: x.get('width', 0))
            raw_path = os.path.join(OUTPUT_DIR, "raw_bg.mp4")
            v_data = requests.get(best_video['link']).content
            with open(raw_path, "wb") as f:
                f.write(v_data)
            return raw_path
    except Exception:
        pass
    return None

async def generate_voiceover(text: str, voice_code: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice_code)
    await communicate.save(output_path)

def create_pop_sound(duration=0.15):
    import numpy as np
    from moviepy.audio.AudioClip import AudioArrayClip
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = 0.5 * np.sin(2 * np.pi * 880 * t) * np.exp(-10 * t)
    audio_array = np.vstack((wave, wave)).T
    return AudioArrayClip(audio_array, fps=sample_rate)

def build_poorshort_auto_video(script_text, search_keyword, aspect_key, voice_key, font_color, duration_sec, api_key=None):
    width, height = ASPECT_RATIOS[aspect_key]
    audio_voice_path = os.path.join(OUTPUT_DIR, "voice.mp3")
    output_final_path = os.path.join(OUTPUT_DIR, "PoorShort_Auto_Render.mp4")
    
    asyncio.run(generate_voiceover(script_text, MALE_VOICES[voice_key], audio_voice_path))
    voice_clip = AudioFileClip(audio_voice_path)
    final_duration = min(duration_sec, voice_clip.duration) if voice_clip.duration > 0 else duration_sec
    
    orient = "portrait" if "9:16" in aspect_key else "square"
    bg_video_path = fetch_pexels_video(search_keyword, orientation=orient, api_key=api_key)
    
    if bg_video_path and os.path.exists(bg_video_path):
        bg_clip = VideoFileClip(bg_video_path).resized((width, height)).subclip(0, final_duration).without_audio()
    else:
        bg_clip = ColorClip(size=(width, height), color=(15, 23, 42), duration=final_duration)
        
    base_fontsize = int(width * 0.06)
    txt_clip = TextClip(
        text=script_text,
        font_size=base_fontsize,
        color=font_color,
        font='Arial',
        method='caption',
        size=(int(width * 0.85), None)
    ).with_position(('center', 'center')).with_duration(final_duration)
    
    pop_sfx = create_pop_sound().with_start(0.1)
    composite_audio = CompositeAudioClip([voice_clip, pop_sfx]).with_duration(final_duration)
    
    final_video = CompositeVideoClip([bg_clip, txt_clip]).with_audio(composite_audio)
    final_video.write_videofile(output_final_path, fps=30, codec="libx264", audio_codec="aac", preset="fast")
    
    bg_clip.close()
    voice_clip.close()
    final_video.close()
    return output_final_path

# Streamlit Interface
st.set_page_config(page_title="PoorShort AI v2 Cloud", page_icon="🎬", layout="wide")
st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🎬 PoorShort AI v2</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Server Active 24/7 - Auto Video & Hashtag Generator</p>", unsafe_allow_html=True)
st.divider()

with st.sidebar:
    st.header("⚙️ Server Status")
    st.success("🟢 Server Online (24 Hours)")
    user_api_key = st.text_input("Pexels API Key (Opsional):", type="password")

col1, col2 = st.columns(2, gap="medium")

with col1:
    st.subheader("🔍 1. Kategori & Naskah")
    search_topic = st.text_input("Kata Kunci Latar Video:", value="construction")
    script_input = st.text_area("Naskah Edukasi / Fakta Unik:", height=120, value="Tahukah kamu? Keramik dipotong menggunakan mata pisau berlapis intan agar hasilnya rapi!")
    male_voice = st.selectbox("Pilihan Suara Pria AI:", list(MALE_VOICES.keys()))

with col2:
    st.subheader("📐 2. Frame & Visual")
    aspect_choice = st.selectbox("Rasio Frame Video:", list(ASPECT_RATIOS.keys()))
    font_color_choice = st.color_picker("Warna Font Subtitle:", "#FFE600")
    duration_choice = st.slider("Durasi Maksimal (Detik):", 5, 60, 15, 5)
    generate_btn = st.button("🚀 Render Video & Hashtags", type="primary", use_container_width=True)

st.divider()

if generate_btn:
    if not script_input.strip():
        st.error("Naskah tidak boleh kosong!")
    else:
        with st.spinner("Memproses video, voiceover, dan hashtag..."):
            try:
                res_video = build_poorshort_auto_video(
                    script_input, search_topic, aspect_choice, 
                    male_voice, font_color_choice, duration_choice, user_api_key
                )
                generated_tags = generate_hashtags(search_topic)
                
                st.success("🎉 Video Berhasil Dibuat!")
                r_col1, r_col2 = st.columns([1.2, 0.8])
                
                with r_col1:
                    st.video(res_video)
                    with open(res_video, "rb") as f:
                        st.download_button("📥 Download Video MP4", f, "PoorShort_Ready.mp4", "video/mp4", use_container_width=True)
                
                with r_col2:
                    st.text_area("Salin Hashtag Ini:", value=generated_tags, height=120)
            except Exception as e:
                st.error(f"Gagal merender: {e}")
