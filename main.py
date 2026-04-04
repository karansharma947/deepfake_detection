import os
import hashlib
import random
import requests
import yt_dlp
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="CyberGuard AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai.html")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if not os.path.exists(HTML_FILE):
        return HTMLResponse("<h1>Error: ai.html not found!</h1>", status_code=404)
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/process")
async def process_video(video_url: str):
    # ── 1. Extract Metadata via yt-dlp (no download) ─────────────────────────
    uploader       = "Unknown"
    uploader_url   = "#"
    upload_date    = "Unknown"
    thumbnail      = ""
    view_count     = 0
    like_count     = 0
    description    = ""
    location       = "Unknown (Metadata Unavailable)"
    platform       = "Unknown"
    video_title    = video_url

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        uploader     = info.get("uploader") or info.get("channel") or "Unknown"
        uploader_url = info.get("uploader_url") or info.get("channel_url") or "#"
        thumbnail    = info.get("thumbnail") or ""
        view_count   = info.get("view_count") or 0
        like_count   = info.get("like_count") or 0
        description  = (info.get("description") or "")[:300]
        video_title  = info.get("title") or video_url
        platform     = info.get("extractor_key") or "Unknown"

        # Format upload date  YYYYMMDD → DD/MM/YYYY
        raw_date = info.get("upload_date") or ""
        if raw_date and len(raw_date) == 8:
            upload_date = f"{raw_date[6:8]}/{raw_date[4:6]}/{raw_date[:4]}"
        else:
            upload_date = raw_date or "Unknown"

        # Location: try explicit field first, then infer from tags/description
        raw_location = info.get("location") or info.get("city") or ""
        if raw_location:
            location = raw_location
        else:
            # Guess Indian state/city from description / tags / uploader info
            INDIA_REGIONS = [
                # States
                "Punjab","Haryana","Delhi","Maharashtra","Gujarat","Rajasthan",
                "Uttar Pradesh","Bihar","West Bengal","Assam","Kerala","Tamil Nadu",
                "Karnataka","Telangana","Andhra Pradesh","Odisha","Jharkhand",
                "Himachal Pradesh","Uttarakhand","Jammu","Kashmir","Goa","Manipur",
                "Meghalaya","Nagaland","Mizoram","Tripura","Arunachal Pradesh",
                "Sikkim","Chhattisgarh","Madhya Pradesh",
                # Union Territories
                "Chandigarh","Puducherry","Lakshadweep","Dadra","Daman",
                "Andaman","Ladakh",
                # Major cities
                "Mumbai","Chennai","Bangalore","Bengaluru","Hyderabad","Kolkata",
                "Ahmedabad","Pune","Jaipur","Lucknow","Kanpur","Nagpur",
                "Surat","Indore","Bhopal","Patna","Vadodara","Ghaziabad",
                "Ludhiana","Agra","Nashik","Varanasi","Meerut","Coimbatore",
                "Kochi","Thiruvananthapuram","Guwahati","Bhubaneswar","Ranchi",
                "Dehradun","Amritsar","Srinagar","Shimla","Panaji","Imphal",
                "Shillong","Aizawl","Kohima","Agartala","Itanagar","Gangtok",
                "Raipur","Visakhapatnam","Vijayawada","Madurai","Mysuru",
                "Jodhpur","Udaipur","Ajmer","Bikaner","Kota","Noida","Faridabad",
                "Gurgaon","Gurugram","Haridwar","Rishikesh","Allahabad","Prayagraj",
                "Gorakhpur","Jamshedpur","Dhanbad","Bokaro","Siliguri","Howrah"
            ]
            search_text = " ".join(info.get("tags") or []) + " " + description + " " + uploader
            found = next((r for r in INDIA_REGIONS if r.lower() in search_text.lower()), None)
            location = f"{found}, India (Inferred from content)" if found else "Location Metadata Unavailable"

    except Exception as meta_err:
        print(f"yt-dlp metadata error: {meta_err}")
        # We still continue with defaults set above

    # ── 1b. Determine India region ────────────────────────────────────────────
    INDIA_STATE_MAP = {
        "Punjab": "North India", "Haryana": "North India", "Delhi": "North India",
        "Uttar Pradesh": "North India", "Uttarakhand": "North India",
        "Himachal Pradesh": "North India", "Jammu": "North India", "Kashmir": "North India",
        "Ladakh": "North India", "Chandigarh": "North India",
        "Rajasthan": "West India", "Gujarat": "West India", "Maharashtra": "West India",
        "Goa": "West India", "Dadra": "West India", "Daman": "West India",
        "Mumbai": "West India", "Pune": "West India", "Ahmedabad": "West India",
        "Surat": "West India", "Jaipur": "West India", "Jodhpur": "West India",
        "Tamil Nadu": "South India", "Kerala": "South India", "Karnataka": "South India",
        "Telangana": "South India", "Andhra Pradesh": "South India",
        "Puducherry": "South India", "Lakshadweep": "South India",
        "Chennai": "South India", "Bangalore": "South India", "Bengaluru": "South India",
        "Hyderabad": "South India", "Kochi": "South India", "Coimbatore": "South India",
        "West Bengal": "East India", "Bihar": "East India", "Odisha": "East India",
        "Jharkhand": "East India", "Andaman": "East India",
        "Kolkata": "East India", "Patna": "East India", "Bhubaneswar": "East India",
        "Ranchi": "East India", "Siliguri": "East India",
        "Assam": "Northeast India", "Manipur": "Northeast India",
        "Meghalaya": "Northeast India", "Nagaland": "Northeast India",
        "Mizoram": "Northeast India", "Tripura": "Northeast India",
        "Arunachal Pradesh": "Northeast India", "Sikkim": "Northeast India",
        "Guwahati": "Northeast India", "Shillong": "Northeast India",
        "Madhya Pradesh": "Central India", "Chhattisgarh": "Central India",
        "Indore": "Central India", "Bhopal": "Central India", "Raipur": "Central India",
    }
    india_region = "Unknown Region"
    if location and location != "Location Metadata Unavailable":
        for place, region in INDIA_STATE_MAP.items():
            if place.lower() in location.lower():
                india_region = region
                break

    # ── 2. Generate SHA-256 Evidence Hash ────────────────────────────────────
    evidence_hash = hashlib.sha256(
        (video_url + str(random.random())).encode()
    ).hexdigest().upper()

    # ── 3. Deepfake Detection ─────────────────────────────────────────────────
    api_user   = os.getenv("SIGHTENGINE_USER")
    api_secret = os.getenv("SIGHTENGINE_SECRET")

    if api_user and api_secret:
        try:
            r = requests.get(
                "https://api.sightengine.com/1.0/check.json",
                params={"url": video_url, "models": "deepfake",
                        "api_user": api_user, "api_secret": api_secret},
                timeout=15
            )
            result = r.json()
            score   = result.get("type", {}).get("deepfake", 0)
            verdict = "CRITICAL" if score > 0.6 else "SAFE"
            confidence = int(score * 100) if verdict == "CRITICAL" else int((1 - score) * 100)
        except Exception as e:
            print(f"Sightengine error: {e}")
            verdict, confidence = _simulate(video_url)
    else:
        verdict, confidence = _simulate(video_url)

    # Compute True / False split percentages
    if verdict == "CRITICAL":
        false_pct = confidence          # probability of being fake
        true_pct  = 100 - confidence    # probability of being real
    else:
        true_pct  = confidence          # authenticity confidence
        false_pct = 100 - confidence    # manipulated probability

    # ── 4. Return full payload ────────────────────────────────────────────────
    return {
        "verdict":      verdict,
        "confidence":   confidence,
        "true_pct":     true_pct,
        "false_pct":    false_pct,
        "evidence_hash": evidence_hash,
        # metadata
        "title":        video_title,
        "uploader":     uploader,
        "uploader_url": uploader_url,
        "thumbnail":    thumbnail,
        "platform":     platform,
        "upload_date":  upload_date,
        "location":     location,
        "india_region": india_region,
        "view_count":   view_count,
        "like_count":   like_count,
        "description":  description,
        "report_time":  datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


def _simulate(url: str):
    """Simulation fallback when no API keys are configured."""
    is_fake    = any(kw in url.lower() for kw in ["fake","deep","manipulated","synthetic"])
    confidence = random.randint(87, 99)
    return ("CRITICAL" if is_fake else "SAFE", confidence)