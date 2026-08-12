# results_card.py
import asyncio
import os
import io
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pilmoji import Pilmoji
import concurrent.futures
from playwright.async_api import async_playwright

def _render_async_wrapper(html, max_width, max_height):
    async def _inner():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = await browser.new_page(viewport={"width": 1000, "height": 200})
            await page.set_content(html, wait_until="domcontentloaded")
            body_elem = await page.query_selector("body")
            box = await body_elem.bounding_box()
            width = max(int(box["width"]), 10)
            height = max(int(box["height"]), 10)
            
            await page.set_viewport_size({"width": width + 20, "height": height + 20})
            screenshot_bytes = await body_elem.screenshot(type="png", omit_background=True)
            await browser.close()
            
            img = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")
            
            # التكبير/التصغير حتى يتلاصق مع الحدود تماماً (0px gap) ويتوقف عند أول حد يتم بلوغه
            t_max_w = max_width if max_width else img.width
            t_max_h = max_height if max_height else img.height
            
            scale_w = t_max_w / img.width if img.width > 0 else 1.0
            scale_h = t_max_h / img.height if img.height > 0 else 1.0
            
            # أيهما يلامس حوافه أولاً (أفقياً أو عمودياً) سيتوقف عنده التكبير تماماً بدون فراغات
            scale = min(scale_w, scale_h)
            
            new_w = max(int(img.width * scale), 1)
            new_h = max(int(img.height * scale), 1)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            return img
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(_inner())).result()

def render_text_via_playwright(text, font_size=24, fill=(255,255,255,255), max_width=None, max_height=None):
    r, g, b, a = fill
    color_css = f"rgba({r}, {g}, {b}, {a/255})"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
    <meta charset="UTF-8">
    <style>
        @font-face {{
            font-family: 'Sultan';
            src: url('file://{os.path.abspath(FONT_SULTAN)}') format('truetype');
        }}
        @font-face {{
            font-family: 'Amiri';
            src: url('file://{os.path.abspath(AMIRI_FONT)}') format('truetype');
        }}
        @font-face {{
            font-family: 'Shorooq';
            src: url('file://{os.path.abspath(FONT_SHOROOQ)}') format('opentype');
        }}
        body {{
            margin: 0;
            padding: 2px;
            background: transparent;
            color: {color_css};
            font-weight: bold;
            text-shadow: 0 1px 3px rgba(0,0,0,0.8);
            font-family: 'Sultan', 'Amiri', sans-serif;
            font-size: {font_size}px;
            white-space: nowrap;
            display: inline-block;
        }}
    </style>
    </head>
    <body>
        {text}
    </body>
    </html>
    """
    try:
        res = _render_async_wrapper(html, max_width, max_height)
        if res is not None:
            return res
        raise Exception("Playwright returned None image")
    except Exception as e:
        print(f"⚠️ Playwright fallback to Pillow/Pilmoji due to: {e}")
        # Fallback آمن باستخدام Pillow و Pilmoji والخطوط المتاحة
        try:
            from PIL import Image, ImageFont, ImageDraw
            import os
            font_path = os.path.abspath(FONT_SULTAN) if os.path.exists(FONT_SULTAN) else None
            font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
            
            # معالجة النص العربي إن أمكن
            display_text = text
            if HAS_ARABIC:
                try:
                    reshaped = arabic_reshaper.reshape(text)
                    display_text = get_display(reshaped)
                except Exception:
                    pass
            
            # قياس حجم النص
            dummy_img = Image.new("RGBA", (10, 10))
            d_draw = ImageDraw.Draw(dummy_img)
            bbox = d_draw.textbbox((0, 0), display_text, font=font)
            tw = max(10, bbox[2] - bbox[0] + 10)
            th = max(10, bbox[3] - bbox[1] + 10)
            
            out_img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            if HAS_PILMOJI:
                try:
                    with Pilmoji(out_img) as pilmoji:
                        pilmoji.text((5, 2), display_text, fill=fill, font=font)
                    return out_img
                except Exception:
                    pass
            
            # رسم عادي عبر Pillow إذا لم تتوفر Pilmoji
            draw = ImageDraw.Draw(out_img)
            draw.text((5, 2), display_text, fill=fill, font=font)
            return out_img
        except Exception as fallback_err:
            print(f"⚠️ Pillow fallback also failed: {fallback_err}")
            return Image.new("RGBA", (50, 20), (0, 0, 0, 0))
#للتحريبي
DEBUG_MODE = False   # ← للتجربة فقط

# Optional helpers (improve Arabic shaping and emoji). If not installed, code continues.
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except Exception:
    HAS_ARABIC = False

try:
    from pilmoji import Pilmoji
    from pilmoji.source import NotoEmojiSource
    HAS_PILMOJI = True
except Exception:
    HAS_PILMOJI = False

#الوضع التجريبي
if not DEBUG_MODE:
    from utils.helpers import get_group_photo, get_group_name, format_participant
else:
    async def get_group_photo(bot, chat_id):
        return None

    async def get_group_name(bot, chat_id):
        return f"• الطَّآمَّة |{chat_id}"

    def format_participant(uid, data, max_total, global_ranking, bot_id=None):
        # نسخة تجريبية مبسطة
        name = data.get("name", f"User {uid}")
        points = data.get("points", 0)
        rank = global_ranking.get(uid, "?")
        return f"{name} 🎖🏆🥇"

# ---------------- إعداد المسارات الافتراضية ----------------
GOLD_BG = "utils/gold_bg/gold_bg.jpg"
DEFAULT_AVATAR = "utils/defaults/no_avatar.png"
DEFAULT_GROUP_IMG = "utils/defaults/no_group.png"
FONTS_DIR = "utils/fonts/"

# الأسماء الافتراضية للخطوط ضمن المجلد الذي أعددته
FONT_SULTAN = os.path.join(FONTS_DIR, "sultan-nahia.ttf")
AMIRI_FONT = os.path.join(FONTS_DIR, "Amiri Bold.ttf")
FONT_SHOROOQ = os.path.join(FONTS_DIR, "Shorooq Yara Bold.otf")

#للتجريبي
async def run_debug_preview():
    print("🧪 تشغيل الوضع التجريبي لبطاقة النتائج")
    global DEBUG_MODE
    DEBUG_MODE = False   # ← للتجربة فقط

    # -------- بيانات وهمية --------
    fake_groups = {
        -1001: {
            "group_total": 20,
            "avg_percentage": 100.0,
            "group_rank": 1,
            "medals": "🏆🥇",
            "participants": [
                (101, 5, 100.0),
                (102, 5, 100.0),
                (103, 5, 100.0),
#                (104, 5, 100.0),  # ← 4 متفوقين
#                (105, 4, 80.0),
#                (106, 4, 80.0),
#                (107, 4, 80.0),
#                (108, 0, 0.0),
            ],
        },
        -1002: {
            "group_total": 20,
            "avg_percentage": 50.0,
            "group_rank": 2,
            "medals": "🏅",
            "participants": [
                (201, 4, 80.0),
                (202, 3, 60.0),
#                (203, 3, 60.0),
#                (204, 2, 40.0),
#                (205, 2, 40.0),
#                (206, 2, 40.0),
#                (207, 1, 20.0),
#                (208, 1, 20.0),
#                (209, 1, 20.0),
#                (210, 1, 20.0),
            ],
        },
#        -1003: {
#            "group_total": 20,
#            "avg_percentage": 50.0,
#            "group_rank": 2,
#            "medals": "🎖",
#            "participants": [
#                (301, 4, 80.0),
#                (302, 3, 60.0),
#                (303, 3, 60.0),
#                (304, 2, 40.0),
#                (305, 2, 40.0),
#                (306, 2, 40.0),
#                (307, 1, 20.0),
#                (308, 1, 20.0),
#                (309, 1, 20.0),
#            ],
#        },
#        -1004: {
#            "group_total": 20,
#            "avg_percentage": 50.0,
#            "group_rank": 2,
#            "medals": "🎗",
#            "participants": [
#                (401, 4, 80.0),
#                (402, 3, 60.0),
#                (403, 3, 60.0),
#                (404, 2, 40.0),
#                (405, 2, 40.0),
#                (406, 2, 40.0),
#                (407, 1, 20.0),
#                (408, 1, 20.0),
#                (409, 1, 20.0),
#                (410, 1, 20.0),
#            ],
#        },
    }

    fake_parts = {
        101: {"name": "ســ᭄ۛۛـــ𖤓̟̟̟̟̟̟̥̥̥̥̟͜͡ــمــر"},
        102: {"name": "ᯓ𓆩𖡡𓏺.ضيـ꯭ــاء꯭ۦ٭||𝓓𝓮𝔂𝓪'𝓪.𓏺𖡡𓆪"},
        103: {"name": "◥ ツآحِݦد آݪقِآڼَۅڼَيツ ◤"},

#        104: {"name": "دنـ❥ـ🌸ــيا"},
#        105: {"name": "امــ❥༄⍣ـ𖤓̟̟̟̟̟̟̥ـ𖤓̟̟̟̟̟̟̥ـــيـر"},
#        106: {"name": "أّلَوٌأّثًـقُ بًأّلَلَهّ 🇾🇪"},
#        107: {"name": "ا̍ڵــبــڕۄڣــېْۧــڛۜــﯡڕ"},
#        108: {"name": "آلِٰـِۢقِٰـِۢيِٰـِۢصِٰـِۢر🇾🇪 ᵛ͢ᵎᵖ ⌯﴾❥,"},

        201: {"name": "جـ,ـۅآډ𓅓"},
        202: {"name": "الطـــــ𓆩𖡡𓏺🇾🇪⃟ٰ⍣ــوفــان ¹𐏓"},
        #203: {"name": "ابو جـ̸ــبᬼٰٰٰٰٖٖـ͜ــ̸ريل 🇾🇪"},
#        204: {"name": "➼ڪ⃟⃟مـــــ⃠ــال🇾🇪"},
#        205: {"name": "هـ𓊿ـدهـ𓊿ـد سۣۗـــِْ๋͜͡℘ـيمــِْ๋͜͡ـآٖٖنۣۗ"},
#        206: {"name": "𝒂𝒍𝒊𝒔𝒉𝒐‿𝒐"},
#        207: {"name": "Ａｊｗａｎ"},
#        208: {"name": "ر؏د"},
#        209: {"name": ".❀𝓠𝓾𝓮𝓮𝓷❀ٜ"},
#        210: {"name": "نََآريِٰـِۢنََ آلِٰـِۢﯛ̲୭رده🌸"},

#        301: {"name": "\"رِضَّاٍّكَ رًّبّْيٌّ غٌّاٍّيٌّتُّي\""},
#        302: {"name": "حَــيْـ⸙⃝ 𓂆ــ²‌⁰‌²‌‌⁶ـــدّر"},
#        303: {"name": "𝑺𝒉𝒂𝒊𝒎𝒂𝒂♡"},
#        304: {"name": "ʜᴀᴅᴇᴇʟ ᥫ ᭡"},
#        305: {"name": "s̸̷͟͟s̸̷͟͟"},
#        306: {"name": "👑حڪٰۧۧيٰۧمٰۧ🇵🇸ٱۧلٰۧزۧمٖۧۧان👑"},
#        307: {"name": "بشـﮧ͡ـ̷ٰ̯ــار عــامࢪ💞ֆۦ🇵🇸"},
#        308: {"name": "👑سِلَيَمًآنِيَ 👑🌧"},
#        309: {"name": "꧁الـسيَف اليمـا̨̥̬̩ني꧁"},


#        401: {"name": "👑 شَــــغَفْ 🩷✨"},
#        402: {"name": "🌹 وࢪدة🌹"},
#        403: {"name": "🔃 جمال🔃"},
#        404: {"name": "🦋"},
#        405: {"name": "• الطَّآمَّة |"},
#        406: {"name": "سامي"},
#        407: {"name": "رامي"},
#        408: {"name": "ناصر"},
#        409: {"name": "سامي"},
#        410: {"name": "رامي"},
    }

    # المتفوقون (4 من القروب الأول)
    fake_top_users = [101]

    output_path, caption = await create_results_card(
        bot=None,
        groups=fake_groups,
        parts=fake_parts,
        contest_name="اختبار تجريبي",
        top_users=fake_top_users,
        max_user_score=5,
        max_total=20,
        group_images={}
    )

    print("✅ تم توليد الصورة:", output_path)


# ----------------- دوال مساعدة -----------------
def load_special_names(names_file, images_dir):
    """
    يحمّل الأسماء المزخرفة من ملف نصي
    ويربط كل اسم بصورة PNG مقابلة (حسب رقم السطر)

    returns:
        dict[str, Image.Image]
        {
            "الاسم المزخرف": Image,
            ...
        }
    """
    special_names = {}

    if not os.path.exists(names_file):
        print(f"⚠️ ملف الأسماء غير موجود: {names_file}")
        return special_names

    if not os.path.isdir(images_dir):
        print(f"⚠️ مجلد الصور غير موجود: {images_dir}")
        return special_names

    with open(names_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            name = line.rstrip("\n")
            if not name:
                continue

            img_path = os.path.join(images_dir, f"{idx}.png")
            if not os.path.exists(img_path):
                print(f"⚠️ لا توجد صورة للاسم في السطر {idx}: {img_path}")
                continue

            try:
                img = Image.open(img_path).convert("RGBA")
                special_names[name] = img
            except Exception as e:
                print(f"❌ فشل تحميل الصورة {img_path}: {e}")

    return special_names


# تحميل خريطة الأسماء المزخرفة عند استيراد الوحدة
SPECIAL_NAMES_MAP = load_special_names(
    "utils/special_names.txt",
    "utils/special_names_images"
)

_font_cache = {}

def load_font(path, size):
    """
    تحميل الخط مع caching. إذا فشل، يرجع ImageFont.load_default()
    """
    key = (path, size)
    if key in _font_cache:
        return _font_cache[key]
    try:
        f = ImageFont.truetype(path, size)
    except Exception as e:
        # طباعة تحذير لكن نستمر
        print(f"⚠️ فشل تحميل الخط '{path}': {e}. سيتم استخدام خط افتراضي.")
        f = ImageFont.load_default()
    _font_cache[key] = f
    return f

def _measure_text(font, text):
    """
    قياس النص بشكل موثوق: نستخدم font.getbbox إذا متاح، وإلا نجرب ImageDraw.textbbox كبديل.
    يرجع (width, height, bbox)
    """
    try:
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height, bbox
    except Exception:
        # fallback: create temp image to measure
        im = Image.new("RGBA", (10,10))
        draw = ImageDraw.Draw(im)
        try:
            bbox = draw.textbbox((0,0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height, bbox
        except Exception:
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height, bbox

def safe_text(image_or_draw, pos, text, font, fill=(255,255,255,255), anchor=None):
    """
    Render text with optional Arabic shaping and emoji support.
    Uses Libraqm if available, else fallback to arabic_reshaper + bidi.
    """
    txt = text

    # --- استخدام Libraqm إذا متاحة ---
    # Pillow >= 9.0 مع libraqm يدعم العربية مباشرة
    if not getattr(ImageFont, "raqm", False):
        # fallback: reshape + bidi
        if HAS_ARABIC:
            try:
                reshaped = arabic_reshaper.reshape(text)
                txt = get_display(reshaped)
            except Exception:
                txt = text

    # --- رسم الرموز التعبيرية إذا متاحة ---
    if HAS_PILMOJI and isinstance(image_or_draw, Image.Image):
        try:
            src = NotoEmojiSource(FONT_EMOJI) if os.path.exists(FONT_EMOJI) else None
            with Pilmoji(image_or_draw, source=src) as pilmoji:
                if anchor:
                    w, h, _ = _measure_text(font, txt)
                    x, y = pos
                    if anchor == "mm":
                        pos2 = (x - w//2, y - h//2)
                    else:
                        pos2 = pos
                    pilmoji.text(pos2, txt, font=font, fill=fill)
                else:
                    pilmoji.text(pos, txt, font=font, fill=fill)
            return
        except Exception as e:
            print(f"⚠️ pilmoji failed: {e} — fallback to ImageDraw.text")

    # --- fallback إلى ImageDraw.text ---
    if isinstance(image_or_draw, Image.Image):
        draw = ImageDraw.Draw(image_or_draw)
    else:
        draw = image_or_draw

    if anchor:
        try:
            draw.text(pos, txt, font=font, fill=fill, anchor=anchor)
        except Exception:
            draw.text(pos, txt, font=font, fill=fill)
    else:
        draw.text(pos, txt, font=font, fill=fill)


async def get_user_avatar(bot, user_id):
    """
    Return PIL.Image or None.
    Uses aiogram 3 bot methods: get_user_profile_photos and download.
    """
    try:
        photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
        if photos.total_count == 0:
            return None
        file_id = photos.photos[0][0].file_id
        buffer = await bot.download(file_id)
        img = Image.open(buffer).convert("RGBA")
        return img
    except Exception as e:
        # لا نرمي استثناء كي يعمل البوت بأمان
        print(f"⚠️ تعذر جلب صورة المستخدم {user_id}: {e}")
        return None


def debug_bidi_runtime():
    try:
        import bidi
        import inspect

    except Exception as e:
        print("BIDI DEBUG ERROR:", e)


def debug_text_render_stack():


    # ---- Pillow ----
    try:
        import PIL
        from PIL import Image, features

    except Exception as e:
        print("Pillow check failed :", e)

    # ---- bidi ----
    try:
        import bidi
        from bidi.algorithm import get_display

    except Exception as e:
        print("bidi check failed   :", e)

    # ---- arabic_reshaper ----
    try:
        import arabic_reshaper


    except Exception as e:
        print("arabic_reshaper chk :", e)


def prepare_arabic_text(text: str) -> str:
        #في حال كان السيرفر يدعم اتجاة العربية تلقائيا
    return text
#def prepare_arabic_text(text):
    #في حال كان السيرفر لا يدعم اتجاه العربية
#    reshaped = arabic_reshaper.reshape(text)
#    return get_display(reshaped)

def make_circle(im, size, border=4, border_color=(255, 215, 0, 255)):
    """
    Creates a circular avatar:
    - crops image to square
    - resizes to target size
    - then shrinks avatar 50% inside the border
    """

    # safe resample
    try:
        resample = Image.LANCZOS
    except:
        resample = Image.Resampling.LANCZOS

    # --- 1) قص الصورة الأصلية إلى مربع ---
    im = im.copy().convert("RGBA")
    w, h = im.size
    min_side = min(w, h)

    left = (w - min_side) // 2
    top = (h - min_side) // 2
    im = im.crop((left, top, left + min_side, top + min_side))

    # --- 2) تغيير الحجم إلى الحجم الأساسي ---
    im = im.resize((size, size), resample)

    # --- 3) قصها إلى دائرة ---
    mask = Image.new("L", (size, size), 0)
    m = ImageDraw.Draw(mask)
    m.ellipse((0, 0, size, size), fill=255)

    avatar = Image.new("RGBA", (size, size), (0,0,0,0))
    avatar.paste(im, (0,0), mask)

    # --- 4) تصغير الصورة بنسبة 50% ---
    shrink = 0.5   # 50%
    new_size = int(size * shrink)

    avatar_small = avatar.resize((new_size, new_size), resample)

    # قص مرة أخرى للدائرة بعد التصغير:
    mask_small = Image.new("L", (new_size, new_size), 0)
    m2 = ImageDraw.Draw(mask_small)
    m2.ellipse((0, 0, new_size, new_size), fill=255)

    avatar_small.putalpha(mask_small)

    # --- 5) إنشاء إطار ملاصق للصورة المصغرة ---
    total = new_size + border * 2
    out = Image.new("RGBA", (total, total), (0,0,0,0))
    draw = ImageDraw.Draw(out)

    # رسم الإطار الذهبي
    draw.ellipse(
        (0, 0, total, total),
        outline=border_color,
        width=border
    )

    # وضع الصورة داخل الإطار
    out.paste(avatar_small, (border, border), avatar_small)

    return out

def load_background(path=GOLD_BG, min_w=1200, min_h=700):
    """
    Load a background image, ensure minimal dimensions by scaling up while preserving aspect ratio.
    Compatible with all Pillow versions.
    """

    # fix: safe LANCZOS selection
    try:
        resample = Image.LANCZOS
    except AttributeError:
        resample = Image.Resampling.LANCZOS

    if not os.path.exists(path):
        W, H = max(min_w, 1200), max(min_h, 700)
        bg = Image.new("RGBA", (W, H), (230, 190, 90, 255))
        return bg

    bg = Image.open(path).convert("RGBA")
    W, H = bg.size

    # scale only if smaller than minimum required size
    if W < min_w or H < min_h:
        scale = max(min_w / W, min_h / H)
        new_w = int(W * scale)
        new_h = int(H * scale)
        bg = bg.resize((new_w, new_h), resample)

    return bg



#دوال مساعدة في بناء البطاقة
import random

def calculate_groups_blocks_height(groups, parts, col_w):
    """
    حساب الارتفاع الكلي لكتل القروبات بشكل متطابق مع حلقة الرسم
    """
    avatar_group_h = int(col_w * 0.60)
    avatar_display_size = avatar_group_h // 2

    # --- قيم متطابقة مع حلقة الرسم الفعلية ---
    pad_top = 4
    pad_bottom = 1

    # ⚠️ هذه القيمة الصحيحة من حلقة الرسم (سطر 1130)
    INFO_BOX_H = 30
    name_box_h = 30

    participant_h = 35
    spacing_y = 6
    gap_between_groups = 20

    total_height = 0

    for cid, info in groups.items():
        participants = info.get("participants", [])
        participants_count = len(participants)

        # --- Medals Logic ---
        group_medals = info.get("medals", "")
        has_medals = bool(group_medals)
        medals_block_h = participant_h + spacing_y if has_medals else 0
        padding_medals_to_first_participant = 1

        # ⚠️ تصحيح: يجب تضمين INFO_BOX_H و +12 (كما في سطر 1130)
        full_h = INFO_BOX_H + avatar_display_size + name_box_h + 12
        frame_h = full_h + pad_top + pad_bottom

        # ---- participants ----
        if participants_count:
            total_rects_height = (
                participants_count * participant_h
                + (participants_count - 1) * spacing_y
            )
        else:
            total_rects_height = 0

        effective_rects_height = total_rects_height + medals_block_h + padding_medals_to_first_participant

        # حساب avatar_center_rel_y بشكل صحيح (كما في سطر 1165)
        avatar_center_rel_y = pad_top + INFO_BOX_H + 1 + avatar_display_size / 2

        block_center = max(avatar_center_rel_y, effective_rects_height / 2.0)

        framed_top = int(math.floor(block_center - avatar_center_rel_y))
        rects_top = int(math.floor(block_center - total_rects_height / 2.0)) if participants_count else 0

        # حساب الأسفل
        bottom_frame = framed_top + frame_h

        if participants_count:
            start_y_rects = int(round(block_center - effective_rects_height / 2.0))
            bottom_rects = start_y_rects + total_rects_height + medals_block_h + padding_medals_to_first_participant
        else:
            bottom_rects = -1

        last_y_for_divider = max(bottom_rects, bottom_frame)

        # ⚠️ تصحيح: استخدم +4 ثم نضيف المزيد للتوافق مع الرسم
        divider_y_in_block = last_y_for_divider + 5
        actual_block_used_height = divider_y_in_block + 4

        block_h_needed = max(
            framed_top + frame_h,
            rects_top + total_rects_height + medals_block_h + padding_medals_to_first_participant
        )

        block_h = max(block_h_needed, frame_h)

        # ⚠️ استخدم effective_block_h كما في حلقة الرسم (سطر 1633)
        effective_block_h = max(block_h, actual_block_used_height)

        total_height += int(effective_block_h)

    if groups:
        total_height += gap_between_groups * (len(groups) - 1)

    return total_height


def calculate_top_users_height(num_tops, frame_h, GAP):
    if num_tops == 0:
        return 0

    cols = 1 if num_tops <= 3 else 2
    rows = math.ceil(num_tops / cols)

    return rows * frame_h + (rows - 1) * GAP

def draw_embossed_border(canvas, thickness=10, radius=20):
    """
    Draw a rounded embossed (raised) border with soft gradient shadow.
    - canvas: كائن PIL Image
    - thickness: سماكة الحافة
    - radius: نصف قطر الزوايا المدورة
    """
    w, h = canvas.size
    base = canvas.copy()
    draw = ImageDraw.Draw(base, "RGBA")

    # لون الخلفية الأساسي
    bg_color = canvas.getpixel((0,0))  # يفترض أن اللون متجانس
    r, g, b, a = bg_color

    # إنشاء تدريج الظل: أغمق وأفتح
    light = (min(r+40,255), min(g+40,255), min(b+40,255), 120)
    dark = (max(r-40,0), max(g-40,0), max(b-40,0), 120)

    # نرسم عدة خطوط متدرجة للضوء والظل لتعطي إحساس 3D
    for i in range(thickness):
        alpha = int(120 * (1 - i/thickness))
        # خطوط الزوايا العليا واليسار (light)
        draw.line([(i, radius), (i, h-radius-1)], fill=(*light[:3], alpha))
        draw.line([(radius, i), (w-radius-1, i)], fill=(*light[:3], alpha))

        # خطوط الزوايا السفلى واليمن (dark)
        draw.line([(w-i-1, radius), (w-i-1, h-radius-1)], fill=(*dark[:3], alpha))
        draw.line([(radius, h-i-1), (w-radius-1, h-i-1)], fill=(*dark[:3], alpha))

    # رسم الزوايا مدورة: استخدام pieslice للزوايا الأربع
    draw.pieslice([0,0, 2*radius,2*radius], 180, 270, fill=light)
    draw.pieslice([w-2*radius,0, w,2*radius], 270, 360, fill=light)
    draw.pieslice([0,h-2*radius, 2*radius,h], 90, 180, fill=dark)
    draw.pieslice([w-2*radius,h-2*radius, w,h], 0, 90, fill=dark)

    return base

import random
import colorsys

def generate_gold_like_colors():
    # اختيار درجة لون عشوائية (0 إلى 1)
    h = random.random()

    # الإطار الخارجي: مشرق
    s_outer = 0.9
    v_outer = 1.0

    # الإطار الداخلي: نفس اللون لكن أغمق
    s_inner = 0.9
    v_inner = 0.6

    r1, g1, b1 = colorsys.hsv_to_rgb(h, s_outer, v_outer)
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s_inner, v_inner)

    OUTER_COLOR = (
        int(r1 * 255),
        int(g1 * 255),
        int(b1 * 255),
        255
    )

    INNER_COLOR = (
        int(r2 * 255),
        int(g2 * 255),
        int(b2 * 255),
        255
    )

    return OUTER_COLOR, INNER_COLOR

# ----------------- الدالة الرئيسة التي تبني البطاقة -----------------
async def create_results_card(bot,
                        groups,
                        top_users,
                        parts,
                        contest_name,
                        *,
                        canvas_w=1400,
                        canvas_h=900,
                        output_path="full_results_card.png",
                        group_images=None,
                        max_user_score=0,
                        max_total=1):



    # --- safe LANCZOS fallback for Pillow compatibility ---
    try:
        RESAMPLE = Image.LANCZOS
    except AttributeError:
        RESAMPLE = Image.Resampling.LANCZOS



    avatar_cache = {}
    circle_cache = {}
    group_img_cache = {}

    # ---------------- layout ----------------
    col_w = canvas_w // 3
    right_x0 = canvas_w - col_w
    mid_x0 = right_x0 - col_w
    left_x0 = 0
    left_x1 = col_w
    mid_x1 = right_x0

    # ================== حساب ارتفاع الكانفاس ديناميكيًا ==================

    # ارتفاع عمود القروبات + المشاركين
    groups_height = calculate_groups_blocks_height(groups, parts, col_w)

    # ارتفاع عمود المتفوقين
    TOP_GAP = 2
    TOP_FRAME_H = 260
    tops_height = calculate_top_users_height(len(top_users), TOP_FRAME_H, TOP_GAP)

    # نأخذ الأكبر
    content_height = max(groups_height, tops_height)

    EXTRA_MARGIN = 300
    canvas_h = int(content_height + EXTRA_MARGIN)


    # ================== إنشاء الكانفاس ==================
    bg_color = (
        random.randint(15, 45),
        random.randint(15, 45),
        random.randint(15, 45),
        255
    )
#    bg_color = (
#        random.randint(100, 220),
#        random.randint(100, 220),
#        random.randint(100, 220),
#        255
#    )

    canvas = Image.new("RGBA", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(canvas, "RGBA")


# أضف حواف كالبرواز
    canvas = draw_embossed_border(canvas, thickness=8, radius=25)


    # ================= إعدادات عامة =================
    EMBOSS_THICKNESS = 10     # نفس المستخدم في draw_embossed_border
    RADIUS = 5               # نفس radius في البرواز
    GAP = 2                   # الفاصل الأسود

    OFFSET = EMBOSS_THICKNESS + GAP + RADIUS

    TOP_BAR_H = 50
    SIDE_BAR_W = 7
    BOTTOM_BAR_H = 7

    GOLD, GOLD_SOFT = generate_gold_like_colors()
    #GOLD = (255, 215, 0, 255)
#    GOLD_SOFT = (184, 134, 11, 255)  # ذهبي غامق وغير شفاف
    BLACK = (0, 0, 0, 255)
    TEXT_COLOR = (0, 0, 0, 255)

    inner_w = canvas_w - OFFSET * 2
    inner_h = canvas_h - OFFSET * 2

    draw_canvas = ImageDraw.Draw(canvas, "RGBA")

        # ---------------- توسيط العمود الأيمن عموديًا ----------------
    # بعد إنشاء canvas مباشرة
    mid_canvas_y = canvas_h // 2
    start_y_right_col = mid_canvas_y - groups_height // 2

    # =================================================
    # 1) الإطار الأسود الفاصل (2px فقط – بدون ملء)
    # =================================================
    draw_canvas.rectangle(
        [
            OFFSET - GAP,
            OFFSET - GAP,
            OFFSET + inner_w + GAP - 1,
            OFFSET + inner_h + GAP - 1
        ],
        outline=BLACK,
        width=GAP
    )

    # =================================================
    # 2) الإطار الذهبي الرئيسي
    # =================================================

    # الشريط العلوي
    top_bar = Image.new("RGBA", (inner_w, TOP_BAR_H), GOLD)

    # تجهيز نص اسم المسابقة
    display_name = prepare_arabic_text(f"اسم المسابقة: {contest_name}")

    font_size = 42
    min_font_size = 20
    font_dynamic = load_font(FONT_SHOROOQ, font_size)

    draw_top = ImageDraw.Draw(top_bar)
    max_text_width = inner_w - 40

    while font_size >= min_font_size:
        bbox = draw_top.textbbox((0, 0), display_name, font=font_dynamic)
        text_w = bbox[2] - bbox[0]
        if text_w <= max_text_width:
            break
        font_size -= 1
        font_dynamic = load_font(FONT_SHOROOQ, font_size)

    ascent, descent = font_dynamic.getmetrics()
    text_h = ascent + descent

    text_x = (inner_w - text_w) // 2
    text_y = (TOP_BAR_H - text_h) // 2

    with Pilmoji(top_bar) as pilmoji:
        pilmoji.text(
            (text_x, text_y),
            display_name,
            font=font_dynamic,
            fill=TEXT_COLOR
        )

    canvas.paste(top_bar, (OFFSET, OFFSET), top_bar)

    # الشريط السفلي
    canvas.paste(
        Image.new("RGBA", (inner_w, BOTTOM_BAR_H), GOLD),
        (OFFSET, OFFSET + inner_h - BOTTOM_BAR_H)
    )

    # الشريط الأيسر
    canvas.paste(
        Image.new("RGBA", (SIDE_BAR_W, inner_h), GOLD),
        (OFFSET, OFFSET)
    )

    # الشريط الأيمن
    canvas.paste(
        Image.new("RGBA", (SIDE_BAR_W, inner_h), GOLD),
        (OFFSET + inner_w - SIDE_BAR_W, OFFSET)
    )

    # =================================================
    # 3) الإطار الذهبي الشفاف الداخلي (2px)
    # =================================================
    INNER_BORDER_OFFSET = OFFSET + SIDE_BAR_W
    INNER_BORDER_W = inner_w - SIDE_BAR_W * 2
    INNER_BORDER_H = inner_h - TOP_BAR_H - BOTTOM_BAR_H

    draw_canvas.rectangle(
        [
            INNER_BORDER_OFFSET,
            OFFSET + TOP_BAR_H,
            INNER_BORDER_OFFSET + INNER_BORDER_W - 1,
            OFFSET + TOP_BAR_H + INNER_BORDER_H - 1
        ],
        outline=GOLD_SOFT,
        width=4
    )


    # ---------- صندوق الامتداد الجديد (اتجاه يسار) ----------

    EXT_LEN = 800        # الامتداد الأفقي
    TOP_BAR_H2 = 34      # سماكة الجزء العلوي
    TAIL_W = 1           # سماكة الذيل
    VERTICAL_OFFSET = 4  # الإزاحة للأسفل
#    GOLD = GOLD_SOFT

    # حدود الإطار الشفاف
    inner_left   = INNER_BORDER_OFFSET
    inner_top    = OFFSET + TOP_BAR_H
    inner_right  = INNER_BORDER_OFFSET + INNER_BORDER_W - 1
    inner_bottom = OFFSET + TOP_BAR_H + INNER_BORDER_H - 1

    # --------- الجزء العلوي (يمين ← يسار) ---------
    top_bar_x1 = inner_right
    top_bar_x0 = top_bar_x1 - EXT_LEN
    top_bar_y0 = inner_top + VERTICAL_OFFSET
    top_bar_y1 = top_bar_y0 + TOP_BAR_H2

    draw_canvas.rectangle(
        [top_bar_x0, top_bar_y0, top_bar_x1, top_bar_y1],
        fill=GOLD
    )

    # --------- كتابة العنوان داخل الجزء العلوي ---------
    title_text = "ترتيب المجموعات"
    debug_text_render_stack()

    # تجهيز النص العربي (في حال وجود تشكيل / اتجاه)
    display_title = prepare_arabic_text(title_text)

    # إعداد الخط
    title_font_size = 30
    title_font = load_font(FONT_SHOROOQ, title_font_size)

    # حساب أبعاد النص
    bbox = draw_canvas.textbbox((0, 0), display_title, font=title_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # حساب مركز الصندوق العلوي
    text_x = top_bar_x0 + (EXT_LEN - text_w) // 2
    text_y = top_bar_y0 + (TOP_BAR_H2 - text_h) // 2

    # رسم النص (أسود)
    draw_canvas.text(
        (text_x, text_y),
        display_title,
        font=title_font,
        fill=(0, 0, 0, 255)
    )


    # --------- الذيل العمودي ---------
    tail_v_x0 = top_bar_x0
    tail_v_x1 = top_bar_x0 + TAIL_W
    tail_v_y0 = top_bar_y1
    tail_v_y1 = inner_bottom

    draw_canvas.rectangle(
        [tail_v_x0, tail_v_y0, tail_v_x1, tail_v_y1],
        fill=GOLD
    )

    # --------- الذيل الأفقي (ملاصق للإطار السفلي) ---------
    draw_canvas.rectangle(
        [
            top_bar_x0,
            inner_bottom - TAIL_W,
            inner_right,
            inner_bottom
        ],
        fill=GOLD
    )


#إطار ذهبي داخلي لصندوق ترتيب القروبات
    INNER_OFFSET = 2  # الإزاحة للداخل

    H_THICK = 4  # السماكة الأفقية (علوي + سفلي)
    draw_canvas.rectangle(
        [
            top_bar_x0 + INNER_OFFSET,
            inner_bottom - INNER_OFFSET - H_THICK,
            inner_right - INNER_OFFSET,
            inner_bottom - INNER_OFFSET
        ],
        fill=GOLD_SOFT
    )



    # ================== توليد لون نص داكن ومغاير للكانفاس ==================
    bg_lum = sum(bg_color[:3]) / 3  # متوسط السطوع
    if bg_lum < 140:  # خلفية داكنة نسبيًا
    # نختار نص فاتح نسبيًا
        text_color_dynamic = (
            random.randint(180, 255),
            random.randint(180, 255),
            random.randint(180, 255),
            255
        )
    else:  # خلفية فاتحة نسبيًا
        # نختار نص داكن
        text_color_dynamic = (
            random.randint(20, 70),
            random.randint(20, 70),
            random.randint(20, 70),
            255
        )



# ----------------- BLOKS: عمود القروبات + المشاركين (Block-based) -----------------

    group_items = []        # سنخزن (cid, framed_image, frame_w, frame_h, extra_meta)
    group_layout = {}       # تخزين مواضع القروبات النهائية إذا رغبت باستخدامها لاحقًا

    # إعدادات القيم الثابتة
    avatar_group_h = int(col_w * 0.60)
    avatar_display_size = avatar_group_h // 2

    pad_top = 4
    pad_sides = 30
    pad_bottom = 1
    border_width = 4
    border_color = (255, 215, 0, 255)

    # participant rect config (ثابت بالنسبة للعرض والارتفاع)
    participant_w = 260
    participant_h = 35
    spacing_y = 6
    gap_between_groups = 20

    # نرتب القروبات بحسب النقاط (عالي أولاً)
    sorted_groups = sorted(groups.items(), key=lambda x: x[1].get("group_total", x[1].get("score", 0)), reverse=True)

    # ======== 1) نجهز framed لكل قروب أولاً (لكن لا نرسمها على canvas بعد) ========
    for cid, info in sorted_groups:
        # اسم وصورة القروب
        group_name = await get_group_name(bot, cid)
        if cid in group_img_cache:
            gimg = group_img_cache[cid]
        else:
            gimg = await get_group_photo(bot, cid)
            if gimg is None:
                if os.path.exists(DEFAULT_AVATAR):
                    gimg = Image.open(DEFAULT_AVATAR).convert("RGBA")
                else:
                    gimg = Image.new("RGBA", (avatar_group_h, avatar_group_h), (200,180,170,255))
            group_img_cache[cid] = gimg


        # تصغير الصورة وقصها بزوايا مدورة
        gimg_resized = gimg.resize((avatar_display_size, avatar_display_size), RESAMPLE)
        radius = avatar_display_size // 4
        mask = Image.new("L", (avatar_display_size, avatar_display_size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, avatar_display_size, avatar_display_size),
            radius=radius,
            fill=255
        )
        gimg_rounded = Image.new("RGBA", (avatar_display_size, avatar_display_size), (0,0,0,0))
        gimg_rounded.paste(gimg_resized, (0,0), mask)
        #اطار ذهبي ملاصق للصورة
        border_thickness = 3
        border_color = (255, 215, 0, 255)

        border_draw = ImageDraw.Draw(gimg_rounded)
        for i in range(border_thickness):
            border_draw.rounded_rectangle(
                (
                    i,
                    i,
                    avatar_display_size - 1 - i,
                    avatar_display_size - 1 - i
                ),
                radius=radius - i,
                outline=GOLD
            )


#        #ثوابت خاصة بألوان الصناديق
#        DDARK_BOX_BG = (255, 255, 255, 200)
#        DDARK_BOX_TEXT = (255, 255, 255, 255)
#        # ---------- صندوق معلومات القروب (أعلى الصورة) ----------
#        INFO_BOX_H = 30
#        INFO_BOX_W = avatar_display_size + 50

#        # تعريف info_box
#        info_box = Image.new("RGBA", (INFO_BOX_W, INFO_BOX_H), DDARK_BOX_BG)
#        draw_info = ImageDraw.Draw(info_box)

#        group_score = info.get("group_total", info.get("score", 0))
#        avg_pct = info.get("avg_percentage", 0.0)
#        info_font = load_font(FONT_SULTAN, 18)

#        draw_info.text(
#            (8, INFO_BOX_H // 2),
#            f"{avg_pct:.0f}%",
#            font=info_font,
#            fill=(0, 0, 0, 255),
#            anchor="lm"
#        )
#        draw_info.text(
#            (INFO_BOX_W - 8, INFO_BOX_H // 2),
#            str(group_score),
#            font=info_font,
#            fill=(0, 0, 0, 255),
#            anchor="rm"
#        )

        #ثوابت خاصة بألوان الصناديق
        DDARK_BOX_BG = (255, 255, 255, 200)
        DDARK_BOX_TEXT = (255, 255, 255, 255)                
        # ---------- صندوق معلومات القروب (أعلى الصورة) ----------
        INFO_BOX_H = 30
        INFO_BOX_W = avatar_display_size + 50
                        
        info_box = Image.new("RGBA", (INFO_BOX_W, INFO_BOX_H), DDARK_BOX_BG)
        draw_info = ImageDraw.Draw(info_box)
        
        # القيم
        group_score = info.get("group_total", info.get("score", 0))
        group_avg = info.get("avg_percentage", 0)
        
        info_font = load_font(FONT_SULTAN, 22)
        
        # يسار: المعدل
        safe_text(
            info_box,
            (8, INFO_BOX_H // 2),
            f"{group_avg:.1f}%",
            info_font,
            fill=DDARK_BOX_TEXT,
            anchor="lm"
        )
        
        # يمين: النقاط
        safe_text(
            info_box,
            (INFO_BOX_W - 8, INFO_BOX_H // 2),
            str(group_score),
            info_font,
            fill=DDARK_BOX_TEXT,
            anchor="rm"
        )

        # ---------- صندوق اسم القروب (أسفل الصورة) ----------
        name_box_w = avatar_display_size + 50
        name_box_h = 30
        name_box = Image.new("RGBA", (name_box_w, name_box_h), DDARK_BOX_BG)

        display_name = prepare_arabic_text(group_name)

        font_size = 26
        min_font_size = 12
        font_dynamic = load_font(FONT_SULTAN, font_size)
        max_text_width = name_box_w - 10

        draw_name_tmp = ImageDraw.Draw(name_box)
        while font_size >= min_font_size:
            bbox = draw_name_tmp.textbbox((0, 0), display_name, font=font_dynamic)
            text_w = bbox[2] - bbox[0]
            if text_w <= max_text_width:
                break
            font_size -= 1
            font_dynamic = load_font(FONT_SULTAN, font_size)

        # حساب ارتفاع النص
        ascent, descent = font_dynamic.getmetrics()
        text_h = ascent + descent

        # التوسيط الأفقي والعمودي بدقة
        text_x = (name_box_w - text_w) // 2
        text_y = (name_box_h - text_h) // 2

        # رسم النص + إيموجي
        with Pilmoji(name_box) as pilmoji:
            pilmoji.text(
                (text_x, text_y),
                display_name,
                font=font_dynamic,
                fill=DDARK_BOX_TEXT
            )

        # تجميع الصورة + الاسم في block صغير
        full_h = INFO_BOX_H + avatar_display_size + name_box_h + 12
        full_w = max(avatar_display_size, name_box_w)
        block = Image.new("RGBA", (full_w, full_h), (0,0,0,0))
        img_x = (full_w - avatar_display_size)//2
        name_x = (full_w - name_box_w)//2
        y_cursor = 0

# صندوق المعلومات
        info_x = (full_w - INFO_BOX_W) // 2
        block.paste(info_box, (info_x, y_cursor), info_box)
        y_cursor += INFO_BOX_H + 1

# الصورة الرمزية
        block.paste(gimg_rounded, (img_x, y_cursor), gimg_rounded)
        y_cursor += avatar_display_size + 6

# صندوق الاسم
        block.paste(name_box, (name_x, y_cursor), name_box)


        # الإطار الذهبي حول block (ثابت العرض بالنسبة لليمين)
        frame_w = avatar_display_size + pad_sides*2
        frame_h = full_h + pad_top + pad_bottom
        framed = Image.new("RGBA", (frame_w, frame_h), (0,0,0,0))
        draw_frame = ImageDraw.Draw(framed)
        draw_frame.rectangle([(0,0),(frame_w-1, frame_h-1)], outline=GOLD, width=border_width)

        content_x = (frame_w - full_w)//2
        content_y = pad_top
        framed.paste(block, (content_x, content_y), block)

        # بعض الميتاداتا اللازمة لاحقًا:
        # - avatar_center_rel_x داخل الـ framed (نقطة مركز صورة القروب أفقياً داخل framed)
        # - avatar_center_rel_y داخل الـ framed (نقطة مركز صورة القروب عمودياً داخل framed)
        avatar_center_rel_x = content_x + img_x + avatar_display_size/2
        avatar_center_rel_y = content_y + INFO_BOX_H + 1 + avatar_display_size / 2

        # نحفظ العنصر مؤقتًا (لم نقم بوضعه بعد على canvas)
        group_items.append({
            "cid": cid,
            "framed": framed,
            "frame_w": frame_w,
            "frame_h": frame_h,
            "avatar_center_rel_x": avatar_center_rel_x,
            "avatar_center_rel_y": avatar_center_rel_y,
            "block_full_w": full_w,
            "block_full_h": full_h,
            "block_img_x": img_x,
            "block_content_x": content_x
        })

    # ======== 2) نحسب الارتفاع الكلي لجميع الكتل ومن ثم نحدد y البداية لتوسيط الكتل عمودياً ========
    total_height = sum(item["frame_h"] for item in group_items) + gap_between_groups * (len(group_items)-1 if len(group_items)>0 else 0)
    start_y = (canvas_h - total_height) // 2
    cur_y = start_y

    # ======== 3) الآن نجهز كل كتلة نهائياً (نضيف المشاركين داخل نفس الكتلة) ونلصقها على canvas ========
    cur_y = start_y_right_col
    for item in group_items:
        cid = item["cid"]
        info = groups[cid]   # ✅ هذا هو القروب الحالي
        framed = item["framed"]
        frame_w = item["frame_w"]
        frame_h = item["frame_h"]
        avatar_center_rel_x = item["avatar_center_rel_x"]
        avatar_center_rel_y = item["avatar_center_rel_y"]

        # participants: رتّبهم نزولياً حسب النقاط داخل info
        participants = sorted(groups[cid].get("participants", []), key=lambda x: -x[1])  # (uid, pts, percent)

        # ------ نحسب حجم منطقة المستطيلات (الجزء الأيسر من الكتلة) ------
        total_rects_height = 0
        if participants:
            total_rects_height = len(participants) * participant_h + (len(participants)-1) * spacing_y
        else:
            total_rects_height = 0


        group_medals = info.get("medals", "")
        has_medals = bool(group_medals)

        # ---- تحديد ارتفاع ميداليات افتراضية ----
        medals_block_h = participant_h + spacing_y if has_medals else 0
        padding_medals_to_first_participant = 1
        # نريد أن تكون نقطة مركز المستطيلات مساوية لنقطة مركز الصورة داخل الكتلة
        # لذلك نحدد مركز الكتلة (block_center) بحيث avatar_center_rel_y + framed_y == block_center
        # ونجعل مركز المستطيلات = block_center أيضًا
        # أبسط حل عملي: نجعل block_center = max(avatar_center_rel_y, total_rects_height/2)
        effective_rects_height = total_rects_height + medals_block_h + padding_medals_to_first_participant

        block_center = max(
            avatar_center_rel_y,
            effective_rects_height / 2.0
        )

        # طول الكتلة النهائي يجب أن يكفي لاستيعاب الإطار (framed) والمستطيلات إذا امتدّت أسفل أو فوق
        # نحتاج التأكد أن framed يمكن وضعه بحيث avatar_center_rel_y يتطابق مع block_center
        # framed_top_in_block = block_center - avatar_center_rel_y
        framed_top = int(math.floor(block_center - avatar_center_rel_y))
        # framed_bottom = framed_top + frame_h
        # المستطيلات ستبدأ عند:
        rects_top = int(math.floor(block_center - total_rects_height/2.0)) if participants else 0


# نحتاج طول كافٍ لاستيعاب أعلى عنصر وأدناه
        block_h_needed = max(
            framed_top + frame_h,
            rects_top + total_rects_height + (medals_block_h + padding_medals_to_first_participant)
        )


        # اجعل block_h على الأقل frame_h
        block_h = max(block_h_needed, frame_h)


        # الان نخلق صورة الكتلة النهائية بعرض (col_w * 2) لأننا سنضع هذه الكتلة في منتصف العمود الأوسط+الأيمن
        block_w = col_w * 2
        block_img = Image.new("RGBA", (block_w, block_h), (0,0,0,0))
        draw_block = ImageDraw.Draw(block_img)

        # موضع framed داخل block_img (مركزياً في القسم الأيمن)
        framed_x_in_block = col_w + (col_w - frame_w)//2
        framed_y_in_block = framed_top
        block_img.paste(framed, (framed_x_in_block, framed_y_in_block), framed)

        # احسب مركز الصورة في إحداثيات block_img لتحديد محاذاة المستطيلات
        avatar_center_x_in_block = framed_x_in_block + avatar_center_rel_x
        avatar_center_y_in_block = framed_y_in_block + avatar_center_rel_y

        # ------ رسم المستطيلات (participants) أمام منتصف صورة القروب من جهة اليسار ------
        if participants:
            # -----------------------------
            # ترتيب عالمي حقيقي للمستخدمين (يدعم التعادل)
            # -----------------------------
            all_users = []

            for _, gdata in groups.items():
                for uid, pts, _ in gdata.get("participants", []):
                    all_users.append((uid, pts))

            global_ranking = {}
            sorted_users = sorted(all_users, key=lambda x: -x[1])

            current_rank = 0
            last_points = None

            for idx, (uid, pts) in enumerate(sorted_users, start=1):
                if pts != last_points:
                    current_rank = idx
                    last_points = pts
                global_ranking[uid] = current_rank

 #///////////////////////////////



            # ---- الآن نحسب موقع بداية رسم المشاركين مع أخذ الميداليات والحشو بالحسبان ----
            effective_rects_height = total_rects_height + medals_block_h + padding_medals_to_first_participant

# start_y_rects يتحرك فقط لتوسيط المشاركين داخل البلوك
            start_y_rects = int(round(avatar_center_y_in_block - effective_rects_height / 2.0))

            # --- موضع صندوق الميداليات (كمشارك وهمي فوق الجميع) ---
            if has_medals:
    # نضع الميدالية فوق أول صندوق للمشاركين مباشرة مع فرق 2px
                medals_y0 = start_y_rects + 2
                medals_y1 = medals_y0 + participant_h
            rect_center_x = int(round(avatar_center_x_in_block - 330))

            # صندوق المشارك الأساسي
            rect_left = rect_center_x - participant_w // 2
            rect_right = rect_left + participant_w


            # صندوق النسبة (100px) – ملاصق للمشارك
            side2_w = 40
            side2_right = rect_left - 4
            side2_left = side2_right - side2_w

            # صندوق إضافي (150px) – أبعد
            side1_w = 100
            side1_right = side2_left - 4
            side1_left = side1_right - side1_w




            for i, p in enumerate(participants):
                uid = p[0]
                data = parts.get(uid, {})


                y0 = start_y_rects + medals_block_h + padding_medals_to_first_participant + i * (participant_h + spacing_y)
                y1 = y0 + participant_h

                # الصندوق الأبعد (150px)
                draw_block.rectangle(
                    [side1_left, y0, side1_right, y1],
                    outline=GOLD,
                    width=2
                )

            # ===== رسم ميداليات القروب (بدون صندوق) =====
            if group_medals:
                # استخدم كل الصناديق الثلاثة لتحديد الوسط
                medals_y1 = medals_y0 + participant_h
                total_left = side1_left
                total_right = rect_right
                center_x = (total_left + total_right) // 2
                center_y = (medals_y0 + medals_y1) // 2

                # تجهيز النص (نفس منطق الأسماء)
                display_medals = prepare_arabic_text(group_medals)

                # 🔍 هل توجد صورة مزخرفة للإيموجي؟
                special_img = SPECIAL_NAMES_MAP.get(display_medals)

                if special_img:
                    # ====== لصق صورة بدل الإيموجي ======
                    img_w, img_h = special_img.size

                    # تحديد الحجم بناءً على الارتفاع فقط (85% من ارتفاع الصندوق)
                    target_h = participant_h * 1.1
                    scale = min(target_h / img_h, 1.0)

                    new_w = int(img_w * scale)
                    new_h = int(img_h * scale)

                    if scale < 1.0:
                        try:
                            resample = Image.Resampling.LANCZOS  # Pillow >= 9
                        except AttributeError:
                            try:
                                resample = Image.LANCZOS            # Pillow القديمة
                            except AttributeError:
                                resample = 3

                        special_img = special_img.resize((new_w, new_h), resample)

                    paste_x = center_x - new_w // 2
                    paste_y = center_y - new_h // 2

                    block_img.paste(
                        special_img,
                        (paste_x, paste_y),
                        special_img
                    )

                else:
                    # ====== المسار القديم (Pilmoji) ======
                    font_medals = load_font(FONT_SULTAN, 40)

                    tmp = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
                    with Pilmoji(tmp) as pilmoji:
                        pilmoji.text(
                            (0, 0),
                            display_medals,
                            font=font_medals,
                            fill=(255, 255, 255, 255)
                        )

                    bbox = tmp.getbbox()
                    if bbox:
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]

                        paste_x = center_x - w // 2
                        paste_y = center_y - h // 2

                        block_img.paste(
                            tmp.crop(bbox),
                            (paste_x, paste_y),
                            tmp.crop(bbox)
                        )


                    # ----- الحصول على الإنجازات من الدالة الجاهزة -----
            # إنشاء ترتيب حقيقي حسب النقاط (يدعم التعادل)
            for i, p in enumerate(participants):
                uid = p[0]
                data = parts.get(uid, {})
                name = data.get("name", f"User {uid}")

                y0 = start_y_rects + medals_block_h + padding_medals_to_first_participant + i * (participant_h + spacing_y)
                y1 = y0 + participant_h

                # --- الصندوق الرأسي لكل مشارك ---
                side1_w = 100
                side1_right = side2_left - 4
                side1_left = side1_right - side1_w

                draw_block.rectangle([side1_left, y0, side1_right, y1],
                                     outline=GOLD, width=2)


                # --- الجوائز ---
                participant_text = format_participant(uid, data, max_total, global_ranking, bot_id=None)
                achievements = participant_text.split(name)[-1].strip()

                if achievements:
                    # تجهيز النص (نفس أسلوب الأسماء)
                    display_achievements = prepare_arabic_text(achievements)

                    # 🔍 هل توجد صورة مزخرفة للجائزة؟
                    special_img = SPECIAL_NAMES_MAP.get(display_achievements)

                    center_x = (side1_left + side1_right) // 2
                    center_y = (y0 + y1) // 2

                    if special_img:
                        # ====== لصق صورة الجائزة بدل الإيموجي ======
                        img_w, img_h = special_img.size

                        max_w = side1_w - 10
                        max_h = participant_h - 6

                        scale = min(max_w / img_w, max_h / img_h, 1.0)
                        new_w = int(img_w * scale)
                        new_h = int(img_h * scale)

                        if scale < 1.0:
                            try:
                                resample = Image.Resampling.LANCZOS
                            except AttributeError:
                                try:
                                    resample = Image.LANCZOS
                                except AttributeError:
                                    resample = 3

                            special_img = special_img.resize((new_w, new_h), resample)

                        paste_x = center_x - new_w // 2
                        paste_y = center_y - new_h // 2

                        block_img.paste(
                            special_img,
                            (paste_x, paste_y),
                            special_img
                        )

                    else:
                        # ====== المسار القديم (الإيموجي العادي) ======
                        font_emoji = load_font(FONT_SULTAN, 25)

                        tmp = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
                        with Pilmoji(tmp) as pilmoji:
                            pilmoji.text(
                                (0, 0),
                                display_achievements,
                                font=font_emoji,
                                fill=(255, 255, 255, 255)
                            )

                        bbox = tmp.getbbox()
                        if bbox:
                            emoji_w = bbox[2] - bbox[0]
                            emoji_h = bbox[3] - bbox[1]

                            paste_x = center_x - emoji_w // 2
                            paste_y = center_y - emoji_h // 2

                            block_img.paste(
                                tmp.crop(bbox),
                                (paste_x, paste_y),
                                tmp.crop(bbox)
                            )

                # صندوق النسبة (100px)
                draw_block.rectangle(
                    [side2_left, y0, side2_right, y1],
                    outline=GOLD,
                    width=2
                )

                percentage = (p[1] / max_total * 100) if max_total else 0
                safe_text(
                    block_img,
                    ((side2_left + side2_right)//2, (y0 + y1)//2),
                    f"{percentage:.0f}%",
                    load_font(AMIRI_FONT, 15),
                    fill=(255, 255, 255, 255),
                    anchor="mm"
                )


                # صندوق اسم المشارك


                draw_block.rectangle(
                    [rect_left, y0, rect_right, y1],
                    outline=GOLD,
                    width=2
                )

                # تجهيز النص (عربي + زخرفة + إيموجي)
                name = parts.get(uid, {}).get("name", f"User {uid}")

                display_name = prepare_arabic_text(name) # للرسم فقط

                # ============================================
                # 🔍 هل الاسم موجود ضمن الأسماء المزخرفة الخاصة؟
                # ============================================
                special_img = SPECIAL_NAMES_MAP.get(name)

                if special_img:
                    # --- لصق صورة الاسم المزخرف بدل النص ---

                    img_w, img_h = special_img.size

                    max_w = participant_w - 10
                    max_h = participant_h - 6

                    scale = min(max_w / img_w, max_h / img_h, 1.0)
                    new_w = int(img_w * scale)
                    new_h = int(img_h * scale)

                    if scale < 1.0:
    # اختيار طريقة إعادة التحجيم بشكل متوافق مع جميع نسخ Pillow
                        try:
                            resample = Image.Resampling.LANCZOS  # Pillow >= 9
                        except AttributeError:
                            try:
                                resample = Image.LANCZOS            # الإصدارات القديمة
                            except AttributeError:
                                resample = 3

                        special_img = special_img.resize((new_w, new_h), resample)

                    paste_x = (rect_left + rect_right) // 2 - new_w // 2
                    paste_y = (y0 + y1) // 2 - new_h // 2

                    block_img.paste(
                        special_img,
                        (paste_x, paste_y),
                        special_img
                    )

                else:
                    # ================== تلاصق تام (0px gap) أفقياً أو عمودياً للمشاركين (أبيض ناصع + زيادة الحجم بمقدار رقمين) ==================
                    rendered_img = render_text_via_playwright(display_name, font_size=34, fill=(255,255,255,255), max_width=participant_w, max_height=participant_h)
                    if rendered_img:
                        rw, rh = rendered_img.size
                        rx = (rect_left + rect_right) // 2 - rw // 2
                        ry = (y0 + y1) // 2 - rh // 2
                        block_img.paste(rendered_img, (rx, ry), rendered_img)


        # ------ لصق block_img على canvas أولًا ------
        GROUP_SHIFT_X = 50  # جرّب 20–40 حسب الذوق

        paste_x = mid_x0 + GROUP_SHIFT_X
        paste_y = cur_y
        canvas.paste(block_img, (paste_x, paste_y), block_img)

        # ------ رسم الخط الأزرق بعد آخر جزء من البلوك مباشرة على canvas ------
        draw_canvas = ImageDraw.Draw(canvas)
        bottom_rects = (start_y_rects + medals_block_h + padding_medals_to_first_participant + total_rects_height)
        if participants:
            bottom_rects = start_y_rects + total_rects_height + (medals_block_h if has_medals else 0) + padding_medals_to_first_participant
        else:
            bottom_rects = -1


# حد أسفل الإطار
        bottom_frame = framed_y_in_block + frame_h

# آخر موضع رأسي للرسم (سواء المشاركين+ميداليات أو الإطار)
        last_y_for_divider = max(bottom_rects, bottom_frame)

        divider_y_in_block = last_y_for_divider + 5

# ⬅️ آخر ارتفاع فعلي استُخدم داخل البلوك
        actual_block_used_height = divider_y_in_block + 4
# ⬅️ الارتفاع الحقيقي المعتمد للبلوك
        effective_block_h = max(block_h, actual_block_used_height)

        line_y_canvas = paste_y + divider_y_in_block
        line_x0_canvas = paste_x + avatar_center_x_in_block - 640  # يبدأ من 500px يسار مركز الصورة الرمزية
        # لا تجعل الخط يتجاوز الذيل العمودي للصندوق الذهبي
        right_bar_x = OFFSET + inner_w - SIDE_BAR_W
        line_x1_canvas = min(paste_x + block_img.width, right_bar_x)

        draw_canvas.line(
            [line_x0_canvas, line_y_canvas, line_x1_canvas, line_y_canvas],
            fill=GOLD,
            width=3
        )

        # --------- الخط السفلي الملاصق ---------
        DARK_GOLD = (180, 140, 0, 255)  # ذهبي غامق – عدله حسب ذوقك

        draw_canvas.line(
            [
                line_x0_canvas,
                line_y_canvas + 2,   # ملاصق من الأسفل
                line_x1_canvas,
                line_y_canvas + 2
            ],
            fill=GOLD_SOFT,
            width=2
        )

        # ------ حفظ group_layout بالمواضع المطلقة ------
        group_layout[cid] = {
            "x": paste_x + framed_x_in_block,
            "y": paste_y + framed_y_in_block,
            "w": frame_w,
            "h": frame_h,
            "avatar_center_x": paste_x + avatar_center_x_in_block,
            "avatar_center_y": paste_y + avatar_center_y_in_block
        }

        # ------ تحديث cur_y للكتلة التالية ------
        cur_y += effective_block_h + gap_between_groups

 # ----------------------------------------------------------------------------------------
    # انتهى بناء كتل القروبات + المشاركين؛ تبقى العمود الأيسر (المتفوقين) يتم إنشاؤه كما قبل
    # ----------------------------------------------------------------------------------------
    # ----------------- العمود الأيسر (المتفوقين) -----------------
    #أولا ثوابت الصندوق العلوي
    SCORE_BOX_HEIGHT = 28
    SCORE_BOX_BG = (0, 0, 0, 130)   # شفاف
    SCORE_TEXT_COLOR = (255, 255, 255, 255)
    SCORE_PADDING = 10

    # ===== ثوابت سهلة التعديل =====
    NAME_BOX_WIDTH = 190        # عرض ثابت لصندوق الاسم
    NAME_BOX_HEIGHT = 40        # ارتفاع ثابت لصندوق الاسم

    FRAME_BORDER_WIDTH = 6      # سماكة الإطار الذهبي
    NAME_BOX_Y_OFFSET = 5     # إنزال صندوق الاسم للأسفل
    # =============================

    top_avatars = []
    for uid in top_users:
        if uid in avatar_cache:
            avat = avatar_cache[uid]
        else:
            avat = await get_user_avatar(bot, uid) if bot else None
            if avat is None and os.path.exists(DEFAULT_AVATAR):
                avat = Image.open(DEFAULT_AVATAR).convert("RGBA")
            if avat is None:
                avat = Image.new("RGBA", (200,200), (180,180,180,255))
            avatar_cache[uid] = avat
        top_avatars.append((uid, avat))

    num_tops = len(top_avatars)
    if num_tops == 0:
        return  # لا يوجد متفوقون

    # حجم الصورة الرمزية
    avatar_display_size = int(col_w * 0.6)
    avatar_display_size = max(60, avatar_display_size)

    # المسافة الفارغة بين المتفوقين
    GAP = 2

    # عرض الإطار (يعتمد على الأكبر: الصورة أو صندوق الاسم)
    frame_padding = 1
    FRAME_WIDTH_OFFSET = 77
    frame_w = avatar_display_size - FRAME_WIDTH_OFFSET

    # تحديد عدد الأعمدة
    cols = 1 if num_tops <= 3 else 2
    rows = math.ceil(num_tops / cols)

    # ---------------- الحساب الحقيقي لارتفاع الإطار ----------------

    IMG_TOP = 25

    content_bottom = (
        NAME_BOX_HEIGHT // 2
    )

    frame_h = content_bottom + 250   # هامش سفلي صغير فقط

    # ----------------------------------------------------------------

    # حساب أبعاد الشبكة
    grid_width = cols * frame_w + (cols - 1) * GAP
    grid_height = rows * frame_h + (rows - 1) * GAP

    # منتصف العمود الأيسر
    mid_col_y = canvas_h // 2
    start_x = left_x0 + (col_w - grid_width) // 2
    start_y = mid_col_y - grid_height // 2


    # ---------- صندوق عنوان المتفوقين ----------
    TITLE_TEXT = prepare_arabic_text("المتفوقون")
    TITLE_BOX_W = 80
    TITLE_BOX_H = 25
    TITLE_BG = SCORE_BOX_BG   # أو لون مخصص
    DDARK_BOX_TEXT = (255, 255, 255, 255)
    TITLE_TEXT_COLOR = DDARK_BOX_TEXT

    title_box = Image.new("RGBA", (TITLE_BOX_W, TITLE_BOX_H), TITLE_BG)
    draw_title = ImageDraw.Draw(title_box)

    title_font = load_font(FONT_SULTAN, 22)


    draw_title.text(
        (TITLE_BOX_W // 2, TITLE_BOX_H // 2),
        TITLE_TEXT,
        font=title_font,
        fill=TITLE_TEXT_COLOR,
        anchor="mm"
    )

# حساب مكان الصندوق
    row_width = cols * frame_w + (cols - 1) * GAP
    title_x = start_x + (row_width - TITLE_BOX_W) // 2 + 63
    title_y = start_y - TITLE_BOX_H + 4  # ملتصق بأعلى عنصر

    canvas.paste(title_box, (title_x, title_y), title_box)

    for idx, (uid, avat) in enumerate(top_avatars):

        circ = make_circle(
            avat,
            avatar_display_size,
            border=4,
            border_color=GOLD
        )

        block_img = Image.new("RGBA", (frame_w, frame_h), (0,0,0,0))
        draw_block = ImageDraw.Draw(block_img)

        # ---------- صندوق المعلومات أعلى الصورة ----------
        INFO_BOX_H = 25
        INFO_BOX_W = NAME_BOX_WIDTH  # نفس عرض صندوق الاسم
        info_box = Image.new("RGBA", (INFO_BOX_W, INFO_BOX_H), SCORE_BOX_BG)
        draw_info = ImageDraw.Draw(info_box)

        percentage = (max_user_score / max_total * 100) if max_total else 0
        info_font = load_font(FONT_SULTAN, 22)

        # يسار: النسبة
        safe_text(
            info_box,
            (8, INFO_BOX_H // 2),
            f"{percentage:.1f}%",
            info_font,
            fill=DDARK_BOX_TEXT,
            anchor="lm"
        )

        # يمين: النقاط
        safe_text(
            info_box,
            (INFO_BOX_W - 8, INFO_BOX_H // 2),
            str(max_user_score),
            info_font,
            fill=DDARK_BOX_TEXT,
            anchor="rm"
        )

        # لصق الصندوق أعلى الصورة الرمزية
        y_cursor = IMG_TOP - INFO_BOX_H // 2
        info_x = (frame_w - INFO_BOX_W) // 2
        block_img.paste(info_box, (info_x, y_cursor), info_box)
        frame_top = y_cursor - 6   # ملاصق تقريبًا لصندوق النسبة

        # ---------- الصورة الرمزية ----------
        img_x = (frame_w - circ.size[0]) // 2
        img_y = y_cursor + INFO_BOX_H
        block_img.paste(circ, (img_x, img_y), circ)
        y_cursor = img_y + circ.size[1] + 4

        # ---------- صندوق الاسم أسفل الصورة ----------
        name = parts.get(uid, {}).get("name", f"User {uid}")
        display_name = prepare_arabic_text(name)

        name_box = Image.new("RGBA", (NAME_BOX_WIDTH, NAME_BOX_HEIGHT), SCORE_BOX_BG)
        draw_name = ImageDraw.Draw(name_box)

        # ======= التحقق من الاسم المزخرف =======
        special_img = SPECIAL_NAMES_MAP.get(name)

        if special_img:
            img_w, img_h = special_img.size

            max_w = NAME_BOX_WIDTH - 6  # اترك حافة صغيرة
            max_h = NAME_BOX_HEIGHT - 4

            # ---- تحديد scale ليملأ الصندوق قدر الإمكان مع الحفاظ على النسبة ----
            scale_w = max_w / img_w
            scale_h = max_h / img_h
            scale = min(scale_w, scale_h)  # نحافظ على النسبة الأصلية

            # ---- الحجم النهائي للصورة بعد التحجيم ----
            final_w = int(img_w * scale)
            final_h = int(img_h * scale)

            # ---- إعادة تحجيم الصورة مع LANCZOS لضمان جودة عالية ----
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                try:
                    resample = Image.LANCZOS
                except AttributeError:
                    resample = 3

            special_img_resized = special_img.resize((final_w, final_h), resample)

            # ---- لصق الصورة في منتصف الصندوق ----
            paste_x = (NAME_BOX_WIDTH - final_w) // 2
            paste_y = (NAME_BOX_HEIGHT - final_h) // 2

            name_box.paste(special_img_resized, (paste_x, paste_y), special_img_resized)

        else:
            # ======= تلاصق تام (0px gap) أفقياً أو عمودياً للمتفوقين (أبيض ناصع + زيادة الحجم بمقدار رقمين) =======
            rendered_img = render_text_via_playwright(display_name, font_size=30, fill=(255,255,255,255), max_width=NAME_BOX_WIDTH, max_height=NAME_BOX_HEIGHT)
            if rendered_img:
                rw, rh = rendered_img.size
                rx = (NAME_BOX_WIDTH - rw) // 2
                ry = (NAME_BOX_HEIGHT - rh) // 2
                name_box.paste(rendered_img, (rx, ry), rendered_img)


        name_x = (frame_w - NAME_BOX_WIDTH) // 2
        block_img.paste(name_box, (name_x, y_cursor), name_box)
        y_cursor += NAME_BOX_HEIGHT + 6
        frame_bottom = y_cursor + 34  # أطول قليلًا من الأسفل

        # ---------- كأس تحت صندوق الاسم ----------
        trophy_text = "🏆"
        trophy_font_size = 33  # يمكن تعديلها
        trophy_font = load_font(FONT_SULTAN, trophy_font_size)

        # قياس حجم الكأس
        draw_tmp = ImageDraw.Draw(block_img)
        bbox = draw_tmp.textbbox((0, 0), trophy_text, font=trophy_font)
        trophy_w = bbox[2] - bbox[0]
        trophy_h = bbox[3] - bbox[1]

        # محاذاة أفقية مع منتصف صندوق الاسم
        trophy_x = name_x + (NAME_BOX_WIDTH - trophy_w) // 2 - 9

        # أسفل صندوق الاسم مباشرة
        trophy_y = y_cursor - 5  # مسافة بسيطة (عدّلها إن أحببت)

        # رسم الكأس
        with Pilmoji(block_img) as pilmoji:
            pilmoji.text(
                (trophy_x, trophy_y),
                trophy_text,
                font=trophy_font,
                fill=(0, 0, 0, 255)  # أسود
            )

        # تحديث المؤشر العمودي
        y_cursor += trophy_h + 6


        # ---------- الإطار الذهبي حول البلوك ----------
        draw_block.rectangle(
            [0, frame_top, frame_w - 1, frame_bottom],
            outline=GOLD,
            width=FRAME_BORDER_WIDTH
        )

        # تحديد مكان كل متفوق في الشبكة
        row = idx // cols
        col = idx % cols

        if cols == 2 and idx == num_tops - 1 and num_tops % 2 == 1:
            cx = left_x0 + (col_w - frame_w) // 2 + 63
        else:
            cx = start_x + col * (frame_w + GAP) + 63

        cy = start_y + row * (frame_h + GAP)

        canvas.paste(block_img, (cx, cy), block_img)


    # ----------------- حفظ وإخراج -----------------
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    canvas.save(output_path)

    # ----------------- إعداد الكابشن النصي -----------------
    caption = "نتائج المشاركين من المجموعات والأعضاء"

    # ---- تحقق من أن القيم صحيحة قبل الإرجاع ----
    if not isinstance(output_path, str) or not isinstance(caption, str):
        raise ValueError(
            f"create_results_card returned invalid types: "
            f"{type(output_path)}, {type(caption)}"
        )

    return output_path, caption


if __name__ == "__main__":
    asyncio.run(run_debug_preview())
