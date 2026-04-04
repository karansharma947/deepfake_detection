import os, hashlib, requests, yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fpdf import FPDF

# 1. Setup
load_dotenv()
app = FastAPI()

# 2. The Bridge: Allow the frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. HOME ROUTE: This stops the "list of files" error
@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("2.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: 2.html not found in this folder!</h1>"

# 4. ANALYSIS ROUTE: The Brain
@app.get("/process")
async def process_video(video_url: str):
    try:
        # A. Download & Hash Video
        ydl_opts = {'outtmpl': 'temp_vid.mp4', 'format': 'best[ext=mp4]', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Unknown Title')
            
        with open('temp_vid.mp4', "rb") as f:
            v_hash = hashlib.sha256(f.read()).hexdigest()

        # B. Deepfake Detection (Sightengine)
        df_params = {
            'url': video_url, 
            'models': 'deepfake',
            'api_user': os.getenv('SIGHTENGINE_USER'), 
            'api_secret': os.getenv('SIGHTENGINE_SECRET')
        }
        df_res = requests.get('https://api.sightengine.com/1.0/check.json', params=df_params).json()
        score = df_res.get('type', {}).get('deepfake', 0)

        # C. Generate the Legal PDF Report
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "CYBER CRIMINOLOGY EVIDENCE REPORT", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.multi_cell(0, 10, f"Target: {title}\nSHA-256 Hash: {v_hash}\nDeepfake Probability: {score*100}%\nVerified by: CyberGuard AI Engine")
        pdf.output("Police_Evidence_Report.pdf")

        return {
            "verdict": "CRITICAL" if score > 0.6 else "SAFE",
            "deepfake_score": score,
            "evidence_hash": v_hash,
            "title": title
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))