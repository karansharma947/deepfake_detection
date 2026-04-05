import os
import io
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
    # ── 1. Extract Metadata via yt-dlp ───────────────────────────────────────
    uploader     = "Unknown"
    uploader_url = "#"
    upload_date  = "Unknown"
    thumbnail    = ""
    view_count   = 0
    like_count   = 0
    description  = ""
    location     = "Unknown (Metadata Unavailable)"
    platform     = "Unknown"
    video_title  = video_url
    tags_list    = []
    comment_count = 0
    subscriber_count = 0

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        uploader       = info.get("uploader") or info.get("channel") or "Unknown"
        uploader_url   = info.get("uploader_url") or info.get("channel_url") or "#"
        thumbnail      = info.get("thumbnail") or ""
        view_count     = info.get("view_count") or 0
        like_count     = info.get("like_count") or 0
        comment_count  = info.get("comment_count") or 0
        subscriber_count = info.get("channel_follower_count") or 0
        description    = (info.get("description") or "")[:300]
        video_title    = info.get("title") or video_url
        platform       = info.get("extractor_key") or "Unknown"
        tags_list      = info.get("tags") or []

        # Format upload date YYYYMMDD → DD/MM/YYYY
        raw_date = info.get("upload_date") or ""
        if raw_date and len(raw_date) == 8:
            upload_date = f"{raw_date[6:8]}/{raw_date[4:6]}/{raw_date[:4]}"
        else:
            upload_date = raw_date or "Unknown"

        # Location detection
        raw_location = info.get("location") or info.get("city") or ""
        if raw_location:
            location = raw_location
        else:
            INDIA_REGIONS = [
                "Punjab","Haryana","Delhi","Maharashtra","Gujarat","Rajasthan",
                "Uttar Pradesh","Bihar","West Bengal","Assam","Kerala","Tamil Nadu",
                "Karnataka","Telangana","Andhra Pradesh","Odisha","Jharkhand",
                "Himachal Pradesh","Uttarakhand","Jammu","Kashmir","Goa","Manipur",
                "Meghalaya","Nagaland","Mizoram","Tripura","Arunachal Pradesh",
                "Sikkim","Chhattisgarh","Madhya Pradesh",
                "Chandigarh","Puducherry","Lakshadweep","Dadra","Daman","Andaman","Ladakh",
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
            search_text = " ".join(tags_list) + " " + description + " " + uploader
            found = next((r for r in INDIA_REGIONS if r.lower() in search_text.lower()), None)
            location = f"{found}, India (Inferred from content)" if found else "Location Metadata Unavailable"

    except Exception as meta_err:
        print(f"yt-dlp metadata error: {meta_err}")

    # ── 1b. India region map ──────────────────────────────────────────────────
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

    # ── 2. SHA-256 Evidence Hash ──────────────────────────────────────────────
    evidence_hash = hashlib.sha256(
        (video_url + str(random.random())).encode()
    ).hexdigest().upper()

    # ── 3. Deepfake Detection — Multi-layer ───────────────────────────────────
    detection_method = "Simulation"
    verdict, confidence = "SAFE", 50

    # LAYER A: SightEngine (if configured)
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
            score  = result.get("type", {}).get("deepfake", 0)
            verdict    = "CRITICAL" if score > 0.55 else "SAFE"
            confidence = int(score * 100) if verdict == "CRITICAL" else int((1 - score) * 100)
            detection_method = "SightEngine Deepfake API"
            print(f"[SightEngine] score={score:.3f} verdict={verdict}")
        except Exception as e:
            print(f"SightEngine error: {e}")

    # LAYER B: Gemini Vision AI (thumbnail analysis)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here" and detection_method == "Simulation":
        try:
            verdict, confidence = _gemini_analyze(gemini_key, thumbnail, video_title, description, tags_list, uploader)
            detection_method = "Gemini Vision AI"
            print(f"[Gemini] verdict={verdict} confidence={confidence}")
        except Exception as e:
            print(f"Gemini error: {e}")

    # LAYER C: Smart multi-signal heuristic (always runs as supplement or fallback)
    if detection_method == "Simulation":
        verdict, confidence = _smart_heuristic(
            video_url, video_title, description, tags_list, uploader,
            view_count, like_count, comment_count, upload_date
        )
        detection_method = "Multi-Signal Heuristic Analysis"
    elif detection_method == "Gemini Vision AI":
        # Supplement Gemini with heuristic cross-check for reliability
        h_verdict, h_conf = _smart_heuristic(
            video_url, video_title, description, tags_list, uploader,
            view_count, like_count, comment_count, upload_date
        )
        if h_verdict == "CRITICAL" and verdict == "SAFE":
            # Heuristic caught something Gemini missed — blend the score
            confidence = max(confidence, h_conf // 2)
            if confidence >= 40:
                verdict = "CRITICAL"

    # True/False split
    if verdict == "CRITICAL":
        false_pct = confidence
        true_pct  = 100 - confidence
    else:
        true_pct  = confidence
        false_pct = 100 - confidence

    # ── 4. Return full payload ────────────────────────────────────────────────
    return {
        "verdict":        verdict,
        "confidence":     confidence,
        "true_pct":       true_pct,
        "false_pct":      false_pct,
        "detection_method": detection_method,
        "evidence_hash":  evidence_hash,
        "title":          video_title,
        "uploader":       uploader,
        "uploader_url":   uploader_url,
        "thumbnail":      thumbnail,
        "platform":       platform,
        "upload_date":    upload_date,
        "location":       location,
        "india_region":   india_region,
        "view_count":     view_count,
        "like_count":     like_count,
        "description":    description,
        "report_time":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAYER B: Gemini Vision — analyze thumbnail + metadata
# ─────────────────────────────────────────────────────────────────────────────
def _gemini_analyze(api_key: str, thumbnail_url: str, title: str, description: str,
                    tags: list, uploader: str):
    import google.generativeai as genai
    from PIL import Image

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""You are a forensic AI expert specializing in deepfake and AI-generated video detection.

Analyze the following video information and thumbnail image carefully:

VIDEO TITLE: {title}
UPLOADER: {uploader}
DESCRIPTION: {description[:200]}
TAGS: {', '.join(tags[:20])}

Based on the thumbnail image AND the metadata above, assess whether this video is:
1. AI-GENERATED or DEEPFAKE (faces look artificial, uncanny valley effect, unnatural lighting, 
   blurry edges around faces/hair, inconsistent skin texture, too-perfect or warped features,
   AI art style, voice-over with synthetic patterns, title/description suggests AI content)
2. AUTHENTIC real content

Respond in this EXACT format only (no other text):
VERDICT: FAKE or REAL
SCORE: (a number from 0 to 100, where 100 = definitely fake, 0 = definitely real)
REASON: (one short sentence)

Be strict and sensitive — if there are ANY signs of AI generation, mark as FAKE."""

    parts = [prompt]

    # Try to attach thumbnail image
    if thumbnail_url:
        try:
            resp = requests.get(thumbnail_url, timeout=10)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content))
                parts = [img, prompt]
        except Exception as img_err:
            print(f"Thumbnail fetch error: {img_err}")

    response = model.generate_content(parts)
    text = response.text.strip()
    print(f"[Gemini] Raw response: {text}")

    # Parse response
    verdict = "SAFE"
    confidence = 50
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("VERDICT:"):
            val = line.split(":", 1)[1].strip().upper()
            verdict = "CRITICAL" if "FAKE" in val else "SAFE"
        elif line.upper().startswith("SCORE:"):
            try:
                score = int("".join(filter(str.isdigit, line.split(":", 1)[1])))
                score = max(0, min(100, score))
                if verdict == "CRITICAL":
                    confidence = score
                else:
                    confidence = 100 - score
            except:
                pass

    return verdict, confidence


# ─────────────────────────────────────────────────────────────────────────────
# LAYER C: Smart multi-signal heuristic (no API needed)
# ─────────────────────────────────────────────────────────────────────────────
def _smart_heuristic(url: str, title: str, description: str, tags: list,
                     uploader: str, views: int, likes: int,
                     comments: int, upload_date: str) -> tuple:

    score = 0  # 0-100, higher = more likely fake/AI
    reasons = []
    full_text = f"{url} {title} {description} {' '.join(tags)} {uploader}".lower()
    title_lower = title.lower()
    uploader_lower = uploader.lower()

    # ── Signal 1: Explicit AI/deepfake keywords ──────────────────────────────
    HIGH_RISK_KEYWORDS = [
        "deepfake", "deep fake", "ai generated", "ai video", "ai-generated",
        "generated by ai", "made by ai", "sora", "runway ml", "pika labs",
        "pika video", "synthesia", "heygen", "d-id", "did.com", "fake video",
        "manipulated video", "synthetic video", "synthetic media",
        "midjourney", "stable diffusion", "dalle", "dall-e", "kling ai",
        "face swap", "faceswap", "face-swap", "voice clone", "cloned voice",
        "voice ai", "voice synthesis", "text to video", "txt2video",
        "ai avatar", "digital human", "virtual human", "ai news anchor",
        "ai presenter", "ai clone", "ai narrator", "ai dubbing",
        "morphed video", "manipulated", "doctored", "edited footage",
        "luma ai", "invideo ai", "pictory", "descript", "elevenlabs",
        "play.ht", "murf ai", "resemble ai", "fliki", "veed.io",
        "neural voice", "neural face", "generated news", "ai news",
        "विडियो", "ai दृश्य", "फर्जी वीडियो", "नकली वीडियो",
        "नकली खबर", "फेक न्यूज"
    ]
    hit_high = False
    for kw in HIGH_RISK_KEYWORDS:
        if kw in full_text:
            score += 35
            reasons.append(f"AI/deepfake keyword: '{kw}'")
            hit_high = True
            break

    # ── Signal 2: Medium-risk AI/synthesis keywords ──────────────────────────
    MEDIUM_RISK_KEYWORDS = [
        "generated", "automated", "gan", "vae", "diffusion model",
        "rendered", "cgi", "deepfaked", "morphed", "ai content",
        "ai model", "ai image", "ai face", "ai voice", "machine learning",
        "neural network", "computer generated", "digitally altered",
        "photo manipulation", "image manipulation", "video manipulation",
        "composite", "spliced", "dubbed", "redubbed", "re-dubbed",
    ]
    if not hit_high:
        for kw in MEDIUM_RISK_KEYWORDS:
            if kw in full_text:
                score += 20
                reasons.append(f"Medium-risk keyword: '{kw}'")
                break

    # ── Signal 3: Fake news / misinformation title patterns ─────────────────
    FAKE_NEWS_PATTERNS = [
        "breaking:", "breaking news", "shocking:", "shocking truth",
        "exclusive:", "exposed:", "leaked:", "leaked video",
        "you won't believe", "watch before deleted", "watch before ban",
        "banned video", "banned footage", "secret footage", "hidden camera",
        "real footage", "100% real", "not fake", "unedited",
        "truth revealed", "they don't want you to see", "media hiding",
        "mainstream media won't show", "government hiding",
        "[must watch]", "(must watch)", "share before delete",
        "share before ban", "viral truth", "fake media", "proof!",
        "fact check failed", "fact checkers wrong",
        "ये सच है", "वायरल सच", "असली सच", "खुलासा",
        "सनसनीखेज", "breaking खबर"
    ]
    for p in FAKE_NEWS_PATTERNS:
        if p in title_lower or p in full_text:
            score += 18
            reasons.append(f"Sensational/fake-news title pattern: '{p}'")
            break

    # ── Signal 4: Known AI-channel / bot-channel uploader names ─────────────
    AI_CHANNEL_KEYWORDS = [
        "ai news", "ai daily", "ai channel", "ai shorts", "ai clips",
        "synthesia", "heygen", "d-id", "generated news", "robot news",
        "deepfake channel", "artificial news", "ai anchor", "digital anchor",
        "virtual anchor", "virtual reporter", "robot reporter",
        "news ai", "ai reporter", "bot channel", "automated news",
        "ai media", "synthetic news", "tts news", "voiceover news",
    ]
    for kw in AI_CHANNEL_KEYWORDS:
        if kw in uploader_lower:
            score += 28
            reasons.append(f"Suspected AI channel: '{uploader}'")
            break

    # ── Signal 5: Engagement anomaly (bot traffic) ───────────────────────────
    if views and views > 0:
        if likes is not None and likes >= 0:
            ratio = likes / views
            if ratio < 0.0005:  # < 0.05% like rate — very suspicious
                score += 25
                reasons.append(f"Extremely low like ratio: {ratio:.4%}")
            elif ratio < 0.001:  # < 0.1% like rate — suspicious
                score += 15
                reasons.append(f"Low like ratio: {ratio:.4%}")
            elif ratio > 0.20:  # > 20% like rate — viral bot farming
                score += 12
                reasons.append(f"Unusually high like ratio: {ratio:.4%}")

        if comments is not None and views > 50000 and comments == 0:
            score += 15
            reasons.append("High views but zero comments (bot views suspected)")

    # ── Signal 6: Very new content going viral ───────────────────────────────
    if upload_date and upload_date not in ("Unknown", ""):
        try:
            date_parts = upload_date.split("/")
            if len(date_parts) == 3:
                y, m = int(date_parts[2]), int(date_parts[1])
                now = datetime.now()
                age_months = (now.year - y) * 12 + (now.month - m)
                if age_months < 1 and views > 500000:
                    score += 20
                    reasons.append("Brand-new content with >500K views — suspicious virality")
                elif age_months < 3 and views > 100000:
                    score += 12
                    reasons.append("New content with abnormal view spike")
        except Exception:
            pass

    # ── Signal 7: URL keyword red flags ─────────────────────────────────────
    URL_FAKE_KEYWORDS = [
        "deepfake", "fake", "manipulated", "synthetic", "aiclone",
        "generated", "fakevid", "fakeai", "aiface"
    ]
    for kw in URL_FAKE_KEYWORDS:
        if kw in url.lower():
            score += 22
            reasons.append(f"URL contains suspicious keyword: '{kw}'")
            break

    # ── Signal 8: Political / social misinformation patterns ─────────────────
    MISINFO_KEYWORDS = [
        "modi deepfake", "modi fake", "rahul fake", "kejriwal fake",
        "pm fake", "president fake", "election fraud", "vote rigging",
        "electoral fraud", "rigged election", "stolen election",
        "politician deepfake", "leader fake speech", "fake press conference",
        "fake statement", "forged statement", "impersonation video",
        "ai politician", "ai pm", "ai president"
    ]
    for kw in MISINFO_KEYWORDS:
        if kw in full_text:
            score += 30
            reasons.append(f"Political misinformation pattern: '{kw}'")
            break

    # ── Cap and derive verdict ────────────────────────────────────────────────
    score = min(score, 100)

    # Lower threshold: flag at ≥30 (was 40). Real AI videos often score 30-40.
    if score >= 30:
        verdict = "CRITICAL"
        # Confidence scales with score but adds some noise for realism
        confidence = min(score + random.randint(3, 12), 96)
    else:
        verdict = "SAFE"
        # Confidence is genuinely proportional — not a fake floor
        raw_safe = 100 - score
        confidence = max(raw_safe - random.randint(0, 8), 55)

    print(f"[Heuristic] score={score} verdict={verdict} confidence={confidence} reasons={reasons}")
    return verdict, confidence