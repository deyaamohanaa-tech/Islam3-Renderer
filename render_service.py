from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import base64
import io
from PIL import Image

app = FastAPI(title="Islam3-Bot Card Rendering Microservice")

# استيراد دالة توليد البطاقة الأصلية من utils/image.py
from utils.image import create_results_card

class ContestData(BaseModel) :
    groups_data: dict
    global_ranking: dict
    top_winners: list
    output_path: str = "results_card.png"

@app.post("/render-card")
async def render_card(data: ContestData):
    try:
        # استدعاء دالة توليد البطاقة الأصلية 100% باستخدام Playwright والملفات الأصلية
        card_image = await create_results_card(
            groups_data=data.groups_data,
            global_ranking=data.global_ranking,
            top_winners=data.top_winners,
            output_path=data.output_path
        )
        
        if not os.path.exists(data.output_path):
            raise HTTPException(status_code=500, detail="Failed to generate card image.")
            
        # قراءة الصورة وتحويلها إلى base64 للإرسال السريع عبر الـ API
        with open(data.output_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        return {
            "status": "success",
            "image_base64": encoded_string
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "online", "service": "Islam3-Bot Card Renderer"}
