#!/usr/bin/env python3
"""
أوابد: أتمتة كاملة في ملف واحد.
  python main.py publish     # ينتج فيديو ويرفعه مجدول (يشتغل من GitHub Actions)
  python main.py health      # فحص صحي (توكن يوتيوب، مفتاح Gemini، ffmpeg، الصوت)
  python main.py dry-run     # اختبار بمكونات وهمية بدون شبكة (--render لتشغيل Remotion)
  python main.py selftest    # اختبارات الوحدات
  python main.py setup       # ينشئ ملفات مشروع الفيديو (مدموجة في هذا الملف)
كل الإعدادات في الكلاس C أول الملف.
"""
import argparse
import argparse, random, subprocess, tempfile
import asyncio
import io
import json
import math
import numpy as np
import os
import random
import re
import requests
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timedelta, timezone
from datetime import datetime, timezone
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve
from zoneinfo import ZoneInfo


# ============ config ============
VERSION = "2026-11-02 doodle + director v2 + shorts v2"


class C:
    """كل الإعدادات في مكان واحد."""
    CHANNEL_NAME = "أوابد"
    TZ = ZoneInfo("Asia/Riyadh")

    # ---- النشر: (يوم الأسبوع, الساعة) الاثنين=0 ... الأحد=6 ----
    # 5 أيام بالأسبوع وأوقات متنوعة (بتوقيت الرياض): أحد صباحاً، اثنين ظهراً، أربعاء عصراً، خميس ليلاً، جمعة بعد العصر
    SCHEDULE = [(6, "09:00"), (0, "13:00"), (2, "17:00"), (3, "21:00"), (4, "16:00")]
    HORIZON_DAYS = 9          # نجهز فيديوهات قدام بـ9 أيام = رصيد يغطي أي عطل قصير
    MIN_LEAD_HOURS = 3        # أقل مدة بين الآن وموعد النشر (الرندر ياخذ وقت)
    MAX_ATTEMPTS = 3          # محاولات لكل موعد في اليوم، وبعدها نرتاح 20 ساعة ثم نعيد (ما نستسلم أبداً)
    RETRY_AFTER_HOURS = 20

    # ---- المحتوى ----
    TARGET_WORDS = (850, 1150)    # تقريباً 6 إلى 8 دقايق
    BEAT_WORDS_MAX = 75
    BANNED_WORDS = ["جنس", "عاري", "مخدرات", "انتحار"]   # عدّلها براحتك
    # ---- التصنيفات: القناة تدور عليها بالتساوي (ما تكون كلها عن موضوع واحد) ----
    CATEGORIES = {
        "الإنسان القديم وما قبل التاريخ": [
            "لماذا رسم الإنسان القديم على جدران الكهوف في الظلام؟",
            "لماذا انقرض إنسان النياندرتال وبقي الإنسان العاقل؟",
            "كيف تعلم الإنسان القديم إشعال النار وكيف غيرت حياته؟"],
        "الرافدين: سومر وبابل وآشور": [
            "كيف بنى السومريون أول مدن العالم؟",
            "ما سر مدينة بابل وبرجها الشهير بين الأسطورة والتاريخ؟",
            "لماذا كانت آشور أقوى إمبراطورية عسكرية في عصرها؟"],
        "مصر القديمة": [
            "كيف بنى المصريون القدماء الأهرامات؟",
            "لماذا حنط المصريون القدماء موتاهم؟",
            "من هي حتشبسوت الملكة التي حاول خلفاؤها محو اسمها؟"],
        "بلاد الشام وسوريا القديمة": [
            "ما قصة مدينة إيبلا السورية وألواحها الطينية؟",
            "من هم الفينيقيون وكيف سادوا البحر المتوسط؟",
            "كيف تحدت زنوبيا ملكة تدمر قوة روما؟"],
        "بلاد فارس": [
            "كيف أسس قورش أول إمبراطورية كبرى في التاريخ؟",
            "من هم الخالدون الجيش الفارسي الأسطوري؟",
            "لماذا سقطت الإمبراطورية الساسانية؟"],
        "الإمبراطورية الرومانية": [
            "كيف نشأت روما ولماذا سيطرت على العالم القديم؟",
            "لماذا سقطت الإمبراطورية الرومانية الغربية؟",
            "كيف كانت الحياة في مدينة بومبي قبل ثوران بركان فيزوف؟"],
        "اليونان القديمة": [
            "لماذا ظهرت الفلسفة في اليونان القديمة؟",
            "كيف فتح الإسكندر الأكبر نصف العالم المعروف؟",
            "ما سر حرب طروادة بين الأسطورة والتاريخ؟"],
        "العرب قبل الإسلام وحضاراتهم": [
            "ما قصة مملكة سبأ وسد مأرب؟",
            "من هم الأنباط وكيف نحتوا مدينة البتراء؟",
            "ما سر مدائن صالح وحضارة الحجر؟"],
        "الحضارة الإسلامية والعصر الذهبي": [
            "كيف أصبحت بغداد أكبر مدينة في العالم؟",
            "ما قصة بيت الحكمة وعلماء العصر الذهبي؟",
            "كيف بنى المسلمون حضارة الأندلس؟"],
        "الصين القديمة": [
            "لماذا بنى الصينيون سور الصين العظيم؟",
            "ما سر جيش الطين المدفون مع أول إمبراطور صيني؟",
            "كيف غير طريق الحرير وجه العالم؟"],
        "اليابان": [
            "من هم الساموراي وما سر شرفهم؟",
            "لماذا أغلقت اليابان أبوابها أمام العالم قرنين؟",
            "كيف حكم الشوغون اليابان بينما الإمبراطور في القصر؟"],
        "الهند وجنوب آسيا": [
            "ما سر مدينة موهنجو دارو التي اختفت؟",
            "من هو أشوكا الإمبراطور الذي غير طريقه بعد المعركة؟",
            "كيف بنيت أعجوبة تاج محل؟"],
        "الأمريكتان القديمة": [
            "لماذا اختفت مدن المايا الكبرى؟",
            "كيف بنى الإنكا ماتشو بيتشو في قمة الجبال؟",
            "كيف بنى الأزتك عاصمتهم فوق بحيرة؟"],
        "إفريقيا القديمة": [
            "من هو منسا موسى أغنى رجل في التاريخ؟",
            "ما قصة مملكة أكسوم التي سيطرت على البحر الأحمر؟",
            "من هم ملوك النوبة الذين حكموا مصر؟"],
        "أوروبا في العصور الوسطى": [
            "من هم الفايكنج حقا بعيدا عن الصورة الشائعة؟",
            "كيف غير الطاعون الأسود وجه أوروبا؟",
            "كيف كانت الحياة داخل قلعة في العصور الوسطى؟"],
        "ملوك وقادة غيروا التاريخ": [
            "كيف أصبح جنكيز خان أعظم فاتح في التاريخ؟",
            "من هي كليوباترا بعيدا عن الأسطورة؟",
            "كيف عبر هنيبعل جبال الألب بالفيلة نحو روما؟"],
        "ألغاز أثرية غريبة": [
            "لماذا بني ستونهنج وما سر أحجاره الضخمة؟",
            "ما سر معبد غوبكلي تيبي الأقدم من الزراعة؟",
            "ما لغز تماثيل جزيرة الفصح العملاقة؟",
            "لماذا ثقب القدماء جماجم بعضهم؟"],
        "ماذا يحدث لو؟ حيوانات وحشرات": [
            "ماذا يحدث لو حُبست عنكبوتة تحت كوب ونُسيت؟",
            "كيف تعيش الصراصير أياما بدون رأس؟",
            "ماذا يحدث لو اختفت كل النحل من الأرض؟"],
        "جسم الإنسان وصحته": [
            "ماذا يحدث لجسمك لو لم تنم أسبوعا؟",
            "ماذا يحدث لو لم تشرب الماء ثلاثة أيام؟",
            "لماذا نشعر بالجوع عند رؤية الطعام؟"],
        "الفضاء والكواكب": [
            "ماذا يحدث لو سقطت داخل ثقب أسود؟",
            "لماذا لا نشعر بدوران الأرض؟",
            "ماذا يحدث لو اختفى القمر فجأة؟"],
        "ظواهر الطبيعة": [
            "لماذا السماء زرقاء؟",
            "كيف يتشكل البرق؟",
            "ماذا يحدث لو ذابت كل ثلوج القطبين؟"],
        "علوم الحياة اليومية": [
            "لماذا ننسى أحلامنا بعد الاستيقاظ؟",
            "كيف يسخن الميكروويف الطعام؟",
            "لماذا تتجعد أصابعنا في الماء؟"],
        "حيوانات غريبة": [
            "لماذا يمتلك الأخطبوط ثلاثة قلوب؟",
            "كيف ينام الدلفين دون أن يغرق؟",
            "كيف تعيش السلحفاة أكثر من مئة سنة؟"],
        "قصص حقيقية غريبة": [
            "كيف باع محتال برج إيفل مرتين؟",
            "كيف أصبح دب جنديا في الجيش؟",
            "كيف خسر جيش حربا أمام الطيور؟"],
    }
    FALLBACK_TOPICS = [(c, t) for c, ts in CATEGORIES.items() for t in ts]

    # ---- الصوت ----
    VOICES = ["fr-FR-RemyMultilingualNeural", "ar-SA-HamedNeural", "ar-AE-HamdanNeural", "ar-EG-ShakirNeural"]   # ريمي أولاً
    TTS_RATE = "+6%"
    TTS_PITCH = "-2Hz"
    LEAD_SEC = 1.0        # سكوت قبل أول كلمة
    SENT_GAP = 0.22       # وقفة بين الجمل
    BEAT_GAP = 0.38       # وقفة بين المقاطع
    TAIL_SEC = 4.0        # نهاية الفيديو (موسيقى فقط)

    # ---- الفيديو ----
    FPS = 24
    WIDTH, HEIGHT = 1280, 720
    SHOW_CAPTIONS = False
    RENDER_CONCURRENCY = 2
    LOGO_WIDTH = 88        # بكسل (من 1280)
    LOGO_OPACITY = 0.7

    # ---- المخرج: مشهد متحرك لكل جملة (شخصيات عصا + مجسمات + كاميرا + انتقالات + مؤثرات صوتية) ----
    DIRECTOR_ENABLED = True
    DIRECTOR_CHUNK = 12                 # عدد الجمل في كل طلب لـ Gemini (صغير = أنجح)
    DIRECTOR_RETRIES = 3                # محاولات لكل جزء
    LLM_GAP_SEC = 3.0                   # راحة بين طلبات Gemini (يحمي الحصة المجانية)
    SFX_GAIN = 0.25                     # مستوى المؤثرات الصوتية
    SCENES = ["scene", "map", "stat", "timeline", "question", "closeup", "bars", "calendar", "compare", "gauge", "diagram"]
    ROLES = ["person", "scientist", "narrator", "king", "queen", "soldier", "worker", "trader", "scholar", "sailor", "farmer", "caveman", "child"]
    ACTOR_EXPRS = ["neutral", "happy", "surprised", "sad", "think"]
    ACTIONS = ["idle", "walk", "run", "point", "raise", "work", "fight", "carry", "think", "talk", "kneel", "celebrate", "fall",
               "wave", "scared", "dance", "jump", "cry", "sleep", "push"]
    POSITIONS = ["far_left", "left", "center", "right", "far_right"]
    PROP_SIZES = ["small", "medium", "large"]
    PROPS = ["pyramid", "temple", "ship", "castle", "tent", "fire", "tree", "mountain", "coins", "scroll", "crown", "book", "camel", "tower", "city", "swords", "sun", "moon", "chest", "pot", "wave", "whale", "fish", "shark", "octopus", "turtle", "bird", "snake", "spider", "bee", "horse", "elephant", "heart", "brain", "skull", "eye", "dna", "flask", "microscope", "lightbulb", "atom", "thermometer", "earth", "planet", "rocket", "star", "blackhole", "cloud", "rain", "lightning", "snowflake", "tornado", "volcano", "house", "car", "key", "lock", "hourglass", "clock", "flag", "shield", "bow", "cannon", "torch", "bridge", "column", "statue", "throne", "chariot", "tablet", "helmet", "spear", "anchor", "compass", "telescope", "obelisk", "ziggurat", "colosseum", "wall", "moneybag", "trophy", "ballet", "note", "question", "exclaim", "warning", "forbidden", "check", "cross", "cup", "crowd", "magnifier", "sarcophagus", "wheel", "pickaxe", "lamp", "mask", "sword"]
    CAMERAS = ["none", "zoom_in", "zoom_out", "pan_left", "pan_right", "shake"]
    TRANSITIONS = ["cut", "fade", "slide", "zoom", "wipe"]
    BGS = ["cave", "desert", "ruins", "hills", "sea", "room", "paper", "night", "sky", "living", "lab", "outdoor", "street", "cream",
           "underwater", "space", "palace", "forest", "snow", "battlefield", "volcano"]
    SFX = ["none", "whoosh", "pop", "impact", "sparkle", "tick"]

    # ---- أسلوب الدودل (فيديوهات "ماذا يحدث لو" العلمية والفضولية): أسرع وأخف وبمشاهد توضيحية ----
    DOODLE_RATE = "+16%"             # سرعة التعليق (الأسلوب التاريخي بطيء -4%)
    DOODLE_PITCH = "+0Hz"
    DOODLE_SENT_GAP = 0.10           # وقفات قصيرة مثل الفيديو المرجعي
    DOODLE_BEAT_GAP = 0.18
    DOODLE_MUSIC_GAIN = 0.10         # موسيقى شبه خفية
    CURIOSITY_SHARE = 0.6            # نسبة فيديوهات العلوم والفضول من المجموع
    CURIOSITY_CATS = ["ماذا يحدث لو؟ حيوانات وحشرات", "جسم الإنسان وصحته", "الفضاء والكواكب",
                      "ظواهر الطبيعة", "علوم الحياة اليومية", "حيوانات غريبة", "قصص حقيقية غريبة"]

    # ---- الشورتات: فيديوهات رأسية قصيرة تتبع كل فيديو طويل وتوجه المشاهد له ----
    SHORTS_ENABLED = True
    SHORTS_PER_VIDEO = 2
    SHORT_WORDS = (65, 105)         # كلمات الشورت الواحد (يطلع 35 إلى 55 ثانية تقريباً)
    SHORT_DELAY_HOURS = [3, 27]     # الأول بعد الفيديو الطويل بـ3 ساعات، والثاني بعد يوم وثلاث ساعات
    MAX_PACKAGES_PER_DAY = 1        # فيديو طويل + شورتاته باليوم (يحمي حصة يوتيوب اليومية)

    # ---- الموسيقى (هادئة جداً تحت صوت المعلق) ----
    MUSIC_GAIN = 0.20      # كل ما صغّرته صارت أخفض
    MOOD_STYLE = {          # مزاج المقطع -> نمط الموسيقى
        "calm": "deep_calm", "story": "warm_evening", "sad": "still_water",
        "wonder": "starlight", "epic": "dawn",
    }
    MIN_SEGMENT_SEC = 25
    XFADE_SEC = 5

    MOODS = ["calm", "story", "sad", "wonder", "epic"]
    GESTURES = ["none", "open", "point", "raise"]
    SETTINGS = ["cave", "desert", "ruins", "hills", "sea", "room"]
    NARRATOR_STYLES = ["tribal", "arab", "roman", "east", "neutral"]
    EXPRESSIONS = ["neutral", "happy", "surprised", "sad"]


# ============ numbers ============
_ONES = ["صفر", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة",
         "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر",
         "ثمانية عشر", "تسعة عشر"]
_TENS = {2: "عشرون", 3: "ثلاثون", 4: "أربعون", 5: "خمسون", 6: "ستون", 7: "سبعون", 8: "ثمانون", 9: "تسعون"}
_HUND = {1: "مائة", 2: "مائتان", 3: "ثلاثمائة", 4: "أربعمائة", 5: "خمسمائة", 6: "ستمائة",
         7: "سبعمائة", 8: "ثمانمائة", 9: "تسعمائة"}


def _below_1000(n):
    parts = []
    h, r = divmod(n, 100)
    if h:
        parts.append(_HUND[h])
    if r:
        if r < 20:
            parts.append(_ONES[r])
        else:
            t, u = divmod(r, 10)
            parts.append(f"{_ONES[u]} و{_TENS[t]}" if u else _TENS[t])
    return " و".join(parts)


def num_ar(n: int) -> str:
    if n == 0:
        return "صفر"
    if n >= 10 ** 12:
        return " ".join(_ONES[int(c)] for c in str(n))
    scales = [(10 ** 9, "مليار", "ملياران", "مليارات"),
              (10 ** 6, "مليون", "مليونان", "ملايين"),
              (10 ** 3, "ألف", "ألفان", "آلاف")]
    parts = []
    for val, one, two, few in scales:
        q, n = divmod(n, val)
        if not q:
            continue
        if q == 1:
            parts.append(one)
        elif q == 2:
            parts.append(two)
        elif q <= 10:
            parts.append(f"{_below_1000(q)} {few}")
        else:
            parts.append(f"{_below_1000(q)} {one}")
    if n:
        parts.append(_below_1000(n))
    return " و".join(parts)


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")


def digits_to_words(text: str) -> str:
    s = text.translate(_AR_DIGITS)
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", s)          # 1,200 -> 1200

    def conv(m):
        t = m.group(0)
        if "." in t:
            a, b = t.split(".", 1)
            return f"{num_ar(int(a))} فاصلة {' '.join(_ONES[int(c)] for c in b)}"
        return num_ar(int(t))

    s = re.sub(r"\d+(?:\.\d+)?", conv, s)
    s = s.replace("%", " بالمئة").replace("٪", " بالمئة")
    return re.sub(r"[ \t]{2,}", " ", s).strip()


# ============ gemini ============
API = "https://generativelanguage.googleapis.com/v1beta"
SKIP = ("embedding", "tts", "image", "live", "aqa", "vision", "robotics", "computer-use",
        "audio", "imagen", "veo", "learnlm", "gemma", "native")


class GeminiError(RuntimeError):
    pass


class _Retry(Exception):
    pass


class _Dead(Exception):
    pass


def get_key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not k:
        raise GeminiError("مفتاح GEMINI_API_KEY غير موجود في الأسرار")
    return k.strip()


def _rank(name):
    n = name.lower()
    tier = 0 if ("flash" in n and "lite" not in n) else 1 if "flash" in n else 2   # flash ثم lite ثم pro
    unstable = 1 if ("preview" in n or "exp" in n) else 0
    m = re.search(r"(\d+(?:\.\d+)?)", n)
    ver = float(m.group(1)) if m else 0.0
    return (tier, unstable, -ver, n)


def list_models(key=None):
    key = key or get_key()
    names, token = [], None
    for _ in range(5):
        params = {"key": key, "pageSize": 200}
        if token:
            params["pageToken"] = token
        r = requests.get(f"{API}/models", params=params, timeout=30)
        if r.status_code in (400, 401, 403):
            raise GeminiError(f"مفتاح Gemini مرفوض ({r.status_code}): {r.text[:200]}")
        r.raise_for_status()
        d = r.json()
        for m in d.get("models", []):
            name = m["name"].split("/")[-1]
            if ("generateContent" in m.get("supportedGenerationMethods", [])
                    and name.startswith("gemini") and not any(s in name for s in SKIP)):
                names.append(name)
        token = d.get("nextPageToken")
        if not token:
            break
    return sorted(set(names), key=_rank)


def _salvage(t):
    """رد مقطوع (حد الإخراج)؟ نقص من آخر عنصر مكتمل ونقفل الأقواس."""
    cuts = [i for i, ch in enumerate(t) if ch == "}"]
    for i in reversed(cuts[-80:]):
        for tail in ("]}", "}", "]"):
            try:
                return json.loads(t[: i + 1] + tail)
            except Exception:
                pass
    raise ValueError("تعذر إصلاح JSON المقطوع")


def extract_json(text):
    t = (text or "").replace("\ufeff", "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        return json.loads(t)
    except Exception:
        a = t.find("{")
        if a == -1:
            raise ValueError(f"الرد ما فيه JSON (بدايته: {t[:120]!r})")
        b = t.rfind("}")
        if b > a:
            try:
                return json.loads(t[a:b + 1])
            except Exception:
                pass
        return _salvage(t[a:])


# ---- احتياطي: OpenAI (اختياري، يشتغل فقط لو Gemini فشل وكان المفتاح موجود) ----
OPENAI_URL = "https://api.openai.com/v1"


def openai_key():
    return (os.environ.get("OPENAI_API_KEY") or "").strip()


def _openai_rank(name):
    n = name.lower()
    tier = 0 if "mini" in n else 1 if "nano" in n else 2          # الأرخص أولاً
    m = re.search(r"gpt-(\d+(?:\.\d+)?)", n)
    return (tier, -(float(m.group(1)) if m else 0.0), n)


def openai_models(key):
    r = requests.get(f"{OPENAI_URL}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if r.status_code in (401, 403):
        raise GeminiError(f"مفتاح OpenAI مرفوض ({r.status_code}): {r.text[:160]}")
    r.raise_for_status()
    ids = [x["id"] for x in r.json().get("data", [])]
    ok = [i for i in ids if re.fullmatch(r"gpt-\d+(\.\d+)?(-mini|-nano)?|gpt-4o(-mini)?", i)]
    return sorted(set(ok), key=_openai_rank)


def openai_complete(key, prompt, system, json_mode, temperature, max_tokens):
    """يرجع (النص, الموديل, سبب الإنهاء). يتكيف مع أخطاء 400 (حد التوكنات، درجة الحرارة، وضع JSON)."""
    models = openai_models(key)
    if not models:
        raise GeminiError("OpenAI: ما فيه موديلات متاحة لمفتاحك")
    last = None
    for model in models[:4]:
        body = {"model": model,
                "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}],
                "max_completion_tokens": min(max_tokens, 16384), "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        for attempt in range(6):
            try:
                r = requests.post(f"{OPENAI_URL}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=300)
            except requests.RequestException as e:
                last = f"{model}: شبكة {e}"
                time.sleep(5 * (attempt + 1))
                continue
            s = r.status_code
            if s == 200:
                ch = r.json()["choices"][0]
                text = (ch["message"].get("content") or "").strip()
                if text:
                    return text, model, ch.get("finish_reason")
                last = f"{model}: رد فاضي"
                break
            if s in (401, 403):
                raise GeminiError(f"مفتاح OpenAI مرفوض ({s}): {r.text[:160]}")
            if s == 404:
                last = f"{model}: 404"
                break
            if s in (429, 500, 502, 503, 504):
                last = f"{model}: {s}"
                time.sleep(6 * (attempt + 1))
                continue
            msg = r.text
            if s == 400:                                                        # نعدّل الطلب ونعيد
                mt = re.search(r"at most (\d+)", msg)
                if mt and "max" in msg:
                    body["max_completion_tokens"] = int(mt.group(1))
                elif "max_completion_tokens" in msg and "max_completion_tokens" in body:
                    body["max_tokens"] = body.pop("max_completion_tokens")
                elif "max_tokens" in msg and "max_tokens" in body:
                    body["max_completion_tokens"] = body.pop("max_tokens")
                elif "temperature" in msg and "temperature" in body:
                    body.pop("temperature")
                elif "response_format" in msg and "response_format" in body:
                    body.pop("response_format")
                else:
                    last = f"{model}: 400 {msg[:140]}"
                    break
                continue
            last = f"{model}: {s} {msg[:140]}"
            break
    raise GeminiError(f"فشل OpenAI: {last}")


class Gemini:
    def __init__(self, key=None):
        self.key = (key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not self.key and not openai_key():
            raise GeminiError("مفتاح GEMINI_API_KEY غير موجود في الأسرار")
        self.use_fallback = False
        self.models = None
        self.dead = set()
        self.last_model = None

    def _candidates(self):
        if self.models is None:
            try:
                self.models = list_models(self.key)
            except GeminiError:
                raise
            except Exception:
                self.models = []
            if not self.models:
                self.models = ["gemini-flash-latest", "gemini-flash-lite-latest"]
        return [m for m in self.models if m not in self.dead]

    def fallback_ok(self):
        return bool(openai_key())

    def _openai(self, prompt, system, json_mode, temperature, max_tokens):
        text, model, finish = openai_complete(openai_key(), prompt, system, json_mode, temperature, max_tokens)
        self.last_model, self.last_finish = f"openai:{model}", finish
        print(f"[llm] OpenAI {model} finish={finish} طول الرد={len(text)}")
        return text

    def generate(self, prompt, system=None, json_mode=False, temperature=0.8, max_tokens=24576):
        """Gemini أولاً؛ لو فشل (أو طلبنا التبديل) نستخدم OpenAI إذا مفتاحه موجود."""
        if self.use_fallback and self.fallback_ok():
            try:
                return self._openai(prompt, system, json_mode, temperature, max_tokens)
            except GeminiError as e:
                print(f"[llm] OpenAI فشل، نرجع لـ Gemini: {e}")
        try:
            return self._gemini_generate(prompt, system, json_mode, temperature, max_tokens)
        except GeminiError as e:
            if not self.fallback_ok():
                raise
            print(f"[llm] Gemini فشل ({e}); نستخدم OpenAI احتياطاً")
            return self._openai(prompt, system, json_mode, temperature, max_tokens)

    def _gemini_generate(self, prompt, system=None, json_mode=False, temperature=0.8, max_tokens=24576):
        if not self.key:
            raise GeminiError("ما فيه مفتاح Gemini")
        delays = [0, 8, 25, 60]
        last = None
        for rnd, d in enumerate(delays):
            if d:
                time.sleep(d + random.random() * 2)
            models = self._candidates()
            if not models:                       # كلهم ماتوا: نعيد الجلب من جديد
                self.dead.clear()
                self.models = None
                models = self._candidates()
            for m in models[:6]:
                try:
                    out = self._call(m, prompt, system, json_mode, temperature, max_tokens)
                    self.last_model = m
                    print(f"[gemini] {m} finish={getattr(self, 'last_finish', None)} طول الرد={len(out)}")
                    return out
                except _Dead as e:
                    self.dead.add(m)
                    last = e
                except _Retry as e:
                    last = e
        raise GeminiError(f"فشل Gemini بعد كل المحاولات: {last}")

    def _call(self, model, prompt, system, json_mode, temperature, max_tokens=24576, _mime=True):
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode and _mime:
            body["generationConfig"]["responseMimeType"] = "application/json"
        try:
            r = requests.post(f"{API}/models/{model}:generateContent", params={"key": self.key},
                              json=body, timeout=180)
        except requests.RequestException as e:
            raise _Retry(f"{model}: شبكة {e}")
        s = r.status_code
        if s == 200:
            try:
                cand = r.json()["candidates"][0]
                self.last_finish = cand.get("finishReason")
                text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought")).strip()
            except Exception:
                raise _Retry(f"{model}: رد فاضي أو محجوب")
            if not text:
                raise _Retry(f"{model}: نص فاضي")
            return text
        if s == 404:
            raise _Dead(f"{model}: 404 (الموديل ما عاد موجود)")
        if s == 400 and json_mode and _mime:
            return self._call(model, prompt, system, json_mode, temperature, max_tokens, _mime=False)
        if s in (401, 403):
            raise GeminiError(f"مفتاح Gemini مرفوض ({s}): {r.text[:200]}")
        if s == 429 and '"limit": 0' in r.text.replace('":0', '": 0'):
            raise _Dead(f"{model}: ما له حصة مجانية")
        if s in (429, 500, 502, 503, 504):
            raise _Retry(f"{model}: {s}")
        raise _Retry(f"{model}: {s} {r.text[:150]}")


# ============ content ============
_TASHKEEL = re.compile(r"[\u064B-\u0652\u0670\u0640]")

SYSTEM = ("You are a senior Arabic documentary scriptwriter for a curious, calm YouTube channel about the history of "
          "ALL civilizations and ancient humans (Mesopotamia, Syria and the Levant, Egypt, Persia, Rome, Greece, "
          "Arabia, China, Japan, India, the Americas, Africa, medieval Europe, kings and queens, archaeological "
          "mysteries). You write in clear Modern Standard Arabic and you are a master of curiosity: every video "
          "opens with a mystery or a 'why/how' question and keeps a thread of suspense. You never use the straight double-quote character inside text values. "
          "You rely on mainstream "
          "historical and archaeological consensus and never invent facts: when something is uncertain or debated "
          "you say so plainly (e.g. 'يرجح المؤرخون' or 'لا أحد يعرف بالتأكيد'). You treat every people and religion "
          "with respect and never discuss modern politics.")


def strip_tashkeel(t):
    return _TASHKEEL.sub("", t or "")


def clean_tts(t):
    """نص للتعليق الصوتي: يبقي التشكيل (فتحة وضمة وكسرة وشدة...) ويحول الأرقام لحروف."""
    t = re.sub(r"[*#_`>\[\]{}|~^]", "", t or "")
    t = digits_to_words(t)
    return re.sub(r"\s+", " ", t).strip()


def diacritic_ratio(t):
    letters = len(re.findall(r"[\u0621-\u064A]", t or ""))
    marks = len(re.findall(r"[\u064B-\u0652]", t or ""))
    return marks / max(1, letters)


def clean_text(t):
    t = _TASHKEEL.sub("", t or "")
    t = re.sub(r"[*#_`>\[\]{}|~^]", "", t)
    t = digits_to_words(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def style_of(cat):
    return "doodle" if cat in C.CURIOSITY_CATS else "history"


def pick_category(state):
    """نوازن بين مجموعتين: الفضول والعلوم (أسلوب الدودل) والتاريخ، ثم الأقل استخداماً داخل المجموعة."""
    hist = state.get("history", [])[-40:]
    recent = Counter(h.get("category") for h in hist)
    cur = [c for c in C.CATEGORIES if c in C.CURIOSITY_CATS]
    his = [c for c in C.CATEGORIES if c not in C.CURIOSITY_CATS]
    n_cur = sum(1 for h in hist if h.get("category") in C.CURIOSITY_CATS)
    pool = cur if (not hist or n_cur / len(hist) < C.CURIOSITY_SHARE) else his
    low = min(recent.get(c, 0) for c in pool)
    return random.choice([c for c in pool if recent.get(c, 0) == low])


def pick_topic(state, gem=None):
    """يرجع (التصنيف, الموضوع)."""
    cat = pick_category(state)
    used = [h.get("topic", "") for h in state.get("history", [])][-120:]
    if gem is not None:
        try:
            out = gem.generate(
                f"Suggest ONE fresh video topic for a 7-minute Arabic documentary in this category: «{cat}». "
                "Phrase it as a curious Arabic question that creates mystery, starting with one of: لماذا، كيف، "
                "من، ما سر، ماذا حدث، ماذا يحدث لو. It must be a real, well-documented subject (history, archaeology, "
                "science, nature, animals, the human body or space; no modern politics). For science, animal and body "
                "categories prefer a vivid 'ماذا يحدث لو ...؟' scenario. "
                f" Do NOT repeat or closely resemble any of these used topics: {used}. "
                'Return JSON only: {"topic": "<Arabic question, max 90 chars>"}',
                system=SYSTEM, json_mode=True, temperature=1.0)
            topic = clean_text(extract_json(out)["topic"])
            if 8 <= len(topic) <= 120 and topic not in used:
                return cat, topic
        except Exception as e:
            print(f"[topic] Gemini فشل، نستخدم القائمة الاحتياطية: {e}")
    pool = [(c, t) for c, t in C.FALLBACK_TOPICS if c == cat and t not in used] \
        or [(c, t) for c, t in C.FALLBACK_TOPICS if t not in used] or C.FALLBACK_TOPICS
    return random.choice(pool)


def _prompt_history(cat, topic):
    lo, hi = C.TARGET_WORDS
    return f"""Write the full narration script for a YouTube documentary video in Arabic.
Category: {cat}
Topic: "{topic}"

Script rules:
- Modern Standard Arabic written WITHOUT diacritics in every field (a separate step adds tashkeel to the narration later). Never use the straight double-quote character inside any text value; use « » instead.
- Total {lo}-{hi} words in 18-26 beats; each beat 30-65 words.
- Short sentences ending with a period or comma so the voice pauses naturally. Write ALL numbers as Arabic words.
- Beat 1 = a gripping hook that states the puzzle as a question (no greeting, no "welcome").
- Structure: the mystery, what historians/archaeologists actually found, the main explanations (say which are debated),
  a surprising detail every ~90 seconds to keep curiosity, then a clear closing answer. Last beat: one short line asking to subscribe.
- Factual, respectful, no politics, flag uncertain facts.
- Per beat choose: mood in {C.MOODS}; gesture in {C.GESTURES}; setting in {C.SETTINGS}; expression in {C.EXPRESSIONS}.
  setting guide: cave=prehistoric humans, desert=Arabia/Egypt/Mesopotamia, ruins=temples and ancient cities (Rome, Greece, Persia, Maya),
  hills=China/Japan/India/Europe landscapes, sea=sailors/ports/naval history, room=indoor scholars and courts.
  mood drives background music: calm=lots of talking, story=narrative, sad=loss/fall, wonder=discovery, epic=grand moments.
- Add "chapter" (2-5 Arabic words) on 6-9 beats only (beat 1 included), empty string on the others.
- narrator_style in {C.NARRATOR_STYLES} (tribal=prehistory, arab=Arabia/Islamic world/Levant/Mesopotamia/Egypt, roman=Rome/Greece/medieval Europe, east=China/Japan/India/Persia, neutral=other).

SEO rules (important):
- title: max 60 chars, the main searchable keyword FIRST, then a curiosity/mystery hook; honest, not clickbait lies, no ALL CAPS.
- description: first 2 lines (max 150 chars total) = hook + main keywords; then 2 short paragraphs using related keywords naturally (no stuffing).
- thumb_text: 2-4 powerful Arabic words that create curiosity (e.g. «من بنى الأهرامات؟»), NOT the full title.
- thumb_setting: the single most striking setting from {C.SETTINGS}.
- tags: 12-15 mixed Arabic and English search tags. hashtags: exactly 3.

Return JSON only, exactly this shape:
{{"title": "...", "thumb_text": "...", "thumb_setting": "cave", "narrator_style": "arab",
  "description": "...", "tags": ["..."], "hashtags": ["#...", "#...", "#..."],
  "beats": [{{"text": "...", "mood": "story", "gesture": "open", "setting": "desert", "expression": "neutral", "chapter": "المقدمة"}}]}}"""


def _prompt_doodle(cat, topic):
    lo, hi = C.TARGET_WORDS
    return f"""Write the full narration script for a YouTube "curiosity explainer" video in Arabic, in the style of popular "what happens if..." science and animal explainers.
Category: {cat}
Topic: "{topic}"

Voice and tone: an energetic, curious, friendly storyteller. Conversational Modern Standard Arabic with simple everyday words. FAST pacing and short punchy sentences (max 14 words each). Talk to the viewer ("تخيّل...", "هل تعلم...؟"). Use rhetorical questions, small twists ("لكن المفاجأة..."), light humor, concrete numbers and real study results (say "وجدت تجربة..." only when you are sure, otherwise "يرجّح العلماء").
Structure: (1) a hook in beat 1: a surprising scenario or question; (2) a relatable setup scene; (3) the reveal step by step as stages or a timeline (day one, a week, a month...); (4) the science explained with one simple analogy (for example a car fuel gauge); (5) a comparison with another case or animal using numbers; (6) a surprising twist; (7) a clear takeaway and one short subscribe line in the last beat.

Rules:
- Write ALL fields in Arabic WITHOUT diacritics (a separate step adds tashkeel to the narration later). Never use the straight double-quote character inside any text value; use « » instead.
- Total {lo}-{hi} words in 18-26 beats; each beat 30-65 words. Write ALL numbers as Arabic words.
- Factual and careful: flag uncertain facts, never invent studies or numbers.
- Per beat choose: mood in {C.MOODS}; gesture in {C.GESTURES}; setting in {C.SETTINGS}; expression in {C.EXPRESSIONS}.
- Add "chapter" (2-5 Arabic words) on 6-9 beats only (beat 1 included), empty string on the others.
- narrator_style: "neutral".

SEO rules: title max 60 chars, main searchable keyword first, curiosity hook, honest. description: first 2 lines (max 150 chars) = hook + keywords, then 2 short paragraphs. thumb_text: 2-4 powerful Arabic words. thumb_emoji: ONE emoji that shows the main subject (for example 🕷️). tags: 12-15 mixed Arabic and English. hashtags: exactly 3.

Return JSON only, exactly this shape:
{{"title": "...", "thumb_text": "...", "thumb_emoji": "spider (an icon name from the props list)", "thumb_setting": "ruins", "narrator_style": "neutral",
  "description": "...", "tags": ["..."], "hashtags": ["#...", "#...", "#..."],
  "beats": [{{"text": "...", "mood": "story", "gesture": "open", "setting": "desert", "expression": "neutral", "chapter": "المقدمة"}}]}}"""


def _prompt(cat, topic, style="history"):
    return _prompt_doodle(cat, topic) if style == "doodle" else _prompt_history(cat, topic)


def infer_mood(text):
    if re.search(r"سقط|دمار|حرب|هلك|اختف|نهاية|انهار|مات", text):
        return "sad"
    if re.search(r"اكتشف|عجيب|لغز|سر|مذهل|غامض", text):
        return "wonder"
    if re.search(r"عظيم|امبراطور|إمبراطور|ملك|مجد|انتصر", text):
        return "epic"
    return "story"


def normalize(sc):
    sc = dict(sc)
    sc["title"] = clean_text(sc.get("title", ""))[:95]
    sc["thumb_text"] = clean_text(sc.get("thumb_text", "")) or sc["title"][:28]
    sc["thumb_setting"] = sc.get("thumb_setting") if sc.get("thumb_setting") in C.SETTINGS else "ruins"
    sc["thumb_emoji"] = _emoji(sc.get("thumb_emoji")) or "question"
    sc["narrator_style"] = sc.get("narrator_style") if sc.get("narrator_style") in C.NARRATOR_STYLES else "arab"
    sc["description"] = (sc.get("description") or "").strip()
    sc["tags"] = [str(t).strip() for t in sc.get("tags", []) if str(t).strip()][:15]
    tags = [str(h).strip() for h in sc.get("hashtags", []) if str(h).strip()]
    sc["hashtags"] = [("#" + h.lstrip("#").replace(" ", "_")) for h in tags][:3] or ["#أوابد", "#تاريخ", "#وثائقي"]
    beats = []
    for b in sc.get("beats", []):
        text = clean_tts(b.get("text", ""))
        plain = strip_tashkeel(text)
        if not plain:
            continue
        beats.append({
            "text": text, "plain": plain,
            "mood": b.get("mood") if b.get("mood") in C.MOODS else infer_mood(plain),
            "gesture": b.get("gesture") if b.get("gesture") in C.GESTURES else "none",
            "setting": b.get("setting") if b.get("setting") in C.SETTINGS else "ruins",
            "expression": b.get("expression") if b.get("expression") in C.EXPRESSIONS else "neutral",
            "chapter": clean_text(b.get("chapter", ""))[:40],
        })
    sc["beats"] = beats
    return sc


def word_count(sc):
    return sum(len(b.get("plain", b["text"]).split()) for b in sc["beats"])


def validate(sc):
    """يرجع قائمة مشاكل. فاضية = السكربت سليم."""
    p = []
    lo, hi = C.TARGET_WORDS
    n = word_count(sc)
    if len(sc["beats"]) < 12:
        p.append(f"عدد المقاطع {len(sc['beats'])} قليل، المطلوب 18 إلى 26")
    if n < lo * 0.85:
        p.append(f"عدد الكلمات {n} أقل من المطلوب ({lo}-{hi})، زد التفاصيل")
    if n > hi * 1.15:
        p.append(f"عدد الكلمات {n} أكثر من المطلوب ({lo}-{hi})، اختصر")
    for i, b in enumerate(sc["beats"]):
        if len(b.get("plain", b["text"]).split()) > C.BEAT_WORDS_MAX:
            p.append(f"المقطع {i + 1} طويل ({len(b.get('plain', b['text']).split())} كلمة)")
    blob = " ".join([sc["title"], sc["description"]] + [b.get("plain", b["text"]) for b in sc["beats"]])
    for w in C.BANNED_WORDS:
        if w in blob:
            p.append(f"فيه كلمة ممنوعة: {w}")
    if re.search(r"\d", " ".join(b.get("plain", b["text"]) for b in sc["beats"])):
        p.append("فيه أرقام بالأرقام، اكتبها بالحروف")
    if not sc["title"]:
        p.append("العنوان فاضي")
    if len(sc["title"]) > 70:
        p.append("العنوان أطول من 60 حرف، اختصره وخل الكلمة المفتاحية أول شي")
    return p


def _build_script(cat, topic, gem, max_rounds=3, style="history"):
    sc, problems = None, []
    jm = True
    for rnd in range(max_rounds):
        if rnd == 0 or sc is None:
            raw = gem.generate(_prompt(cat, topic, style), system=SYSTEM, json_mode=jm)
        else:
            raw = gem.generate(
                "Fix this Arabic documentary script JSON. Problems found:\n- " + "\n- ".join(problems) +
                "\nKeep the same JSON shape and the same rules. Return the full corrected JSON only.\n\n"
                + str(sc), system=SYSTEM, json_mode=True, temperature=0.5)
        try:
            sc = normalize(extract_json(raw))
        except Exception as e:
            problems = [f"JSON غير صالح: {e}"]
            sc = None
            jm = not jm                                   # جرّب الوضع الثاني في الجولة الجاية
            if getattr(gem, "fallback_ok", lambda: False)():
                gem.use_fallback = True                   # وجرّب OpenAI لو مفتاحه موجود
            print(f"[script] رد Gemini غير صالح (finish={getattr(gem, 'last_finish', None)}, طوله {len(raw)}): {raw[:200]!r}")
            continue
        problems = validate(sc)
        print(f"[script] جولة {rnd + 1}: {word_count(sc)} كلمة، {len(sc['beats'])} مقطع، مشاكل: {problems or 'لا شيء'}")
        if not problems:
            return sc
    hard = [x for x in problems if "ممنوعة" in x or "JSON" in x or "فاضي" in x]
    if sc is not None and not hard:
        print("[script] نقبله مع ملاحظات بسيطة:", problems)
        return sc
    raise RuntimeError(f"السكربت ما اجتاز التحقق: {problems}")


def _letters(t):
    return re.sub(r"[^\u0621-\u064A0-9a-zA-Z]", "", strip_tashkeel(t))


def diacritize_beats(beats, gem, chunk=5):
    """خطوة منفصلة وخفيفة تضيف التشكيل لكل مقطع. أي فشل: نبقي النص بدون تشكيل ولا نوقف الفيديو."""
    done = 0
    for k in range(0, len(beats), chunk):
        part = beats[k:k + chunk]
        lines = "\n".join(f"T{i}: {b.get('plain', b['text'])}" for i, b in enumerate(part))
        prompt = ("Add FULL Arabic diacritics (tashkeel: fatha, damma, kasra, sukun, shadda, tanween) to each text below so a "
                  "text-to-speech voice reads every word correctly, especially names and places. Do NOT change, add or remove "
                  "any word or punctuation mark; only add diacritics. Never use the straight double-quote character inside values.\n\n"
                  f"{lines}\n\nReturn JSON only: {{\"texts\": [\"...\", \"...\"]}} with exactly {len(part)} items in the same order.")
        try:
            data = extract_json(gem.generate(prompt, system=SYSTEM, json_mode=True, temperature=0.2, max_tokens=16384))
            texts = data.get("texts") if isinstance(data, dict) else data
            if not isinstance(texts, list) or len(texts) != len(part):
                raise ValueError("عدد النصوص غير مطابق")
            for b, t in zip(part, texts):
                t = clean_tts(str(t))
                if _letters(t) == _letters(b.get("plain", b["text"])) and diacritic_ratio(t) > 0.15:
                    b["text"] = t
                    done += 1
        except Exception as e:
            print(f"[tashkeel] جزء فشل (نبقيه بدون تشكيل): {e}")
        if not getattr(gem, "fast", False):
            time.sleep(C.LLM_GAP_SEC)
    print(f"[tashkeel] شُكّل {done} من {len(beats)} مقطع")
    return done


def build_script(cat, topic, gem, max_rounds=3, style="history"):
    sc = _build_script(cat, topic, gem, max_rounds, style)
    sc["style"] = style
    diacritize_beats(sc["beats"], gem)
    return sc


def _ts(sec):
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def build_description(sc, manifest):
    """وصف سيو: خطاف + فقرات + فصول بالوقت الفعلي + دعوة + هاشتاقات (أول 3 تظهر فوق العنوان)."""
    chapters, last = [], -999
    for b in manifest["beats"]:
        if b.get("chapter") and b["start_sec"] - last >= 12:
            chapters.append((0 if not chapters else b["start_sec"], b["chapter"]))
            last = b["start_sec"]
    parts = [sc["description"].strip()]
    if len(chapters) >= 3:
        parts.append("فصول الفيديو:\n" + "\n".join(f"{_ts(t)} {name}" for t, name in chapters))
    parts.append("اشترك في قناة أوابد وفعل الجرس لتصلك رحلات جديدة في التاريخ والحضارات والألغاز كل أسبوع.")
    parts.append(" ".join(sc["hashtags"]))
    return "\n\n".join(parts)[:4900]


# ============ tts ============
SR = 44100


def split_sentences(text):
    import re
    parts = [p.strip() for p in re.split(r"(?<=[.!؟?…])\s+", text) if p.strip()]
    out = []
    for p in parts:                       # الجملة القصيرة جداً تنضم لقبلها
        if out and len(p.split()) < 3:
            out[-1] += " " + p
        else:
            out.append(p)
    return out or [text]


async def _edge(text, voice, rate=None, pitch=None):
    import edge_tts
    buf = bytearray()
    async for ch in edge_tts.Communicate(text, voice, rate=rate or C.TTS_RATE, pitch=pitch or C.TTS_PITCH).stream():
        if ch["type"] == "audio":
            buf += ch["data"]
    if not buf:
        raise RuntimeError("edge-tts رجع صوت فاضي")
    return bytes(buf)


def make_edge_synth(rate=None, pitch=None):
    """يختار أول صوت شغال مرة وحدة (عشان صوت الفيديو يبقى موحد)، ثم يعيد المحاولة على نفس الصوت."""
    voice = None
    errs = []
    for v in C.VOICES:
        try:
            asyncio.run(_edge("مرحبا", v))
            voice = v
            break
        except Exception as e:
            errs.append(f"{v}: {e}")
    if voice is None:
        raise RuntimeError("كل أصوات edge-tts فشلت: " + " | ".join(errs))
    print(f"[tts] الصوت المستخدم: {voice}")

    def synth(text):
        last = None
        for attempt in range(5):
            try:
                return asyncio.run(_edge(text, voice, rate, pitch))
            except Exception as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"فشل توليد جملة بعد 5 محاولات: {last}")

    return synth


def decode(data: bytes) -> np.ndarray:
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                       input=data, capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def _trim(a, keep=0.04):
    idx = np.where(np.abs(a) > 0.004)[0]
    if len(idx) == 0:
        return a
    k = int(keep * SR)
    return a[max(0, idx[0] - k): idx[-1] + k]


def _sil(sec):
    return np.zeros(int(sec * SR), np.float32)


def tts_build(beats, outdir, synth, fps=None, sent_gap=None, beat_gap=None):
    fps = fps or C.FPS
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    chunks, pos, starts = [_sil(C.LEAD_SEC)], int(C.LEAD_SEC * SR), []
    sentences = []
    for bi, b in enumerate(beats):
        starts.append(pos)
        sents = split_sentences(clean_tts(b["text"]))
        for i, s in enumerate(sents):
            a = _trim(decode(synth(s)))
            s0 = pos
            chunks.append(a)
            pos += len(a)
            sentences.append({"beat": bi, "text": s, "plain": strip_tashkeel(s),
                              "start_sec": s0 / SR, "end_sec": pos / SR})
            if i < len(sents) - 1:
                g = _sil(C.SENT_GAP if sent_gap is None else sent_gap)
                chunks.append(g)
                pos += len(g)
        g = _sil(C.BEAT_GAP if beat_gap is None else beat_gap)
        chunks.append(g)
        pos += len(g)
    chunks.append(_sil(C.TAIL_SEC))
    audio = np.concatenate(chunks)

    # مستوى الصوت: RMS للأجزاء الناطقة حول -20dB وحد أعلى للقمة
    voiced = audio[np.abs(audio) > 0.01]
    rms = float(np.sqrt(np.mean(voiced ** 2))) if len(voiced) else 0.1
    audio = audio * (0.10 / max(rms, 1e-6))
    peak = float(np.max(np.abs(audio))) or 1.0
    if peak > 0.95:
        audio *= 0.95 / peak
    wavfile.write(str(outdir / "narration.wav"), SR, (audio * 32767).astype(np.int16))

    total_sec = len(audio) / SR
    total_frames = math.ceil(total_sec * fps)
    win = int(SR / fps)
    n = total_frames
    pad = np.zeros(n * win - len(audio) if n * win > len(audio) else 0, np.float32)
    frames = np.concatenate([audio, pad])[: n * win].reshape(n, win)
    env = np.sqrt((frames ** 2).mean(axis=1))
    ref = np.percentile(env[env > 0.01], 95) if np.any(env > 0.01) else 1.0
    env = np.clip(env / max(ref, 1e-6), 0, 1)
    env = np.where(env < 0.08, 0, env)
    k = np.array([0.25, 0.5, 0.25])
    env = np.convolve(env, k, mode="same")
    envelope = [round(float(x), 3) for x in env]

    out_beats = []
    for i, b in enumerate(beats):
        f0 = int(starts[i] / SR * fps)
        f1 = int(starts[i + 1] / SR * fps) if i + 1 < len(beats) else total_frames
        out_beats.append({**b, "from": f0, "to": f1,
                          "start_sec": starts[i] / SR,
                          "end_sec": (starts[i + 1] / SR) if i + 1 < len(beats) else total_sec})
    manifest = {"fps": fps, "totalFrames": total_frames, "totalSec": total_sec, "beats": out_beats, "sentences": sentences}
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return manifest, envelope, outdir / "narration.wav"


# ============ music ============
#!/usr/bin/env python3
"""
Generative calm background music, 100% code, no downloads, no copyright.
Needs: pip install numpy scipy   and   ffmpeg on PATH

  python music.py --style dawn --seconds 420 --out public/music.mp3
  python music.py --style random --seconds 600 --out public/music.mp3
  python music.py --samples samples/        # 60s preview of every style

Styles: dawn | still_water | warm_evening | starlight | deep_calm
"""


# chords are MIDI note lists (soft, low-mid voicings). chord_len in seconds.
STYLES = {
    "dawn":         dict(chords=[[48,55,59,62,64],[45,52,55,60,64],[41,48,52,57,60],[43,50,55,59,64]],
                         chord_len=12, pluck=0.35, pad=1.0,  bright=2200, seed=11),
    "still_water":  dict(chords=[[38,45,53,57,64],[46,53,57,62,65],[43,50,53,58,62],[45,52,57,62,64]],
                         chord_len=14, pluck=0.22, pad=1.0,  bright=1500, seed=23),
    "warm_evening": dict(chords=[[41,48,52,57,64],[38,45,53,57,60],[46,53,57,62,64],[48,55,57,60,64]],
                         chord_len=12, pluck=0.50, pad=0.9,  bright=2000, seed=37),
    "starlight":    dict(chords=[[45,52,55,59,64],[41,48,52,57,64],[48,55,59,64,67],[40,47,52,55,62]],
                         chord_len=13, pluck=0.60, pad=0.85, bright=2800, seed=51),
    "deep_calm":    dict(chords=[[38,45,52,57,64],[38,45,50,57,62]],
                         chord_len=18, pluck=0.0,  pad=1.1,  bright=1100, seed=7),
}

def mtof(m):
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)

def pad_chord(notes, length, att, rng):
    """Soft evolving pad: detuned sine stacks, stereo-widened, slow tremolo."""
    n = int(length * SR)
    t = np.arange(n, dtype=np.float32) / SR
    a = min(int(att * SR), n // 2)
    env = np.ones(n, np.float32)
    ramp = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))).astype(np.float32)
    env[:a] = ramp
    env[-a:] = ramp[::-1]
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    for m in notes:
        f = mtof(m)
        ph = rng.uniform(0, 2 * np.pi, 3)
        for ch, det in ((L, 1.0012), (R, 0.9988)):
            ch += 0.50 * np.sin(2 * np.pi * f * det * t + ph[0])
            ch += 0.18 * np.sin(2 * np.pi * f * 2 * det * t + ph[1])
            ch += 0.07 * np.sin(2 * np.pi * f * 3 * det * t + ph[2])
    trem = 1 + 0.12 * np.sin(2 * np.pi * rng.uniform(0.06, 0.12) * t + rng.uniform(0, 6.28))
    g = env * trem / len(notes)
    return L * g, R * g

def bell(f, dur=5.0):
    """Soft bell/piano-ish pluck."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 1.6)
    s += 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.9)
    s += 0.12 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.45)
    s += 0.05 * np.sin(2 * np.pi * f * 4.2 * t) * np.exp(-t / 0.2)
    return (s * (1 - np.exp(-t / 0.006))).astype(np.float32)

def reverb(stereo, rng, seconds=3.2):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = []
    sos = butter(2, 3500, btype="low", fs=SR, output="sos")
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / 0.9)
        ir = sosfilt(sos, ir)
        ir[: int(0.02 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out.append(fftconvolve(stereo[c], ir)[: stereo.shape[1]])
    return np.stack(out).astype(np.float32)

def render(style, seconds, seed=None, fade_in=4.0, fade_out=None):
    p = STYLES[style]
    rng = np.random.default_rng(p["seed"] if seed is None else seed)
    tail = 6.0
    total = seconds + tail
    N = int(total * SR)
    cl, att = p["chord_len"], 3.5
    buf = np.zeros((2, N), np.float32)

    # pads: chords cycle, each crossfades into the next
    i, t0 = 0, 0.0
    while t0 < total:
        notes = p["chords"][i % len(p["chords"])]
        seg = cl + att
        L, R = pad_chord(notes, seg, att, rng)
        s = int(t0 * SR)
        e = min(N, s + len(L))
        buf[0, s:e] += L[: e - s] * p["pad"]
        buf[1, s:e] += R[: e - s] * p["pad"]
        # plucks for this chord: sparse, from chord tones one/two octaves up
        if p["pluck"] > 0:
            k = rng.poisson(p["pluck"] * cl)
            for _ in range(k):
                when = t0 + att * 0.8 + round(rng.uniform(0, cl - 1) / 0.75) * 0.75
                note = int(rng.choice(notes)) + int(rng.choice([12, 12, 24]))
                b = bell(mtof(note)) * rng.uniform(0.10, 0.20)
                pan = rng.uniform(0.25, 0.75)
                ps = int(when * SR)
                pe = min(N, ps + len(b))
                if pe > ps:
                    buf[0, ps:pe] += b[: pe - ps] * (1 - pan)
                    buf[1, ps:pe] += b[: pe - ps] * pan
        t0 += cl
        i += 1

    wet = reverb(buf, rng)
    out = buf * 0.6 + wet * 0.7
    out = sosfilt(butter(2, p["bright"], btype="low", fs=SR, output="sos"), out, axis=1)
    out = sosfilt(butter(2, 35, btype="high", fs=SR, output="sos"), out, axis=1)
    out = out[:, : int(seconds * SR)]

    # level: quiet bed (about -22 dBFS RMS) BEFORE fades so every style has the same loudness
    rms = np.sqrt(np.mean(out ** 2)) + 1e-9
    out *= 0.08 / rms
    peak = np.max(np.abs(out))
    if peak > 0.89:
        out *= 0.89 / peak

    # fades
    fo_s = min(8.0, seconds * 0.15) if fade_out is None else fade_out
    fi, fo = int(fade_in * SR), int(fo_s * SR)
    if fi > 0:
        out[:, :fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    if fo > 0:
        out[:, -fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    return out


def save(out, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (out.T * 32767).astype(np.int16)
    if path.suffix == ".wav":
        wavfile.write(str(path), SR, pcm)
        return
    with tempfile.TemporaryDirectory() as d:
        w = Path(d) / "t.wav"
        wavfile.write(str(w), SR, pcm)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(w),
                        "-b:a", "160k", str(path)], check=True)


# ===================== موسيقى تتفاعل مع نص الفيديو =====================
def plan_segments(beats, total_sec, mood_style, min_seg=25.0):
    """كل مقطع له مزاج -> نمط موسيقى. الأجزاء القصيرة تنضم لأطول جار لها عشان يبقى التنويع."""
    segs = []
    for i, b in enumerate(beats):
        style = "dawn" if i == 0 else mood_style.get(b.get("mood", "story"), "warm_evening")
        s, e = float(b["start_sec"]), float(b["end_sec"])
        if i == 0:
            s = 0.0
        if i == len(beats) - 1:
            e = total_sec
        if segs and segs[-1][0] == style:
            segs[-1][2] = e
        else:
            segs.append([style, s, e])
    while len(segs) > 1:
        short = [i for i, x in enumerate(segs) if x[2] - x[1] < min_seg]
        if not short:
            break
        i = min(short, key=lambda k: segs[k][2] - segs[k][1])
        left = segs[i - 1] if i > 0 else None
        right = segs[i + 1] if i < len(segs) - 1 else None
        if right is None or (left is not None and (left[2] - left[1]) >= (right[2] - right[1])):
            segs[i - 1][2] = segs[i][2]
        else:
            segs[i + 1][1] = segs[i][1]
        segs.pop(i)
        j = 1
        while j < len(segs):                       # توحيد المتجاورين بنفس النمط
            if segs[j][0] == segs[j - 1][0]:
                segs[j - 1][2] = segs[j][2]
                segs.pop(j)
            else:
                j += 1
    return [tuple(x) for x in segs]


def render_timeline(beats, total_sec, mood_style, xfade=5.0, min_seg=25.0, seed=0):
    segs = plan_segments(beats, total_sec, mood_style, min_seg)
    N = int(total_sec * SR)
    out = np.zeros((2, N), np.float32)
    for idx, (style, s, e) in enumerate(segs):
        a = max(0.0, s - xfade / 2)
        b = min(total_sec, e + xfade / 2)
        r = render(style, b - a, seed=(STYLES[style]["seed"] + seed + idx),
                   fade_in=(xfade if a > 0 else 3.0), fade_out=(xfade if b < total_sec else 8.0))
        i0 = int(a * SR)
        i1 = min(N, i0 + r.shape[1])
        out[:, i0:i1] += r[:, : i1 - i0]
    return out, segs


# ============ mix ============
def mix(narration_wav, music, out_mp3, sfx=None, gain=None):
    """music: مصفوفة (2, N). sfx: مصفوفة (2, N) اختيارية للمؤثرات (ما تنخفض مع الكلام)."""
    narration_wav, out_mp3 = Path(narration_wav), Path(out_mp3)
    music_wav = narration_wav.parent / "music.wav"
    wavfile.write(str(music_wav), SR, (np.clip(music.T, -1, 1) * 32767).astype(np.int16))
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    g = C.MUSIC_GAIN if gain is None else gain
    inputs = ["-i", str(narration_wav), "-i", str(music_wav)]
    fc = (f"[0:a]aformat=channel_layouts=stereo,asplit=2[nar][sc];"
          f"[1:a]volume={g}[m];"
          f"[m][sc]sidechaincompress=threshold=0.02:ratio=12:attack=30:release=700:makeup=1[duck];")
    if sfx is not None:
        sfx_wav = narration_wav.parent / "sfx.wav"
        wavfile.write(str(sfx_wav), SR, (np.clip(sfx.T, -1, 1) * 32767).astype(np.int16))
        inputs += ["-i", str(sfx_wav)]
        fc += (f"[2:a]volume={C.SFX_GAIN}[fx];"
               f"[nar][duck][fx]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0[mx];")
    else:
        fc += "[nar][duck]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[mx];"
    fc += "[mx]loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "[out]",
                    "-ar", "44100", "-b:a", "192k", str(out_mp3)], check=True)
    return out_mp3


# ============ schedule ============
STATE_PATH = Path("state.json")


def load_state(path=STATE_PATH):
    try:
        s = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        s = {}
    s.setdefault("history", [])
    s.setdefault("attempts", {})
    s.setdefault("done", [])
    s.setdefault("alerted", [])
    s.setdefault("last_run", None)
    s.setdefault("last_error", None)
    return s


def save_state(state, path=STATE_PATH):
    state["history"] = state["history"][-300:]
    state["done"] = state["done"][-300:]
    state["alerted"] = state["alerted"][-100:]
    Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def upcoming_slots(now_utc):
    """المواعيد القادمة (UTC) خلال الأفق، مرتبة."""
    now_local = now_utc.astimezone(C.TZ)
    earliest = now_utc + timedelta(hours=C.MIN_LEAD_HOURS)
    slots = []
    for d in range(C.HORIZON_DAYS + 1):
        day = (now_local + timedelta(days=d)).date()
        for wd, hhmm in C.SCHEDULE:
            if day.weekday() == wd:
                h, m = map(int, hhmm.split(":"))
                dt = datetime(day.year, day.month, day.day, h, m, tzinfo=C.TZ).astimezone(timezone.utc)
                if earliest <= dt <= now_utc + timedelta(days=C.HORIZON_DAYS):
                    slots.append(dt)
    return sorted(slots)


def slot_key(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _att(state, k):
    a = state["attempts"].get(k)
    if isinstance(a, int):                       # توافق مع نسخة قديمة
        return {"n": a, "t": None}
    return a or {"n": 0, "t": None}


def _resting(state, k, now_utc):
    a = _att(state, k)
    if a["n"] < C.MAX_ATTEMPTS:
        return False
    if not a["t"]:
        return True
    last = datetime.fromisoformat(a["t"])
    return now_utc - last < timedelta(hours=C.RETRY_AFTER_HOURS)


def register_attempt(state, k, now_utc):
    a = _att(state, k)
    if a["n"] >= C.MAX_ATTEMPTS and a["t"] and not _resting(state, k, now_utc):
        a = {"n": 0, "t": None}                  # خلص وقت الراحة: نبدأ العد من جديد
    a = {"n": a["n"] + 1, "t": now_utc.isoformat()}
    state["attempts"][k] = a
    return a["n"]


def pick_slot(now_utc, state, existing_utc=()):
    """أول موعد فاضي: ما انحجز، ما فيه فيديو مجدول قريب منه، وما هو في فترة راحة بعد فشل متكرر."""
    for slot in upcoming_slots(now_utc):
        k = slot_key(slot)
        if k in state["done"]:
            continue
        if any(abs((slot - e).total_seconds()) < 90 * 60 for e in existing_utc):
            continue
        if _resting(state, k, now_utc):
            continue
        return slot
    return None


def resting_slots(now_utc, state):
    return [slot_key(s) for s in upcoming_slots(now_utc)
            if slot_key(s) not in state["done"] and _resting(state, slot_key(s), now_utc)]


# ============ youtube ============
SCOPES = ["https://www.googleapis.com/auth/youtube"]


class AuthError(RuntimeError):
    pass


def _env(*names):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    return None


def credentials():
    from google.oauth2.credentials import Credentials
    cid = _env("YT_CLIENT_ID", "YOUTUBE_CLIENT_ID")
    sec = _env("YT_CLIENT_SECRET", "YOUTUBE_CLIENT_SECRET")
    rt = _env("YT_REFRESH_TOKEN", "YOUTUBE_REFRESH_TOKEN")
    if not (cid and sec and rt):
        raise AuthError("ناقص سر من: YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN")
    return Credentials(None, refresh_token=rt, token_uri="https://oauth2.googleapis.com/token",
                       client_id=cid, client_secret=sec)


def check_token():
    """يفشل بسرعة وبرسالة واضحة إذا التوكن ميت (بدل ما نصرف 30 دقيقة رندر)."""
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    creds = credentials()
    try:
        creds.refresh(Request())
    except RefreshError as e:
        raise AuthError(
            "توكن يوتيوب منتهي أو ملغي (invalid_grant). السبب الأشهر: تطبيق OAuth في وضع Testing "
            "فتنتهي التوكنات بعد 7 أيام. حوّل التطبيق إلى In production من Google Cloud ثم "
            f"أنشئ refresh token جديد بـ tools/get_refresh_token.py. التفاصيل: {e}")
    return creds


def yt_client(creds=None):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds or check_token(), cache_discovery=False)


def existing_scheduled(yt):
    """مواعيد النشر للفيديوهات المجدولة حالياً (UTC)."""
    out = []
    try:
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        ids = [i["contentDetails"]["videoId"] for i in
               yt.playlistItems().list(part="contentDetails", playlistId=pl, maxResults=50).execute().get("items", [])]
        if ids:
            for v in yt.videos().list(part="status", id=",".join(ids)).execute().get("items", []):
                pa = v.get("status", {}).get("publishAt")
                if pa:
                    dt = datetime.fromisoformat(pa.replace("Z", "+00:00"))
                    if dt > datetime.now(timezone.utc):
                        out.append(dt)
    except Exception as e:
        print(f"[youtube] تعذر قراءة المجدول (نعتمد على state.json): {e}")
    return out


def yt_upload(yt, mp4, meta, publish_at, thumb=None):
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    tags, total = [], 0
    for t in meta.get("tags", []):
        if total + len(t) + 1 > 450:
            break
        tags.append(t)
        total += len(t) + 1
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"][:4900], "tags": tags,
                    "categoryId": "27", "defaultLanguage": "ar", "defaultAudioLanguage": "ar"},
        "status": {"privacyStatus": "private", "publishAt": publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                   "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(mp4), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, fails = None, 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and fails < 8:
                fails += 1
                time.sleep(2 ** min(fails, 5))
                continue
            raise
        except (ConnectionError, TimeoutError, OSError):
            fails += 1
            if fails > 8:
                raise
            time.sleep(2 ** min(fails, 5))
    vid = resp["id"]
    locked = not resp.get("status", {}).get("publishAt")      # لو الجدولة ما انحفظت: غالباً المشروع يحتاج Audit
    if thumb:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
        except Exception as e:                       # الصورة المصغرة ما توقف النشر أبداً
            print(f"[youtube] الصورة المصغرة فشلت (الفيديو انرفع ومجدول عادي): {e}")
    return vid, locked


# ============ render ============
VIDEO_DIR = Path("video")


def write_props(manifest, envelope, script, path=None, shots=None):
    path = path or VIDEO_DIR / "public" / "props.json"
    props = {"fps": manifest["fps"], "totalFrames": manifest["totalFrames"], "beats": manifest["beats"],
             "envelope": envelope, "showCaptions": C.SHOW_CAPTIONS, "title": script["title"],
             "thumbText": script["thumb_text"], "thumbSetting": script["thumb_setting"],
             "narratorStyle": script["narrator_style"], "logoWidth": C.LOGO_WIDTH, "logoOpacity": C.LOGO_OPACITY,
             "audio": "audio/mix.mp3"}
    props["beats"] = [{**b, "text": b.get("plain", b["text"])} for b in manifest["beats"]]
    props["style"] = script.get("style", "history")
    props["thumbEmoji"] = script.get("thumb_emoji") or ""
    if shots:
        props["shots"] = shots
    setup_video()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    return path


def render_video(out_mp4):
    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npx", "remotion", "render", "src/index.tsx", "Main", str(Path(out_mp4).resolve()),
                    "--props=public/props.json", f"--concurrency={C.RENDER_CONCURRENCY}",
                    "--codec=h264", "--crf=25", "--log=warn"], cwd=VIDEO_DIR, check=True)


def render_thumb(out_jpg):
    """الصورة المصغرة اختيارية: لو فشلت نرجع None والنشر يكمل."""
    try:
        Path(out_jpg).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["npx", "remotion", "still", "src/index.tsx", "Thumb", str(Path(out_jpg).resolve()),
                        "--props=public/props.json", "--image-format=jpeg", "--jpeg-quality=92", "--log=warn"],
                       cwd=VIDEO_DIR, check=True)
        return out_jpg
    except Exception as e:
        print(f"[render] الصورة المصغرة فشلت: {e}")
        return None


def frame_thumbnail(mp4, out_jpg, sec=20):
    """خطة بديلة: لقطة من الفيديو نفسه (بدون أي اعتماد على Remotion). ما توقف النشر لو فشلت."""
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(sec), "-i", str(mp4), "-frames:v", "1",
                        "-q:v", "2", str(out_jpg)], check=True)
        return out_jpg
    except Exception as e:
        print(f"[render] لقطة الفيديو فشلت (ننشر بدون صورة مصغرة): {e}")
        return None


# ============ health ============
def run_checks():
    rows = []   # (الاسم, ok, تفصيل, حرج؟)

    def add(name, fn, critical=True):
        try:
            rows.append((name, True, str(fn() or "ok"), critical))
        except Exception as e:
            rows.append((name, False, str(e)[:400], critical))

    def tool(n):
        def f():
            if not shutil.which(n):
                raise RuntimeError(f"{n} غير مثبت")
            return subprocess.run([n, "-version"], capture_output=True, text=True).stdout.splitlines()[0][:60]
        return f

    add("نسخة الكود", lambda: VERSION)
    add("ffmpeg", tool("ffmpeg"))
    add("node", lambda: subprocess.run(["node", "-v"], capture_output=True, text=True, check=True).stdout.strip())

    def token():
        creds = check_token()
        yt = yt_client(creds)
        ch = yt.channels().list(part="snippet", mine=True).execute()
        return "القناة: " + ch["items"][0]["snippet"]["title"]
    add("توكن يوتيوب", token)

    def gem():
        m = list_models()
        if not m:
            raise RuntimeError("ما فيه موديلات متاحة")
        return f"{len(m)} موديل، الأول: {m[0]}"
    add("مفتاح Gemini", gem)

    def voice():
        import asyncio
        for v in C.VOICES:
            try:
                asyncio.run(_edge("مرحبا بكم", v))
                return f"شغال: {v}"
            except Exception:
                continue
        raise RuntimeError("كل أصوات edge-tts فشلت")
    add("edge-tts", voice, critical=False)

    def oai():
        if not openai_key():
            return "غير مضاف (اختياري)"
        ms = openai_models(openai_key())
        if not ms:
            raise RuntimeError("ما فيه موديلات متاحة")
        return f"احتياطي جاهز، الأول: {ms[0]}"
    add("OpenAI احتياطي", oai, critical=False)

    return rows


def report(rows):
    lines = ["| الفحص | النتيجة | التفصيل |", "|---|---|---|"]
    for n, ok, d, crit in rows:
        lines.append(f"| {n} | {'✅' if ok else ('❌' if crit else '⚠️')} | {d} |")
    bad = [n for n, ok, d, crit in rows if not ok and crit]
    return "\n".join(lines), bad


# ============ run ============
WORK = Path("work")


def summary(md):
    print(md)
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(md + "\n")


# ============ المخرج: يوزع مشهد متحرك لكل جملة ============
DIRECTOR_SYSTEM = "You are a precise visual director for animated educational videos. You answer with valid JSON only."


# كلمات مفتاحية -> إيموجي/مجسم، تُستخدم لو فشل المخرج في جملة (عشان الصورة تبقى مناسبة للكلام)
KEYWORD_EMOJI = [
    ("عنكبوت", "🕷️"), ("ذبابة", "🪰"), ("حشر", "🐛"), ("نحل", "🐝"), ("نملة", "🐜"), ("صرصور", "🪳"), ("كلب", "🐕"),
    ("سمك", "🐟"), ("حوت", "🐋"), ("دلفين", "🐬"), ("أخطبوط", "🐙"), ("سلحفاة", "🐢"), ("طائر", "🐦"), ("ثعبان", "🐍"),
    ("قلب", "❤️"), ("دماغ", "🧠"), ("عين", "👁️"), ("نوم", "😴"), ("حلم", "💭"), ("ماء", "💧"), ("طعام", "🍽️"), ("جوع", "🍽️"),
    ("نار", "🔥"), ("شمس", "☀️"), ("قمر", "🌙"), ("نجم", "⭐"), ("كوكب", "🪐"), ("الأرض", "🌍"), ("فضاء", "🚀"), ("صاروخ", "🚀"),
    ("ثقب أسود", "🕳️"), ("برق", "⚡"), ("رعد", "⚡"), ("مطر", "🌧️"), ("ثلج", "❄️"), ("بحر", "🌊"), ("جبل", "⛰️"), ("بركان", "🌋"),
    ("مختبر", "🔬"), ("عالم", "🔬"), ("دراسة", "📊"), ("تجربة", "🧪"), ("وقود", "⛽"), ("سيارة", "🚗"), ("طاقة", "⚡"),
    ("وقت", "⏳"), ("أسبوع", "📅"), ("شهر", "📅"), ("مال", "💰"), ("ذهب", "🪙"), ("كتاب", "📖"), ("ملك", "👑"), ("ملكة", "👑"),
    ("سيف", "⚔️"), ("حرب", "⚔️"), ("جيش", "🛡️"), ("سفينة", "🚢"), ("هرم", "🔺"), ("مدينة", "🏙️"), ("قلعة", "🏰"),
    ("خريطة", "🗺️"), ("لغز", "❓"), ("سر", "❓"), ("خطر", "⚠️"), ("جسم", "🧍"), ("حرارة", "🌡️"), ("هواء", "💨"), ("أكسجين", "💨"),
]
KEYWORD_PROPS = [("هرم", "pyramid"), ("معبد", "temple"), ("سفين", "ship"), ("قلعة", "castle"), ("خيمة", "tent"), ("نار", "fire"),
                 ("شجر", "tree"), ("جبل", "mountain"), ("ذهب", "coins"), ("مال", "coins"), ("كتاب", "book"), ("لفافة", "scroll"),
                 ("تاج", "crown"), ("ملك", "crown"), ("جمل", "camel"), ("برج", "tower"), ("مدينة", "city"), ("سيف", "swords"),
                 ("حرب", "swords"), ("معركة", "swords"), ("شمس", "sun"), ("قمر", "moon"), ("كنز", "chest"), ("فخار", "pot")]


def _fallback_raw(sent, beat, idx, style):
    """مشهد احتياطي متنوع (مو نفس الصورة كل مرة) مبني على كلمات الجملة."""
    text = sent["plain"]
    q = "؟" in text or "?" in text
    pos = ["left", "right", "center"][idx % 3]
    base = {"camera": ["none", "zoom_in"][idx % 2] if style == "doodle" else ["zoom_in", "zoom_out", "pan_left", "pan_right"][idx % 4],
            "transition": ["cut", "cut", "fade"][idx % 3] if style == "doodle" else ["slide", "fade", "zoom", "wipe"][idx % 4]}
    if style == "doodle":
        emo, kw = next(((e, k) for k, e in KEYWORD_EMOJI if k in text), ("", ""))
        v = idx % 6
        if v in (0, 3) and emo:
            return {**base, "scene": "closeup", "emoji": emo, "question": q, "callout": kw if v == 0 else ""}
        bg = ["living", "outdoor", "lab", "street", "cream", "outdoor"][v]
        actor = {"role": "scientist" if bg == "lab" else "person", "action": ["talk", "think", "point", "walk", "idle", "raise"][v],
                 "pos": pos, "expr": "think" if q else ["neutral", "happy", "surprised"][idx % 3]}
        icon = emo or ["💡", "🔎", "📌"][idx % 3]
        return {**base, "scene": "scene", "bg": bg, "actors": [actor],
                "props": [{"emoji": icon, "pos": "center" if pos != "center" else "right", "size": "medium"}],
                "bubble": {"kind": "thought", "text": "؟", "emoji": emo} if q else None,
                "callout": kw if idx % 2 == 0 else ""}
    prop = next((p for k, p in KEYWORD_PROPS if k in text), "")
    setting = beat.get("setting") if beat.get("setting") in C.BGS else ["desert", "hills", "ruins", "sky", "sea"][idx % 5]
    return {**base, "scene": "scene", "bg": setting,
            "props": [{"name": prop, "pos": "center" if pos != "center" else "right", "size": "medium"}] if prop else [],
            "actors": [{"role": "narrator", "action": ["talk", "point", "raise", "think"][idx % 4], "pos": pos}]}



def _sentences_of(script):
    out = []
    for bi, b in enumerate(script["beats"]):
        for s in split_sentences(clean_tts(b["text"])):
            out.append({"i": len(out), "beat": bi, "plain": strip_tashkeel(s)})
    return out


def _dir_prompt_history(script, topic, chunk, prev):
    lines = "\n".join(f"S{s['i']}: {s['plain']}" for s in chunk)
    return f"""You are the visual director of an animated stick-figure explainer video (Arabic documentary).
Video title: "{script['title']}"   Topic: "{topic}"
For EACH numbered sentence below, design ONE shot (a single animated scene) that literally illustrates what the sentence says.

Vocabulary (use ONLY these exact words):
- scene: {C.SCENES}  (scene = props + stick-figure actors; map = a route from one place to another; stat = a big animated number; timeline = a big date; question = a big question mark)
- bg: {C.BGS}
- props (max 3 per shot): name {C.PROPS}; pos {C.POSITIONS}; size {C.PROP_SIZES}
- actors (0-3 per shot): role {C.ROLES}; action {C.ACTIONS}; pos {C.POSITIONS}
- camera: {C.CAMERAS}; transition: {C.TRANSITIONS}; sfx: {C.SFX}

Rules:
- Match the meaning: pyramid+worker for building, ship+sailor for sea voyages, castle+soldier+swords for war, scroll/book+scholar for writing and science, coins/chest+trader for trade and wealth, camel/tent+trader for caravans, fire/cave+caveman for prehistory, crown+king/queen for rulers, crowds = 3 soldiers or workers.
- Use "map" with mapFrom/mapTo (place names, max 2 words each) for a journey, conquest or trade route. Use "stat" for a sentence with a number (callout = the number in digits like 25000, label = Arabic words for what it counts). Use "timeline" for a year or era (callout like "539 ق.م", label = short event). Use "question" for riddles (callout = the question, max 6 words).
- callout: 1-4 key Arabic words shown on screen (name, place or term), max 25 characters, NO diacritics; empty on about half of the shots.
- Never repeat the same bg + props in two consecutive shots; vary camera and transition; use "cut" rarely.
- host=true (the storyteller appears in a corner) only for the hook, big reveals and the final sentence (max 25% of shots).
- sfx: whoosh for travel or fast moves, pop for callouts, impact for battles and collapses, sparkle for discoveries and treasure, tick for timeline, else none.
Previous shot (for variety): {prev}

Sentences:
{lines}

Return JSON only: {{"shots": [{{"i": 0, "scene": "scene", "bg": "desert", "props": [{{"name": "pyramid", "pos": "center", "size": "large"}}], "actors": [{{"role": "worker", "action": "work", "pos": "left"}}], "camera": "zoom_in", "transition": "slide", "callout": "", "label": "", "mapFrom": "", "mapTo": "", "host": false, "sfx": "none"}}]}}
Return exactly one shot per sentence, with "i" equal to the sentence number."""


def _dir_prompt_doodle(script, topic, chunk, prev):
    lines = "\n".join(f"S{s['i']}: {s['plain']}" for s in chunk)
    return f"""You are the visual director of a DOODLE STYLE animated explainer (like popular "what happens if..." science channels): cream backgrounds, a simple stick-figure character, big emoji illustrations, speech and thought bubbles, labels, arrows, bar charts and calendars.
Video title: "{script['title']}"   Topic: "{topic}"
For EACH numbered sentence below, design ONE shot that clearly illustrates what the sentence says.

Scene types ({C.SCENES}):
- scene: a place (bg in {C.BGS}; prefer living, lab, outdoor, street, cream) with stick-figure actors and icon props.
- closeup: ONE big emoji (field "emoji") with an optional "label" tag and "question": true for a red question mark (the main subject or a mystery).
- bars: a bar chart comparing 2-4 items (field "items": label, text = number plus unit, value = relative bar length 2-100, icon); "callout" = chart title.
- calendar: calendar pages crossed out one by one (field "count" 1-24; "label" = big text such as "تقريبا سبعة أشهر"; optional "emoji").
- compare: two sides ("left" and "right": title, icon, level 0-5 red arrows, note), for example food vs no food.
- gauge: a dial ("level" 0-1; "callout" = text; "emoji" = subject) for energy, speed or risk analogies.
- diagram: a central "emoji" with 2-4 "tags" (short labels) pointing at it; "callout" = title such as "كيف؟".
- map (mapFrom/mapTo), stat (callout number + label), timeline (callout year + label), question (callout).
Fields: props = up to 3 items {{"emoji": "🕷️", "pos": {C.POSITIONS}, "size": {C.PROP_SIZES}}} (ONE icon NAME from this list, drawn by code: {", ".join(C.PROPS)}); actors = 0-2 items with role in {C.ROLES} (use "person" for the main character, "scientist" in labs, "child" for kids), action in {C.ACTIONS}, pos, expr in {C.ACTOR_EXPRS}; bubble = optional {{"kind": "speech" or "thought", "text": max 4 words, "emoji": optional}}; camera in {C.CAMERAS} (mostly none or zoom_in); transition in {C.TRANSITIONS} (mostly cut, sometimes fade); sfx in {C.SFX}.
Rules:
- Show the story literally: a person noticing an animal, a glass over a spider, a lab with scientists, a calendar for time spans, bars for numbers, a gauge or car-fuel analogy for hidden mechanisms, compare for two cases, a thought bubble for doubts and questions.
- Any number or time span becomes bars, calendar or stat. A mystery becomes closeup with question=true or a thought bubble.
- Vary scene types: never the same type more than twice in a row; closeup, bars, calendar, compare, gauge and diagram together should be at least 40% of the shots.
- All on-screen text in Arabic, max 4 words per label, NO diacritics; digits are allowed for numbers. host is always false.
Previous shot (for variety): {prev}

Sentences:
{lines}

Return JSON only: {{"shots": [{{"i": 0, "scene": "scene", "bg": "living", "props": [{{"emoji": "🕷️", "pos": "center", "size": "small"}}], "actors": [{{"role": "person", "action": "idle", "pos": "left", "expr": "surprised"}}], "bubble": {{"kind": "thought", "text": "؟", "emoji": ""}}, "camera": "none", "transition": "cut", "callout": "", "label": "", "emoji": "", "question": false, "items": [], "count": 0, "left": null, "right": null, "level": 0, "tags": [], "mapFrom": "", "mapTo": "", "host": false, "sfx": "none"}}]}}
Return exactly one shot per sentence, with "i" equal to the sentence number."""


def _dir_prompt(script, topic, chunk, prev):
    f = _dir_prompt_doodle if script.get("style") == "doodle" else _dir_prompt_history
    return f(script, topic, chunk, prev)


EMO2ICON = {
    "🕷️": "spider",
    "🕷": "spider",
    "🐝": "bee",
    "🐟": "fish",
    "🐋": "whale",
    "🐬": "whale",
    "🐙": "octopus",
    "🐢": "turtle",
    "🐦": "bird",
    "🐍": "snake",
    "❤️": "heart",
    "❤": "heart",
    "🧠": "brain",
    "👁️": "eye",
    "👁": "eye",
    "💧": "cup",
    "🔥": "fire",
    "☀️": "sun",
    "☀": "sun",
    "🌙": "moon",
    "⭐": "star",
    "🪐": "planet",
    "🌍": "earth",
    "🚀": "rocket",
    "🕳️": "blackhole",
    "⚡": "lightning",
    "🌧️": "rain",
    "❄️": "snowflake",
    "🌊": "wave",
    "⛰️": "mountain",
    "🌋": "volcano",
    "🔬": "microscope",
    "🧪": "flask",
    "🚗": "car",
    "⏳": "hourglass",
    "📅": "clock",
    "💰": "moneybag",
    "🪙": "coins",
    "📖": "book",
    "👑": "crown",
    "⚔️": "swords",
    "🛡️": "shield",
    "🚢": "ship",
    "🔺": "pyramid",
    "🏙️": "city",
    "🏰": "castle",
    "🗺️": "compass",
    "❓": "question",
    "⚠️": "warning",
    "🌡️": "thermometer",
    "💨": "tornado",
    "🧍": "crowd",
    "💡": "lightbulb",
    "🔎": "magnifier",
    "📌": "flag",
    "🏠": "house",
    "🐴": "horse",
    "🐘": "elephant",
    "🦈": "shark",
    "💀": "skull",
    "🧬": "dna",
    "⚛️": "atom",
    "🎵": "note",
    "🩰": "ballet",
    "🏆": "trophy",
    "🔑": "key",
    "🔒": "lock",
    "⚓": "anchor",
    "🧭": "compass",
    "🔭": "telescope",
    "🏛️": "column",
    "🗿": "statue",
    "🏺": "pot",
}


def _emoji(x, n=14):
    """يرجع اسم مجسم مرسوم بالكود (أو يحوّل إيموجي قديم لأقرب مجسم)؛ فاضي إذا غير معروف."""
    s = str(x or "").strip()
    if s in C.PROPS:
        return s
    return EMO2ICON.get(s, "")


def _pick(v, allowed, default):
    return v if v in allowed else default


def _vis(x, n):
    """نص يظهر على الشاشة: بدون تشكيل ولا رموز (الأرقام تبقى أرقام)."""
    return re.sub(r"[*#_`>\[\]{}|~^]", "", strip_tashkeel(str(x or ""))).strip()[:n]


def _norm_shot(raw, sent, beat, idx, style="history"):
    raw = raw if isinstance(raw, dict) else {}
    doodle = style == "doodle"
    scene = _pick(raw.get("scene"), C.SCENES, "scene")
    setting = beat.get("setting") if beat.get("setting") in C.BGS else "desert"
    default_bg = "living" if doodle else setting
    props = []
    for p in (raw.get("props") or [])[:3]:
        if not isinstance(p, dict):
            continue
        base = {"pos": _pick(p.get("pos"), C.POSITIONS, "center"), "size": _pick(p.get("size"), C.PROP_SIZES, "medium")}
        if _emoji(p.get("icon") or p.get("emoji") or p.get("name")):
            props.append({"emoji": _emoji(p.get("icon") or p.get("emoji") or p.get("name")), **base})
        elif p.get("name") in C.PROPS:
            props.append({"name": p["name"], **base})
    actors = []
    for a in (raw.get("actors") or [])[:3]:
        if isinstance(a, dict):
            actors.append({"role": _pick(a.get("role"), C.ROLES, "person" if doodle else "narrator"),
                           "action": _pick(a.get("action"), C.ACTIONS, "idle"),
                           "pos": _pick(a.get("pos"), C.POSITIONS, "center"),
                           "expr": _pick(a.get("expr"), C.ACTOR_EXPRS, "neutral")})
    callout, label = _vis(raw.get("callout"), 28), _vis(raw.get("label"), 44)
    map_from, map_to = _vis(raw.get("mapFrom"), 22), _vis(raw.get("mapTo"), 22)
    emoji = _emoji(raw.get("icon") or raw.get("emoji"))
    bub = raw.get("bubble")
    bubble = None
    if isinstance(bub, dict) and (_vis(bub.get("text"), 30) or _emoji(bub.get("icon") or bub.get("emoji"))):
        bubble = {"kind": _pick(bub.get("kind"), ["speech", "thought"], "speech"),
                  "text": _vis(bub.get("text"), 30), "emoji": _emoji(bub.get("icon") or bub.get("emoji"))}
    items = []
    for it in (raw.get("items") or [])[:4]:
        if isinstance(it, dict) and _vis(it.get("label"), 24):
            try:
                val = float(it.get("value", 50))
            except Exception:
                val = 50.0
            items.append({"label": _vis(it.get("label"), 24), "text": _vis(it.get("text"), 22),
                          "value": max(2.0, min(100.0, val)), "emoji": _emoji(it.get("icon") or it.get("emoji")) or "magnifier"})

    def side(x):
        if not isinstance(x, dict) or not _vis(x.get("title"), 26):
            return None
        try:
            lv = int(x.get("level", 0))
        except Exception:
            lv = 0
        return {"title": _vis(x.get("title"), 26), "emoji": _emoji(x.get("icon") or x.get("emoji")) or "question",
                "level": max(0, min(5, lv)), "note": _vis(x.get("note"), 28)}

    left, right = side(raw.get("left")), side(raw.get("right"))
    tags = [_vis(t, 28) for t in (raw.get("tags") or [])[:4] if _vis(t, 28)]
    try:
        count = int(raw.get("count", 0))
    except Exception:
        count = 0
    try:
        level = max(0.0, min(1.0, float(raw.get("level", 0.3))))
    except Exception:
        level = 0.3
    if scene == "map" and not (map_from and map_to):
        scene = "scene"
    if scene in ("stat", "timeline", "question") and not callout:
        scene = "scene"
    if scene == "closeup" and not emoji:
        scene = "scene"
    if scene == "bars" and len(items) < 2:
        scene = "closeup" if emoji else "scene"
    if scene == "calendar" and not (label or callout):
        scene = "scene"
    if scene == "compare" and not (left and right):
        scene = "scene"
    if scene == "diagram" and (len(tags) < 2 or not emoji):
        scene = "closeup" if emoji else "scene"
    if scene == "gauge" and not (callout or label):
        scene = "scene"
    if scene == "scene" and not props and not actors:
        actors = [{"role": "person" if doodle else "narrator", "action": "talk", "pos": "center", "expr": "neutral"}]
    return {"scene": scene, "bg": _pick(raw.get("bg"), C.BGS, default_bg), "props": props, "actors": actors,
            "camera": _pick(raw.get("camera"), C.CAMERAS, ["zoom_in", "none", "zoom_out", "none"][idx % 4] if doodle else ["zoom_in", "zoom_out", "pan_left", "pan_right"][idx % 4]),
            "transition": _pick(raw.get("transition"), C.TRANSITIONS, ["cut", "cut", "fade", "cut"][idx % 4] if doodle else ["slide", "fade", "zoom", "wipe"][idx % 4]),
            "callout": callout, "label": label, "mapFrom": map_from, "mapTo": map_to, "emoji": emoji,
            "question": bool(raw.get("question")), "bubble": bubble, "items": items,
            "count": max(1, min(24, count)) if count else 7, "left": left, "right": right, "level": level, "tags": tags,
            "host": False if doodle else bool(raw.get("host")), "sfx": _pick(raw.get("sfx"), C.SFX, "none"),
            "text": sent["plain"], "expression": beat.get("expression", "neutral"), "setting": setting}


def _polish(shots, style="history"):
    """تنويع وضبط: المذيع بالأول والآخر وبدون تكرار، وما نكرر نفس التركيبة ولا نفس الانتقال."""
    n = len(shots)
    if not n:
        return
    if style == "doodle":
        for s in shots:
            s["host"] = False
    else:
        shots[0]["host"] = True
        shots[-1]["host"] = True
    since = 99
    for i, s in enumerate(shots):
        if s["host"] and i not in (0, n - 1) and since < 6:
            s["host"] = False
        since = 0 if s["host"] else since + 1
    alt = ["living", "outdoor", "lab", "street", "cream"] if style == "doodle" else ["desert", "hills", "sky", "night", "paper", "sea"]
    prev_key, same = None, 0
    for i, s in enumerate(shots):
        key = (s["scene"], s["bg"], tuple(p.get("name") or p.get("emoji") for p in s["props"]), tuple(a["role"] for a in s["actors"]), s["emoji"])
        if key == prev_key:
            s["camera"] = C.CAMERAS[(C.CAMERAS.index(s["camera"]) + 1) % len(C.CAMERAS)]
            if s["scene"] == "scene":
                s["bg"] = alt[(alt.index(s["bg"]) + 1) % len(alt)] if s["bg"] in alt else alt[0]
        prev_key = key
        if i and s["transition"] == shots[i - 1]["transition"]:
            same += 1
            if same >= 2:
                s["transition"] = [t for t in C.TRANSITIONS if t not in (s["transition"], "cut")][i % 3]
                same = 0
        else:
            same = 0


def direct_shots(script, gem, topic=""):
    """مشهد لكل جملة. كل جزء له إعادة محاولة (مع راحة وتبديل لـ OpenAI)، وأي جملة تفشل تاخذ مشهداً احتياطياً متنوعاً."""
    sents = _sentences_of(script)
    fast = getattr(gem, "fast", False)
    style = script.get("style", "history")
    raws = {}
    chunks = [sents[k:k + C.DIRECTOR_CHUNK] for k in range(0, len(sents), C.DIRECTOR_CHUNK)]

    def run(chunk, prev, attempt):
        ids = {s["i"] for s in chunk}
        data = extract_json(gem.generate(_dir_prompt(script, topic, chunk, prev), system=DIRECTOR_SYSTEM,
                                         json_mode=(attempt % 2 == 0), temperature=0.7))
        got = 0
        for s in (data if isinstance(data, list) else data.get("shots", [])):
            if isinstance(s, dict) and isinstance(s.get("i"), int) and s["i"] in ids:
                raws[s["i"]] = s
                got += 1
        return got

    def last_of(chunk):
        last = raws.get(chunk[-1]["i"])
        return json.dumps({x: last.get(x) for x in ("scene", "bg", "props")}, ensure_ascii=False) if last else "none"

    failed, prev = [], "none"
    for ci, chunk in enumerate(chunks):
        ok = False
        for attempt in range(C.DIRECTOR_RETRIES):
            try:
                if run(chunk, prev, attempt) >= max(1, len(chunk) // 2):
                    ok = True
                    break
            except Exception as e:
                print(f"[director] جزء {ci + 1}/{len(chunks)} محاولة {attempt + 1} فشلت: {e}")
            if attempt == 1 and getattr(gem, "fallback_ok", lambda: False)():
                gem.use_fallback = True
            if not fast:
                time.sleep(8 * (attempt + 1))
        if not ok:
            failed.append(ci)
        prev = last_of(chunk)
        if not fast:
            time.sleep(C.LLM_GAP_SEC)
    if failed:                                    # جولة أخيرة للأجزاء الفاشلة بعد استراحة (لو الحصة المجانية خلصت)
        if not fast:
            time.sleep(45)
        for ci in failed:
            try:
                run(chunks[ci], "none", 0)
            except Exception as e:
                print(f"[director] جزء {ci + 1} فشل نهائياً (مشاهد احتياطية): {e}")
    shots = []
    for s in sents:
        raw = raws.get(s["i"])
        shot = _norm_shot(raw if raw else _fallback_raw(s, script["beats"][s["beat"]], s["i"], style),
                          s, script["beats"][s["beat"]], s["i"], style)
        shot["src"] = "llm" if raw else "fallback"
        shots.append(shot)
    _polish(shots, style)
    n_llm = sum(1 for x in shots if x["src"] == "llm")
    print(f"[director] {len(shots)} مشهد: {n_llm} من المخرج و{len(shots) - n_llm} احتياطي")
    return shots


def shots_to_frames(shots, manifest):
    """يربط كل مشهد بوقت جملته الفعلي في الصوت (فريم البداية والنهاية)."""
    sents, fps, total = manifest["sentences"], manifest["fps"], manifest["totalFrames"]
    if not shots or not sents:
        return []
    shots = (list(shots) + [shots[-1]] * len(sents))[: len(sents)]
    out, prev_end = [], 0
    for i, sh in enumerate(shots):
        start = 0 if i == 0 else int(round(sents[i]["start_sec"] * fps))
        start = max(start, prev_end)
        end = total if i == len(sents) - 1 else int(round(sents[i + 1]["start_sec"] * fps))
        end = max(end, start + 8)
        out.append({**sh, "from": start, "to": end, "text": sents[i]["plain"]})
        prev_end = end
    out[-1]["to"] = max(out[-1]["to"], total)
    return out


# ============ مؤثرات صوتية بالكود ============
def sfx_sound(kind):
    rng = np.random.default_rng(7)
    t = lambda d: np.arange(int(d * SR)) / SR
    if kind == "whoosh":
        x = t(0.7)
        y = rng.standard_normal(len(x)) * np.sin(np.pi * x / 0.7) ** 2
        y = sosfilt(butter(2, [400, 3500], btype="bandpass", fs=SR, output="sos"), y)
    elif kind == "pop":
        x = t(0.14)
        y = np.sin(2 * np.pi * (480 + 900 * np.exp(-x * 45)) * x) * np.exp(-x * 32)
    elif kind == "impact":
        x = t(0.8)
        y = np.sin(2 * np.pi * 62 * x) * np.exp(-x * 7) + rng.standard_normal(len(x)) * np.exp(-x * 22) * 0.5
        y = sosfilt(butter(2, 900, btype="low", fs=SR, output="sos"), y)
    elif kind == "sparkle":
        x = t(0.9)
        y = np.zeros(len(x))
        for j, f in enumerate((1760, 2217, 2637, 3520)):
            s0 = int(j * 0.07 * SR)
            y[s0:] += np.sin(2 * np.pi * f * x[: len(x) - s0]) * np.exp(-x[: len(x) - s0] * 7) * 0.5
    else:  # tick
        x = t(0.5)
        y = np.zeros(len(x))
        click = rng.standard_normal(int(0.02 * SR)) * np.exp(-np.arange(int(0.02 * SR)) / (0.004 * SR))
        for j in range(3):
            s0 = int(j * 0.14 * SR)
            y[s0:s0 + len(click)] += click
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.8
    return y.astype(np.float32)


def sfx_track(shots, manifest):
    N = int(manifest["totalSec"] * SR)
    out = np.zeros(N, np.float32)
    cache = {k: sfx_sound(k) for k in ("whoosh", "pop", "impact", "sparkle", "tick")}

    def put(kind, t0, g=1.0):
        a, i0 = cache[kind], int(max(0, t0) * SR)
        if i0 < N:
            j = min(N, i0 + len(a))
            out[i0:j] += a[: j - i0] * g

    fps = manifest["fps"]
    for i, sh in enumerate(shots):
        t0 = sh["from"] / fps
        if i and sh["transition"] in ("slide", "zoom", "wipe"):
            put("whoosh", t0 - 0.05, 0.5)
        if sh["sfx"] in cache:
            put(sh["sfx"], t0 + (0.0 if sh["sfx"] == "whoosh" else 0.05), 0.9 if sh["sfx"] == "whoosh" else 1.0)
        elif sh["callout"] and sh["scene"] == "scene":
            put("pop", t0 + 0.33, 0.6)
    return np.stack([out, out])



def produce(cat, topic, gem, synth, do_render=True):
    """موضوع -> سكربت -> صوت -> موسيقى -> مزج -> (رندر). يرجع (script, manifest, mp4, thumb)."""
    style = style_of(cat)
    doodle = style == "doodle"
    script = build_script(cat, topic, gem, style=style)
    plan = []
    if C.DIRECTOR_ENABLED:
        try:
            plan = direct_shots(script, gem, topic)
        except Exception as e:
            print(f"[director] فشل المخرج (نكمل بالرسم الكلاسيكي): {type(e).__name__}: {e}")
    manifest, envelope, narr = tts_build(script["beats"], WORK, synth,
                                         sent_gap=C.DOODLE_SENT_GAP if doodle else None,
                                         beat_gap=C.DOODLE_BEAT_GAP if doodle else None)
    print(f"[tts] المدة {manifest['totalSec'] / 60:.1f} دقيقة، {manifest['totalFrames']} فريم")
    shots = shots_to_frames(plan, manifest) if plan else []
    script["_stats"] = {"shots": len(shots), "from_director": sum(1 for x in shots if x.get("src") == "llm"),
                        "engine": "explainer" if shots else "classic"}
    bed, segs = render_timeline(manifest["beats"], manifest["totalSec"], C.MOOD_STYLE)
    print("[music] الأقسام:", [(s, round(a), round(b)) for s, a, b in segs])
    mix(narr, bed, VIDEO_DIR / "public" / "audio" / "mix.mp3", sfx_track(shots, manifest) if shots else None,
        gain=C.DOODLE_MUSIC_GAIN if doodle else None)
    write_props(manifest, envelope, script, shots=shots)
    if not do_render:
        return script, manifest, None, None
    mp4 = WORK / "video.mp4"
    render_video(mp4)
    thumb = render_thumb(WORK / "thumb.jpg") or frame_thumbnail(mp4, WORK / "thumb.jpg")
    return script, manifest, mp4, thumb



# ============ الشورتات: فيديوهات رأسية قصيرة تتبع الفيديو الطويل وتوجه المشاهد له ============
def _short_prompt(topic, sc, n):
    lo, hi = C.SHORT_WORDS
    gist = " ".join(b.get("plain", b["text"]) for b in sc["beats"][:10])[:2200]
    return f"""Write {n} different YouTube Shorts scripts in Arabic that tease a long documentary video.
Long video title: "{sc['title']}"
Topic: "{topic}"
Source facts (use ONLY facts found here or well-established consensus, never invent):
{gist}

Rules for EACH Short:
- Modern Standard Arabic WITHOUT diacritics (a separate step adds them). Never use the straight double-quote character inside text values. ALL numbers written as Arabic words.
- {lo}-{hi} words total in 4-6 beats (about 12-22 words per beat), short sentences ending with a period.
- Beat 1 = a shocking question or fact (max 14 words), no greeting.
- Middle beats = one gripping fact each. Each Short covers a DIFFERENT angle of the topic.
- Last beat = a cliffhanger that ends exactly with this sentence: القصة كاملة في الفيديو الجديد على قناة أوابد.
- Per beat: gesture in {C.GESTURES}; setting in {C.SETTINGS}; expression in {C.EXPRESSIONS}.
- title: max 60 chars, hook first, no hashtags. hook_text: 2-5 powerful Arabic words shown on screen. tags: 6-10 Arabic/English tags.

Return JSON only: {{"shorts": [{{"title": "...", "hook_text": "...", "tags": ["..."], "beats": [{{"text": "...", "gesture": "raise", "setting": "ruins", "expression": "surprised"}}]}}]}}"""


def build_shorts(topic, sc, gem):
    """يكتب شورتات من نفس موضوع الفيديو الطويل. أي فشل هنا ما يأثر على الفيديو الطويل."""
    if not C.SHORTS_ENABLED:
        return []
    lo, hi = C.SHORT_WORDS
    try:
        data = extract_json(gem.generate(_short_prompt(topic, sc, C.SHORTS_PER_VIDEO), system=SYSTEM, json_mode=True))
    except Exception as e:
        print(f"[shorts] فشل كتابة الشورتات (الفيديو الطويل ما تأثر): {e}")
        return []
    out = []
    for s in data.get("shorts", [])[: C.SHORTS_PER_VIDEO]:
        beats = []
        for b in s.get("beats", []):
            text = clean_tts(b.get("text", ""))
            if strip_tashkeel(text):
                beats.append({"text": text, "plain": strip_tashkeel(text), "mood": "wonder", "chapter": "",
                              "gesture": b.get("gesture") if b.get("gesture") in C.GESTURES else "none",
                              "setting": b.get("setting") if b.get("setting") in C.SETTINGS else "ruins",
                              "expression": b.get("expression") if b.get("expression") in C.EXPRESSIONS else "neutral"})
        words = sum(len(b["plain"].split()) for b in beats)
        blob = " ".join(b["plain"] for b in beats) + " " + str(s.get("title", ""))
        if len(beats) < 3 or not (lo * 0.8 <= words <= hi * 1.1) or any(w in blob for w in C.BANNED_WORDS):
            print(f"[shorts] شورت مرفوض: {len(beats)} مقاطع، {words} كلمة")
            continue
        if "الفيديو" not in beats[-1]["plain"]:
            beats[-1]["text"] += " القِصَّةُ كَامِلَةٌ فِي الفِيدِيُو الجَدِيدِ عَلَى قَنَاةِ أَوَابِدَ."
            beats[-1]["plain"] = strip_tashkeel(beats[-1]["text"])
        diacritize_beats(beats, gem)
        out.append({"title": clean_text(s.get("title", ""))[:70] or sc["title"][:60],
                    "hook_text": clean_text(s.get("hook_text", ""))[:40] or "شاهد القصة",
                    "tags": [str(t).strip() for t in s.get("tags", []) if str(t).strip()][:10], "beats": beats})
    return out


def write_short_props(manifest, envelope, short, style, audio_rel, path, shots=None, vstyle="history"):
    setup_video()
    props = {"fps": manifest["fps"], "totalFrames": manifest["totalFrames"],
             "beats": [{**b, "text": b.get("plain", b["text"])} for b in manifest["beats"]],
             "envelope": envelope, "hookText": short["hook_text"], "endText": "القصة كاملة على القناة",
             "narratorStyle": style, "logoWidth": C.LOGO_WIDTH, "logoOpacity": C.LOGO_OPACITY, "audio": audio_rel}
    props["style"] = vstyle
    if shots:
        props["shots"] = shots
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")


def render_short(props_name, out_mp4):
    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npx", "remotion", "render", "src/index.tsx", "Short", str(Path(out_mp4).resolve()),
                    f"--props=public/{props_name}", f"--concurrency={C.RENDER_CONCURRENCY}",
                    "--codec=h264", "--crf=25", "--log=warn"], cwd=VIDEO_DIR, check=True)


def produce_short(i, short, style, synth, do_render=True, gem=None, vstyle="history", topic=""):
    """شورت: صوت + مشاهد المخرج (نفس أسلوب الفيديو الطويل) + موسيقى + مزج + رندر رأسي. يرجع (mp4, manifest)."""
    doodle = vstyle == "doodle"
    outdir = WORK / f"short{i}"
    manifest, envelope, narr = tts_build(short["beats"], outdir, synth,
                                         sent_gap=C.DOODLE_SENT_GAP if doodle else None,
                                         beat_gap=C.DOODLE_BEAT_GAP if doodle else None)
    if manifest["totalSec"] > 59:
        raise RuntimeError(f"الشورت {i} طويل ({manifest['totalSec']:.0f} ثانية)")
    shots = []
    if gem is not None and C.DIRECTOR_ENABLED:
        try:
            plan = direct_shots({"title": short["title"], "beats": short["beats"], "style": vstyle}, gem, topic)
            for s in plan:
                s["host"] = False
            shots = shots_to_frames(plan, manifest)
        except Exception as e:
            print(f"[director] مخرج الشورت فشل (نكمل بالرسم الكلاسيكي): {type(e).__name__}: {e}")
    bed = render(["starlight", "warm_evening"][(i - 1) % 2], manifest["totalSec"], seed=100 + i,
                 fade_in=1.5, fade_out=3.0)
    audio_rel = f"audio/short{i}.mp3"
    mix(narr, bed, VIDEO_DIR / "public" / audio_rel, sfx_track(shots, manifest) if shots else None,
        gain=C.DOODLE_MUSIC_GAIN if doodle else None)
    write_short_props(manifest, envelope, short, style, audio_rel, VIDEO_DIR / "public" / f"short{i}.json",
                      shots=shots, vstyle=vstyle)
    if not do_render:
        return None, manifest
    mp4 = WORK / f"short{i}.mp4"
    render_short(f"short{i}.json", mp4)
    return mp4, manifest


def publish_shorts(yt, gem, topic, script, long_id, long_slot, synth, do_render=True):
    """ينتج ويرفع شورتات مجدولة بعد الفيديو الطويل، ووصفها فيه رابطه. أي شورت يفشل ما يوقف شي."""
    ids = []
    for i, sh in enumerate(build_shorts(topic, script, gem), 1):
        try:
            mp4, _ = produce_short(i, sh, script["narrator_style"], synth, do_render, gem, script.get("style", "history"), topic)
            when = long_slot + timedelta(hours=C.SHORT_DELAY_HOURS[min(i - 1, len(C.SHORT_DELAY_HOURS) - 1)])
            desc = (f"{sh['hook_text']}\n\nشاهد القصة كاملة 👇\nhttps://youtu.be/{long_id}\n\n"
                    "#Shorts #أوابد #تاريخ #حضارات")
            sid, _locked = yt_upload(yt, mp4, {"title": sh["title"] + " #Shorts", "description": desc,
                                               "tags": sh["tags"] + ["Shorts", "shorts", "شورتس"]}, when, None)
            ids.append(sid)
            print(f"[shorts] تم الشورت {i}: https://youtube.com/shorts/{sid} (ينزل {when.astimezone(C.TZ):%Y-%m-%d %H:%M})")
        except Exception as e:
            print(f"[shorts] الشورت {i} فشل (الفيديو الطويل سليم): {type(e).__name__}: {e}")
    return ids


def publish():
    print(f"[version] {VERSION}")
    state = load_state()
    now = datetime.now(timezone.utc)
    state["last_run"] = now.isoformat()
    k = None
    try:
        creds = check_token()                       # أهم نقطة: نفشل بسرعة لو التوكن ميت
        yt = yt_client(creds)
        slot = pick_slot(now, state, existing_scheduled(yt))
        if slot is None:
            rest = [x for x in resting_slots(now, state) if x not in state["alerted"]]
            if rest:
                state["alerted"].extend(rest)
                save_state(state)
                summary(f"❌ مواعيد فشلت محاولاتها وتنتظر إعادة المحاولة: {rest}\nراجع آخر خطأ: {state.get('last_error')}")
                return 1
            save_state(state)
            summary("✅ ما فيه موعد يحتاج فيديو الحين (الرصيد مكتمل).")
            return 0
        today = now.astimezone(C.TZ).date().isoformat()
        pkg = state.setdefault("pkg", {})
        if pkg.get(today, 0) >= C.MAX_PACKAGES_PER_DAY:
            save_state(state)
            summary(f"⏸️ وصلنا الحد اليومي ({C.MAX_PACKAGES_PER_DAY} فيديو مع شورتاته) لحماية حصة يوتيوب. نكمل بكرة تلقائياً.")
            return 0
        k = slot_key(slot)
        n = register_attempt(state, k, now)
        save_state(state)                           # نسجل المحاولة قبل أي شغل ثقيل
        print(f"[run] الموعد {k} (محاولة {n}/{C.MAX_ATTEMPTS})")

        gem = Gemini()
        cat, topic = pick_topic(state, gem)
        print(f"[run] التصنيف: {cat} | الموضوع: {topic}")
        synth = make_edge_synth(C.DOODLE_RATE, C.DOODLE_PITCH) if style_of(cat) == "doodle" else make_edge_synth()
        script, manifest, mp4, thumb = produce(cat, topic, gem, synth)
        vid, locked = yt_upload(
            yt, mp4, {"title": script["title"], "description": build_description(script, manifest),
                      "tags": script["tags"]}, slot, thumb)
        state["done"].append(k)
        pkg[today] = pkg.get(today, 0) + 1
        for d in sorted(pkg)[:-10]:
            pkg.pop(d)
        entry = {"category": cat, "topic": topic, "title": script["title"], "slot": k, "video_id": vid,
                 "at": now.isoformat(), "shorts": []}
        state["history"].append(entry)
        state["last_error"] = None
        save_state(state)
        shorts_ids = [] if locked else publish_shorts(yt, gem, topic, script, vid, slot, synth)
        entry["shorts"] = shorts_ids
        save_state(state)
        summary(f"### ✅ تم\n- العنوان: {script['title']}\n- التصنيف: {cat}\n- الموضوع: {topic}\n"
                f"- الموعد: {slot.astimezone(C.TZ):%Y-%m-%d %H:%M} (الرياض)\n- الرابط: https://youtu.be/{vid}\n"
                f"- موديل Gemini: {gem.last_model}\n- الكلمات: {word_count(script)}\n"
                f"- الصورة المصغرة: {'نعم' if thumb else 'لا (تخطيناها والنشر كمل)'}\n"
                f"- الشورتات: {len(shorts_ids)} من {C.SHORTS_PER_VIDEO if C.SHORTS_ENABLED else 0}\n"
                f"- النسخة: {VERSION}\n- الأسلوب: {script.get('style')} | المحرك: {script.get('_stats', {}).get('engine')} | "
                f"المشاهد من المخرج: {script.get('_stats', {}).get('from_director')} من {script.get('_stats', {}).get('shots')}")
        if locked:
            summary("### ⚠️ الفيديو انرفع لكن الجدولة ما انحفظت\nغالباً مشروع Google Cloud غير موثّق فيوتيوب يقفل الفيديو خاص. "
                    "افتح YouTube Studio وتأكد، وإذا كان مقفل قدّم نموذج YouTube API Services Audit.")
            return 1
        return 0
    except Exception as e:
        traceback.print_exc()
        text = str(e)
        if any(x in text for x in ("quotaExceeded", "uploadLimitExceeded", "dailyLimitExceeded")):
            a = state["attempts"].get(k) if k else None
            if isinstance(a, dict):
                a["n"] = max(0, a["n"] - 1)          # حد يوتيوب اليومي ما هو خطأ منا: ما نحسبها محاولة
            state["last_error"] = "حد يوتيوب اليومي وصل، نعيد تلقائياً"
            save_state(state)
            summary("⏸️ وصلنا حد يوتيوب اليومي (Quota). يعيد تلقائياً بكرة بدون تدخل منك.")
            return 0
        state["last_error"] = f"{type(e).__name__}: {text[:400]}"
        save_state(state)
        summary(f"### ❌ فشل\n```\n{state['last_error']}\n```")
        return 1


def health():
    md, bad = report(run_checks())
    summary("### الفحص الصحي\n" + md)
    return 1 if bad else 0


# ---------------- اختبار كامل بمكونات وهمية (بدون شبكة) ----------------
def _fake_tashkeel(t):
    """تشكيل وهمي للاختبار فقط: فتحة بعد كل حرف عربي."""
    return re.sub(r"([\u0621-\u064A])", "\\1\u064E", t)


class FakeGemini:
    last_model = "fake"
    fast = True

    def generate(self, prompt, **kw):
        if "Add FULL Arabic diacritics" in prompt:
            texts = [_fake_tashkeel(t) for t in re.findall(r"^T\d+: (.*)$", prompt, flags=re.M)]
            return json.dumps({"texts": texts}, ensure_ascii=False)
        if "visual director" in prompt:
            ids = [int(x) for x in re.findall(r"^S(\d+):", prompt, flags=re.M)]
            kinds = ["scene", "scene", "map", "scene", "stat", "scene", "timeline", "scene", "question", "scene"]
            shots = []
            if "DOODLE STYLE" in prompt:
                dk = ["scene", "closeup", "bars", "calendar", "compare", "gauge", "diagram", "scene", "question", "stat"]
                for i in ids:
                    k = dk[i % len(dk)]
                    shots.append({
                        "i": i, "scene": k, "bg": ["living", "lab", "outdoor", "street", "cream"][i % 5],
                        "props": [{"emoji": "🕷️", "pos": C.POSITIONS[i % 5], "size": "medium"}],
                        "actors": [{"role": "scientist" if i % 5 == 1 else "person", "action": C.ACTIONS[i % len(C.ACTIONS)],
                                    "pos": C.POSITIONS[(i + 2) % 5], "expr": C.ACTOR_EXPRS[i % 5]}],
                        "bubble": ({"kind": "thought" if i % 2 else "speech", "text": "جوع؟", "emoji": "🪰"} if i % 3 == 0 else None),
                        "camera": "none", "transition": "cut",
                        "callout": "25000" if k == "stat" else ("كلمة" if k in ("scene", "bars", "gauge", "diagram", "question") else ""),
                        "label": "تقريبا سبعة أشهر" if k in ("calendar", "closeup", "stat") else "", "emoji": "🕷️", "question": i % 2 == 0,
                        "items": [{"label": "أ", "text": "208 يوما", "value": 70, "emoji": "🕷️"},
                                  {"label": "ب", "text": "276 يوما", "value": 100, "emoji": "🕸️"}],
                        "count": 7, "left": {"title": "طعام", "emoji": "🕷️", "level": 4, "note": "طاقة"},
                        "right": {"title": "بدون", "emoji": "🕷️", "level": 1, "note": "طاقة"},
                        "level": 0.2, "tags": ["أ", "ب", "ج"], "mapFrom": "", "mapTo": "", "host": False,
                        "sfx": C.SFX[i % len(C.SFX)]})
                return json.dumps({"shots": shots}, ensure_ascii=False)
            for i in ids:
                k = kinds[i % len(kinds)]
                shots.append({"i": i, "scene": k, "bg": C.BGS[i % len(C.BGS)],
                              "props": [{"name": C.PROPS[i % len(C.PROPS)], "pos": C.POSITIONS[i % 5], "size": "medium"}],
                              "actors": [{"role": C.ROLES[i % len(C.ROLES)], "action": C.ACTIONS[i % len(C.ACTIONS)],
                                          "pos": C.POSITIONS[(i + 2) % 5]}],
                              "camera": C.CAMERAS[i % len(C.CAMERAS)], "transition": C.TRANSITIONS[i % len(C.TRANSITIONS)],
                              "callout": "25000" if k == "stat" else ("539 ق.م" if k == "timeline" else ("كلمة" if i % 2 == 0 else "")),
                              "label": "نسمة", "mapFrom": "تدمر", "mapTo": "روما", "host": i % 9 == 0,
                              "sfx": C.SFX[i % len(C.SFX)]})
            return json.dumps({"shots": shots}, ensure_ascii=False)
        if "Suggest ONE" in prompt:
            return json.dumps({"topic": "لماذا بنيت مدينة تجريبية قديمة؟"}, ensure_ascii=False)
        if "Shorts scripts" in prompt:
            def _short(tag):
                lines = [f"هل تعلم أن قصة {tag} غيرت وجه المنطقة كلها في زمنها القديم؟",
                         "بدأت الحكاية من مدينة صغيرة على طريق القوافل بين الشرق والغرب.",
                         "وكانت الأموال تجري إليها من التجارة والضرائب كل موسم ومع كل قافلة.",
                         "ثم جاء جيش كبير وغير مجرى الأحداث في أيام قليلة فقط وبلا إنذار.",
                         "ولا يزال المؤرخون يختلفون حول ما جرى في ليلة السقوط الأخيرة تلك.",
                         "القصة كاملة في الفيديو الجديد على قناة أوابد."]
                return {"title": f"سر {tag} الذي لا يعرفه أحد", "hook_text": "سر غامض؟", "tags": ["تاريخ", "Shorts"],
                        "beats": [{"text": t, "gesture": C.GESTURES[j % 4], "setting": C.SETTINGS[j % 3],
                                   "expression": C.EXPRESSIONS[j % 4]} for j, t in enumerate(lines)]}
            return json.dumps({"shorts": [_short("المدينة"), _short("الملكة")]}, ensure_ascii=False)
        base = ("في عام 539 قبل الميلاد سقطت مدينة عظيمة أمام جيش كبير، وبعد ذلك تغير وجه المنطقة كلها. "
                "تقول بعض المصادر إن عدد السكان وصل إلى 25000 نسمة، وهذا رقم مذهل لتلك الأيام. "
                "كان الناس يعملون في الزراعة والتجارة، وكانت القوافل تعبر الصحراء بحثا عن الماء. "
                "ثم جاءت سنوات صعبة، واختفت الأنهار القديمة، وبقيت الأطلال شاهدة على ما حدث. ")
        base = " ".join(base.split("، ")[:3]) + ". "
        moods = ["story", "story", "sad", "wonder", "calm", "epic"]
        beats = [{"text": base + f"المشهد رقم {i + 1}.", "mood": moods[i % 6],
                  "gesture": C.GESTURES[i % 4], "setting": C.SETTINGS[i % len(C.SETTINGS)],
                  "expression": C.EXPRESSIONS[i % 4],
                  "chapter": ("المقدمة" if i == 0 else f"الفصل {i}") if i % 3 == 0 else ""} for i in range(22)]
        return json.dumps({"title": "من بنى المدينة المفقودة؟ القصة الكاملة", "thumb_text": "المدينة المفقودة؟",
                           "thumb_setting": "ruins", "narrator_style": "arab",
                           "description": "سطر الخطاف مع الكلمات المفتاحية.\nفقرة ثانية.", "tags": ["تاريخ", "حضارات"],
                           "hashtags": ["#تاريخ", "#حضارات", "#ألغاز"], "beats": beats}, ensure_ascii=False)


def fake_synth(text):
    sr = 24000
    dur = max(0.4, 0.062 * len(text))
    t = np.arange(int(dur * sr)) / sr
    syl = 0.5 + 0.5 * np.sin(2 * np.pi * 4.2 * t) ** 2          # إيقاع مقاطع
    y = 0.4 * syl * np.sin(2 * np.pi * 140 * t) * (np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.05))
    buf = io.BytesIO()
    wavfile.write(buf, sr, (y * 32767).astype(np.int16))
    return buf.getvalue()


def _dry_one(cat, topic, do_render, with_shorts):
    gem = FakeGemini()
    style = style_of(cat)
    print(f"[dry] ===== {cat} ({style}) =====")
    script, manifest, mp4, thumb = produce(cat, topic, gem, fake_synth, do_render=do_render)
    sr, nar = wavfile.read(WORK / "narration.wav")
    nar = nar.astype(np.float32) / 32768
    _, m = wavfile.read(WORK / "music.wav")
    m = m.astype(np.float32) / 32768 * (C.DOODLE_MUSIC_GAIN if style == "doodle" else C.MUSIC_GAIN)
    v = nar[np.abs(nar) > 0.01]
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    print(f"[dry] صوت المعلق {db(v):.1f} dB | الموسيقى {db(m):.1f} dB | الفرق {db(v) - db(m):.1f} dB")
    print(f"[dry] {len(script['beats'])} مقطع، {word_count(script)} كلمة، {manifest['totalSec']:.0f} ثانية")
    desc = build_description(script, manifest)
    print("[dry] الوصف:\n" + desc)
    assert db(v) - db(m) > 12, "الموسيقى عالية نسبة لصوت المعلق"
    assert not any(ch.isdigit() for b in script["beats"] for ch in b["text"]), "بقيت أرقام"
    assert "00:00" not in desc and "0:00" in desc, "الفصول لازم تبدأ من 0:00"
    shorts = build_shorts(topic, script, gem) if with_shorts else []
    assert len(shorts) == (C.SHORTS_PER_VIDEO if with_shorts else 0), f"الشورتات: {len(shorts)}"
    for i, sh in enumerate(shorts, 1):
        _, man = produce_short(i, sh, script["narrator_style"], fake_synth, False, gem, style, topic)
        sp = json.loads((VIDEO_DIR / "public" / f"short{i}.json").read_text(encoding="utf-8"))
        assert sp.get("shots") and sp["style"] == style and all(not x["host"] for x in sp["shots"]), "الشورت بدون مشاهد المخرج"
        print(f"[dry] شورت {i}: {man['totalSec']:.0f} ثانية، {len(sh['beats'])} مقاطع | {sh['title']}")
        assert man["totalSec"] < 59 and "الفيديو" in sh["beats"][-1]["plain"]
        assert (VIDEO_DIR / "public" / f"short{i}.json").exists()
    props = json.loads((VIDEO_DIR / "public" / "props.json").read_text(encoding="utf-8"))
    sh = props.get("shots", [])
    assert len(sh) == len(manifest["sentences"]), (len(sh), len(manifest["sentences"]))
    assert sh[0]["from"] == 0 and sh[-1]["to"] >= manifest["totalFrames"], "المشاهد ما تغطي الفيديو"
    assert all(sh[i]["to"] == sh[i + 1]["from"] for i in range(len(sh) - 1)), "فجوات بين المشاهد"
    print(f"[dry] {len(sh)} مشهد، أنواعها: {sorted({x['scene'] for x in sh})}، المذيع في {sum(x['host'] for x in sh)} منها")
    assert C.VOICES[0] == "fr-FR-RemyMultilingualNeural", "الصوت الأول لازم ريمي"
    assert diacritic_ratio(" ".join(b["text"] for b in script["beats"])) > 0.3, "التشكيل ناقص"
    assert all("plain" in b and not _TASHKEEL.search(b["plain"]) for b in script["beats"])
    print("[dry] التعليق يقرأ نص مشكّل:", script["beats"][0]["text"][:40])
    assert props.get("style") == style and script.get("style") == style
    if style == "doodle":
        kinds = {x["scene"] for x in sh}
        assert {"closeup", "bars", "calendar", "compare", "gauge", "diagram"} <= kinds, kinds
        assert not any(x["host"] for x in sh) and props.get("thumbEmoji")
        assert any(p.get("emoji") for x in sh for p in x["props"]), "لا إيموجي في المجسمات"
    print("[dry] الموعد القادم:", pick_slot(datetime.now(timezone.utc), load_state("/tmp/none.json")))
    print(f"[dry] OK ({style})")
    return 0


def dry_run(do_render=False):
    his = next(c for c in C.CATEGORIES if c not in C.CURIOSITY_CATS)
    rc = _dry_one(his, "لماذا بنيت مدينة تجريبية قديمة؟", do_render, True)
    rc |= _dry_one(C.CURIOSITY_CATS[0], "ماذا يحدث لو حُبست عنكبوتة تحت كوب؟", do_render, False)
    return rc


# ============ اختبارات الوحدات ============
def selftest():
    assert num_ar(1200) == "ألف ومائتان"
    assert "539" not in digits_to_words("عام 539 ق.م") and "بالمئة" in digits_to_words("45%")
    sc = normalize({"title": "عنوان", "description": "x", "tags": [],
                    "beats": [{"text": "في عام 500 كان مخدرات"}] * 3})
    p = validate(sc)
    assert any("ممنوعة" in x for x in p) and not any("أرقام" in x for x in p), p
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    slots = upcoming_slots(now)
    assert slots and all(s >= now + timedelta(hours=C.MIN_LEAD_HOURS) for s in slots)
    st = {"done": [], "attempts": {}}
    first = pick_slot(now, st)
    assert pick_slot(now, st, existing_utc=[first]) != first
    for _ in range(C.MAX_ATTEMPTS):
        register_attempt(st, slot_key(first), now)
    assert pick_slot(now, st) != first
    assert pick_slot(now + timedelta(hours=C.RETRY_AFTER_HOURS + 1), st) is not None
    week = {s.astimezone(C.TZ).date() for s in upcoming_slots(datetime(2026, 10, 26, 0, 0, tzinfo=timezone.utc) )}
    assert len(C.SCHEDULE) == 5 and len(week) >= 5
    beats = [{"mood": "story", "start_sec": 1, "end_sec": 40}, {"mood": "sad", "start_sec": 40, "end_sec": 90},
             {"mood": "wonder", "start_sec": 90, "end_sec": 100}, {"mood": "calm", "start_sec": 100, "end_sec": 150}]
    segs = plan_segments(beats, 154, C.MOOD_STYLE)
    assert segs[0][1] == 0 and segs[-1][2] == 154 and (all(b - a >= 25 for _, a, b in segs) or len(segs) == 1)
    assert len(C.CATEGORIES) >= 15 and all(len(v) >= 3 for v in C.CATEGORIES.values())
    h_his = {"history": [{"category": c} for c in C.CATEGORIES if c not in C.CURIOSITY_CATS]}
    assert pick_category(h_his) in C.CURIOSITY_CATS                      # التاريخ كثير: نروح للفضول
    h_cur = {"history": [{"category": c} for c in C.CURIOSITY_CATS]}
    assert pick_category(h_cur) not in C.CURIOSITY_CATS
    assert style_of(C.CURIOSITY_CATS[0]) == "doodle" and style_of("مصر القديمة") == "history"
    nd = _norm_shot({"scene": "bars", "items": [{"label": "أ", "text": "5", "value": 50}], "emoji": "🕷️"}, {"plain": "ن"}, {}, 0, "doodle")
    assert nd["scene"] == "closeup" and nd["bg"] == "living" and nd["host"] is False
    nd2 = _norm_shot({"scene": "compare", "left": {"title": "أ", "level": 9}, "right": {"title": "ب"},
                      "bubble": {"kind": "x", "text": "؟"}, "props": [{"emoji": "🕷️"}, {"emoji": "abc"}]},
                     {"plain": "ن"}, {}, 0, "doodle")
    assert nd2["scene"] == "compare" and nd2["left"]["level"] == 5 and nd2["bubble"]["kind"] == "speech" and len(nd2["props"]) == 1
    assert len(split_sentences("جملة أولى طويلة هنا. جملة ثانية طويلة هنا؟ نعم.")) == 2
    class _G:
        def generate(self, *a, **k):
            return json.dumps({"shorts": [{"title": "ت", "hook_text": "ه", "tags": [],
                                           "beats": [{"text": "كلمة واحدة"}] * 5}]}, ensure_ascii=False)
    assert build_shorts("موضوع", {"title": "ع", "beats": [{"text": "نص"}]}, _G()) == []
    assert strip_tashkeel("قَالَ") == "قال" and diacritic_ratio("قَالَ") > 0.4
    assert "خمسمائة" in clean_tts("سَنَةَ 539") and "َ" in clean_tts("سَنَةَ 539")
    ns = _norm_shot({"scene": "x", "bg": "bad", "props": [{"name": "nope"}, {"name": "pyramid", "pos": "bad"}],
                     "actors": [{"role": "king", "action": "zzz"}], "camera": "q", "sfx": "z", "callout": "قَالَ 25"},
                    {"i": 0, "plain": "ن"}, {"setting": "ruins", "expression": "happy"}, 0)
    assert ns["scene"] == "scene" and len(ns["props"]) == 1 and ns["props"][0]["pos"] == "center"
    assert ns["actors"][0]["action"] == "idle" and ns["sfx"] == "none" and ns["callout"] == "قال 25" and ns["bg"] == "ruins"
    fake_m = {"fps": 24, "totalFrames": 300, "totalSec": 12.5, "sentences": [
        {"plain": "أ", "start_sec": 1.0}, {"plain": "ب", "start_sec": 4.0}, {"plain": "ج", "start_sec": 8.0}]}
    sf = shots_to_frames([ns, ns, ns], fake_m)
    assert sf[0]["from"] == 0 and sf[1]["from"] == 96 and sf[-1]["to"] == 300 and sf[0]["to"] == sf[1]["from"]
    assert len(sfx_sound("pop")) > 100 and np.isfinite(sfx_track(sf, fake_m)).all()
    for bad in ("hello", "", "رد بلا JSON"):
        try:
            extract_json(bad)
            raise AssertionError("لازم يفشل")
        except ValueError:
            pass
    assert extract_json('{"beats": [{"text": "a"}, {"text": "b"}, {"text": "c')["beats"][-1] == {"text": "b"}   # رد مقطوع
    assert extract_json('نص قبل {"a": 1} نص بعد') == {"a": 1} and extract_json("```json\n{\"a\": 2}\n```") == {"a": 2}
    bs = [{"text": "قال", "plain": "قال"}, {"text": "كتب", "plain": "كتب"}]
    assert diacritize_beats(bs, FakeGemini()) == 2 and diacritic_ratio(bs[0]["text"]) > 0.3 and strip_tashkeel(bs[0]["text"]) == "قال"
    fb = [_fallback_raw({"plain": t}, {}, i, "doodle") for i, t in enumerate(
        ["كانت العنكبوت تنتظر؟", "وفي المختبر قاسوا الوقت", "ثم شربت الماء", "العنكبوت لا تأكل", "الطاقة قليلة", "وهكذا انتهت التجربة"])]
    assert len({(x["scene"], x.get("bg"), x.get("emoji")) for x in fb}) >= 4, "المشاهد الاحتياطية متشابهة"
    assert fb[0]["scene"] == "closeup" and fb[0]["emoji"] == "🕷️" and fb[0]["question"] is True
    fh = _fallback_raw({"plain": "بنوا الهرم الكبير"}, {}, 1, "history")
    assert fh["props"][0]["name"] == "pyramid" and fh["actors"][0]["role"] == "narrator"
    print("selftest OK")
    return 0



# ============ مشروع الفيديو (Remotion): مدموج داخل هذا الملف، ما تحتاج ملفات ثانية ============
VIDEO_PACKAGE_JSON = r'''{
  "name": "awabid-video",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@remotion/cli": "4.0.200",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "remotion": "4.0.200"
  }
}
'''

VIDEO_INDEX_TSX = r'''import React from 'react';
import {
  AbsoluteFill, Audio, CalculateMetadataFunction, Composition, Img, Still,
  interpolate, registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';

const FONT = "'Noto Kufi Arabic','Noto Sans Arabic','Noto Naskh Arabic','Cairo','Tajawal',sans-serif";
// ============ أنواع ============
export type Beat = {
  from: number;
  to: number;
  text: string;
  mood: string;
  gesture: 'none' | 'open' | 'point' | 'raise';
  setting: 'cave' | 'desert' | 'ruins' | 'hills' | 'sea' | 'room';
  expression: 'neutral' | 'happy' | 'surprised' | 'sad';
};

export type Props = {
  fps: number;
  totalFrames: number;
  beats: Beat[];
  envelope: number[];
  showCaptions: boolean;
  title: string;
  thumbText: string;
  thumbSetting: string;
  narratorStyle: string;
  logoWidth: number;
  logoOpacity: number;
  audio: string | null;
  shots?: Shot[];
  style?: string;
  thumbEmoji?: string;
};

export type ShortProps = {
  shots?: Shot[];
  style?: string;
  fps: number;
  totalFrames: number;
  beats: Beat[];
  envelope: number[];
  hookText: string;
  endText: string;
  narratorStyle: string;
  logoWidth: number;
  logoOpacity: number;
  audio: string | null;
};

// ============ الشخصية (Rig) ============

// ====== الـ Rig: الشخصية مكتوبة مرة وحدة، وكل فريم نفس الدالة ترسمها ======
export type Mood = 'neutral' | 'happy' | 'surprised' | 'sad';
export type Pose = {
  headAngle: number; // درجات
  armL: number;      // زاوية اليد اليسار
  armR: number;      // زاوية اليد اليمين
  bob: number;       // حركة الجسم فوق/تحت
  mouth: number;     // 0 مقفل .. 1 مفتوح
  blink: number;     // 0 عين مفتوحة .. 1 مغمضة
  brow: number;      // -1 حزين .. 1 مستغرب
  mood: Mood;
};

type CharProps = {pose: Pose; x?: number; y?: number; scale?: number; skin?: string; robe?: string; turban?: string};

export const Character: React.FC<CharProps> = ({
  pose, x = 0, y = 0, scale = 1, skin = '#e0ac82', robe = '#f2efe6', turban = '#b3202a',
}) => {
  const {headAngle, armL, armR, bob, mouth, blink, brow, mood} = pose;
  const eyeH = 14 * (1 - blink) + 1.5;
  const mouthPath =
    mood === 'sad'
      ? `M -22 ${58} Q 0 ${48 - mouth * 10} 22 ${58}`
      : `M -22 ${50} Q 0 ${50 + 12 + mouth * 26} 22 ${50}`;

  const Arm: React.FC<{angle: number; side: 1 | -1}> = ({angle, side}) => (
    <g transform={`translate(${side * 78} 190) rotate(${angle})`}>
      <rect x={-16} y={0} width={32} height={120} rx={16} fill={robe} stroke="#cfc9b8" strokeWidth={3} />
      <circle cx={0} cy={128} r={19} fill={skin} />
    </g>
  );

  return (
    <g transform={`translate(${x} ${y + bob}) scale(${scale})`}>
      {/* ظل */}
      <ellipse cx={0} cy={440 - bob} rx={120} ry={16} fill="#000" opacity={0.25} />
      {/* الجسم */}
      <path d="M -95 190 Q -110 330 -100 440 L 100 440 Q 110 330 95 190 Q 0 160 -95 190 Z" fill={robe} stroke="#cfc9b8" strokeWidth={3} />
      <path d="M -10 200 L -10 440 M 10 200 L 10 440" stroke="#d9d3c1" strokeWidth={2} />
      <rect x={-95} y={300} width={190} height={14} fill="#7a5a2b" />
      <Arm angle={armL} side={-1} />
      <Arm angle={armR} side={1} />
      {/* الرقبة */}
      <rect x={-22} y={140} width={44} height={60} fill={skin} />
      {/* الرأس (يدور من الرقبة) */}
      <g transform={`translate(0 150) rotate(${headAngle}) translate(0 -150)`}>
        <ellipse cx={0} cy={70} rx={78} ry={88} fill={skin} />
        {/* العمامة */}
        <path d="M -82 55 Q -85 -40 0 -45 Q 85 -40 82 55 Q 40 20 0 22 Q -40 20 -82 55 Z" fill={turban} />
        <path d="M -70 30 Q 0 -5 70 30" stroke="#8d1820" strokeWidth={4} fill="none" />
        {/* الحواجب */}
        <path d={`M -48 ${28 - brow * 6} Q -30 ${20 - brow * 8} -14 ${30 - brow * 4}`} stroke="#2b1b10" strokeWidth={7} strokeLinecap="round" fill="none" />
        <path d={`M 48 ${28 - brow * 6} Q 30 ${20 - brow * 8} 14 ${30 - brow * 4}`} stroke="#2b1b10" strokeWidth={7} strokeLinecap="round" fill="none" />
        {/* العيون */}
        <ellipse cx={-31} cy={52} rx={11} ry={eyeH} fill="#fff" />
        <ellipse cx={31} cy={52} rx={11} ry={eyeH} fill="#fff" />
        {blink < 0.6 && (<>
          <circle cx={-31} cy={52} r={5.5} fill="#2b1b10" />
          <circle cx={31} cy={52} r={5.5} fill="#2b1b10" />
        </>)}
        {/* الأنف */}
        <path d="M 0 60 Q -8 78 2 82" stroke="#b9855e" strokeWidth={4} fill="none" strokeLinecap="round" />
        {/* اللحية */}
        <path d="M -62 85 Q -50 175 0 178 Q 50 175 62 85 Q 40 108 0 104 Q -40 108 -62 85 Z" fill="#2b1b10" />
        {/* الفم */}
        <g transform="translate(0 100)">
          <path d={mouthPath} fill={mouth > 0.15 ? '#5a1010' : 'none'} stroke="#e9d9c5" strokeWidth={4} strokeLinecap="round" />
        </g>
      </g>
    </g>
  );
};

// ============ الخلفيات ============

// غرفة ليلية بإضاءة لمبة ونافذة: كلها كود
export const Room: React.FC<{tight?: boolean}> = ({tight}) => {
  const f = useCurrentFrame();
  const flicker = 0.85 + Math.sin(f * 0.37) * 0.06 + Math.sin(f * 1.13) * 0.04;
  const lampX = tight ? 1160 : 1500;
  const lampY = 380;
  return (
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <defs>
        <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2a2233" />
          <stop offset="1" stopColor="#3b2f3f" />
        </linearGradient>
        <radialGradient id="lampGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#ffd37a" stopOpacity={0.75} />
          <stop offset="0.5" stopColor="#ffb347" stopOpacity={0.25} />
          <stop offset="1" stopColor="#ffb347" stopOpacity={0} />
        </radialGradient>
        <radialGradient id="moonGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#bcd4ff" stopOpacity={0.35} />
          <stop offset="1" stopColor="#bcd4ff" stopOpacity={0} />
        </radialGradient>
      </defs>
      <rect width={1920} height={1080} fill="url(#wall)" />
      <rect y={820} width={1920} height={260} fill="#2a1d17" />
      <rect y={820} width={1920} height={6} fill="#1b110d" />
      <ellipse cx={960} cy={960} rx={560} ry={80} fill="#6b2230" opacity={0.9} />
      <g transform="translate(180 170)">
        <rect width={320} height={420} rx={160} fill="#0b1330" stroke="#6e5a40" strokeWidth={14} />
        <circle cx={220} cy={140} r={38} fill="#f4f1de" />
        <circle cx={236} cy={130} r={34} fill="#0b1330" />
        {[[70, 90], [120, 200], [240, 260], [90, 320]].map(([sx, sy], i) => (
          <circle key={i} cx={sx} cy={sy} r={2.5 + (i % 2)} fill="#fff" opacity={0.6 + 0.4 * Math.sin(f * 0.1 + i)} />
        ))}
        <line x1={160} y1={0} x2={160} y2={420} stroke="#6e5a40" strokeWidth={8} />
        <line x1={0} y1={210} x2={320} y2={210} stroke="#6e5a40" strokeWidth={8} />
      </g>
      <circle cx={340} cy={380} r={420} fill="url(#moonGlow)" />
      <g transform={tight ? 'translate(-340 0)' : undefined}>
        <rect x={1380} y={640} width={240} height={20} rx={6} fill="#5a3d26" />
        <rect x={1490} y={660} width={20} height={170} fill="#4a301d" />
        <rect x={1488} y={560} width={24} height={80} fill="#3a3a3a" />
        <path d="M 1450 560 L 1550 560 L 1530 470 L 1470 470 Z" fill="#c98b2b" />
      </g>
      <circle cx={lampX} cy={lampY + 130} r={16} fill="#fff3c4" opacity={flicker} />
      <circle cx={lampX} cy={lampY + 130} r={620 * flicker} fill="url(#lampGlow)" style={{mixBlendMode: 'screen'}} />
    </svg>
  );
};


const Column: React.FC<{x: number; h: number; broken?: boolean}> = ({x, h, broken}) => {
  const top = 880 - h;
  return (
    <g>
      <rect x={x - 46} y={top} width={92} height={h} fill="#e6c79a" />
      <rect x={x + 14} y={top} width={32} height={h} fill="#c9a674" />
      {[0.2, 0.45, 0.7].map((k, i) => (
        <rect key={i} x={x - 46} y={top + h * k} width={92} height={5} fill="#b58f5e" opacity={0.6} />
      ))}
      {broken ? (
        <path d={`M ${x - 46} ${top} L ${x - 20} ${top - 30} L ${x} ${top - 6} L ${x + 24} ${top - 40} L ${x + 46} ${top} Z`} fill="#e6c79a" />
      ) : (
        <>
          <rect x={x - 62} y={top - 22} width={124} height={22} fill="#f0d6ab" />
          <rect x={x - 54} y={top - 38} width={108} height={16} fill="#e6c79a" />
        </>
      )}
      <rect x={x - 70} y={876} width={140} height={14} fill="#c9a674" />
    </g>
  );
};

// صحراء وغروب وأطلال: كلها كود
export const Desert: React.FC<{ruins?: boolean; tight?: boolean}> = ({ruins, tight}) => {
  const f = useCurrentFrame();
  const glow = 1 + Math.sin(f * 0.03) * 0.04;
  const sway1 = Math.sin(f * 0.012) * 14;
  const sway2 = Math.sin(f * 0.009 + 1) * 24;
  return (
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#16365a" />
          <stop offset="0.5" stopColor="#c8694a" />
          <stop offset="0.85" stopColor="#f3b46b" />
          <stop offset="1" stopColor="#f6c98a" />
        </linearGradient>
        <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#ffe2a0" stopOpacity={0.9} />
          <stop offset="0.4" stopColor="#ffb86b" stopOpacity={0.35} />
          <stop offset="1" stopColor="#ffb86b" stopOpacity={0} />
        </radialGradient>
      </defs>
      <rect width={1920} height={1080} fill="url(#sky)" />
      {[[200, 90], [420, 160], [700, 70], [980, 130], [1250, 60], [1560, 150], [1780, 80], [90, 230], [1100, 230]].map(([sx, sy], i) => (
        <circle key={i} cx={sx} cy={sy} r={2 + (i % 2)} fill="#fff" opacity={0.35 + 0.3 * Math.sin(f * 0.08 + i)} />
      ))}
      <circle cx={tight ? 1150 : 1380} cy={600} r={380 * glow} fill="url(#sunGlow)" />
      <circle cx={tight ? 1150 : 1380} cy={600} r={100} fill="#fff0c2" />
      <g transform={`translate(${sway2} 0)`}>
        <path d="M -200 760 Q 200 640 620 740 T 1420 700 T 2200 760 L 2200 1080 L -200 1080 Z" fill="#b8704a" />
      </g>
      {ruins && (
        tight ? (
          <g>
            <Column x={720} h={290} />
            <Column x={1210} h={210} broken />
          </g>
        ) : (
          <g>
            <Column x={250} h={300} />
            <Column x={470} h={190} broken />
            <Column x={1650} h={340} />
          </g>
        )
      )}
      <g transform={`translate(${sway1} 0)`}>
        <path d="M -200 840 Q 300 760 800 830 T 1700 810 T 2200 850 L 2200 1080 L -200 1080 Z" fill="#d79a62" />
      </g>
      <path d="M 0 890 Q 480 850 960 888 T 1920 870 L 1920 1080 L 0 1080 Z" fill="#e8b97a" />
    </svg>
  );
};


// كهف ونار ورسومات جدارية: كلها كود
export const Cave: React.FC<{tight?: boolean}> = ({tight}) => {
  const f = useCurrentFrame();
  const fl = 0.85 + Math.sin(f * 0.31) * 0.07 + Math.sin(f * 0.97) * 0.05;
  const h = 150 * fl;
  const fx = tight ? 1190 : 1520;
  const fy = 880;
  const Hand: React.FC<{x: number; y: number; r?: number}> = ({x, y, r = 0}) => (
    <g transform={`translate(${x} ${y}) rotate(${r})`} fill="#a63d2a" opacity={0.75}>
      <ellipse cx={0} cy={0} rx={26} ry={30} />
      {[-22, -11, 0, 11, 22].map((dx, i) => (
        <rect key={i} x={dx - 4} y={-62 + Math.abs(dx) * 0.7} width={8} height={38} rx={4} />
      ))}
    </g>
  );
  return (
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <defs>
        <radialGradient id="fireGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#ffb347" stopOpacity={0.8} />
          <stop offset="0.5" stopColor="#d9622b" stopOpacity={0.3} />
          <stop offset="1" stopColor="#d9622b" stopOpacity={0} />
        </radialGradient>
        <linearGradient id="rock" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#120d0a" />
          <stop offset="1" stopColor="#3a2a20" />
        </linearGradient>
      </defs>
      <rect width={1920} height={1080} fill="url(#rock)" />
      <path d="M0 0 H1920 V120 L1800 220 L1700 130 L1560 260 L1430 140 L1250 230 L1100 120 L930 250 L780 130 L600 240 L430 120 L260 230 L120 130 L0 210 Z" fill="#0b0806" />
      <Hand x={tight ? 705 : 330} y={420} r={-8} />
      <Hand x={tight ? 745 : 430} y={500} r={10} />
      <Hand x={tight ? 690 : 250} y={590} r={-15} />
      <g transform={tight ? 'translate(1100 340) scale(0.55)' : 'translate(560 360)'} fill="#7a2f20" opacity={0.7}>
        <ellipse cx={120} cy={60} rx={120} ry={52} />
        <circle cx={-10} cy={50} r={36} />
        <path d="M-30 20 L-60 -10 L-35 35 Z M-5 15 L-5 -22 L12 22 Z" />
        {[30, 70, 160, 200].map((x, i) => <rect key={i} x={x} y={90} width={14} height={70} rx={6} />)}
      </g>
      <rect y={880} width={1920} height={200} fill="#2a1d15" />
      <circle cx={fx} cy={fy - 40} r={520 * fl} fill="url(#fireGlow)" style={{mixBlendMode: 'screen'}} />
      <rect x={fx - 90} y={fy - 14} width={180} height={26} rx={13} fill="#4a2f1b" transform={`rotate(-8 ${fx} ${fy})`} />
      <rect x={fx - 90} y={fy - 14} width={180} height={26} rx={13} fill="#3a2414" transform={`rotate(8 ${fx} ${fy})`} />
      <path d={`M ${fx - 60} ${fy - 6} Q ${fx - 40} ${fy - h * 0.8} ${fx - 10} ${fy - h} Q ${fx + 10} ${fy - h * 0.6} ${fx + 60} ${fy - 6} Z`} fill="#ff8c1a" />
      <path d={`M ${fx - 32} ${fy - 6} Q ${fx - 15} ${fy - h * 0.55} ${fx} ${fy - h * 0.7} Q ${fx + 18} ${fy - h * 0.4} ${fx + 34} ${fy - 6} Z`} fill="#ffd25a" />
    </svg>
  );
};

// تلال وجبال ونهر: صين/يابان/هند/أوروبا، كلها كود
export const Hills: React.FC<{tight?: boolean}> = ({tight}) => {
  const f = useCurrentFrame();
  const c1 = ((f * 0.25) % 2400) - 400;
  const c2 = ((f * 0.18 + 1100) % 2400) - 400;
  return (
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <defs>
        <linearGradient id="hSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4f8fc4" />
          <stop offset="0.6" stopColor="#bfe0f2" />
          <stop offset="1" stopColor="#f7e2b0" />
        </linearGradient>
        <radialGradient id="hSun" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#fff6c2" stopOpacity={0.9} />
          <stop offset="1" stopColor="#fff6c2" stopOpacity={0} />
        </radialGradient>
      </defs>
      <rect width={1920} height={1080} fill="url(#hSky)" />
      <circle cx={tight ? 1150 : 1500} cy={260} r={260} fill="url(#hSun)" />
      <circle cx={tight ? 1150 : 1500} cy={260} r={64} fill="#fffbe0" />
      {[c1, c2].map((cx, i) => (
        <g key={i} opacity={0.9} transform={`translate(${cx} ${150 + i * 90})`}>
          <ellipse cx={0} cy={0} rx={150} ry={34} fill="#fff" />
          <ellipse cx={-70} cy={-18} rx={80} ry={30} fill="#fff" />
          <ellipse cx={60} cy={-22} rx={90} ry={32} fill="#fff" />
        </g>
      ))}
      <path d="M -100 720 L 300 340 L 540 540 L 860 290 L 1200 560 L 1520 390 L 2000 720 Z" fill="#6c7fa0" />
      {[[300, 340], [860, 290], [1520, 390]].map(([x, y], i) => (
        <path key={i} d={`M ${x} ${y} L ${x - 70} ${y + 95} L ${x - 20} ${y + 78} L ${x + 10} ${y + 105} L ${x + 70} ${y + 92} Z`} fill="#f4f7fb" />
      ))}
      <path d="M -100 800 Q 300 660 700 760 T 1500 730 T 2100 790 L 2100 1080 L -100 1080 Z" fill="#5b9a52" />
      <path d="M 760 760 Q 900 820 820 880 T 880 1080 L 1120 1080 Q 1060 920 1130 860 T 1000 760 Z" fill="#4aa3c7" opacity={0.9} />
      <path d="M -100 860 Q 400 790 960 850 T 2100 840 L 2100 1080 L -100 1080 Z" fill="#3f7f3d" />
      <path d="M 0 900 Q 480 870 960 898 T 1920 886 L 1920 1080 L 0 1080 Z" fill="#6a9b3d" />
    </svg>
  );
};

// بحر وسفينة وغروب: كلها كود
export const Sea: React.FC<{tight?: boolean}> = ({tight}) => {
  const f = useCurrentFrame();
  const shipX = 200 + ((f * 0.35) % 1500);
  return (
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <defs>
        <linearGradient id="sSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1a3a66" />
          <stop offset="0.55" stopColor="#e07a5f" />
          <stop offset="1" stopColor="#f6c177" />
        </linearGradient>
        <linearGradient id="sSea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2a6f97" />
          <stop offset="1" stopColor="#0b2f4a" />
        </linearGradient>
      </defs>
      <rect width={1920} height={1080} fill="url(#sSky)" />
      <circle cx={tight ? 1120 : 1350} cy={560} r={110} fill="#fff0c2" />
      <rect y={620} width={1920} height={460} fill="url(#sSea)" />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={(tight ? 1120 : 1350) - 130 + i * 8} y={630 + i * 34} width={260 - i * 16} height={7} rx={3} fill="#ffe3a3" opacity={0.55 - i * 0.08} />
      ))}
      {[0, 1, 2, 3, 4, 5, 6].map((i) => (
        <path key={i} d={`M ${-200 + ((f * (0.6 + i * 0.08) + i * 300) % 2200)} ${680 + i * 38} q 60 -16 120 0 t 120 0`}
          stroke="#cfe8f5" strokeWidth={3} fill="none" opacity={0.35} />
      ))}
      <g transform={`translate(${shipX} ${610 + Math.sin(f * 0.05) * 4}) scale(0.9)`}>
        <path d="M -70 0 L 70 0 L 50 30 L -50 30 Z" fill="#3a2414" />
        <rect x={-3} y={-110} width={6} height={110} fill="#2a1a0e" />
        <path d="M 6 -105 L 62 -20 L 6 -20 Z" fill="#f4ecd8" />
        <path d="M -6 -95 L -48 -20 L -6 -20 Z" fill="#e8dcc0" />
      </g>
      <path d="M 0 900 Q 480 860 960 898 T 1920 880 L 1920 1080 L 0 1080 Z" fill="#d8b98a" />
    </svg>
  );
};

// ============ المشهد والصورة المصغرة ============

const PALETTES: Record<string, {robe: string; turban: string; skin: string}> = {
  tribal: {robe: '#8b5e3c', turban: '#2e2118', skin: '#c98f64'},
  arab: {robe: '#f2efe6', turban: '#b3202a', skin: '#e0ac82'},
  roman: {robe: '#efe7d4', turban: '#3a2a1e', skin: '#e3b48a'},
  east: {robe: '#2c4a7a', turban: '#1b1b1b', skin: '#e8c39e'},
  neutral: {robe: '#d9d2c0', turban: '#4a3b2c', skin: '#dba87d'},
};

const GESTURES = {
  none: {L: 4, R: -4},
  open: {L: 35, R: -35},
  point: {L: 4, R: -110},
  raise: {L: 150, R: -150},
} as const;

export const Backdrop: React.FC<{setting: string; tight?: boolean}> = ({setting, tight}) => {
  if (setting === 'room') return <Room tight={tight} />;
  if (setting === 'cave') return <Cave tight={tight} />;
  if (setting === 'hills') return <Hills tight={tight} />;
  if (setting === 'sea') return <Sea tight={tight} />;
  return <Desert ruins={setting === 'ruins'} tight={tight} />;
};

export const Scene: React.FC<Props> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const {beats, envelope} = props;
  const pal = PALETTES[props.narratorStyle] ?? PALETTES.arab;

  let bi = 0;
  for (let i = 0; i < beats.length; i++) {
    if (frame >= beats[i].from) bi = i;
  }
  const beat = beats[bi];
  const prev = beats[Math.max(0, bi - 1)];
  const since = frame - beat.from;
  const t = spring({frame: since, fps, config: {damping: 14, stiffness: 90}});
  const g = GESTURES[beat.gesture] ?? GESTURES.none;
  const pg = GESTURES[prev.gesture] ?? GESTURES.none;

  const e = envelope[frame] ?? 0;
  const mouth = Math.min(1, e * 1.25);
  const blink = interpolate(frame % 95, [0, 3, 6], [0, 1, 0], {extrapolateRight: 'clamp'});
  const mood = beat.expression as Mood;

  const pose: Pose = {
    headAngle: Math.sin(frame / 22) * 3 + (mood === 'sad' ? 7 : 0) + e * Math.sin(frame * 0.35) * 2.2,
    armL: interpolate(t, [0, 1], [pg.L, g.L]) + Math.sin(frame / 18) * 2 + e * 3,
    armR: interpolate(t, [0, 1], [pg.R, g.R]) + Math.sin(frame / 18 + 1) * 2 - e * 3,
    bob: Math.sin(frame / 25) * 5,
    mouth,
    blink,
    brow: mood === 'surprised' ? 1 : mood === 'sad' ? -1 : mood === 'happy' ? 0.3 : 0,
    mood,
  };

  const len = Math.max(1, beat.to - beat.from);
  const zoom = interpolate(since, [0, len], [1, 1.05], {extrapolateRight: 'clamp'});
  const fadeBg = interpolate(since, [0, 14], [0, 1], {extrapolateRight: 'clamp'});
  const showPrev = bi > 0 && prev.setting !== beat.setting && fadeBg < 1;
  const fadeIn = interpolate(frame, [0, 18], [1, 0], {extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 36, durationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${zoom})`, transformOrigin: '50% 62%'}}>
        {showPrev && <Backdrop setting={prev.setting} />}
        <div style={{position: 'absolute', inset: 0, opacity: showPrev ? fadeBg : 1}}>
          <Backdrop setting={beat.setting} />
        </div>
        <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
          <Character pose={pose} x={960} y={310} scale={1.3} robe={pal.robe} turban={pal.turban} skin={pal.skin} />
        </svg>
      </div>

      {props.showCaptions && (
        <div style={{position: 'absolute', bottom: 34, left: 150, right: 150, textAlign: 'center', direction: 'rtl',
          color: '#fff', fontSize: 34, fontFamily: FONT, fontWeight: 700, textShadow: '0 2px 10px #000'}}>
          {beat.text}
        </div>
      )}

      {/* الشعار: يسار تحت، صغير، شفافية 70% */}
      <LogoMark size={props.logoWidth * 1.5} opacity={props.logoOpacity} style={{position: 'absolute', left: 24, top: 24}} />

      <AbsoluteFill style={{background: '#000', opacity: Math.max(fadeIn, fadeOut), pointerEvents: 'none'}} />
      {props.audio && <Audio src={staticFile(props.audio)} />}
    </AbsoluteFill>
  );
};

const THUMB_POSE: Pose = {headAngle: -4, armL: 150, armR: -35, bob: 0, mouth: 0.6, blink: 0, brow: 1, mood: 'surprised'};

// ============ الشورت (فيديو رأسي 720x1280): خطاف أول 3 ثواني + ترجمة كبيرة + بطاقة نهاية توجه للفيديو الطويل ============
const ShortClassic: React.FC<ShortProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const {beats, envelope} = props;
  const pal = PALETTES[props.narratorStyle] ?? PALETTES.arab;

  let bi = 0;
  for (let i = 0; i < beats.length; i++) {
    if (frame >= beats[i].from) bi = i;
  }
  const beat = beats[bi];
  const prev = beats[Math.max(0, bi - 1)];
  const since = frame - beat.from;
  const t = spring({frame: since, fps, config: {damping: 14, stiffness: 90}});
  const g = GESTURES[beat.gesture] ?? GESTURES.none;
  const pg = GESTURES[prev.gesture] ?? GESTURES.none;
  const e = envelope[frame] ?? 0;
  const mood = beat.expression as Mood;
  const pose: Pose = {
    headAngle: Math.sin(frame / 22) * 3 + (mood === 'sad' ? 7 : 0) + e * Math.sin(frame * 0.35) * 2.2,
    armL: interpolate(t, [0, 1], [pg.L, g.L]) + Math.sin(frame / 18) * 2 + e * 3,
    armR: interpolate(t, [0, 1], [pg.R, g.R]) + Math.sin(frame / 18 + 1) * 2 - e * 3,
    bob: Math.sin(frame / 25) * 5,
    mouth: Math.min(1, e * 1.25),
    blink: interpolate(frame % 95, [0, 3, 6], [0, 1, 0], {extrapolateRight: 'clamp'}),
    brow: mood === 'surprised' ? 1 : mood === 'sad' ? -1 : mood === 'happy' ? 0.3 : 0,
    mood,
  };

  const S = 1.3;                                   // تكبير المشهد العريض ليملأ الشاشة الرأسية
  const left = (720 - 1920 * S) / 2;
  const top = -(1080 * S - 1280) / 2;
  const hookOpacity = interpolate(frame, [0, 8, 62, 76], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const endStart = durationInFrames - Math.round(fps * 3.6);
  const endOpacity = interpolate(frame, [endStart, endStart + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pulse = 1 + Math.sin(frame * 0.3) * 0.04;
  const fadeIn = interpolate(frame, [0, 6], [1, 0], {extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 12, durationInFrames - 1], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const stroke = {WebkitTextStroke: '9px #140a14', paintOrder: 'stroke fill'} as const;

  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left, top, width: 1920, height: 1080, transform: `scale(${S})`, transformOrigin: '0 0'}}>
        <Backdrop setting={beat.setting} tight />
        <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
          <Character pose={pose} x={960} y={310} scale={1.3} robe={pal.robe} turban={pal.turban} skin={pal.skin} />
        </svg>
      </div>

      <div style={{position: 'absolute', top: 150, left: 30, right: 30, textAlign: 'center', direction: 'rtl',
        fontFamily: FONT, fontWeight: 900, fontSize: 88, lineHeight: 1.2, color: '#ffd23f', opacity: hookOpacity,
        textShadow: '0 8px 24px rgba(0,0,0,0.7)', ...stroke}}>
        {props.hookText}
      </div>

      <div style={{position: 'absolute', bottom: 270, left: 36, right: 36, textAlign: 'center', direction: 'rtl',
        fontFamily: FONT, fontWeight: 800, fontSize: 52, lineHeight: 1.4, color: '#ffffff',
        textShadow: '0 4px 14px rgba(0,0,0,0.8)', ...stroke, WebkitTextStroke: '8px #140a14'}}>
        {beat.text}
      </div>

      <div style={{position: 'absolute', top: 120, left: 50, right: 50, textAlign: 'center', direction: 'rtl',
        opacity: endOpacity, transform: `scale(${pulse})`}}>
        <div style={{display: 'inline-block', background: '#e11d2e', color: '#fff', fontFamily: FONT, fontWeight: 900,
          fontSize: 64, lineHeight: 1.3, padding: '26px 44px', borderRadius: 28, border: '6px solid #fff',
          boxShadow: '0 10px 40px rgba(0,0,0,0.6)'}}>
          {props.endText}
        </div>
      </div>

      <LogoMark size={props.logoWidth * 1.5} opacity={props.logoOpacity} style={{position: 'absolute', left: 24, top: 24}} />
      <AbsoluteFill style={{background: '#000', opacity: Math.max(fadeIn, fadeOut), pointerEvents: 'none'}} />
      {props.audio && <Audio src={staticFile(props.audio)} />}
    </AbsoluteFill>
  );
};

// ============ محرك الشرح v2: شخصيات عصا + مجسمات + كاميرا + انتقالات + خرائط وأرقام ============
// =====================================================================
// ===== المحرك الجديد: كل شيء مرسوم بالكود، ويشتغل أفقي وعمودي =====
// =====================================================================
const OL = '#16161d';
const INK = OL;
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const easeInOut = (x: number) => { const t = clamp01(x); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const easeBack = (x: number) => {
  const t = clamp01(x);
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
const rad = (d: number) => (d * Math.PI) / 180;

type World = {W: number; H: number; v: boolean};
const WorldCtx = React.createContext<World>({W: 1920, H: 1080, v: false});
const useWorld = () => React.useContext(WorldCtx);
const groundY = (w: World) => w.H * (w.v ? 0.72 : 0.78);
const POSF_L: Record<string, number> = {far_left: 0.12, left: 0.28, center: 0.5, right: 0.72, far_right: 0.88};
const POSF_V: Record<string, number> = {far_left: 0.2, left: 0.27, center: 0.5, right: 0.73, far_right: 0.8};
const posX = (w: World, pos: string) => w.W * ((w.v ? POSF_V : POSF_L)[pos] ?? 0.5);

const ABS: React.CSSProperties = {position: 'absolute', inset: 0, width: '100%', height: '100%'};
const INKT: React.CSSProperties = {fontFamily: FONT, fontWeight: 900, color: INK, direction: 'rtl', textAlign: 'center', lineHeight: 1.2};
const K = {stroke: OL, strokeWidth: 6, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const};

// ============ الشعار (مرسوم بالكود، حاد على أي حجم) ============
const LogoMark: React.FC<{size: number; opacity?: number; withText?: boolean; uid?: string; style?: React.CSSProperties}> = (
  {size, opacity = 1, withText = false, uid = 'lg', style},
) => {
  const h = withText ? size * 1.28 : size;
  return (
    <svg width={size} height={h} viewBox={withText ? '0 0 200 256' : '0 0 200 200'} style={{opacity, ...style}}>
      <defs>
        <linearGradient id={uid + 'g'} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ffe9a3" /><stop offset="0.5" stopColor="#f2b830" /><stop offset="1" stopColor="#a8650c" />
        </linearGradient>
        <radialGradient id={uid + 'b'} cx="0.5" cy="0.35" r="0.8">
          <stop offset="0" stopColor="#2c4a8a" /><stop offset="1" stopColor="#0b1430" />
        </radialGradient>
        <linearGradient id={uid + 's'} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffd77a" /><stop offset="1" stopColor="#e08a2c" />
        </linearGradient>
        <clipPath id={uid + 'c'}><circle cx="100" cy="100" r="82" /></clipPath>
      </defs>
      <circle cx="100" cy="100" r="97" fill={'url(#' + uid + 'g)'} />
      <circle cx="100" cy="100" r="89" fill="#0b1430" />
      <circle cx="100" cy="100" r="84" fill={'url(#' + uid + 'b)'} />
      <g clipPath={'url(#' + uid + 'c)'}>
        {Array.from({length: 14}).map((_, i) => (
          <path key={i} d="M100 96 L100 8" stroke="#ffd77a" strokeWidth={3} opacity={0.22} transform={'rotate(' + (i * 360 / 14) + ' 100 96)'} />
        ))}
        <circle cx="100" cy="92" r="40" fill="#ffcf5a" opacity={0.25} />
        <circle cx="100" cy="92" r="30" fill={'url(#' + uid + 'g)'} />
        <path d="M18 150 L74 92 L112 132 L130 114 L182 160 L182 190 L18 190 Z" fill="#17254f" opacity={0.9} />
        <path d="M38 150 L100 64 L162 150 Z" fill="#f6e3b4" />
        <path d="M100 64 L162 150 L110 150 Z" fill="#d7b46a" />
        <path d="M70 108 L130 108 M54 129 L146 129" stroke="#a8803a" strokeWidth={3} opacity={0.8} />
        <path d="M0 152 Q50 138 100 152 T200 150 L200 200 L0 200 Z" fill="#e0a64a" />
        <path d="M0 166 Q60 152 110 168 T200 164 L200 200 L0 200 Z" fill="#c4842c" />
        <circle cx="30" cy="40" r="2.4" fill="#fff" opacity={0.9} /><circle cx="168" cy="52" r="2" fill="#fff" opacity={0.8} />
        <circle cx="52" cy="66" r="1.6" fill="#fff" opacity={0.7} />
      </g>
      <path d="M100 100 m-84 0 a84 84 0 0 1 168 0" fill="none" stroke="#fff" strokeWidth={2} opacity={0.18} />
      {withText && (
        <g>
          <rect x="22" y="204" width="156" height="44" rx="22" fill={'url(#' + uid + 'g)'} stroke="#0b1430" strokeWidth={4} />
          <text x="100" y="236" textAnchor="middle" fontSize="32" fontWeight={900} fill="#0b1430" style={{fontFamily: FONT}}>أوابد</text>
        </g>
      )}
    </svg>
  );
};

// ============ خلفيات مرسومة بالكود (مرنة: تتكيف مع أفقي/عمودي) ============
const wavePath = (W: number, y: number, amp: number, len: number, ph: number, bottom: number) => {
  let d = 'M0 ' + bottom + ' L0 ' + (y + Math.sin(ph) * amp);
  for (let x = 0; x <= W + 20; x += 20) d += ' L' + x + ' ' + (y + Math.sin((x / len) * Math.PI * 2 + ph) * amp);
  return d + ' L' + W + ' ' + bottom + ' Z';
};
const hillPath = (W: number, y: number, a1: number, l1: number, a2: number, l2: number, ph: number, bottom: number) => {
  let d = 'M0 ' + bottom;
  for (let x = 0; x <= W + 20; x += 20) d += ' L' + x + ' ' + (y + Math.sin(x / l1 + ph) * a1 + Math.sin(x / l2 + ph * 1.7) * a2);
  return d + ' L' + W + ' ' + bottom + ' Z';
};
const Grad: React.FC<{id: string; c: string[]; x2?: number; y2?: number}> = ({id, c, x2 = 0, y2 = 1}) => (
  <linearGradient id={id} x1="0" y1="0" x2={x2} y2={y2}>
    {c.map((col, i) => <stop key={i} offset={i / (c.length - 1)} stopColor={col} />)}
  </linearGradient>
);
const CloudBg: React.FC<{x: number; y: number; s: number; o?: number; c?: string}> = ({x, y, s, o = 1, c = '#fff'}) => (
  <g transform={'translate(' + x + ' ' + y + ') scale(' + s + ')'} opacity={o} fill={c}>
    <ellipse cx={0} cy={0} rx={90} ry={34} /><circle cx={-40} cy={-24} r={38} /><circle cx={22} cy={-36} r={46} /><circle cx={66} cy={-10} r={30} />
  </g>
);
const Stars: React.FC<{W: number; H: number; n: number; local: number; seed?: number}> = ({W, H, n, local, seed = 3}) => (
  <g fill="#fff">
    {Array.from({length: n}).map((_, i) => {
      const r1 = Math.abs(Math.sin(i * 12.9898 + seed) * 43758.5453) % 1;
      const r2 = Math.abs(Math.sin(i * 78.233 + seed * 2) * 12345.678) % 1;
      const tw = 0.45 + 0.55 * Math.abs(Math.sin(local * 0.06 + i));
      return <circle key={i} cx={r1 * W} cy={r2 * H} r={1.5 + (i % 3)} opacity={tw} />;
    })}
  </g>
);
const Birds: React.FC<{W: number; y: number; local: number}> = ({W, y, local}) => (
  <g stroke="#2b2b36" strokeWidth={4} fill="none" strokeLinecap="round">
    {[0, 1, 2].map((i) => {
      const x = ((local * 2.2 + i * 230) % (W + 300)) - 150;
      const f = Math.sin(local * 0.5 + i) * 10;
      return <path key={i} d={'M' + (x - 24) + ' ' + (y + i * 40 - f) + ' Q' + x + ' ' + (y + i * 40 - 20) + ' ' + x + ' ' + (y + i * 40) + ' Q' + x + ' ' + (y + i * 40 - 20) + ' ' + (x + 24) + ' ' + (y + i * 40 - f)} />;
    })}
  </g>
);

const Bg: React.FC<{kind: string; local: number}> = ({kind, local}) => {
  const w = useWorld();
  const {W, H, v} = w;
  const gy = groundY(w);
  const t = local / 24;
  const u = (n: number) => (v ? n * 0.62 : n);          // تصغير العناصر الأفقية في العمودي
  const id = 'bg' + kind;
  const sc = H / 1080;
  switch (kind) {
    case 'desert':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#f4a259', '#fbd7a0', '#fdeccc']} /><Grad id={id + 'g'} c={['#e6b06a', '#cf9347']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          <circle cx={W * 0.74} cy={gy * 0.4} r={170 * sc} fill="#fff4cf" opacity={0.35} />
          <circle cx={W * 0.74} cy={gy * 0.4} r={92 * sc} fill="#fff7dc" />
          <path d={hillPath(W, gy - 70 * sc, 18 * sc, 260, 10 * sc, 120, 1 + t * 0.05, gy + 6)} fill="#efc386" />
          <g fill="#e2b27a" opacity={0.85}><path d={'M' + W * 0.1 + ' ' + (gy - 60 * sc) + ' l70 -80 l70 80 z'} /><path d={'M' + (W * 0.1 + 90) + ' ' + (gy - 60 * sc) + ' l44 -52 l44 52 z'} /></g>
          <path d={hillPath(W, gy - 26 * sc, 20 * sc, 340, 8 * sc, 140, 2.4 + t * 0.04, gy + 6)} fill="#e3a95c" />
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
          <path d={hillPath(W, gy + 6, 5, 400, 3, 90, 0.4, gy + 24)} fill="#f1c581" opacity={0.7} />
          {Array.from({length: 9}).map((_, i) => <path key={i} d={'M' + ((i * 311) % W) + ' ' + (gy + 70 + (i * 53) % (H - gy - 90)) + ' q40 -14 90 0'} stroke="#b97d36" strokeWidth={4} fill="none" opacity={0.45} strokeLinecap="round" />)}
          <Birds W={W} y={gy * 0.25} local={local} />
        </svg>
      );
    case 'hills':
    case 'outdoor':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#5fb4ee', '#a9dcf7', '#e4f5ff']} /><Grad id={id + 'g'} c={['#79c257', '#4f9d3d']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          <circle cx={W * 0.82} cy={gy * 0.22} r={70 * sc} fill="#fff6bf" /><circle cx={W * 0.82} cy={gy * 0.22} r={120 * sc} fill="#fff6bf" opacity={0.3} />
          {[0.12, 0.45, 0.78].map((fx, i) => <CloudBg key={i} x={((fx * (W + 400) + local * (0.8 + i * 0.3)) % (W + 400)) - 200} y={gy * (0.18 + i * 0.12)} s={sc * (1.1 - i * 0.15)} o={0.95} />)}
          <path d={hillPath(W, gy - 110 * sc, 34 * sc, 280, 14 * sc, 110, 0.5, gy + 6)} fill="#9ad27a" />
          <path d={hillPath(W, gy - 50 * sc, 26 * sc, 220, 12 * sc, 90, 2.1, gy + 6)} fill="#6dbb55" />
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
          {Array.from({length: 14}).map((_, i) => <g key={i} transform={'translate(' + ((i * 197 + 60) % W) + ' ' + (gy + 40 + (i * 71) % Math.max(40, H - gy - 60)) + ')'} stroke="#2f7d2c" strokeWidth={4} strokeLinecap="round"><path d="M0 0 L-8 -22 M0 0 L0 -28 M0 0 L8 -22" /></g>)}
          <Birds W={W} y={gy * 0.3} local={local} />
        </svg>
      );
    case 'sea':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#ff9e6b', '#ffd6a5', '#fff0d6']} /><Grad id={id + 'w'} c={['#2f9bd6', '#1c6aa8', '#12447c']} /></defs>
          <rect width={W} height={H} fill={'url(#' + id + ')'} />
          <circle cx={W * 0.5} cy={gy - 120 * sc} r={110 * sc} fill="#fff3c8" opacity={0.95} />
          <rect y={gy - 100 * sc} width={W} height={H - gy + 100 * sc} fill={'url(#' + id + 'w)'} />
          <rect x={W * 0.5 - 60} y={gy - 100 * sc} width={120} height={H} fill="#ffe9a8" opacity={0.18} />
          {[0, 1, 2, 3].map((i) => <path key={i} d={wavePath(W, gy - 70 * sc + i * 46 * sc, (10 + i * 4) * sc, 240 + i * 70, t * (1.4 - i * 0.2) + i, H)} fill={['#3aa7e0', '#2989c6', '#1e6fae', '#165a94'][i]} opacity={0.9} />)}
          <rect y={gy + 6} width={W} height={Math.max(30, 56 * sc)} fill="#a8713c" stroke={OL} strokeWidth={5} />
          {Array.from({length: Math.ceil(W / 120)}).map((_, i) => <path key={i} d={'M' + i * 120 + ' ' + (gy + 6) + ' l0 ' + Math.max(30, 56 * sc)} stroke={OL} strokeWidth={4} opacity={0.55} />)}
          <Birds W={W} y={gy * 0.25} local={local} />
        </svg>
      );
    case 'underwater':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#3cc4e8', '#1b85c4', '#0b3f7c']} /></defs>
          <rect width={W} height={H} fill={'url(#' + id + ')'} />
          {[0.2, 0.45, 0.7, 0.9].map((fx, i) => <path key={i} d={'M' + (W * fx - 30) + ' 0 L' + (W * fx + 30) + ' 0 L' + (W * fx + 170) + ' ' + gy + ' L' + (W * fx - 110) + ' ' + gy + ' Z'} fill="#fff" opacity={0.07 + 0.03 * Math.sin(t + i)} />)}
          {Array.from({length: 16}).map((_, i) => {
            const bx = (i * 173 + 90) % W;
            const by = H - ((local * (1.6 + (i % 4) * 0.5) + i * 160) % (H + 100));
            return <circle key={i} cx={bx + Math.sin(local * 0.1 + i) * 10} cy={by} r={6 + (i % 4) * 4} fill="none" stroke="#d9f6ff" strokeWidth={3} opacity={0.75} />;
          })}
          <path d={hillPath(W, gy + 6, 12, 300, 6, 110, 1, H)} fill="#e0c07a" />
          <rect y={gy + 30} width={W} height={H - gy - 30} fill="#d1ac62" />
          {[0.08, 0.3, 0.62, 0.9].map((fx, i) => <g key={i} transform={'translate(' + W * fx + ' ' + (gy + 20) + ')'} stroke="#1f8f5a" strokeWidth={14} strokeLinecap="round" fill="none">{[-18, 0, 18].map((o, j) => <path key={j} d={'M' + o + ' 0 Q' + (o + Math.sin(t * 2 + i + j) * 22) + ' -70 ' + o + ' -' + (110 + j * 24)} />)}</g>)}
        </svg>
      );
    case 'night':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#070b24', '#17265c', '#2c3f86']} /><Grad id={id + 'g'} c={['#1d3b4a', '#102a36']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          <Stars W={W} H={gy} n={v ? 46 : 70} local={local} />
          <circle cx={W * 0.78} cy={gy * 0.25} r={150 * sc} fill="#dfe8ff" opacity={0.1} /><circle cx={W * 0.78} cy={gy * 0.25} r={70 * sc} fill="#f4f1de" />
          <circle cx={W * 0.78 + 22 * sc} cy={gy * 0.25 - 10 * sc} r={60 * sc} fill="#17265c" opacity={0.18} />
          <path d={hillPath(W, gy - 90 * sc, 30 * sc, 300, 12 * sc, 110, 0.9, gy + 6)} fill="#0e1a3c" />
          <path d={hillPath(W, gy - 36 * sc, 22 * sc, 240, 10 * sc, 100, 2, gy + 6)} fill="#13294a" />
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
        </svg>
      );
    case 'space':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#05051a', '#150b3a', '#2a1156']} /><Grad id={id + 'g'} c={['#8b8fa8', '#5d6078']} /></defs>
          <rect width={W} height={H} fill={'url(#' + id + ')'} />
          <circle cx={W * 0.25} cy={gy * 0.3} r={260 * sc} fill="#6a3bd1" opacity={0.18} /><circle cx={W * 0.8} cy={gy * 0.55} r={200 * sc} fill="#d1336a" opacity={0.12} />
          <Stars W={W} H={gy} n={v ? 70 : 110} local={local} seed={9} />
          <circle cx={W * 0.76} cy={gy * 0.3} r={86 * sc} fill="#6ec1ff" /><circle cx={W * 0.76 - 26 * sc} cy={gy * 0.3 - 20 * sc} r={34 * sc} fill="#5ab04e" /><circle cx={W * 0.76 + 30 * sc} cy={gy * 0.3 + 28 * sc} r={26 * sc} fill="#5ab04e" />
          <path d={hillPath(W, gy, 10, 200, 6, 90, 0.2, H)} fill={'url(#' + id + 'g)'} />
          {[0.2, 0.5, 0.82].map((fx, i) => <ellipse key={i} cx={W * fx} cy={gy + 60 + i * 24} rx={60 * sc} ry={14 * sc} fill="#4b4e66" />)}
        </svg>
      );
    case 'cave':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#2a1c13', '#4a3322', '#6b4a2e']} /><radialGradient id={id + 'r'} cx="0.5" cy="0.6" r="0.7"><stop offset="0" stopColor="#ffb25a" stopOpacity="0.45" /><stop offset="1" stopColor="#000" stopOpacity="0" /></radialGradient></defs>
          <rect width={W} height={H} fill={'url(#' + id + ')'} />
          <path d={'M0 0 L' + W + ' 0 L' + W + ' ' + H * 0.12 + Array.from({length: 16}).map((_, i) => ' L' + (W - (i + 0.5) * (W / 16)) + ' ' + (H * 0.12 + ((i * 37) % 5) * 26 * sc + 40)).join('') + ' L0 ' + H * 0.12 + ' Z'} fill="#1d130c" />
          <rect y={gy} width={W} height={H - gy} fill="#3a281a" />
          <path d={hillPath(W, gy, 6, 140, 4, 60, 0.3, gy + 14)} fill="#4d3622" />
          <g opacity={0.8} stroke="#d6a36a" strokeWidth={6} strokeLinecap="round" fill="none">
            <path d={'M' + W * 0.12 + ' ' + gy * 0.45 + ' l24 -50 l24 50 m-24 -50 l0 -40 m-30 60 l-34 -12 m88 12 l34 -12'} />
            <path d={'M' + W * 0.62 + ' ' + gy * 0.4 + ' q30 -60 60 0 q30 60 60 0'} />
          </g>
          <rect width={W} height={H} fill={'url(#' + id + 'r)'} opacity={0.75 + 0.25 * Math.sin(local * 0.7)} />
        </svg>
      );
    case 'ruins':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#3b2a63', '#c4587a', '#ffb066', '#ffe0a8']} /><Grad id={id + 'g'} c={['#c9a979', '#a38258']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          <circle cx={W * 0.5} cy={gy - 60 * sc} r={120 * sc} fill="#fff1c9" opacity={0.9} />
          <path d={hillPath(W, gy - 60 * sc, 20 * sc, 300, 10 * sc, 120, 3, gy + 6)} fill="#7a4a63" opacity={0.85} />
          {[[0.1, 260, 40, 1], [0.24, 170, 40, 0], [0.8, 300, 44, 1], [0.92, 200, 40, 0]].map(([fx, hh, ww, br], i) => (
            <g key={i} transform={'translate(' + W * (fx as number) + ' ' + gy + ')'}>
              <rect x={-(ww as number) / 2} y={-(hh as number) * sc} width={ww as number} height={(hh as number) * sc} fill="#d9b98c" stroke="#5b3d2a" strokeWidth={4} />
              <rect x={-(ww as number) / 2 - 8} y={-(hh as number) * sc - 16} width={(ww as number) + 16} height={18} fill="#e8cca0" stroke="#5b3d2a" strokeWidth={4} />
              {br ? <path d={'M' + (-(ww as number) / 2) + ' ' + -(hh as number) * sc * 0.55 + ' l14 -10 l12 14 l14 -8 l8 10'} stroke="#5b3d2a" strokeWidth={3} fill="none" /> : null}
            </g>
          ))}
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
          {Array.from({length: Math.ceil(W / 220)}).map((_, i) => <path key={i} d={'M' + i * 220 + ' ' + gy + ' L' + (i * 220 - 60) + ' ' + H} stroke="#8a6a44" strokeWidth={3} opacity={0.5} />)}
          <path d={'M0 ' + (gy + 70 * sc) + ' L' + W + ' ' + (gy + 70 * sc)} stroke="#8a6a44" strokeWidth={3} opacity={0.5} />
        </svg>
      );
    case 'palace':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#f3e2bd', '#e7cf9c']} /><Grad id={id + 'g'} c={['#a8222c', '#7d1620']} /></defs>
          <rect width={W} height={gy} fill={'url(#' + id + ')'} />
          {Array.from({length: v ? 2 : 4}).map((_, i) => {
            const cw = (v ? W / 2 : W / 4);
            const cx = cw * i + cw / 2;
            return (
              <g key={i}>
                <path d={'M' + (cx - cw * 0.3) + ' ' + gy + ' L' + (cx - cw * 0.3) + ' ' + gy * 0.4 + ' A' + cw * 0.3 + ' ' + cw * 0.3 + ' 0 0 1 ' + (cx + cw * 0.3) + ' ' + gy * 0.4 + ' L' + (cx + cw * 0.3) + ' ' + gy + ' Z'} fill="#20407a" opacity={0.9} />
                <rect x={cx - cw * 0.46} y={gy * 0.18} width={30} height={gy * 0.82} fill="#fbf1d8" stroke="#a88a4a" strokeWidth={4} />
                <rect x={cx + cw * 0.46 - 30} y={gy * 0.18} width={30} height={gy * 0.82} fill="#fbf1d8" stroke="#a88a4a" strokeWidth={4} />
              </g>
            );
          })}
          <rect y={gy * 0.1} width={W} height={20} fill="#c9a24b" />
          <rect y={gy} width={W} height={H - gy} fill="#d9c29a" />
          <path d={'M' + W * 0.35 + ' ' + H + ' L' + W * 0.42 + ' ' + gy + ' L' + W * 0.58 + ' ' + gy + ' L' + W * 0.65 + ' ' + H + ' Z'} fill={'url(#' + id + 'g)'} />
        </svg>
      );
    case 'room':
    case 'living':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#fde8cf', '#f8d5b0']} /><Grad id={id + 'g'} c={['#e9b777', '#d49c5a']} /></defs>
          <rect width={W} height={gy} fill={'url(#' + id + ')'} />
          <rect x={W * (v ? 0.12 : 0.55)} y={gy * 0.16} width={W * (v ? 0.34 : 0.2)} height={gy * 0.42} fill="#bfe6fb" stroke="#fff" strokeWidth={14} />
          <path d={'M' + W * (v ? 0.29 : 0.65) + ' ' + gy * 0.16 + ' l0 ' + gy * 0.42 + ' M' + W * (v ? 0.12 : 0.55) + ' ' + gy * 0.37 + ' l' + W * (v ? 0.34 : 0.2) + ' 0'} stroke="#fff" strokeWidth={8} />
          <CloudBg x={W * (v ? 0.22 : 0.6) + Math.sin(t * 0.4) * 16} y={gy * 0.3} s={0.45 * sc} />
          <rect x={W * (v ? 0.58 : 0.14)} y={gy * 0.2} width={W * (v ? 0.28 : 0.12)} height={gy * 0.28} fill="#fff" stroke="#c98d56" strokeWidth={10} />
          <path d={'M' + W * (v ? 0.62 : 0.16) + ' ' + gy * 0.43 + ' l' + W * (v ? 0.07 : 0.03) + ' -' + gy * 0.12 + ' l' + W * (v ? 0.06 : 0.025) + ' ' + gy * 0.07 + ' l' + W * (v ? 0.07 : 0.03) + ' -' + gy * 0.1} stroke="#6aa86a" strokeWidth={8} fill="none" />
          <rect y={gy - 22} width={W} height={26} fill="#fff" />
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
          {Array.from({length: 7}).map((_, i) => <path key={i} d={'M0 ' + (gy + 30 + i * (H - gy) / 7) + ' L' + W + ' ' + (gy + 30 + i * (H - gy) / 7)} stroke="#b9803f" strokeWidth={3} opacity={0.5} />)}
        </svg>
      );
    case 'lab':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#e6f1ea', '#cfe3d8']} /></defs>
          <rect width={W} height={gy} fill={'url(#' + id + ')'} />
          <rect x={W * 0.1} y={gy * 0.2} width={W * (v ? 0.8 : 0.4)} height={14} fill="#8a6a44" />
          {[0, 1, 2, 3].map((i) => <g key={i} transform={'translate(' + (W * 0.14 + i * W * (v ? 0.2 : 0.09)) + ' ' + (gy * 0.2) + ')'}><rect x={0} y={-70} width={44} height={70} rx={8} fill={['#4ea3f0', '#f59a3b', '#4cc27a', '#d65db1'][i]} stroke={OL} strokeWidth={4} /><rect x={10} y={-92} width={24} height={26} fill="#fff" stroke={OL} strokeWidth={4} /></g>)}
          <rect y={gy - 120 * sc} width={W} height={120 * sc + 4} fill="#9aa5b1" stroke={OL} strokeWidth={5} />
          {Array.from({length: v ? 3 : 6}).map((_, i) => <rect key={i} x={i * (W / (v ? 3 : 6)) + 14} y={gy - 100 * sc} width={W / (v ? 3 : 6) - 28} height={90 * sc} rx={6} fill="#b8c2cc" stroke={OL} strokeWidth={4} />)}
          <rect y={gy + 4} width={W} height={H - gy} fill="#d9dde3" />
          {Array.from({length: 9}).map((_, i) => <path key={i} d={'M' + i * (W / 8) + ' ' + gy + ' L' + (i * (W / 8) - 80) + ' ' + H} stroke="#b8bec7" strokeWidth={3} />)}
        </svg>
      );
    case 'street':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#9fd4f4', '#d8efff']} /></defs>
          <rect width={W} height={gy} fill={'url(#' + id + ')'} />
          <CloudBg x={((W * 0.2 + local * 0.9) % (W + 300)) - 100} y={gy * 0.18} s={sc} o={0.9} />
          {Array.from({length: v ? 6 : 10}).map((_, i) => {
            const bw = (v ? 150 : 170) + ((i * 37) % 60);
            const bh = gy * (0.28 + ((i * 53) % 40) / 100);
            const bx = i * (W / (v ? 5 : 9)) - 20;
            const col = ['#e9c46a', '#f4a261', '#b7c9e2', '#d9a066', '#c8d3de', '#e8b57a'][i % 6];
            return (
              <g key={i}>
                <rect x={bx} y={gy - bh} width={bw} height={bh} fill={col} />
                {Array.from({length: 4}).map((_, r) => <g key={r}>{[0, 1].map((c) => <rect key={c} x={bx + 22 + c * (bw / 2 - 12)} y={gy - bh + 26 + r * 64 * sc} width={bw / 2 - 34} height={38 * sc} fill="#fdf3dc" opacity={0.9} />)}</g>)}
              </g>
            );
          })}
          <rect y={gy} width={W} height={H - gy} fill="#6b707c" />
          <rect y={gy} width={W} height={26} fill="#d8d2c4" />
          {Array.from({length: Math.ceil(W / 220) + 1}).map((_, i) => <rect key={i} x={i * 220 - ((local * 3) % 220)} y={gy + (H - gy) * 0.6} width={120} height={12} rx={4} fill="#fff" opacity={0.9} />)}
        </svg>
      );
    case 'forest':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#2b6f4a', '#a6d6a0']} /><Grad id={id + 'g'} c={['#3d7c3a', '#2a5b2c']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          {[0.2, 0.5, 0.78].map((fx, i) => <path key={i} d={'M' + (W * fx - 50) + ' 0 L' + (W * fx + 40) + ' 0 L' + (W * fx + 190) + ' ' + gy + ' L' + (W * fx - 60) + ' ' + gy + ' Z'} fill="#fff7c0" opacity={0.1 + 0.05 * Math.sin(t + i)} />)}
          {Array.from({length: v ? 6 : 11}).map((_, i) => {
            const x = i * (W / (v ? 5 : 10)) + ((i * 29) % 40);
            const hh = gy * (0.5 + ((i * 47) % 30) / 100);
            return <g key={i} transform={'translate(' + x + ' ' + gy + ')'}><rect x={-14} y={-hh * 0.3} width={28} height={hh * 0.3} fill="#5d3f26" />{[0, 1, 2].map((k) => <path key={k} d={'M' + (-90 + k * 14) + ' ' + (-hh * 0.28 - k * hh * 0.22) + ' L0 ' + (-hh * 0.62 - k * hh * 0.22) + ' L' + (90 - k * 14) + ' ' + (-hh * 0.28 - k * hh * 0.22) + ' Z'} fill={['#1f5a37', '#26703f', '#2f8a4a'][k]} />)}</g>;
          })}
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
        </svg>
      );
    case 'snow':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#9db7dd', '#dcebfb', '#f4faff']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          <path d={'M0 ' + gy + ' L' + W * 0.2 + ' ' + (gy - 340 * sc) + ' L' + W * 0.38 + ' ' + (gy - 130 * sc) + ' L' + W * 0.58 + ' ' + (gy - 420 * sc) + ' L' + W * 0.8 + ' ' + (gy - 150 * sc) + ' L' + W + ' ' + (gy - 260 * sc) + ' L' + W + ' ' + gy + ' Z'} fill="#8da3c4" />
          <path d={'M' + W * 0.58 + ' ' + (gy - 420 * sc) + ' l-70 110 l40 -26 l30 40 l34 -40 l36 30 z'} fill="#fff" />
          <rect y={gy} width={W} height={H - gy} fill="#f6fbff" />
          <path d={hillPath(W, gy + 4, 8, 300, 5, 90, 1, gy + 40)} fill="#e3eef9" />
          {Array.from({length: 40}).map((_, i) => <circle key={i} cx={((i * 197) % W) + Math.sin(local * 0.05 + i) * 14} cy={((local * (2 + (i % 4)) + i * 83) % (H + 20)) - 10} r={3 + (i % 3) * 2} fill="#fff" opacity={0.9} />)}
        </svg>
      );
    case 'battlefield':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#6f5b6e', '#d98a5c', '#f2c58b']} /><Grad id={id + 'g'} c={['#8a7048', '#5e4a2e']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          <circle cx={W * 0.3} cy={gy * 0.65} r={90 * sc} fill="#ffe3a8" opacity={0.85} />
          {[0, 1, 2].map((i) => <ellipse key={i} cx={W * (0.15 + i * 0.35) + Math.sin(t * 0.5 + i) * 30} cy={gy * (0.3 + i * 0.1)} rx={220 * sc} ry={60 * sc} fill="#4a3d4a" opacity={0.35} />)}
          <path d={hillPath(W, gy - 40 * sc, 16 * sc, 280, 8 * sc, 110, 1.2, gy + 6)} fill="#6e5a4a" />
          {[0.12, 0.88].map((fx, i) => <g key={i} transform={'translate(' + W * fx + ' ' + gy + ')'}><path d="M0 0 L0 -300" stroke={OL} strokeWidth={8} /><path d={'M0 -300 q40 ' + (10 + Math.sin(t * 5 + i) * 10) + ' 90 0 l0 90 q-50 ' + (-10 + Math.sin(t * 5 + i) * 10) + ' -90 0 z'} fill={i ? '#1d4e89' : '#c1121f'} stroke={OL} strokeWidth={5} /></g>)}
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
          {Array.from({length: 8}).map((_, i) => <ellipse key={i} cx={(i * 263 + 80) % W} cy={gy + 60 + (i * 41) % Math.max(30, H - gy - 80)} rx={22} ry={7} fill="#4a3a22" opacity={0.6} />)}
        </svg>
      );
    case 'volcano':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#3a1020', '#a5321f', '#ff8a3c']} /><Grad id={id + 'g'} c={['#2a2024', '#150f12']} /></defs>
          <rect width={W} height={gy + 4} fill={'url(#' + id + ')'} />
          {[0, 1, 2, 3].map((i) => <ellipse key={i} cx={W * 0.5 + Math.sin(t + i) * 40} cy={gy * (0.32 - i * 0.05) + i * 14} rx={(130 + i * 60) * sc} ry={(60 + i * 20) * sc} fill="#2c1a20" opacity={0.5} />)}
          <path d={'M' + W * 0.15 + ' ' + gy + ' L' + W * 0.42 + ' ' + (gy - 420 * sc) + ' L' + W * 0.58 + ' ' + (gy - 420 * sc) + ' L' + W * 0.85 + ' ' + gy + ' Z'} fill="#2a1a1c" stroke="#120a0c" strokeWidth={6} />
          <path d={'M' + W * 0.42 + ' ' + (gy - 420 * sc) + ' Q' + W * 0.5 + ' ' + (gy - 380 * sc) + ' ' + W * 0.58 + ' ' + (gy - 420 * sc) + ' Q' + W * 0.5 + ' ' + (gy - 440 * sc) + ' ' + W * 0.42 + ' ' + (gy - 420 * sc) + ' Z'} fill="#ffb02e" />
          {Array.from({length: 10}).map((_, i) => {
            const p = ((local * 0.03 + i * 0.1) % 1);
            return <circle key={i} cx={W * 0.5 + Math.sin(i * 2.3) * 160 * p} cy={gy - 430 * sc - 360 * sc * Math.sin(p * Math.PI)} r={14 - 8 * p} fill="#ff7a1a" opacity={1 - p * 0.6} />;
          })}
          <rect y={gy} width={W} height={H - gy} fill={'url(#' + id + 'g)'} />
          <path d={'M' + W * 0.5 + ' ' + (gy - 400 * sc) + ' q-30 160 20 260 q-40 80 30 140'} stroke="#ff8a1c" strokeWidth={14} fill="none" strokeLinecap="round" />
        </svg>
      );
    case 'sky':
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <defs><Grad id={id} c={['#4aa3ea', '#9fd3f7', '#eaf7ff']} /></defs>
          <rect width={W} height={H} fill={'url(#' + id + ')'} />
          {[0.1, 0.4, 0.7, 0.9, 0.25].map((fx, i) => <CloudBg key={i} x={((fx * (W + 500) + local * (0.7 + i * 0.25)) % (W + 500)) - 250} y={H * (0.12 + i * 0.15)} s={sc * (1.3 - i * 0.12)} o={0.95} />)}
          <path d={wavePath(W, gy + 20, 14, 360, t * 0.6, H)} fill="#fff" opacity={0.95} />
        </svg>
      );
    case 'paper':
    case 'cream':
    default:
      return (
        <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
          <rect width={W} height={H} fill="#fbf4df" />
          {Array.from({length: 26}).map((_, i) => <circle key={i} cx={(i * 211) % W} cy={(i * 137) % H} r={3} fill="#e6d9b8" />)}
          <rect y={gy} width={W} height={H - gy} fill="#f3e8c8" />
          <path d={'M0 ' + gy + ' L' + W + ' ' + gy} stroke="#cdbb8a" strokeWidth={5} strokeDasharray="22 14" />
        </svg>
      );
  }
};

// ============ علامة القناة (شارة احترافية: شعار + اسم على خلفية شفافة داكنة) ============
const Watermark: React.FC<{scale?: number; style?: React.CSSProperties}> = ({scale = 1, style}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 12 * scale, direction: 'rtl', padding: `${8 * scale}px ${26 * scale}px ${8 * scale}px ${10 * scale}px`,
    background: 'rgba(9,16,40,0.74)', border: `${2.5 * scale}px solid rgba(242,184,48,0.9)`, borderRadius: 999 * scale, boxShadow: '0 6px 18px rgba(0,0,0,0.35)', ...style}}>
    <LogoMark size={70 * scale} uid="wm" />
    <span style={{fontFamily: FONT, fontWeight: 900, fontSize: 44 * scale, color: '#fff', letterSpacing: 1, lineHeight: 1}}>أوابد</span>
  </div>
);

type Limb = [number, number];
type StickPose = {armL: Limb; armR: Limb; legL: Limb; legR: Limb; bob: number; lean: number; dy: number; rot: number};
const limbPts = (ox: number, oy: number, a: number, b: number, l1: number, l2: number): [[number, number], [number, number]] => {
  const p1: [number, number] = [ox + l1 * Math.sin(rad(a)), oy + l1 * Math.cos(rad(a))];
  const p2: [number, number] = [p1[0] + l2 * Math.sin(rad(a + b)), p1[1] + l2 * Math.cos(rad(a + b))];
  return [p1, p2];
};
const mixL = (a: Limb, b: Limb, k: number): Limb => [lerp(a[0], b[0], k), lerp(a[1], b[1], k)];
const mixPose = (a: StickPose, b: StickPose, k: number): StickPose => ({
  armL: mixL(a.armL, b.armL, k), armR: mixL(a.armR, b.armR, k), legL: mixL(a.legL, b.legL, k), legR: mixL(a.legR, b.legR, k),
  bob: lerp(a.bob, b.bob, k), lean: lerp(a.lean, b.lean, k), dy: lerp(a.dy, b.dy, k), rot: lerp(a.rot, b.rot, k),
});

function poseFor(action: string, t: number): StickPose {
  const s = Math.sin(t * 6);
  const base: StickPose = {armL: [-16, -6], armR: [16, 6], legL: [-7, 0], legR: [7, 0], bob: Math.sin(t * 2.5) * 3, lean: 0, dy: 0, rot: 0};
  switch (action) {
    case 'walk':
      return {...base, legL: [s * 30, Math.max(0, -s) * 28], legR: [-s * 30, Math.max(0, s) * 28], armL: [-s * 26, -10], armR: [s * 26, 10], bob: Math.abs(s) * 6, lean: 4};
    case 'run': {
      const r = Math.sin(t * 10);
      return {...base, legL: [r * 50, Math.max(0, -r) * 62], legR: [-r * 50, Math.max(0, r) * 62], armL: [-r * 52, -72], armR: [r * 52, 72], bob: Math.abs(r) * 10, lean: 16};
    }
    case 'point':
      return {...base, armR: [88 + Math.sin(t * 4) * 4, 0], armL: [-12, -6], lean: 3};
    case 'raise':
      return {...base, armL: [-160 + Math.sin(t * 5) * 9, 0], armR: [160 - Math.sin(t * 5) * 9, 0]};
    case 'work':
      return {...base, armR: [60 + Math.sin(t * 7) * 55, 40], armL: [30, 30], lean: 9, bob: Math.abs(Math.sin(t * 7)) * 3};
    case 'fight':
      return {...base, armR: [100 + Math.sin(t * 8) * 60, 20], armL: [-45, -50], legL: [-28, 10], legR: [30, 0], lean: 8};
    case 'carry':
      return {...base, armL: [62, 50], armR: [62, 50], legL: [s * 22, Math.max(0, -s) * 20], legR: [-s * 22, Math.max(0, s) * 20], bob: Math.abs(s) * 4, lean: -4};
    case 'think':
      return {...base, armR: [30, 120], armL: [-20, -10], lean: 2};
    case 'talk':
      return {...base, armR: [50 + Math.sin(t * 5) * 24, 40], armL: [-30 - Math.sin(t * 4) * 12, -20]};
    case 'kneel':
      return {...base, legL: [80, -120], legR: [20, -30], dy: 38, armL: [-20, 0], armR: [20, 0], lean: 10};
    case 'celebrate': {
      const j = Math.abs(Math.sin(t * 5));
      return {...base, dy: -j * 46, armL: [-150 - j * 12, 0], armR: [150 + j * 12, 0], legL: [-18, 0], legR: [18, 0]};
    }
    case 'fall':
      return {...base, rot: Math.min(88, t * 95), armL: [-120, 0], armR: [120, 0]};
    case 'wave':
      return {...base, armR: [150 + Math.sin(t * 9) * 22, 8], armL: [-14, -6], lean: -2};
    case 'scared':
      return {...base, armL: [-138 + Math.sin(t * 22) * 4, 78], armR: [138 - Math.sin(t * 22) * 4, -78], legL: [-16 + Math.sin(t * 24) * 4, 8], legR: [16 - Math.sin(t * 24) * 4, 8], rot: Math.sin(t * 28) * 1.6, lean: -6, bob: 0};
    case 'dance': {
      const d = Math.sin(t * 6);
      return {...base, armL: [-140 + d * 34, 0], armR: [140 - d * 34, 0], legL: [d * 26, Math.max(0, -d) * 24], legR: [-d * 26, Math.max(0, d) * 24], dy: -Math.abs(d) * 16, lean: Math.sin(t * 3) * 9, bob: 0};
    }
    case 'jump': {
      const j = Math.abs(Math.sin(t * 4));
      return {...base, dy: -j * 90, armL: [-150, 0], armR: [150, 0], legL: [-22, 40 * j], legR: [22, 40 * j], bob: 0};
    }
    case 'cry':
      return {...base, armL: [-28, 130], armR: [28 + Math.sin(t * 8) * 6, 130], lean: 9, rot: Math.sin(t * 16) * 1.2, bob: Math.sin(t * 8) * 3};
    case 'sleep':
      return {...base, rot: 86, dy: 4, armL: [-30, 10], armR: [30, 10], bob: Math.sin(t * 2) * 2};
    case 'push':
      return {...base, armL: [84, 0], armR: [84, 0], legL: [s * 16 - 14, 0], legR: [-s * 16 + 20, 0], lean: 16, bob: Math.abs(s) * 3};
    default:
      return base;
  }
}

const Stick: React.FC<{x: number; y: number; s?: number; role: string; action: string; t: number; local?: number; flip?: boolean; mouth?: number; expr?: string}> = (
  {x, y, s = 1, role, action, t, local = 0, flip, mouth = 0, expr: exprIn = 'neutral'},
) => {
  const sleeping = action === 'sleep';
  const expr = action === 'scared' ? 'surprised' : action === 'cry' ? 'sad' : action === 'celebrate' || action === 'dance' ? 'happy' : exprIn;
  const look = Math.sin(t * 0.8) * 1.8;
  const lookY = Math.sin(t * 0.55 + 1) * 0.8;
  const blink = (local + Math.round(x)) % 86 < 3;
  const browY = expr === 'surprised' ? -293 : expr === 'sad' ? -286 : -285;
  const tiltL = expr === 'sad' ? 5 : expr === 'happy' ? -2 : expr === 'think' ? 4 : 0;
  const tiltR = expr === 'sad' ? -5 : expr === 'happy' ? -2 : expr === 'think' ? -6 : 0;
  const p = mixPose(poseFor('idle', t), poseFor(action, t), easeOut(local / 7));
  const k = role === 'child' ? 0.68 : 1;
  const pop = local < 14 ? easeBack(local / 12) : 1;
  const land = local < 16 ? Math.sin(clamp01(local / 16) * Math.PI) * 0.07 : 0;
  const sq = {x: pop * (1 + land), y: pop * (1 - land)};
  const [aL1, aL2] = limbPts(0, -214, p.armL[0], p.armL[1], 50, 48);
  const [aR1, aR2] = limbPts(0, -214, p.armR[0], p.armR[1], 50, 48);
  const [lL1, lL2] = limbPts(0, -118, p.legL[0], p.legL[1], 60, 58);
  const [lR1, lR2] = limbPts(0, -118, p.legR[0], p.legR[1], 60, 58);
  const st = {stroke: OL, strokeWidth: 12, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none'};
  const thR = p.armR[0] + p.armR[1];
  const handR = `translate(${aR2[0]} ${aR2[1]}) rotate(${-thR})`;
  const handL = `translate(${aL2[0]} ${aL2[1]})`;
  return (
    <g transform={`translate(${x} ${y}) scale(${(flip ? -1 : 1) * s * k * sq.x} ${s * k * sq.y})`}>
      <ellipse cx={0} cy={0} rx={72} ry={12} fill="rgba(0,0,0,0.2)" />
      <g transform={`translate(0 ${p.dy + p.bob}) rotate(${p.rot} 0 0)`}>
        <path d={`M0 -118 L${lL1[0]} ${lL1[1]} L${lL2[0]} ${lL2[1]}`} {...st} />
        <path d={`M0 -118 L${lR1[0]} ${lR1[1]} L${lR2[0]} ${lR2[1]}`} {...st} />
        <path d={`M${lL2[0]} ${lL2[1]} L${lL2[0] + 20} ${lL2[1]}`} {...st} strokeWidth={13} />
        <path d={`M${lR2[0]} ${lR2[1]} L${lR2[0] + 20} ${lR2[1]}`} {...st} strokeWidth={13} />
        {role === 'king' && <path d="M-28 -214 L28 -214 L62 -34 L-62 -34 Z" fill="#b3202a" stroke={OL} strokeWidth={6} strokeLinejoin="round" />}
        {role === 'queen' && <path d="M-22 -214 L22 -214 L64 -8 L-64 -8 Z" fill="#7b2d8e" stroke={OL} strokeWidth={6} strokeLinejoin="round" />}
        {role === 'trader' && <circle cx={-38} cy={-150} r={40} fill="#8d6e3f" stroke={OL} strokeWidth={6} />}
        <g transform={`rotate(${p.lean} 0 -118)`}>
          <path d="M0 -214 L0 -118" {...st} />
          {role === 'scientist' && <path d="M-30 -214 L30 -214 L44 -78 L-44 -78 Z" fill="#fff" stroke={OL} strokeWidth={6} strokeLinejoin="round" />}
          <path d={`M0 -214 L${aL1[0]} ${aL1[1]} L${aL2[0]} ${aL2[1]}`} {...st} />
          <path d={`M0 -214 L${aR1[0]} ${aR1[1]} L${aR2[0]} ${aR2[1]}`} {...st} />
          <circle cx={aL2[0]} cy={aL2[1]} r={9} fill={OL} />
          <circle cx={aR2[0]} cy={aR2[1]} r={9} fill={OL} />
          {role === 'soldier' && (
            <g>
              <g transform={`translate(${aR2[0]} ${aR2[1]})`}>
                <path d="M0 50 L0 -170" stroke={OL} strokeWidth={7} strokeLinecap="round" />
                <path d="M-11 -168 L0 -204 L11 -168 Z" fill="#cfd8dc" stroke={OL} strokeWidth={5} />
              </g>
              <g transform={handL}>
                <circle cx={0} cy={0} r={38} fill="#c1121f" stroke={OL} strokeWidth={6} />
                <circle cx={0} cy={0} r={12} fill="#ffd23f" stroke={OL} strokeWidth={4} />
              </g>
            </g>
          )}
          {role === 'worker' && (
            <g transform={handR}>
              <path d="M0 0 L0 62" stroke="#6b4a2b" strokeWidth={9} strokeLinecap="round" />
              <rect x={-24} y={54} width={48} height={22} rx={4} fill="#8d99ae" stroke={OL} strokeWidth={5} />
            </g>
          )}
          {role === 'caveman' && (
            <g transform={handR}>
              <path d="M0 0 L0 58" stroke="#6b4a2b" strokeWidth={10} strokeLinecap="round" />
              <ellipse cx={0} cy={66} rx={18} ry={24} fill="#8b5e3c" stroke={OL} strokeWidth={5} />
            </g>
          )}
          {role === 'scholar' && (
            <g transform={handR}>
              <rect x={-9} y={0} width={18} height={50} rx={5} fill="#f1e3c0" stroke={OL} strokeWidth={5} />
              <path d="M-9 12 L9 12 M-9 24 L9 24" stroke={OL} strokeWidth={3} />
            </g>
          )}
          {role === 'trader' && <circle cx={aR2[0]} cy={aR2[1]} r={13} fill="#ffd23f" stroke={OL} strokeWidth={4} />}
          {role === 'farmer' && (
            <g transform={handR}>
              <path d="M0 0 L0 70" stroke="#6b4a2b" strokeWidth={8} strokeLinecap="round" />
              <path d="M-20 70 Q0 96 20 70" stroke={OL} strokeWidth={7} fill="none" strokeLinecap="round" />
            </g>
          )}
          <circle cx={0} cy={-262} r={31} fill="#fff" stroke={OL} strokeWidth={9} />
          {[-11, 11].map((ex) => (
            <g key={ex}>
              {blink ? (
                <path d={`M${ex - 8} -267 L${ex + 8} -267`} stroke={OL} strokeWidth={4} strokeLinecap="round" />
              ) : sleeping ? (
                <path d={`M${ex - 8} -267 Q${ex} -260 ${ex + 8} -267`} stroke={OL} strokeWidth={4} fill="none" strokeLinecap="round" />
              ) : (
                <g>
                  <ellipse cx={ex} cy={-268} rx={8.5} ry={expr === 'surprised' ? 11.5 : 9.5} fill="#fff" stroke={OL} strokeWidth={3} />
                  <circle cx={ex + look} cy={-267 + lookY} r={4.4} fill={OL} />
                  <circle cx={ex + look + 1.6} cy={-268.6 + lookY} r={1.3} fill="#fff" />
                </g>
              )}
            </g>
          ))}
          <path d={`M-20 ${browY + tiltL} L-3 ${browY - tiltL}`} stroke={OL} strokeWidth={4.5} strokeLinecap="round" />
          <path d={`M3 ${browY - tiltR} L20 ${browY + tiltR}`} stroke={OL} strokeWidth={4.5} strokeLinecap="round" />
          {mouth > 0.12 ? (
            <ellipse cx={0} cy={-249} rx={7 + mouth * 3} ry={2.5 + mouth * 8.5} fill="#3a1a1a" stroke={OL} strokeWidth={2.5} />
          ) : expr === 'surprised' ? (
            <ellipse cx={0} cy={-248} rx={6} ry={8} fill="#3a1a1a" stroke={OL} strokeWidth={2.5} />
          ) : expr === 'happy' ? (
            <path d="M-12 -254 Q0 -238 12 -254 Z" fill="#fff" stroke={OL} strokeWidth={3.5} strokeLinejoin="round" />
          ) : expr === 'sad' ? (
            <path d="M-10 -245 Q0 -256 10 -245" stroke={OL} strokeWidth={4} fill="none" strokeLinecap="round" />
          ) : (
            <path d="M-8 -250 L8 -250" stroke={OL} strokeWidth={4} fill="none" strokeLinecap="round" />
          )}
          {(action === 'scared' || action === 'run') && <path d="M34 -284 q8 14 0 20 q-8 -6 0 -20 Z" fill="#6ec1ff" stroke={OL} strokeWidth={2.5} opacity={0.5 + 0.5 * Math.sin(t * 12)} />}
          {action === 'cry' && [-11, 11].map((ex) => <path key={ex} d={`M${ex} -254 q${ex > 0 ? 5 : -5} ${14 + (local % 14)} 0 ${24 + (local % 14)}`} stroke="#4aa3ea" strokeWidth={5} fill="none" strokeLinecap="round" opacity={0.85} />)}
          {sleeping && <text x={36} y={-292 - (local % 40) * 0.8} fontSize={34} fontWeight={900} fill={OL} opacity={0.7} style={{fontFamily: FONT}}>Z</text>}
          {(role === 'narrator' || role === 'trader') && (
            <path d="M-31 -266 Q-31 -304 0 -306 Q31 -304 31 -266 Q10 -284 -31 -266 Z" fill={role === 'trader' ? '#f4ecd8' : '#b3202a'} stroke={OL} strokeWidth={6} strokeLinejoin="round" />
          )}
          {(role === 'king' || role === 'queen') && (
            <path d="M-25 -283 L-25 -313 L-12 -298 L0 -320 L12 -298 L25 -313 L25 -283 Z" fill="#ffd23f" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
          )}
          {role === 'soldier' && (
            <g>
              <path d="M-32 -266 A32 32 0 0 1 32 -266 Z" fill="#8d99ae" stroke={OL} strokeWidth={6} />
              <path d="M0 -298 L0 -322" stroke="#c1121f" strokeWidth={10} strokeLinecap="round" />
            </g>
          )}
          {role === 'worker' && <path d="M-32 -268 A32 32 0 0 1 32 -268 Z" fill="#ffb703" stroke={OL} strokeWidth={6} />}
          {role === 'sailor' && (
            <g>
              <path d="M-30 -272 A30 30 0 0 1 30 -272 Z" fill="#1d4e89" stroke={OL} strokeWidth={6} />
              <rect x={-31} y={-274} width={62} height={9} fill="#fff" stroke={OL} strokeWidth={4} />
            </g>
          )}
          {role === 'farmer' && (
            <g>
              <ellipse cx={0} cy={-280} rx={50} ry={10} fill="#e9c46a" stroke={OL} strokeWidth={5} />
              <path d="M-26 -282 A26 26 0 0 1 26 -282 Z" fill="#e9c46a" stroke={OL} strokeWidth={5} />
            </g>
          )}
          {role === 'caveman' && <path d="M-30 -276 L-22 -300 L-10 -282 L0 -304 L10 -282 L22 -300 L30 -276" stroke={OL} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />}
          {role === 'scientist' && (
            <g>
              <circle cx={-10} cy={-268} r={10} stroke={OL} strokeWidth={3} fill="none" />
              <circle cx={10} cy={-268} r={10} stroke={OL} strokeWidth={3} fill="none" />
              <g transform={handR}>
                <rect x={-22} y={0} width={44} height={58} rx={5} fill="#f1e3c0" stroke={OL} strokeWidth={5} />
                <path d="M-12 16 L12 16 M-12 30 L12 30 M-12 44 L4 44" stroke={OL} strokeWidth={3} />
              </g>
            </g>
          )}
          {role === 'scholar' && (
            <g>
              <circle cx={-10} cy={-268} r={9} stroke={OL} strokeWidth={3} fill="none" />
              <circle cx={10} cy={-268} r={9} stroke={OL} strokeWidth={3} fill="none" />
            </g>
          )}
        </g>
      </g>
    </g>
  );
};

// ---------- مجسمات ----------
const PROP_DRAW: Record<string, (t: number) => React.ReactNode> = {
  pyramid: () => (
    <g>
      <path d="M-200 0 L0 -260 L200 0 Z" fill="#e9c46a" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M0 -260 L200 0 L70 0 Z" fill="#cfa447" opacity={0.75} />
      <path d="M-150 -66 L150 -66 M-100 -132 L100 -132 M-50 -198 L50 -198" stroke={OL} strokeWidth={3} opacity={0.5} />
    </g>
  ),
  temple: () => (
    <g>
      <path d="M-190 -250 L0 -330 L190 -250 Z" fill="#f0e2c4" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <rect x={-190} y={-250} width={380} height={26} fill="#e6d2a8" stroke={OL} strokeWidth={5} />
      {[-150, -50, 50, 150].map((cx) => (
        <rect key={cx} x={cx - 20} y={-224} width={40} height={206} fill="#f6ecd5" stroke={OL} strokeWidth={5} />
      ))}
      <rect x={-205} y={-18} width={410} height={18} fill="#e6d2a8" stroke={OL} strokeWidth={5} />
    </g>
  ),
  ship: (t) => (
    <g transform={`rotate(${Math.sin(t * 2) * 3} 0 0) translate(0 ${Math.sin(t * 2.4) * 6})`}>
      <path d="M-170 -40 L170 -40 L120 30 L-120 30 Z" fill="#8d5a2b" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M0 -40 L0 -250" stroke={OL} strokeWidth={9} />
      <path d="M8 -240 L140 -80 L8 -80 Z" fill="#f4ecd8" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-8 -210 L-100 -80 L-8 -80 Z" fill="#e9dcc0" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M0 -250 L50 -232 L0 -214 Z" fill="#c1121f" stroke={OL} strokeWidth={4} />
    </g>
  ),
  castle: () => (
    <g>
      <rect x={-130} y={-190} width={260} height={190} fill="#b0b7c3" stroke={OL} strokeWidth={6} />
      {[-130, -70, -10, 50, 110].map((cx) => <rect key={cx} x={cx} y={-218} width={26} height={30} fill="#b0b7c3" stroke={OL} strokeWidth={5} />)}
      {[-175, 175].map((cx) => (
        <g key={cx}>
          <rect x={cx - 38} y={-260} width={76} height={260} fill="#9aa2b1" stroke={OL} strokeWidth={6} />
          <path d={`M${cx - 48} -260 L${cx} -330 L${cx + 48} -260 Z`} fill="#c1121f" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
        </g>
      ))}
      <path d="M-34 0 L-34 -80 A34 34 0 0 1 34 -80 L34 0 Z" fill="#3b2f2f" stroke={OL} strokeWidth={5} />
    </g>
  ),
  tent: () => (
    <g>
      <path d="M-140 0 L0 -190 L140 0 Z" fill="#e76f51" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M0 -190 L60 0 L-60 0 Z" fill="#f4a261" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
      <path d="M-30 0 L0 -100 L30 0 Z" fill="#3b2f2f" />
    </g>
  ),
  fire: (t) => {
    const f = 1 + Math.sin(t * 14) * 0.08;
    return (
      <g>
        <rect x={-70} y={-16} width={140} height={22} rx={11} fill="#4a2f1b" stroke={OL} strokeWidth={5} transform="rotate(-6)" />
        <path d={`M-52 -10 Q-34 ${-110 * f} -6 ${-150 * f} Q16 ${-90 * f} 52 -10 Z`} fill="#ff8c1a" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
        <path d={`M-26 -10 Q-12 ${-70 * f} 0 ${-96 * f} Q14 ${-60 * f} 28 -10 Z`} fill="#ffd25a" />
      </g>
    );
  },
  tree: () => (
    <g>
      <path d="M-16 0 L-12 -120 L12 -120 L16 0 Z" fill="#7a5230" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      {[[-48, -150, 56], [48, -150, 56], [0, -200, 70]].map(([cx, cy, r], i) => <circle key={i} cx={cx} cy={cy} r={r} fill="#4f9d4a" stroke={OL} strokeWidth={6} />)}
    </g>
  ),
  mountain: () => (
    <g>
      <path d="M-260 0 L-20 -300 L120 -160 L170 -210 L300 0 Z" fill="#7d8ca6" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-20 -300 L-92 -212 L-56 -226 L-26 -196 L20 -234 Z" fill="#f4f7fb" stroke={OL} strokeWidth={4} strokeLinejoin="round" />
    </g>
  ),
  coins: () => (
    <g>
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <ellipse cx={0} cy={-i * 22 - 10} rx={66} ry={20} fill="#ffd23f" stroke={OL} strokeWidth={5} />
          <ellipse cx={0} cy={-i * 22 - 20} rx={66} ry={20} fill="#ffe27a" stroke={OL} strokeWidth={5} />
        </g>
      ))}
      <ellipse cx={0} cy={-98} rx={30} ry={8} fill="#e6b422" />
    </g>
  ),
  scroll: () => (
    <g>
      <rect x={-90} y={-130} width={180} height={130} rx={10} fill="#f1e3c0" stroke={OL} strokeWidth={6} />
      <rect x={-104} y={-140} width={26} height={150} rx={13} fill="#d9c08a" stroke={OL} strokeWidth={5} />
      <rect x={78} y={-140} width={26} height={150} rx={13} fill="#d9c08a" stroke={OL} strokeWidth={5} />
      <path d="M-56 -100 L56 -100 M-56 -72 L56 -72 M-56 -44 L20 -44" stroke={OL} strokeWidth={4} opacity={0.6} />
    </g>
  ),
  crown: () => (
    <g>
      <path d="M-110 0 L-110 -120 L-55 -60 L0 -150 L55 -60 L110 -120 L110 0 Z" fill="#ffd23f" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      {[[-110, -126], [0, -156], [110, -126]].map(([cx, cy], i) => <circle key={i} cx={cx} cy={cy} r={12} fill="#c1121f" stroke={OL} strokeWidth={4} />)}
      <rect x={-110} y={-26} width={220} height={26} fill="#e6b422" stroke={OL} strokeWidth={5} />
    </g>
  ),
  book: () => (
    <g>
      <path d="M0 -20 L-120 -50 L-120 0 L0 30 Z" fill="#f4ecd8" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M0 -20 L120 -50 L120 0 L0 30 Z" fill="#efe3c8" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-100 -30 L-20 -12 M-100 -14 L-20 4 M100 -30 L20 -12 M100 -14 L20 4" stroke={OL} strokeWidth={3} opacity={0.5} />
    </g>
  ),
  camel: (t) => (
    <g transform={`translate(0 ${Math.abs(Math.sin(t * 4)) * -5})`}>
      <ellipse cx={0} cy={-120} rx={110} ry={52} fill="#d9a066" stroke={OL} strokeWidth={6} />
      <circle cx={-20} cy={-176} r={34} fill="#d9a066" stroke={OL} strokeWidth={6} />
      <path d="M90 -140 Q150 -190 150 -250 L178 -258 Q190 -236 172 -226 Q172 -170 120 -110 Z" fill="#d9a066" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      {[-70, -30, 40, 80].map((x, i) => <path key={i} d={`M${x} -80 L${x + (i % 2 ? 6 : -6) * Math.sin(t * 6)} 0`} stroke={OL} strokeWidth={12} strokeLinecap="round" />)}
      <path d="M-108 -130 Q-140 -110 -132 -70" stroke={OL} strokeWidth={6} fill="none" strokeLinecap="round" />
    </g>
  ),
  tower: () => (
    <g>
      <rect x={-50} y={-330} width={100} height={330} fill="#b0b7c3" stroke={OL} strokeWidth={6} />
      {[-50, -18, 14].map((cx) => <rect key={cx} x={cx} y={-356} width={22} height={28} fill="#b0b7c3" stroke={OL} strokeWidth={5} />)}
      <rect x={-14} y={-250} width={28} height={50} rx={14} fill="#2b2b36" />
      <path d="M0 -356 L0 -410 L46 -392 L0 -374" fill="#c1121f" stroke={OL} strokeWidth={4} />
    </g>
  ),
  city: () => (
    <g>
      {[[-210, 150, 70], [-120, 220, 90], [-10, 170, 100], [100, 250, 80], [190, 140, 90]].map(([cx, h, w], i) => (
        <g key={i}>
          <rect x={cx - w / 2} y={-h} width={w} height={h} fill={['#e9c46a', '#f4a261', '#e9d8a6', '#e8b57a', '#d9c08a'][i]} stroke={OL} strokeWidth={5} />
          <path d={`M${cx - w / 2} ${-h} A${w / 2} ${w / 2} 0 0 1 ${cx + w / 2} ${-h} Z`} fill="#3a86a8" stroke={OL} strokeWidth={5} />
          <rect x={cx - 8} y={-h * 0.5} width={16} height={26} rx={8} fill="#2b2b36" />
        </g>
      ))}
    </g>
  ),
  swords: () => (
    <g>
      <path d="M-110 -170 L90 20" stroke="#cfd8dc" strokeWidth={16} strokeLinecap="round" />
      <path d="M110 -170 L-90 20" stroke="#cfd8dc" strokeWidth={16} strokeLinecap="round" />
      <path d="M-110 -170 L90 20 M110 -170 L-90 20" stroke={OL} strokeWidth={4} opacity={0.5} />
      <circle cx={0} cy={-80} r={52} fill="#c1121f" stroke={OL} strokeWidth={7} />
      <circle cx={0} cy={-80} r={18} fill="#ffd23f" stroke={OL} strokeWidth={5} />
    </g>
  ),
  sun: (t) => (
    <g>
      {Array.from({length: 12}).map((_, i) => (
        <path key={i} d="M0 -120 L0 -150" stroke="#ffb703" strokeWidth={10} strokeLinecap="round" transform={`rotate(${i * 30 + t * 10})`} />
      ))}
      <circle cx={0} cy={0} r={90} fill="#ffd23f" stroke={OL} strokeWidth={7} />
    </g>
  ),
  moon: () => (
    <g>
      <circle cx={0} cy={0} r={80} fill="#f4f1de" stroke={OL} strokeWidth={6} />
      <circle cx={30} cy={-14} r={70} fill="#16264a" />
    </g>
  ),
  chest: () => (
    <g>
      <rect x={-90} y={-90} width={180} height={90} rx={8} fill="#8d5a2b" stroke={OL} strokeWidth={6} />
      <path d="M-90 -90 Q0 -170 90 -90 Z" fill="#a86a33" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <rect x={-14} y={-100} width={28} height={36} rx={5} fill="#ffd23f" stroke={OL} strokeWidth={5} />
    </g>
  ),
  pot: () => (
    <g>
      <path d="M-50 -150 Q-110 -70 -60 0 L60 0 Q110 -70 50 -150 Z" fill="#c8794a" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <rect x={-40} y={-176} width={80} height={30} rx={8} fill="#b5683c" stroke={OL} strokeWidth={6} />
      <path d="M-76 -90 Q0 -60 76 -90" stroke={OL} strokeWidth={4} fill="none" opacity={0.5} />
    </g>
  ),
};

// ---------- مجسمات إضافية (كلها مرسومة بالكود؛ القاعدة y=0 والارتفاع للأعلى) ----------
const PROP_NEW: Record<string, (t: number) => React.ReactNode> = {
  wave: (t) => (
    <g>
      {[0, 1, 2].map((i) => <path key={i} d={wavePath(520, -40 + i * 26, 16 - i * 3, 190 + i * 40, t * (2.4 - i * 0.5) + i, 40).replace(/M0 40/, 'M0 40')} transform="translate(-260 0)" fill={['#3aa7e0', '#2989c6', '#1e6fae'][i]} stroke={OL} strokeWidth={5} />)}
    </g>
  ),
  whale: (t) => (
    <g transform={`translate(0 ${Math.sin(t * 1.6) * 8})`}>
      {[-18, 0, 18].map((o, i) => <path key={i} d={`M150 -190 q${o} ${-50 - Math.sin(t * 5 + i) * 14} ${o * 1.6} -90`} stroke="#8fd4ff" strokeWidth={9} fill="none" strokeLinecap="round" />)}
      <path d="M-200 -70 Q-210 -190 -80 -210 Q80 -240 180 -150 Q214 -110 190 -60 Q120 10 -60 0 Q-160 0 -200 -70 Z" fill="#3b82c4" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-190 -80 Q-120 -60 -40 -50 Q80 -40 190 -70 Q150 0 -40 0 Q-150 0 -190 -80 Z" fill="#cfe8f7" opacity={0.9} />
      <path d="M-200 -70 Q-262 -80 -270 -150 Q-230 -130 -216 -110 Q-250 -60 -226 -30 Q-200 -40 -200 -70 Z" fill="#3b82c4" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <circle cx={120} cy={-120} r={9} fill={OL} /><circle cx={123} cy={-123} r={3} fill="#fff" />
      <path d="M150 -78 Q175 -66 196 -82" stroke={OL} strokeWidth={5} fill="none" strokeLinecap="round" />
    </g>
  ),
  fish: (t) => (
    <g transform={`translate(0 ${-90 + Math.sin(t * 3) * 10})`}>
      <path d={`M-40 0 L-110 ${-34 + Math.sin(t * 8) * 8} L-110 ${34 - Math.sin(t * 8) * 8} Z`} fill="#f08a3c" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <ellipse cx={20} cy={0} rx={90} ry={56} fill="#ffa94d" stroke={OL} strokeWidth={6} />
      <path d="M0 -52 Q30 -96 70 -52 Z" fill="#f08a3c" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
      <path d="M10 -30 Q-10 0 10 30 M40 -34 Q22 0 40 34" stroke="#f08a3c" strokeWidth={5} fill="none" />
      <circle cx={70} cy={-10} r={10} fill="#fff" stroke={OL} strokeWidth={4} /><circle cx={73} cy={-10} r={4} fill={OL} />
    </g>
  ),
  shark: (t) => (
    <g transform={`translate(0 ${-80 + Math.sin(t * 2) * 8})`}>
      <path d="M-170 0 Q-100 -60 40 -64 Q150 -60 190 0 Q120 60 20 60 Q-100 60 -170 0 Z" fill="#7a8ca3" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-20 -62 L20 -150 L60 -62 Z" fill="#6b7d94" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-170 0 L-240 -60 L-220 0 L-240 56 Z" fill="#6b7d94" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M60 14 Q130 40 190 0 Q130 24 60 14" fill="#fff" stroke={OL} strokeWidth={4} />
      {[80, 108, 136, 160].map((x, i) => <path key={i} d={`M${x} ${14 + i * 3} l6 14 l6 -14`} fill="#fff" stroke={OL} strokeWidth={2.5} />)}
      <circle cx={120} cy={-16} r={8} fill={OL} />
    </g>
  ),
  octopus: (t) => (
    <g transform={`translate(0 ${Math.sin(t * 2.4) * 8})`}>
      {[-90, -54, -18, 18, 54, 90].map((x, i) => <path key={i} d={`M${x * 0.6} -90 Q${x + Math.sin(t * 4 + i) * 24} -40 ${x * 1.2} -6 Q${x * 1.4 + Math.sin(t * 4 + i) * 20} 6 ${x * 1.3} 0`} stroke={OL} strokeWidth={24} fill="none" strokeLinecap="round" />)}
      {[-90, -54, -18, 18, 54, 90].map((x, i) => <path key={i} d={`M${x * 0.6} -90 Q${x + Math.sin(t * 4 + i) * 24} -40 ${x * 1.2} -6 Q${x * 1.4 + Math.sin(t * 4 + i) * 20} 6 ${x * 1.3} 0`} stroke="#b05fc9" strokeWidth={14} fill="none" strokeLinecap="round" />)}
      <ellipse cx={0} cy={-150} rx={90} ry={86} fill="#b05fc9" stroke={OL} strokeWidth={7} />
      <circle cx={-30} cy={-140} r={16} fill="#fff" stroke={OL} strokeWidth={4} /><circle cx={30} cy={-140} r={16} fill="#fff" stroke={OL} strokeWidth={4} />
      <circle cx={-27} cy={-138} r={6} fill={OL} /><circle cx={33} cy={-138} r={6} fill={OL} />
    </g>
  ),
  turtle: (t) => (
    <g transform={`translate(0 ${Math.abs(Math.sin(t * 2)) * -3})`}>
      {[-70, 60].map((x, i) => <ellipse key={i} cx={x} cy={-10} rx={26} ry={16} fill="#79b85a" stroke={OL} strokeWidth={6} />)}
      <circle cx={130} cy={-70} r={30} fill="#79b85a" stroke={OL} strokeWidth={6} /><circle cx={140} cy={-76} r={5} fill={OL} />
      <path d="M-120 -20 Q-110 -150 0 -150 Q110 -150 120 -20 Z" fill="#4f9d3d" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-60 -30 L-40 -110 M0 -30 L0 -140 M60 -30 L40 -110 M-100 -60 L100 -60" stroke={OL} strokeWidth={4} opacity={0.5} />
    </g>
  ),
  bird: (t) => {
    const f = Math.sin(t * 9) * 36;
    return (
      <g>
        <path d={`M-30 -10 Q-90 ${-70 - f} -150 ${-30 - f * 1.4} Q-90 ${-30 - f * 0.6} -30 20 Z`} fill="#3b82c4" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
        <ellipse cx={0} cy={0} rx={62} ry={40} fill="#4aa3ea" stroke={OL} strokeWidth={6} />
        <circle cx={58} cy={-30} r={26} fill="#4aa3ea" stroke={OL} strokeWidth={6} />
        <path d="M80 -34 L112 -24 L80 -18 Z" fill="#ffb703" stroke={OL} strokeWidth={4} strokeLinejoin="round" />
        <circle cx={64} cy={-36} r={6} fill={OL} />
        <path d="M-60 0 L-110 -14 L-100 14 Z" fill="#3b82c4" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
      </g>
    );
  },
  snake: (t) => {
    let d = 'M-190 -20';
    for (let i = 1; i <= 24; i++) d += ` L${-190 + i * 16} ${-30 + Math.sin(i * 0.7 + t * 4) * 26 - i * 1.2}`;
    return (
      <g>
        <path d={d} stroke={OL} strokeWidth={36} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <path d={d} stroke="#4cae4f" strokeWidth={24} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <path d={d} stroke="#a8e063" strokeWidth={6} fill="none" strokeDasharray="10 22" strokeLinecap="round" />
        <circle cx={200} cy={-56} r={30} fill="#4cae4f" stroke={OL} strokeWidth={6} />
        <circle cx={208} cy={-64} r={6} fill={OL} />
        <path d={`M228 -50 l${28 + Math.sin(t * 12) * 6} -4 m-${28 + Math.sin(t * 12) * 6} 4 l${28 + Math.sin(t * 12) * 6} 8`} stroke="#e11d2e" strokeWidth={4} fill="none" strokeLinecap="round" />
      </g>
    );
  },
  spider: (t) => (
    <g transform={`translate(0 ${-70 + Math.sin(t * 3) * 6})`}>
      <path d="M0 -300 L0 -70" stroke="#999" strokeWidth={3} />
      {[-1, 1].map((sd) => [0, 1, 2, 3].map((i) => <path key={sd + '_' + i} d={`M0 0 Q${sd * (50 + i * 10)} ${-50 + i * 6} ${sd * (86 + i * 14)} ${6 + i * 22 + Math.sin(t * 6 + i) * 4}`} stroke={OL} strokeWidth={6} fill="none" strokeLinecap="round" />))}
      <ellipse cx={0} cy={6} rx={36} ry={42} fill="#2b2b36" stroke={OL} strokeWidth={5} /><circle cx={0} cy={-34} r={24} fill="#3a3a48" stroke={OL} strokeWidth={5} />
      <circle cx={-9} cy={-38} r={5} fill="#ff5a5a" /><circle cx={9} cy={-38} r={5} fill="#ff5a5a" />
    </g>
  ),
  bee: (t) => (
    <g transform={`translate(0 ${-60 + Math.sin(t * 5) * 10})`}>
      {[-1, 1].map((sd) => <ellipse key={sd} cx={sd * 18} cy={-40} rx={22} ry={Math.max(6, 34 * Math.abs(Math.sin(t * 30)))} fill="#d5eefc" stroke={OL} strokeWidth={4} opacity={0.9} transform={`rotate(${sd * 24} ${sd * 18} -40)`} />)}
      <ellipse cx={0} cy={0} rx={56} ry={40} fill="#ffd23f" stroke={OL} strokeWidth={6} />
      {[-22, 0, 22].map((x) => <path key={x} d={`M${x} -38 Q${x + 8} 0 ${x} 38`} stroke={OL} strokeWidth={11} fill="none" />)}
      <circle cx={52} cy={-6} r={4} fill={OL} /><path d="M-56 0 l-16 4" stroke={OL} strokeWidth={7} strokeLinecap="round" />
    </g>
  ),
  horse: (t) => (
    <g transform={`translate(0 ${Math.abs(Math.sin(t * 4)) * -5})`}>
      <path d="M-110 -110 Q-150 -120 -148 -60 Q-130 -90 -100 -90 Z" fill="#3a2418" stroke={OL} strokeWidth={5} />
      <ellipse cx={0} cy={-118} rx={116} ry={48} fill="#9a5b2e" stroke={OL} strokeWidth={6} />
      <path d="M70 -140 Q110 -200 130 -250 L186 -230 Q196 -204 174 -196 Q160 -150 112 -100 Z" fill="#9a5b2e" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M104 -240 Q90 -200 96 -170" stroke="#3a2418" strokeWidth={14} fill="none" strokeLinecap="round" />
      <circle cx={150} cy={-232} r={6} fill={OL} />
      {[-80, -40, 50, 90].map((x, i) => <path key={i} d={`M${x} -80 L${x + (i % 2 ? 8 : -8) * Math.sin(t * 8)} 0`} stroke={OL} strokeWidth={14} strokeLinecap="round" />)}
    </g>
  ),
  elephant: (t) => (
    <g>
      {[-80, -30, 50, 100].map((x, i) => <rect key={i} x={x - 22} y={-80} width={44} height={80} rx={14} fill="#8f9bb0" stroke={OL} strokeWidth={6} />)}
      <ellipse cx={0} cy={-130} rx={140} ry={80} fill="#9aa6bb" stroke={OL} strokeWidth={7} />
      <circle cx={130} cy={-170} r={56} fill="#9aa6bb" stroke={OL} strokeWidth={7} />
      <path d={`M170 -150 Q${210 + Math.sin(t * 3) * 10} -90 190 -30 q-10 22 -26 8`} stroke={OL} strokeWidth={34} fill="none" strokeLinecap="round" />
      <path d={`M170 -150 Q${210 + Math.sin(t * 3) * 10} -90 190 -30 q-10 22 -26 8`} stroke="#9aa6bb" strokeWidth={22} fill="none" strokeLinecap="round" />
      <path d="M156 -138 q24 14 46 4" stroke="#fff" strokeWidth={9} fill="none" strokeLinecap="round" />
      <ellipse cx={80} cy={-170} rx={34} ry={50} fill="#8794ab" stroke={OL} strokeWidth={6} />
      <circle cx={146} cy={-188} r={6} fill={OL} />
    </g>
  ),
  heart: (t) => {
    const b = 1 + Math.abs(Math.sin(t * 6)) * 0.12;
    return (
      <g transform={`translate(0 -110) scale(${b})`}>
        <path d="M0 90 C-170 -20 -90 -130 0 -50 C90 -130 170 -20 0 90 Z" fill="#e11d2e" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
        <path d="M-70 -50 Q-100 -20 -80 10" stroke="#ff8a95" strokeWidth={10} fill="none" strokeLinecap="round" />
      </g>
    );
  },
  brain: (t) => (
    <g transform={`translate(0 ${-110 + Math.sin(t * 2) * 5})`}>
      <path d="M-30 -80 Q-130 -100 -140 -20 Q-170 20 -110 50 Q-100 100 -30 80 Q0 100 30 80 Q100 100 110 50 Q170 20 140 -20 Q130 -100 30 -80 Q0 -96 -30 -80 Z" fill="#f4a3b8" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M0 -84 Q-12 -20 0 80 M-90 -50 Q-60 -30 -80 0 M-100 20 Q-70 30 -60 60 M90 -50 Q60 -30 80 0 M100 20 Q70 30 60 60 M-40 -40 Q-20 -20 -40 0 M40 -40 Q20 -20 40 0" stroke="#d0708c" strokeWidth={5} fill="none" strokeLinecap="round" />
    </g>
  ),
  skull: () => (
    <g transform="translate(0 -110)">
      <path d="M-90 20 Q-110 -100 0 -110 Q110 -100 90 20 Q80 50 50 56 L50 90 L-50 90 L-50 56 Q-80 50 -90 20 Z" fill="#f6f1e6" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <ellipse cx={-36} cy={-6} rx={24} ry={28} fill={OL} /><ellipse cx={36} cy={-6} rx={24} ry={28} fill={OL} />
      <path d="M0 24 l-12 26 l24 0 Z" fill={OL} /><path d="M-30 90 l0 -22 M-10 90 l0 -22 M10 90 l0 -22 M30 90 l0 -22" stroke={OL} strokeWidth={5} />
    </g>
  ),
  eye: (t) => (
    <g transform="translate(0 -110)">
      <path d="M-170 0 Q0 -130 170 0 Q0 130 -170 0 Z" fill="#fff" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
      <circle cx={Math.sin(t * 1.4) * 22} cy={0} r={58} fill="#3b82c4" stroke={OL} strokeWidth={6} />
      <circle cx={Math.sin(t * 1.4) * 22} cy={0} r={26} fill={OL} /><circle cx={Math.sin(t * 1.4) * 22 + 18} cy={-18} r={10} fill="#fff" />
    </g>
  ),
  dna: (t) => (
    <g>
      {Array.from({length: 14}).map((_, i) => {
        const y = -i * 26 - 10;
        const a = Math.sin(i * 0.7 + t * 3) * 70;
        return (
          <g key={i}>
            <path d={`M${-a} ${y} L${a} ${y}`} stroke="#9aa6bb" strokeWidth={6} strokeLinecap="round" />
            <circle cx={-a} cy={y} r={11} fill="#e11d2e" stroke={OL} strokeWidth={4} /><circle cx={a} cy={y} r={11} fill="#3b82c4" stroke={OL} strokeWidth={4} />
          </g>
        );
      })}
    </g>
  ),
  flask: (t) => (
    <g>
      <path d="M-34 -230 L-34 -130 L-120 -10 Q-130 6 -112 6 L112 6 Q130 6 120 -10 L34 -130 L34 -230 Z" fill="#e8f6ff" stroke={OL} strokeWidth={7} strokeLinejoin="round" opacity={0.95} />
      <path d="M-86 -50 Q0 -70 86 -50 L112 -8 Q116 0 106 0 L-106 0 Q-116 0 -112 -8 Z" fill="#4cc27a" />
      <rect x={-44} y={-244} width={88} height={20} rx={6} fill="#c8a06b" stroke={OL} strokeWidth={6} />
      {[0, 1, 2].map((i) => <circle key={i} cx={-20 + i * 24} cy={-60 - ((t * 40 + i * 30) % 90)} r={7 - i} fill="#bff5d0" stroke={OL} strokeWidth={2} />)}
    </g>
  ),
  microscope: () => (
    <g>
      <rect x={-90} y={-24} width={180} height={24} rx={8} fill="#6b7280" stroke={OL} strokeWidth={6} />
      <path d="M-30 -24 L-30 -140 Q-30 -250 60 -250 L60 -210 Q10 -210 10 -140 L10 -24 Z" fill="#8d99ae" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <rect x={-18} y={-290} width={30} height={90} rx={6} fill="#4a5568" stroke={OL} strokeWidth={6} transform="rotate(-18 0 -240)" />
      <rect x={-66} y={-70} width={110} height={14} rx={4} fill="#4a5568" stroke={OL} strokeWidth={5} />
    </g>
  ),
  lightbulb: (t) => (
    <g transform="translate(0 -130)">
      {Array.from({length: 10}).map((_, i) => <path key={i} d="M0 -100 L0 -128" stroke="#ffd23f" strokeWidth={8} strokeLinecap="round" opacity={0.6 + 0.4 * Math.sin(t * 6 + i)} transform={`rotate(${i * 36})`} />)}
      <circle cx={0} cy={0} r={70} fill="#ffe27a" stroke={OL} strokeWidth={7} />
      <path d="M-26 70 L-26 100 L26 100 L26 70" fill="#cfd8dc" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-20 40 Q0 10 20 40 M-12 40 L-12 0 M12 40 L12 0" stroke={OL} strokeWidth={4} fill="none" />
    </g>
  ),
  atom: (t) => (
    <g transform="translate(0 -130)">
      {[0, 60, 120].map((r) => <ellipse key={r} cx={0} cy={0} rx={120} ry={42} fill="none" stroke={OL} strokeWidth={5} transform={`rotate(${r})`} />)}
      {[0, 60, 120].map((r, i) => <circle key={r} cx={Math.cos(t * 3 + i * 2) * 120} cy={Math.sin(t * 3 + i * 2) * 42} r={11} fill="#3b82c4" stroke={OL} strokeWidth={4} transform={`rotate(${r})`} />)}
      <circle cx={0} cy={0} r={24} fill="#e11d2e" stroke={OL} strokeWidth={6} />
    </g>
  ),
  thermometer: (t) => (
    <g>
      <rect x={-22} y={-300} width={44} height={250} rx={22} fill="#fff" stroke={OL} strokeWidth={7} />
      <circle cx={0} cy={-34} r={50} fill="#e11d2e" stroke={OL} strokeWidth={7} />
      <rect x={-9} y={-190 - Math.sin(t * 2) * 20} width={18} height={150 + Math.sin(t * 2) * 20} rx={9} fill="#e11d2e" />
      {[0, 1, 2, 3, 4].map((i) => <path key={i} d={`M22 ${-270 + i * 36} l22 0`} stroke={OL} strokeWidth={4} />)}
    </g>
  ),
  earth: (t) => (
    <g transform="translate(0 -150)">
      <circle cx={0} cy={0} r={130} fill="#4aa3ea" stroke={OL} strokeWidth={8} />
      <clipPath id="clipEarth"><circle cx={0} cy={0} r={126} /></clipPath>
      <g clipPath="url(#clipEarth)" transform={`translate(${(t * 20) % 260 - 130} 0)`}>
        {[0, 260].map((o) => <g key={o} transform={`translate(${o - 260} 0)`}><path d="M-80 -70 Q-30 -110 20 -60 Q0 -10 -40 10 Q-90 0 -80 -70 Z" fill="#5ab04e" /><path d="M40 20 Q100 0 120 50 Q90 110 50 90 Z" fill="#5ab04e" /></g>)}
      </g>
      <ellipse cx={-40} cy={-60} rx={28} ry={16} fill="#fff" opacity={0.25} transform="rotate(-30 -40 -60)" />
    </g>
  ),
  planet: (t) => (
    <g transform={`translate(0 ${-140 + Math.sin(t * 1.4) * 8})`}>
      <ellipse cx={0} cy={0} rx={190} ry={44} fill="none" stroke="#f5c47a" strokeWidth={22} transform="rotate(-18)" />
      <circle cx={0} cy={0} r={100} fill="#e08a4a" stroke={OL} strokeWidth={7} />
      <path d="M-98 -20 Q0 -40 98 -20 M-90 30 Q0 54 90 30" stroke="#c4662e" strokeWidth={10} fill="none" />
      <path d="M-190 8 Q-100 80 0 70 Q-120 100 -190 8 Z" fill="none" />
      <ellipse cx={0} cy={0} rx={190} ry={44} fill="none" stroke="#f5c47a" strokeWidth={22} transform="rotate(-18)" strokeDasharray="190 600" strokeDashoffset={-290} />
    </g>
  ),
  rocket: (t) => (
    <g transform={`translate(0 ${Math.sin(t * 8) * 4})`}>
      <path d={`M-28 0 Q0 ${70 + Math.sin(t * 20) * 22} 28 0 Z`} fill="#ff8c1a" stroke={OL} strokeWidth={5} />
      <path d="M-70 -20 L-120 20 L-60 -50 Z M70 -20 L120 20 L60 -50 Z" fill="#e11d2e" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M0 -300 Q80 -220 70 -20 L-70 -20 Q-80 -220 0 -300 Z" fill="#f1f5f9" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M0 -300 Q40 -260 52 -210 L-52 -210 Q-40 -260 0 -300 Z" fill="#e11d2e" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <circle cx={0} cy={-150} r={30} fill="#6ec1ff" stroke={OL} strokeWidth={7} />
    </g>
  ),
  star: (t) => (
    <g transform={`translate(0 -90) scale(${1 + Math.sin(t * 4) * 0.06}) rotate(${Math.sin(t * 2) * 6})`}>
      <path d="M0 -100 L29 -32 L100 -28 L45 18 L62 88 L0 50 L-62 88 L-45 18 L-100 -28 L-29 -32 Z" fill="#ffd23f" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M0 -70 L18 -26 L-18 -26 Z" fill="#fff3a8" opacity={0.7} />
    </g>
  ),
  blackhole: (t) => (
    <g transform="translate(0 -150)">
      {[0, 1, 2, 3, 4].map((i) => <ellipse key={i} cx={0} cy={0} rx={190 - i * 24} ry={56 - i * 7} fill="none" stroke={['#ff6b35', '#ff9f1c', '#ffd23f', '#fff3a8', '#ffffff'][i]} strokeWidth={10} opacity={0.85} transform={`rotate(${-14 + Math.sin(t * 0.8) * 4})`} />)}
      <circle cx={0} cy={0} r={74} fill="#05050a" stroke="#6a3bd1" strokeWidth={5} />
    </g>
  ),
  cloud: (t) => (
    <g transform={`translate(${Math.sin(t * 0.8) * 14} -150)`}>
      <path d="M-130 20 Q-170 20 -170 -20 Q-170 -60 -120 -60 Q-110 -120 -40 -110 Q10 -150 60 -100 Q130 -110 140 -40 Q180 -30 170 20 Q160 40 120 40 L-110 40 Q-130 40 -130 20 Z" fill="#f5f9ff" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
    </g>
  ),
  rain: (t) => (
    <g>
      <g transform="translate(0 -260) scale(0.9)"><path d="M-130 20 Q-170 20 -170 -20 Q-170 -60 -120 -60 Q-110 -120 -40 -110 Q10 -150 60 -100 Q130 -110 140 -40 Q180 -30 170 20 Q160 40 120 40 L-110 40 Q-130 40 -130 20 Z" fill="#8a97a8" stroke={OL} strokeWidth={7} strokeLinejoin="round" /></g>
      {Array.from({length: 12}).map((_, i) => {
        const p = (t * 1.8 + i * 0.37) % 1;
        return <path key={i} d={`M${-130 + (i % 6) * 52 + (i > 5 ? 26 : 0)} ${-200 + p * 200} l-8 24`} stroke="#4aa3ea" strokeWidth={7} strokeLinecap="round" opacity={1 - p * 0.5} />;
      })}
    </g>
  ),
  lightning: (t) => (
    <g transform="translate(0 -20)" opacity={0.75 + 0.25 * Math.sin(t * 20)}>
      <path d="M30 -300 L-70 -110 L-10 -110 L-50 40 L80 -150 L12 -150 Z" fill="#ffd23f" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
    </g>
  ),
  snowflake: (t) => (
    <g transform={`translate(0 -130) rotate(${t * 20})`}>
      {[0, 60, 120].map((r) => <g key={r} transform={`rotate(${r})`}><path d="M0 -110 L0 110" stroke="#8fc7f0" strokeWidth={10} strokeLinecap="round" /><path d="M-24 -78 L0 -56 L24 -78 M-24 78 L0 56 L24 78" stroke="#8fc7f0" strokeWidth={8} fill="none" strokeLinecap="round" /></g>)}
    </g>
  ),
  tornado: (t) => (
    <g>
      {Array.from({length: 9}).map((_, i) => <ellipse key={i} cx={Math.sin(t * 5 + i) * 12} cy={-i * 34 - 10} rx={30 + i * 17} ry={11 + i * 2} fill="#9aa6b8" stroke={OL} strokeWidth={5} opacity={0.95} />)}
    </g>
  ),
  volcano: (t) => (
    <g>
      <path d="M-220 0 L-60 -230 L60 -230 L220 0 Z" fill="#6b4a3a" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-60 -230 Q0 -200 60 -230 Q0 -250 -60 -230 Z" fill="#ff8a1c" stroke={OL} strokeWidth={5} />
      <path d="M0 -226 q-24 80 12 130 q-30 50 6 96" stroke="#ff8a1c" strokeWidth={12} fill="none" strokeLinecap="round" />
      {Array.from({length: 8}).map((_, i) => {
        const p = (t * 0.9 + i * 0.125) % 1;
        return <circle key={i} cx={Math.sin(i * 2.1) * 120 * p} cy={-240 - 200 * Math.sin(p * Math.PI)} r={14 - 7 * p} fill="#ff6a1a" opacity={1 - p * 0.5} />;
      })}
    </g>
  ),
  house: () => (
    <g>
      <rect x={-120} y={-150} width={240} height={150} fill="#f2d3a0" stroke={OL} strokeWidth={7} />
      <path d="M-148 -150 L0 -260 L148 -150 Z" fill="#c1432f" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <rect x={-26} y={-100} width={52} height={100} rx={6} fill="#7a4b2a" stroke={OL} strokeWidth={6} />
      <rect x={60} y={-120} width={44} height={44} fill="#bfe6fb" stroke={OL} strokeWidth={5} /><rect x={-104} y={-120} width={44} height={44} fill="#bfe6fb" stroke={OL} strokeWidth={5} />
    </g>
  ),
  car: (t) => (
    <g transform={`translate(0 ${Math.sin(t * 20) * 1.5})`}>
      <path d="M-170 -50 L-170 -100 Q-170 -112 -150 -116 L-90 -124 L-50 -176 L70 -176 L116 -124 L160 -112 Q176 -108 176 -90 L176 -50 Z" fill="#e11d2e" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-70 -124 L-44 -166 L22 -166 L22 -124 Z M40 -124 L40 -166 L64 -166 L98 -124 Z" fill="#bfe6fb" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
      {[-100, 100].map((x) => <g key={x} transform={`translate(${x} -40)`}><circle r={40} fill="#2b2b36" stroke={OL} strokeWidth={6} /><circle r={18} fill="#cfd8dc" /><path d="M0 -18 L0 18 M-18 0 L18 0" stroke={OL} strokeWidth={4} transform={`rotate(${t * 300})`} /></g>)}
    </g>
  ),
  key: () => (
    <g transform="translate(0 -110) rotate(-28)">
      <circle cx={-90} cy={0} r={46} fill="#ffd23f" stroke={OL} strokeWidth={7} /><circle cx={-90} cy={0} r={18} fill="#fbf4df" stroke={OL} strokeWidth={5} />
      <rect x={-50} y={-14} width={170} height={28} fill="#ffd23f" stroke={OL} strokeWidth={7} />
      <path d="M80 14 L80 50 L104 50 L104 14 M114 14 L114 40 L132 40 L132 14" fill="#ffd23f" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
    </g>
  ),
  lock: () => (
    <g transform="translate(0 -20)">
      <path d="M-50 -130 L-50 -190 Q-50 -250 0 -250 Q50 -250 50 -190 L50 -130" fill="none" stroke={OL} strokeWidth={26} strokeLinecap="round" />
      <path d="M-50 -130 L-50 -190 Q-50 -250 0 -250 Q50 -250 50 -190 L50 -130" fill="none" stroke="#cfd8dc" strokeWidth={14} strokeLinecap="round" />
      <rect x={-90} y={-140} width={180} height={140} rx={16} fill="#ffd23f" stroke={OL} strokeWidth={7} />
      <circle cx={0} cy={-84} r={16} fill={OL} /><rect x={-6} y={-84} width={12} height={34} fill={OL} />
    </g>
  ),
  hourglass: (t) => {
    const p = (t * 0.25) % 1;
    return (
      <g>
        <path d="M-80 -300 L80 -300 L80 -270 Q80 -190 14 -150 Q80 -110 80 -30 L80 0 L-80 0 L-80 -30 Q-80 -110 -14 -150 Q-80 -190 -80 -270 Z" fill="#e8f6ff" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
        <path d={`M-60 ${-270 + p * 60} L60 ${-270 + p * 60} Q40 -210 4 -160 L-4 -160 Q-40 -210 -60 ${-270 + p * 60} Z`} fill="#ffc94a" />
        <path d={`M0 -150 L0 -${30 + p * 0} `} stroke="#ffc94a" strokeWidth={5} />
        <path d={`M-60 -6 Q0 ${-30 - p * 70} 60 -6 Z`} fill="#ffc94a" />
        <rect x={-96} y={-318} width={192} height={22} rx={8} fill="#a8713c" stroke={OL} strokeWidth={6} /><rect x={-96} y={-4} width={192} height={22} rx={8} fill="#a8713c" stroke={OL} strokeWidth={6} />
      </g>
    );
  },
  clock: (t) => (
    <g transform="translate(0 -130)">
      <circle cx={0} cy={0} r={118} fill="#fff" stroke={OL} strokeWidth={9} />
      {Array.from({length: 12}).map((_, i) => <path key={i} d="M0 -100 L0 -86" stroke={OL} strokeWidth={i % 3 ? 4 : 8} transform={`rotate(${i * 30})`} />)}
      <path d="M0 0 L0 -62" stroke={OL} strokeWidth={9} strokeLinecap="round" transform={`rotate(${t * 6})`} />
      <path d="M0 0 L0 -88" stroke="#e11d2e" strokeWidth={6} strokeLinecap="round" transform={`rotate(${t * 72})`} />
      <circle cx={0} cy={0} r={10} fill={OL} />
    </g>
  ),
  flag: (t) => (
    <g>
      <path d="M-100 0 L-100 -330" stroke={OL} strokeWidth={10} strokeLinecap="round" />
      <path d={`M-100 -330 Q-30 ${-350 + Math.sin(t * 5) * 14} 40 -330 T180 -330 L180 -210 Q110 ${-190 + Math.sin(t * 5 + 1) * 14} 40 -210 T-100 -210 Z`} fill="#e11d2e" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <circle cx={40} cy={-270} r={30} fill="#fff" opacity={0.9} />
    </g>
  ),
  shield: () => (
    <g transform="translate(0 -10)">
      <path d="M-110 -250 L110 -250 L110 -110 Q110 -30 0 20 Q-110 -30 -110 -110 Z" fill="#1d4e89" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
      <path d="M0 -250 L0 20 M-110 -150 L110 -150" stroke="#ffd23f" strokeWidth={14} />
      <path d="M-110 -250 L110 -250 L110 -110 Q110 -30 0 20 Q-110 -30 -110 -110 Z" fill="none" stroke="#ffd23f" strokeWidth={6} />
    </g>
  ),
  bow: (t) => (
    <g transform="translate(0 -130)">
      <path d="M-30 -150 Q110 0 -30 150" fill="none" stroke="#8d5a2b" strokeWidth={14} strokeLinecap="round" />
      <path d={`M-30 -150 L${-30 - Math.abs(Math.sin(t * 2)) * 40} 0 L-30 150`} fill="none" stroke={OL} strokeWidth={4} />
      <path d={`M${-70 - Math.abs(Math.sin(t * 2)) * 40} 0 L150 0`} stroke={OL} strokeWidth={7} strokeLinecap="round" />
      <path d="M150 0 L126 -14 L126 14 Z" fill="#cfd8dc" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
    </g>
  ),
  cannon: (t) => (
    <g>
      <path d="M-120 -120 L120 -170 L136 -120 L-104 -70 Z" fill="#4a5568" stroke={OL} strokeWidth={7} strokeLinejoin="round" transform="rotate(-6 0 -100)" />
      <circle cx={-40} cy={-44} r={52} fill="#8d5a2b" stroke={OL} strokeWidth={7} /><circle cx={-40} cy={-44} r={14} fill="#cfd8dc" stroke={OL} strokeWidth={4} />
      <circle cx={170} cy={-190 - (t * 120) % 80} r={16} fill="#2b2b36" opacity={(t * 1.4) % 1 < 0.4 ? 1 : 0} />
    </g>
  ),
  torch: (t) => {
    const f = 1 + Math.sin(t * 14) * 0.1;
    return (
      <g>
        <path d="M-12 0 L-8 -190 L8 -190 L12 0 Z" fill="#8d5a2b" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
        <path d={`M-40 -190 Q-30 ${-290 * f} 0 ${-340 * f} Q30 ${-280 * f} 40 -190 Z`} fill="#ff8c1a" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
        <path d={`M-18 -190 Q-10 ${-250 * f} 0 ${-280 * f} Q12 ${-240 * f} 18 -190 Z`} fill="#ffd25a" />
      </g>
    );
  },
  bridge: () => (
    <g>
      <rect x={-260} y={-90} width={520} height={30} fill="#b8a07a" stroke={OL} strokeWidth={7} />
      <path d="M-230 -60 Q-230 -4 -170 0 L-110 0 Q-50 -4 -50 -60 M50 -60 Q50 -4 110 0 L170 0 Q230 -4 230 -60" fill="#b8a07a" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-260 -130 L260 -130 M-200 -130 L-200 -90 M-100 -130 L-100 -90 M0 -130 L0 -90 M100 -130 L100 -90 M200 -130 L200 -90" stroke={OL} strokeWidth={6} />
    </g>
  ),
  column: () => (
    <g>
      <rect x={-70} y={-24} width={140} height={24} fill="#efe2c4" stroke={OL} strokeWidth={6} />
      <path d="M-44 -24 L-38 -280 L38 -280 L44 -24 Z" fill="#f6ecd5" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-18 -30 L-16 -276 M0 -30 L0 -276 M18 -30 L16 -276" stroke="#d9c79a" strokeWidth={5} />
      <rect x={-64} y={-308} width={128} height={30} rx={8} fill="#efe2c4" stroke={OL} strokeWidth={6} />
      <circle cx={-64} cy={-293} r={14} fill="#efe2c4" stroke={OL} strokeWidth={5} /><circle cx={64} cy={-293} r={14} fill="#efe2c4" stroke={OL} strokeWidth={5} />
    </g>
  ),
  statue: () => (
    <g>
      <rect x={-90} y={-70} width={180} height={70} fill="#cfd4dc" stroke={OL} strokeWidth={7} />
      <path d="M-50 -70 Q-60 -200 -30 -250 L30 -250 Q60 -200 50 -70 Z" fill="#dfe3ea" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <circle cx={0} cy={-286} r={38} fill="#dfe3ea" stroke={OL} strokeWidth={7} />
      <path d="M-16 -292 l8 0 M8 -292 l8 0 M-8 -270 l16 0" stroke={OL} strokeWidth={5} strokeLinecap="round" />
    </g>
  ),
  throne: () => (
    <g>
      <path d="M-90 0 L-90 -60 L90 -60 L90 0 Z" fill="#a8222c" stroke={OL} strokeWidth={7} />
      <path d="M-70 -60 L-70 -320 Q0 -370 70 -320 L70 -60 Z" fill="#ffd23f" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-50 -90 L50 -90 L50 -280 Q0 -310 -50 -280 Z" fill="#a8222c" stroke={OL} strokeWidth={6} />
      <rect x={-100} y={-140} width={34} height={86} rx={8} fill="#ffd23f" stroke={OL} strokeWidth={6} /><rect x={66} y={-140} width={34} height={86} rx={8} fill="#ffd23f" stroke={OL} strokeWidth={6} />
    </g>
  ),
  chariot: (t) => (
    <g transform={`translate(0 ${Math.sin(t * 16) * 2})`}>
      <path d="M-100 -80 L100 -80 L100 -170 Q100 -190 80 -190 L-60 -190 Q-100 -150 -100 -80 Z" fill="#c8a06b" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M100 -130 L240 -100" stroke={OL} strokeWidth={9} strokeLinecap="round" />
      <g transform="translate(0 -52)"><circle r={52} fill="#8d5a2b" stroke={OL} strokeWidth={7} />{[0, 45, 90, 135].map((r) => <path key={r} d="M0 -48 L0 48" stroke={OL} strokeWidth={5} transform={`rotate(${r + t * 200})`} />)}<circle r={10} fill="#ffd23f" stroke={OL} strokeWidth={4} /></g>
    </g>
  ),
  tablet: () => (
    <g transform="translate(0 -20) rotate(-4)">
      <path d="M-100 -240 Q-110 -120 -96 -10 L100 0 Q112 -120 96 -230 Z" fill="#c98f5a" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      {[0, 1, 2, 3, 4].map((r) => <g key={r}>{[0, 1, 2, 3, 4].map((c) => <path key={c} d={`M${-70 + c * 32} ${-200 + r * 40} l16 8 l-16 8 M${-70 + c * 32 + 6} ${-200 + r * 40 + 16} l-6 -10`} stroke="#6b3f1f" strokeWidth={4} fill="none" strokeLinecap="round" />)}</g>)}
    </g>
  ),
  helmet: () => (
    <g transform="translate(0 -20)">
      <path d="M-100 0 Q-110 -150 0 -160 Q110 -150 100 0 L60 0 L60 -50 L-60 -50 L-60 0 Z" fill="#b87333" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
      <path d="M-14 -160 Q0 -250 40 -230 Q60 -200 14 -160 Z" fill="#c1121f" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-60 -50 L60 -50 M-24 -50 L-24 -10" stroke={OL} strokeWidth={5} />
    </g>
  ),
  spear: () => (
    <g transform="translate(0 0) rotate(8)">
      <path d="M0 0 L0 -340" stroke="#8d5a2b" strokeWidth={12} strokeLinecap="round" />
      <path d="M0 -420 L-24 -336 L24 -336 Z" fill="#cfd8dc" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
    </g>
  ),
  anchor: () => (
    <g transform="translate(0 -20)">
      <circle cx={0} cy={-250} r={26} fill="none" stroke={OL} strokeWidth={14} />
      <path d="M0 -224 L0 -30 M-70 -190 L70 -190" stroke={OL} strokeWidth={14} strokeLinecap="round" />
      <path d="M-120 -90 Q-110 -20 0 -20 Q110 -20 120 -90" fill="none" stroke={OL} strokeWidth={14} strokeLinecap="round" />
      <path d="M-120 -90 l-22 22 M120 -90 l22 22" stroke={OL} strokeWidth={14} strokeLinecap="round" />
    </g>
  ),
  compass: (t) => (
    <g transform="translate(0 -130)">
      <circle cx={0} cy={0} r={120} fill="#f8f0d8" stroke={OL} strokeWidth={9} /><circle cx={0} cy={0} r={100} fill="none" stroke="#a8803a" strokeWidth={4} />
      {['N', 'E', 'S', 'W'].map((c, i) => <text key={c} x={0} y={-76} textAnchor="middle" fontSize={26} fontWeight={900} fill={OL} transform={`rotate(${i * 90})`}>{c}</text>)}
      <g transform={`rotate(${Math.sin(t * 1.5) * 25 + 20})`}><path d="M0 -84 L16 0 L-16 0 Z" fill="#e11d2e" stroke={OL} strokeWidth={4} strokeLinejoin="round" /><path d="M0 84 L16 0 L-16 0 Z" fill="#fff" stroke={OL} strokeWidth={4} strokeLinejoin="round" /></g>
      <circle cx={0} cy={0} r={8} fill={OL} />
    </g>
  ),
  telescope: () => (
    <g transform="translate(0 0)">
      <path d="M-60 0 L0 -130 L60 0 M0 -130 L0 0" stroke={OL} strokeWidth={9} fill="none" strokeLinecap="round" />
      <g transform="translate(0 -150) rotate(-28)"><rect x={-130} y={-24} width={260} height={48} rx={8} fill="#3b82c4" stroke={OL} strokeWidth={7} /><rect x={90} y={-34} width={60} height={68} rx={8} fill="#1d4e89" stroke={OL} strokeWidth={6} /><rect x={-150} y={-16} width={30} height={32} rx={6} fill="#8d99ae" stroke={OL} strokeWidth={5} /></g>
    </g>
  ),
  obelisk: () => (
    <g>
      <rect x={-80} y={-24} width={160} height={24} fill="#d9c79a" stroke={OL} strokeWidth={6} />
      <path d="M-46 -24 L-30 -340 L30 -340 L46 -24 Z" fill="#e6d4a8" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-30 -340 L0 -400 L30 -340 Z" fill="#ffd23f" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <path d="M-14 -280 l28 0 M-12 -230 l24 0 M-10 -180 l20 0 M-8 -130 l16 0" stroke="#a8803a" strokeWidth={5} />
    </g>
  ),
  ziggurat: () => (
    <g>
      {[0, 1, 2, 3].map((i) => <rect key={i} x={-220 + i * 44} y={-(i + 1) * 62} width={440 - i * 88} height={62} fill={['#d8b878', '#e0c288', '#e8cc98', '#f0d6a8'][i]} stroke={OL} strokeWidth={6} />)}
      <path d="M-26 0 L-26 -62 L26 -62 L26 0 Z" fill="#6b4a2e" stroke={OL} strokeWidth={5} />
    </g>
  ),
  colosseum: () => (
    <g>
      <path d="M-260 0 L-260 -180 Q0 -250 260 -180 L260 0 Z" fill="#e0c9a0" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      {[0, 1, 2].map((r) => <g key={r}>{Array.from({length: 9}).map((_, c) => <path key={c} d={`M${-216 + c * 54} ${-30 - r * 50} L${-216 + c * 54} ${-58 - r * 50} A14 14 0 0 1 ${-188 + c * 54} ${-58 - r * 50} L${-188 + c * 54} ${-30 - r * 50} Z`} fill="#8a6a44" stroke={OL} strokeWidth={3} />)}</g>)}
    </g>
  ),
  wall: () => (
    <g>
      <path d="M-300 0 L-300 -120 L-250 -120 L-250 -150 L-210 -150 L-210 -120 L-170 -120 L-170 -150 L-130 -150 L-130 -120 L-60 -120 L-60 -150 L-20 -150 L-20 -120 L300 -120 L300 0 Z" fill="#b9a789" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <rect x={-90} y={-280} width={120} height={280} fill="#a8967a" stroke={OL} strokeWidth={7} /><path d="M-100 -280 L-60 -330 L40 -330 L40 -280 Z" fill="#c1432f" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
      <rect x={-50} y={-220} width={40} height={50} rx={20} fill="#3b2f2f" />
    </g>
  ),
  moneybag: () => (
    <g>
      <path d="M-50 -210 Q0 -240 50 -210 L30 -170 Q130 -100 100 -30 Q80 0 0 0 Q-80 0 -100 -30 Q-130 -100 -30 -170 Z" fill="#c8a06b" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-34 -176 L34 -176" stroke={OL} strokeWidth={9} strokeLinecap="round" />
      <text x={0} y={-60} textAnchor="middle" fontSize={84} fontWeight={900} fill="#2b2b36" style={{fontFamily: FONT}}>$</text>
    </g>
  ),
  trophy: () => (
    <g>
      <rect x={-60} y={-30} width={120} height={30} rx={6} fill="#8d5a2b" stroke={OL} strokeWidth={6} />
      <path d="M-14 -30 L-14 -90 M14 -30 L14 -90" stroke={OL} strokeWidth={10} /><rect x={-40} y={-100} width={80} height={20} rx={6} fill="#e6b422" stroke={OL} strokeWidth={6} />
      <path d="M-90 -250 L90 -250 Q90 -130 0 -104 Q-90 -130 -90 -250 Z" fill="#ffd23f" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d="M-90 -230 Q-140 -230 -130 -180 Q-120 -150 -80 -150 M90 -230 Q140 -230 130 -180 Q120 -150 80 -150" fill="none" stroke={OL} strokeWidth={8} />
    </g>
  ),
  ballet: (t) => (
    <g transform={`rotate(${Math.sin(t * 3) * 3} 0 0)`}>
      {[-1, 1].map((sd) => (
        <g key={sd} transform={`translate(${sd * 80} 0) rotate(${sd * 10})`}>
          <path d="M-34 0 Q-50 -60 -22 -130 L26 -170 L40 -150 Q30 -90 44 -20 Q40 0 0 0 Z" fill="#f4a8a8" stroke={OL} strokeWidth={6} strokeLinejoin="round" />
          <path d="M-26 -34 Q10 -50 40 -30 M-10 -70 Q20 -86 34 -64" stroke="#e57a86" strokeWidth={6} fill="none" />
          <path d={`M-16 -116 Q-70 ${-90 + Math.sin(t * 4 + sd) * 10} -60 ${-20 + Math.sin(t * 4) * 8} M-10 -126 Q-90 -110 -86 ${-50 + Math.sin(t * 4 + 1) * 8}`} stroke="#e57a86" strokeWidth={7} fill="none" strokeLinecap="round" />
        </g>
      ))}
    </g>
  ),
  note: (t) => (
    <g transform={`translate(0 ${-30 + Math.sin(t * 4) * 8})`}>
      <ellipse cx={-30} cy={-40} rx={38} ry={28} fill={OL} transform="rotate(-20 -30 -40)" />
      <path d="M2 -48 L2 -250 Q70 -230 90 -170" stroke={OL} strokeWidth={14} fill="none" strokeLinecap="round" />
    </g>
  ),
  question: (t) => (
    <g transform={`translate(0 ${-130 + Math.sin(t * 3) * 8}) rotate(${Math.sin(t * 2) * 5})`}>
      <text x={0} y={90} textAnchor="middle" fontSize={300} fontWeight={900} fill="#e11d2e" stroke={OL} strokeWidth={10} style={{fontFamily: FONT, paintOrder: 'stroke fill'}}>؟</text>
    </g>
  ),
  exclaim: (t) => (
    <g transform={`translate(0 ${-130 + Math.sin(t * 4) * 8}) rotate(${Math.sin(t * 3) * 5})`}>
      <text x={0} y={90} textAnchor="middle" fontSize={300} fontWeight={900} fill="#e11d2e" stroke={OL} strokeWidth={10} style={{fontFamily: FONT, paintOrder: 'stroke fill'}}>!</text>
    </g>
  ),
  warning: (t) => (
    <g transform={`translate(0 ${-20 + Math.sin(t * 6) * 3})`}>
      <path d="M0 -270 L140 -20 L-140 -20 Z" fill="#ffd23f" stroke={OL} strokeWidth={9} strokeLinejoin="round" />
      <path d="M0 -190 L0 -100" stroke={OL} strokeWidth={20} strokeLinecap="round" /><circle cx={0} cy={-62} r={12} fill={OL} />
    </g>
  ),
  forbidden: () => (
    <g transform="translate(0 -130)">
      <circle cx={0} cy={0} r={110} fill="none" stroke="#e11d2e" strokeWidth={28} />
      <path d="M-78 -78 L78 78" stroke="#e11d2e" strokeWidth={28} strokeLinecap="round" />
    </g>
  ),
  check: () => (
    <g transform="translate(0 -130)">
      <circle cx={0} cy={0} r={110} fill="#22a06b" stroke={OL} strokeWidth={8} />
      <path d="M-56 4 L-16 46 L60 -40" stroke="#fff" strokeWidth={26} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </g>
  ),
  cross: () => (
    <g transform="translate(0 -130)">
      <circle cx={0} cy={0} r={110} fill="#e11d2e" stroke={OL} strokeWidth={8} />
      <path d="M-50 -50 L50 50 M50 -50 L-50 50" stroke="#fff" strokeWidth={26} strokeLinecap="round" />
    </g>
  ),
  cup: (t) => (
    <g>
      <path d="M-70 -170 L-56 -10 Q-54 0 -40 0 L40 0 Q54 0 56 -10 L70 -170 Z" fill="#e8f6ff" stroke={OL} strokeWidth={7} strokeLinejoin="round" opacity={0.95} />
      <path d={`M-64 -110 Q-20 ${-122 + Math.sin(t * 3) * 4} 0 -110 T64 -110 L55 -12 Q54 -4 40 -4 L-40 -4 Q-54 -4 -55 -12 Z`} fill="#6ec1ff" opacity={0.85} />
    </g>
  ),
  crowd: (t) => (
    <g>
      {[-190, -95, 0, 95, 190].map((x, i) => (
        <g key={i} transform={`translate(${x} ${-Math.abs(Math.sin(t * 5 + i)) * 10})`}>
          <circle cx={0} cy={-160} r={20} fill="#fff" stroke={OL} strokeWidth={6} />
          <path d="M0 -140 L0 -70 M0 -120 L-30 -86 M0 -120 L30 -86 M0 -70 L-22 0 M0 -70 L22 0" stroke={OL} strokeWidth={8} strokeLinecap="round" fill="none" />
        </g>
      ))}
    </g>
  ),
  magnifier: (t) => (
    <g transform={`translate(0 -130) rotate(${Math.sin(t * 2) * 8})`}>
      <path d="M60 60 L150 150" stroke="#8d5a2b" strokeWidth={26} strokeLinecap="round" />
      <circle cx={0} cy={0} r={90} fill="#d5eefc" stroke={OL} strokeWidth={14} opacity={0.9} />
      <path d="M-50 -30 Q-30 -60 10 -62" stroke="#fff" strokeWidth={10} fill="none" strokeLinecap="round" />
    </g>
  ),
  sarcophagus: () => (
    <g transform="translate(0 -20) rotate(-3)">
      <path d="M-70 -300 Q0 -350 70 -300 L90 -160 L70 0 L-70 0 L-90 -160 Z" fill="#e6b422" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
      <path d="M-62 -290 Q0 -330 62 -290 L50 -200 L-50 -200 Z" fill="#1d4e89" stroke={OL} strokeWidth={5} strokeLinejoin="round" />
      <circle cx={-20} cy={-250} r={7} fill={OL} /><circle cx={20} cy={-250} r={7} fill={OL} /><path d="M-14 -222 L14 -222" stroke={OL} strokeWidth={5} strokeLinecap="round" />
      <path d="M-50 -160 L50 -160 M-56 -120 L56 -120 M-58 -80 L58 -80 M-46 -40 L46 -40" stroke="#1d4e89" strokeWidth={8} />
    </g>
  ),
  wheel: (t) => (
    <g transform="translate(0 -110)">
      <circle r={110} fill="#a8713c" stroke={OL} strokeWidth={9} />
      {[0, 30, 60, 90, 120, 150].map((r) => <path key={r} d="M0 -100 L0 100" stroke={OL} strokeWidth={8} transform={`rotate(${r + t * 90})`} />)}
      <circle r={22} fill="#ffd23f" stroke={OL} strokeWidth={6} />
    </g>
  ),
  pickaxe: (t) => (
    <g transform={`translate(0 0) rotate(${-20 + Math.sin(t * 5) * 14} 0 0)`}>
      <path d="M0 0 L0 -280" stroke="#8d5a2b" strokeWidth={14} strokeLinecap="round" />
      <path d="M-120 -250 Q0 -330 120 -250 Q0 -290 -120 -250 Z" fill="#8d99ae" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
    </g>
  ),
  lamp: (t) => (
    <g>
      <path d="M-80 -30 Q-90 -90 -20 -96 L40 -96 Q100 -90 110 -50 L150 -80 L120 -20 Q100 0 20 0 L-60 0 Q-80 0 -80 -30 Z" fill="#d4a24a" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <path d={`M-70 -92 Q-110 ${-150 - Math.sin(t * 12) * 6} -86 -190 Q-60 ${-150 - Math.sin(t * 12) * 6} -70 -92 Z`} fill="#ff9f1c" stroke={OL} strokeWidth={5} strokeLinejoin="round" transform="translate(30 0)" />
    </g>
  ),
  mask: () => (
    <g transform="translate(0 -120)">
      <path d="M-100 -60 Q0 -110 100 -60 Q120 40 60 100 Q0 140 -60 100 Q-120 40 -100 -60 Z" fill="#f5e7c8" stroke={OL} strokeWidth={8} strokeLinejoin="round" />
      <path d="M-70 -10 Q-40 -34 -14 -8 Q-40 16 -70 -10 Z M70 -10 Q40 -34 14 -8 Q40 16 70 -10 Z" fill={OL} />
      <path d="M-30 70 Q0 94 30 70" stroke={OL} strokeWidth={8} fill="none" strokeLinecap="round" />
    </g>
  ),
  sword: () => (
    <g transform="translate(0 0) rotate(-10)">
      <path d="M0 -20 L-14 -330 L0 -380 L14 -330 Z" fill="#dfe6ee" stroke={OL} strokeWidth={7} strokeLinejoin="round" />
      <rect x={-60} y={-40} width={120} height={20} rx={8} fill="#c8a24b" stroke={OL} strokeWidth={6} />
      <rect x={-9} y={-20} width={18} height={70} fill="#6b3f1f" stroke={OL} strokeWidth={5} /><circle cx={0} cy={58} r={14} fill="#c8a24b" stroke={OL} strokeWidth={5} />
    </g>
  ),
};
const PROP_ALL: Record<string, (t: number) => React.ReactNode> = {...PROP_DRAW, ...PROP_NEW};
// عناصر تطفو بالجو (قاعدتها نسبة من ارتفاع الشاشة بدل الأرض)
const PROP_FLOAT: Record<string, number> = {sun: 0.27, moon: 0.27, crown: 0.6, star: 0.34, cloud: 0.42, rain: 0.52, lightning: 0.52, bird: 0.38, bee: 0.46,
  rocket: 0.58, earth: 0.55, planet: 0.52, blackhole: 0.55, snowflake: 0.5, heart: 0.58, brain: 0.58, skull: 0.58, eye: 0.58, lightbulb: 0.58,
  question: 0.5, exclaim: 0.5, note: 0.5, key: 0.58, clock: 0.58, atom: 0.58, compass: 0.58, mask: 0.58, fish: 0.6, shark: 0.62, octopus: 0.7, whale: 0.7, magnifier: 0.58, check: 0.58, cross: 0.58, forbidden: 0.58, lock: 0.66};
const PROP_SCALE: Record<string, number> = {pyramid: 1, city: 1, mountain: 1.1, castle: 1, colosseum: 0.9, wall: 0.9, wave: 1.3};
const PROP_NAMES = Object.keys(PROP_ALL);

const HostInset: React.FC<{frame: number; fps: number; envelope: number[]; expression: string; pal: {robe: string; turban: string; skin: string}}> = (
  {frame, fps, envelope, expression, pal},
) => {
  const e = envelope[frame] ?? 0;
  const mood = (expression || 'neutral') as Mood;
  const pose: Pose = {
    headAngle: Math.sin(frame / 22) * 3 + e * Math.sin(frame * 0.35) * 2.2,
    armL: -22 + Math.sin(frame / 18) * 3 + e * 4,
    armR: 22 - Math.sin(frame / 18 + 1) * 3 - e * 4,
    bob: Math.sin(frame / 25) * 4,
    mouth: Math.min(1, e * 1.25),
    blink: interpolate(frame % 95, [0, 3, 6], [0, 1, 0], {extrapolateRight: 'clamp'}),
    brow: mood === 'surprised' ? 1 : mood === 'sad' ? -1 : 0,
    mood,
  };
  return (
    <div style={{position: 'absolute', right: 28, bottom: 28, width: 250, height: 270, borderRadius: 26, overflow: 'hidden',
      border: '6px solid #fff', boxShadow: '0 10px 30px rgba(0,0,0,0.5)', background: 'linear-gradient(180deg,#f7efd9,#e8d5a8)'}}>
      <svg viewBox="700 200 520 560" style={ABS}>
        <Character pose={pose} x={960} y={310} scale={1.3} robe={pal.robe} turban={pal.turban} skin={pal.skin} />
      </svg>
    </div>
  );
};

// ============ أنواع المشاهد ============
type Actor = {role: string; action: string; pos: string; flip?: boolean; expr?: string};
type PropItem = {name?: string; icon?: string; emoji?: string; pos: string; size: string};
type Bubble = {kind: string; text?: string; icon?: string; emoji?: string};
type BarItem = {label: string; text: string; value: number; icon?: string; emoji?: string};
type Side = {title: string; icon?: string; emoji?: string; level?: number; note?: string};
type Shot = {
  from: number; to: number; text: string; scene: string; bg: string; actors: Actor[]; props: PropItem[];
  camera: string; transition: string; callout: string; label: string; host: boolean; sfx: string;
  mapFrom?: string; mapTo?: string; setting?: string; expression?: string; icon?: string; emoji?: string; question?: boolean;
  bubble?: Bubble; items?: BarItem[]; count?: number; left?: Side; right?: Side; level?: number; tags?: string[];
};

// إيموجي قديم -> مجسم مرسوم بالكود (احتياط لو المخرج رجّع إيموجي)
const EMO2PROP: Record<string, string> = {
  '🕷️': 'spider', '🕷': 'spider', '🐝': 'bee', '🐟': 'fish', '🐋': 'whale', '🐬': 'whale', '🐙': 'octopus', '🐢': 'turtle', '🐦': 'bird',
  '🐍': 'snake', '❤️': 'heart', '❤': 'heart', '🧠': 'brain', '👁️': 'eye', '👁': 'eye', '💧': 'cup', '🔥': 'fire', '☀️': 'sun', '☀': 'sun',
  '🌙': 'moon', '⭐': 'star', '🪐': 'planet', '🌍': 'earth', '🚀': 'rocket', '🕳️': 'blackhole', '⚡': 'lightning', '🌧️': 'rain', '❄️': 'snowflake',
  '🌊': 'wave', '⛰️': 'mountain', '🌋': 'volcano', '🔬': 'microscope', '🧪': 'flask', '🚗': 'car', '⏳': 'hourglass', '📅': 'clock', '💰': 'moneybag',
  '🪙': 'coins', '📖': 'book', '👑': 'crown', '⚔️': 'swords', '🛡️': 'shield', '🚢': 'ship', '🔺': 'pyramid', '🏙️': 'city', '🏰': 'castle',
  '🗺️': 'compass', '❓': 'question', '⚠️': 'warning', '🌡️': 'thermometer', '💨': 'tornado', '🧍': 'crowd', '💡': 'lightbulb', '🔎': 'magnifier',
  '📌': 'flag', '🏠': 'house', '🐴': 'horse', '🐘': 'elephant', '🦈': 'shark', '💀': 'skull', '🧬': 'dna', '⚛️': 'atom', '🎵': 'note', '🩰': 'ballet',
  '🏆': 'trophy', '🔑': 'key', '🔒': 'lock', '⚓': 'anchor', '🧭': 'compass', '🔭': 'telescope', '🏛️': 'column', '🗿': 'statue', '🏺': 'pot',
};
const iconOf = (o: any): string => {
  const n = (o && (o.icon || o.name || o.emoji)) || '';
  if (PROP_ALL[n]) return n;
  return EMO2PROP[n] || 'question';
};

const SIZES: Record<string, number> = {small: 0.62, medium: 1, large: 1.5};

// ============ مجسم مرسوم بالكود مع ظهور "رسم" تدريجي ============
const PropView: React.FC<{name: string; x: number; base: number; size: number; local: number; delay?: number; ground?: boolean}> = (
  {name, x, base, size, local, delay = 0, ground = true},
) => {
  const draw = PROP_ALL[name] ?? PROP_ALL.question;
  const l = local - delay;
  if (l < 0) return null;
  const t = l / 24;
  const p = clamp01(l / 16);
  const pop = 0.82 + 0.18 * easeBack(l / 14);
  const reveal = easeOut(p);
  const cid = 'rv' + name + Math.round(x) + delay;
  const bob = ground ? 0 : Math.sin(t * 2.2) * 8;
  return (
    <g transform={'translate(' + x + ' ' + (base + bob) + ') scale(' + size * pop + ')'}>
      {ground && <ellipse cx={0} cy={6} rx={150} ry={16} fill="rgba(0,0,0,0.16)" />}
      {p < 1 && <clipPath id={cid}><rect x={-800} y={-800 * reveal} width={1600} height={800 * reveal + 80} /></clipPath>}
      <g clipPath={p < 1 ? 'url(#' + cid + ')' : undefined} opacity={clamp01(l / 5)}>{draw(t)}</g>
      {p < 1 && <path d={'M-120 ' + -800 * reveal + ' L120 ' + -800 * reveal} stroke="#ffd23f" strokeWidth={6} strokeLinecap="round" opacity={0.7} />}
    </g>
  );
};

const BubbleView: React.FC<{b: Bubble; ax: number; ay: number; local: number}> = ({b, ax, ay, local}) => {
  const w = useWorld();
  const pop = easeBack((local - 10) / 12);
  if (local < 10) return null;
  const thought = b.kind === 'thought';
  const txt = b.text || '';
  const bw = Math.min(w.W * 0.7, Math.max(300, 120 + txt.length * 44)) + (b.icon || b.emoji ? 130 : 0);
  const bh = 190;
  const cx = Math.min(w.W - bw / 2 - 30, Math.max(bw / 2 + 30, ax));
  const cy = Math.max(bh / 2 + 120, ay);
  const ic = (b.icon || b.emoji) ? iconOf(b) : '';
  return (
    <g transform={'translate(' + cx + ' ' + cy + ') scale(' + pop + ')'}>
      {thought ? (
        <g>
          <ellipse cx={0} cy={0} rx={bw / 2} ry={bh / 2 + 20} fill="#fff" stroke={INK} strokeWidth={7} />
          <circle cx={(ax - cx) * 0.3} cy={bh / 2 + 50} r={24} fill="#fff" stroke={INK} strokeWidth={6} />
          <circle cx={(ax - cx) * 0.5} cy={bh / 2 + 100} r={14} fill="#fff" stroke={INK} strokeWidth={5} />
        </g>
      ) : (
        <path d={'M' + (-bw / 2 + 24) + ' ' + -bh / 2 + ' L' + (bw / 2 - 24) + ' ' + -bh / 2 + ' Q' + bw / 2 + ' ' + -bh / 2 + ' ' + bw / 2 + ' ' + (-bh / 2 + 24) + ' L' + bw / 2 + ' ' + (bh / 2 - 24) + ' Q' + bw / 2 + ' ' + bh / 2 + ' ' + (bw / 2 - 24) + ' ' + bh / 2 + ' L' + ((ax - cx) * 0.3 + 30) + ' ' + bh / 2 + ' L' + (ax - cx) * 0.35 + ' ' + (bh / 2 + 70) + ' L' + ((ax - cx) * 0.3 - 30) + ' ' + bh / 2 + ' L' + (-bw / 2 + 24) + ' ' + bh / 2 + ' Q' + -bw / 2 + ' ' + bh / 2 + ' ' + -bw / 2 + ' ' + (bh / 2 - 24) + ' L' + -bw / 2 + ' ' + (-bh / 2 + 24) + ' Q' + -bw / 2 + ' ' + -bh / 2 + ' ' + (-bw / 2 + 24) + ' ' + -bh / 2 + ' Z'}
          fill="#fff" stroke={INK} strokeWidth={7} strokeLinejoin="round" />
      )}
      {ic && <g transform={'translate(' + (bw / 2 - 90) + ' 40) scale(0.36)'}>{(PROP_ALL[ic] ?? PROP_ALL.question)(local / 24)}</g>}
      <foreignObject x={-bw / 2 + 20} y={-bh / 2 + 10} width={bw - (ic ? 150 : 40)} height={bh - 20}>
        <div style={{...INKT, width: bw - (ic ? 150 : 40), height: bh - 20, fontSize: txt.length > 14 ? 52 : 64, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{txt}</div>
      </foreignObject>
    </g>
  );
};

// ============ مشهد: خلفية + مجسمات + شخصيات ============
const SceneShot: React.FC<{shot: Shot; local: number; env: number}> = ({shot, local, env}) => {
  const w = useWorld();
  const {W, H, v} = w;
  const gy = groundY(w);
  const t = local / 24;
  const feet = gy + H * 0.045;
  const sK = v ? 1.02 : 1;
  const actorS = v ? 2.0 : 1.65;
  const dark = ['night', 'space', 'cave', 'volcano', 'battlefield'].includes(shot.bg);
  const heads: {x: number; y: number}[] = [];
  return (
    <>
      <Bg kind={shot.bg} local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        {(shot.props || []).map((pr, i) => {
          const name = iconOf(pr);
          const fl = PROP_FLOAT[name];
          const base = fl !== undefined ? H * fl : gy + H * 0.028;
          const size = (SIZES[pr.size] ?? 1) * (PROP_SCALE[name] ?? 1) * sK * (fl !== undefined ? 0.95 : 1);
          return <PropView key={'p' + i} name={name} x={posX(w, pr.pos)} base={base} size={size} local={local} delay={i * 6} ground={fl === undefined} />;
        })}
        {(shot.actors || []).map((a, i) => {
          const x0 = posX(w, a.pos);
          const flip = a.flip ?? x0 > W * 0.52;
          const walking = a.action === 'walk' || a.action === 'run';
          const dir = flip ? 1 : -1;
          let x = x0;
          if (walking) x = x0 + dir * W * 0.22 * (1 - easeOut(local / 26)) - dir * (a.action === 'run' ? 3.4 : 1.6) * Math.max(0, local - 20) * (v ? 0.7 : 1);
          if (a.action === 'sleep') x = x0;
          const mouth = a.action === 'talk' || (i === 0 && a.action === 'idle' && env > 0.2) ? Math.min(1, env * 1.35) : 0;
          heads[i] = {x, y: feet - 330 * actorS * (a.role === 'child' ? 0.68 : 1)};
          return <g key={'a' + i} style={dark ? {filter: 'drop-shadow(0 0 5px rgba(255,255,255,0.95)) drop-shadow(0 0 2px #fff)'} : undefined}><Stick x={x} y={feet} s={actorS} role={a.role} action={a.action} t={t + i * 0.37} local={local - i * 4} flip={flip} mouth={mouth} expr={a.expr} /></g>;
        })}
        {shot.bubble && (shot.bubble.text || shot.bubble.icon || shot.bubble.emoji) && (() => {
          const hd = heads[0] ?? {x: W * 0.5, y: feet - 500};
          return <BubbleView b={shot.bubble} ax={hd.x + (hd.x > W * 0.5 ? -40 : 40)} ay={Math.max(260, hd.y - 150)} local={local} />;
        })()}
      </svg>
    </>
  );
};
// ============ مشاهد توضيحية (أرقام، مقارنات، خرائط...): كلها مرسومة بالكود وتتكيف مع الأفقي والعمودي ============
const BAR_COLORS = ['#3b82f6', '#f08a3c', '#22a06b', '#e11d2e'];
const fitSize = (text: string, w: number, size: number) => Math.max(26, Math.min(size, Math.floor(w / Math.max(3, (text || '').length * 0.6))));
const InkText: React.FC<{x: number; y: number; w: number; h: number; size: number; children: React.ReactNode; align?: 'center' | 'right' | 'left'; color?: string; stroke?: string}> = (
  {x, y, w, h, size, children, align = 'center', color = INK, stroke},
) => (
  <foreignObject x={x} y={y} width={w} height={h}>
    <div style={{...INKT, width: w, height: h, fontSize: size, color, display: 'flex', alignItems: 'center',
      justifyContent: align === 'left' ? 'flex-end' : align === 'right' ? 'flex-start' : 'center',
      ...(stroke ? {WebkitTextStroke: '12px ' + stroke, paintOrder: 'stroke fill'} : {})}}>{children}</div>
  </foreignObject>
);
const IconArt: React.FC<{name: string; cx: number; base: number; h: number; local: number; delay?: number}> = ({name, cx, base, h, local, delay = 0}) => {
  const l = local - delay;
  if (l < 0) return null;
  const n = PROP_ALL[name] ? name : 'question';
  return <PropView name={n} x={cx} base={base} size={h / 320} local={l} ground={false} />;
};
const Arrow: React.FC<{x1: number; y1: number; x2: number; y2: number; color?: string; w?: number}> = ({x1, y1, x2, y2, color = '#e11d2e', w = 14}) => {
  const a = Math.atan2(y2 - y1, x2 - x1);
  const hs = w * 2.4;
  const bx = x2 - Math.cos(a) * hs * 0.6;
  const by = y2 - Math.sin(a) * hs * 0.6;
  return (
    <g>
      <path d={'M' + x1 + ' ' + y1 + ' L' + bx + ' ' + by} stroke={color} strokeWidth={w} strokeLinecap="round" />
      <path d={'M' + x2 + ' ' + y2 + ' L' + (x2 - Math.cos(a - 0.5) * hs) + ' ' + (y2 - Math.sin(a - 0.5) * hs) + ' L' + (x2 - Math.cos(a + 0.5) * hs) + ' ' + (y2 - Math.sin(a + 0.5) * hs) + ' Z'} fill={color} stroke={color} strokeWidth={4} strokeLinejoin="round" />
    </g>
  );
};
const Title: React.FC<{text?: string; local: number; y?: number; size?: number}> = ({text, local, y, size}) => {
  const w = useWorld();
  if (!text) return null;
  const sz = size ?? (w.v ? 96 : 104);
  return (
    <g opacity={easeOut(local / 10)} transform={'translate(0 ' + (1 - easeOut(local / 12)) * -30 + ')'}>
      <InkText x={w.W * 0.05} y={y ?? w.H * (w.v ? 0.07 : 0.05)} w={w.W * 0.9} h={w.H * (w.v ? 0.15 : 0.18)} size={fitSize(text, w.W * 0.9, sz)}>{text}</InkText>
    </g>
  );
};

const CloseupShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const size = Math.min(W * 0.78, H * 0.46);
  const bob = Math.sin(local * 0.12) * 10;
  const len = (shot.label || '').length;
  const bw = Math.min(W * 0.9, 160 + len * 50);
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <ellipse cx={W / 2} cy={H * (v ? 0.62 : 0.76)} rx={size * 0.45} ry={size * 0.05} fill="rgba(0,0,0,0.12)" />
        <IconArt name={iconOf(shot)} cx={W / 2} base={H * (v ? 0.6 : 0.74) + bob} h={size} local={local} />
        {shot.question && (
          <text x={W * (v ? 0.82 : 0.72)} y={H * (v ? 0.3 : 0.3) + Math.sin(local * 0.25) * 14} fontSize={v ? 260 : 300} textAnchor="middle" fill="#e11d2e" stroke={INK} strokeWidth={9}
            transform={'rotate(12 ' + W * (v ? 0.82 : 0.72) + ' ' + H * 0.3 + ')'} style={{fontFamily: FONT, fontWeight: 900, paintOrder: 'stroke fill'}}>؟</text>
        )}
        {shot.label && (
          <g opacity={easeOut((local - 10) / 10)} transform={'translate(0 ' + (1 - easeOut((local - 10) / 12)) * 40 + ')'}>
            <rect x={(W - bw) / 2} y={H * (v ? 0.68 : 0.82)} width={bw} height={v ? 140 : 130} rx={28} fill="#ffe27a" stroke={INK} strokeWidth={6} />
            <InkText x={(W - bw) / 2} y={H * (v ? 0.68 : 0.82)} w={bw} h={v ? 140 : 130} size={fitSize(shot.label, bw - 40, 66)}>{shot.label}</InkText>
          </g>
        )}
        <Title text={shot.callout} local={local} />
      </svg>
    </div>
  );
};

const BarsShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const items = (shot.items || []).slice(0, 4);
  const rowH = Math.min(v ? H * 0.19 : H * 0.22, (H * (v ? 0.62 : 0.66)) / Math.max(1, items.length));
  const top = v ? H * 0.3 : H * 0.28;
  const x0 = v ? W * 0.08 : W * 0.3;
  const maxW = v ? W * 0.44 : W * 0.5;
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <Title text={shot.callout} local={local} />
        {!v && <path d={'M' + x0 + ' ' + (top - 20) + ' L' + x0 + ' ' + (top + rowH * items.length)} stroke={INK} strokeWidth={6} />}
        {items.map((it, i) => {
          const g = easeOut((local - i * 8 - 6) / 26);
          const y = top + i * rowH;
          const bw = Math.max(14, (Math.min(100, Math.max(2, it.value)) / 100) * maxW) * g;
          const barH = rowH * (v ? 0.34 : 0.44);
          const by = v ? y + rowH * 0.42 : y + rowH * 0.18;
          return (
            <g key={i}>
              {v ? (
                <>
                  <IconArt name={iconOf(it)} cx={W * 0.89} base={y + rowH * 0.82} h={rowH * 0.7} local={local} delay={i * 8} />
                  <InkText x={W * 0.05} y={y + rowH * 0.02} w={W * 0.7} h={rowH * 0.36} size={fitSize(it.label, W * 0.7, 52)} align="left">{it.label}</InkText>
                </>
              ) : (
                <>
                  <IconArt name={iconOf(it)} cx={W * 0.1} base={y + rowH * 0.78} h={rowH * 0.7} local={local} delay={i * 8} />
                  <InkText x={W * 0.17} y={y + rowH * 0.6} w={W * 0.13} h={rowH * 0.3} size={fitSize(it.label, W * 0.13, 40)}>{it.label}</InkText>
                </>
              )}
              <rect x={x0} y={by} width={bw} height={barH} rx={12} fill={BAR_COLORS[i % 4]} stroke={INK} strokeWidth={6} />
              <g opacity={easeOut((local - i * 8 - 24) / 10)}>
                <InkText x={x0 + bw + 14} y={by} w={Math.max(200, W - (x0 + bw + 14) - W * 0.04)} h={barH} size={v ? 56 : 62} align="left">{it.text}</InkText>
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

const CalendarShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const n = Math.max(1, Math.min(24, shot.count || 7));
  const cols = v ? Math.min(4, n) : n <= 6 ? n : n <= 12 ? 6 : 8;
  const rows = Math.ceil(n / cols);
  const hasIcon = !!(shot.icon || shot.emoji);
  const areaW = v ? W * 0.9 : W * (hasIcon ? 0.68 : 0.88);
  const w = Math.min(v ? 210 : 230, Math.floor(areaW / cols) - 18);
  const h = Math.round(w * 0.95);
  const tw = cols * (w + 18);
  const x0 = v ? (W - tw) / 2 : hasIcon ? W * 0.05 : (W - tw) / 2;
  const y0 = H * (v ? 0.3 : 0.42);
  const heads = ['#e11d2e', '#f08a3c', '#f5c518', '#22a06b', '#3b82f6', '#7b2d8e'];
  const step = Math.max(2, Math.floor(60 / n));
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <Title text={shot.label || shot.callout} local={local} size={v ? 110 : 140} />
        {Array.from({length: n}).map((_, i) => {
          const cx = x0 + (i % cols) * (w + 18);
          const cy = y0 + Math.floor(i / cols) * (h + 24);
          const mark = clamp01((local - 10 - i * step) / 8);
          const pop = easeBack((local - i * 2) / 10);
          return (
            <g key={i} transform={'translate(' + (cx + w / 2) + ' ' + (cy + h / 2) + ') scale(' + pop + ') translate(' + -w / 2 + ' ' + -h / 2 + ')'}>
              <rect x={0} y={0} width={w} height={h} rx={10} fill="#fff" stroke={INK} strokeWidth={5} />
              <rect x={0} y={0} width={w} height={h * 0.24} rx={10} fill={heads[i % 6]} stroke={INK} strokeWidth={5} />
              {[0.3, 0.6].map((k) => <path key={k} d={'M' + w * 0.08 + ' ' + h * (0.3 + k * 0.5) + ' L' + w * 0.92 + ' ' + h * (0.3 + k * 0.5)} stroke="#c9c9c9" strokeWidth={3} />)}
              {mark > 0 && <path d={'M' + w * 0.2 + ' ' + h * 0.42 + ' L' + w * (0.2 + 0.6 * mark) + ' ' + h * (0.42 + 0.46 * mark) + ' M' + w * 0.8 + ' ' + h * 0.42 + ' L' + w * (0.8 - 0.6 * mark) + ' ' + h * (0.42 + 0.46 * mark)} stroke="#e11d2e" strokeWidth={Math.max(6, w * 0.06)} strokeLinecap="round" />}
            </g>
          );
        })}
        {hasIcon && <IconArt name={iconOf(shot)} cx={v ? W * 0.5 : W * 0.84} base={v ? H * 0.78 : H * 0.8} h={v ? 280 : 480} local={local} delay={6} />}
      </svg>
    </div>
  );
};

const arcPt = (cx: number, cy: number, r: number, a: number): [number, number] => [cx + r * Math.sin(rad(a)), cy - r * Math.cos(rad(a))];
const GaugeShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const cx = v ? W * 0.5 : W * 0.62;
  const cy = H * (v ? 0.58 : 0.66);
  const R = Math.min(W * (v ? 0.4 : 0.26), H * 0.32);
  const level = clamp01(shot.level ?? 0.2);
  const a = -90 + 180 * level * easeOut(local / 34);
  const [nx, ny] = arcPt(cx, cy, R * 0.82, a);
  const seg = (a0: number, a1: number, col: string) => {
    const p0 = arcPt(cx, cy, R, a0);
    const p1 = arcPt(cx, cy, R, a1);
    return <path d={'M' + p0[0] + ' ' + p0[1] + ' A' + R + ' ' + R + ' 0 0 1 ' + p1[0] + ' ' + p1[1]} stroke={col} strokeWidth={R * 0.2} fill="none" strokeLinecap="butt" />;
  };
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <Title text={shot.callout || shot.label} local={local} />
        {seg(-90, -30, '#22a06b')}{seg(-30, 30, '#f5c518')}{seg(30, 90, '#e11d2e')}
        <path d={'M' + cx + ' ' + cy + ' L' + nx + ' ' + ny} stroke={INK} strokeWidth={R * 0.07} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={R * 0.1} fill={INK} />
        {(shot.icon || shot.emoji) && <IconArt name={iconOf(shot)} cx={v ? W * 0.5 : W * 0.22} base={v ? H * 0.46 : H * 0.72} h={v ? 300 : 440} local={local} />}
        {shot.label && shot.callout && <InkText x={W * 0.05} y={H * (v ? 0.66 : 0.78)} w={W * 0.9} h={H * 0.12} size={fitSize(shot.label, W * 0.9, 64)}>{shot.label}</InkText>}
      </svg>
    </div>
  );
};

const CompareShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const sides = [shot.left, shot.right];
  const pw = v ? W * 0.88 : W * 0.43;
  const ph = v ? H * 0.33 : H * 0.7;
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <Title text={shot.callout} local={local} size={v ? 84 : 90} y={H * (v ? 0.05 : 0.03)} />
        {sides.map((s, i) => {
          if (!s) return null;
          const px = v ? (W - pw) / 2 : i === 0 ? W * 0.53 : W * 0.04;
          const py = v ? H * (i === 0 ? 0.17 : 0.55) : H * 0.2;
          const pop = easeBack((local - i * 8) / 14);
          const lv = Math.max(0, Math.min(5, s.level ?? 0));
          return (
            <g key={i} transform={'translate(' + (px + pw / 2) + ' ' + (py + ph / 2) + ') scale(' + pop + ') translate(' + -(px + pw / 2) + ' ' + -(py + ph / 2) + ')'}>
              <rect x={px} y={py} width={pw} height={ph} rx={34} fill={i === 0 ? '#e8f6ec' : '#fdeaea'} stroke={INK} strokeWidth={7} />
              <InkText x={px} y={py + ph * 0.03} w={pw} h={ph * 0.17} size={fitSize(s.title, pw * 0.9, v ? 64 : 62)}>{s.title}</InkText>
              <IconArt name={iconOf(s)} cx={px + pw / 2} base={py + ph * 0.66} h={ph * 0.42} local={local} delay={i * 8} />
              {Array.from({length: 5}).map((_, k) => (
                <path key={k} d={'M' + (px + pw / 2 - 100 + k * 50) + ' ' + (py + ph * 0.8) + ' l14 -26 l14 26 Z'} fill={k < lv ? '#e11d2e' : '#ddd'} stroke={INK} strokeWidth={3} strokeLinejoin="round" />
              ))}
              {s.note && <InkText x={px} y={py + ph * 0.84} w={pw} h={ph * 0.14} size={fitSize(s.note, pw * 0.9, 44)}>{s.note}</InkText>}
            </g>
          );
        })}
        <g transform={'translate(' + W / 2 + ' ' + (v ? H * 0.525 : H * 0.55) + ')'}>
          <circle r={50} fill="#ffd23f" stroke={INK} strokeWidth={6} />
          <text y={18} textAnchor="middle" fontSize={50} fontWeight={900} fill={INK} style={{fontFamily: FONT}}>VS</text>
        </g>
      </svg>
    </div>
  );
};

const DiagramShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const tags = (shot.tags || []).slice(0, 4);
  const ix = v ? W * 0.5 : W * 0.5;
  const ib = v ? H * 0.4 : H * 0.7;
  const ih = v ? H * 0.24 : H * 0.42;
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <Title text={shot.callout} local={local} />
        <IconArt name={iconOf(shot)} cx={ix} base={ib} h={ih} local={local} />
        {tags.map((tg, i) => {
          const k = easeOut((local - 10 - i * 7) / 12);
          const tw = Math.min(W * (v ? 0.8 : 0.3), 120 + tg.length * 38);
          const tx = v ? (W - tw) / 2 : (i % 2 === 0 ? W * 0.05 : W * 0.95 - tw);
          const ty = v ? H * (0.47 + i * 0.12) : H * (0.28 + Math.floor(i / 2) * 0.3);
          const ax = v ? ix : (i % 2 === 0 ? tx + tw : tx);
          const ay = ty + 45;
          return (
            <g key={i} opacity={k}>
              <rect x={tx} y={ty} width={tw} height={92} rx={22} fill={['#ffe27a', '#bfe6fb', '#c9f0d0', '#fbd0d0'][i % 4]} stroke={INK} strokeWidth={6} />
              <InkText x={tx} y={ty} w={tw} h={92} size={fitSize(tg, tw - 30, 54)}>{tg}</InkText>
              {(!v || i === 0) && <Arrow x1={v ? ix : ax} y1={v ? ty - 4 : ay} x2={v ? ix : (i % 2 === 0 ? ix - ih * 0.45 : ix + ih * 0.45)} y2={v ? ib + 10 : ib - ih * 0.4} color={INK} w={9} />}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

const MapShot: React.FC<{shot: Shot; local: number; dur: number}> = ({shot, local, dur}) => {
  const {W, H, v} = useWorld();
  const a: [number, number] = v ? [W * 0.26, H * 0.7] : [W * 0.2, H * 0.66];
  const b: [number, number] = v ? [W * 0.74, H * 0.34] : [W * 0.8, H * 0.4];
  const c: [number, number] = v ? [W * 0.78, H * 0.62] : [W * 0.5, H * 0.2];
  const p = easeInOut(local / Math.max(30, dur * 0.8));
  const pt = (tt: number): [number, number] => [(1 - tt) * (1 - tt) * a[0] + 2 * (1 - tt) * tt * c[0] + tt * tt * b[0], (1 - tt) * (1 - tt) * a[1] + 2 * (1 - tt) * tt * c[1] + tt * tt * b[1]];
  const cur = pt(p);
  const pin = (xy: [number, number], label: string, col: string, k: number) => (
    <g transform={'translate(' + xy[0] + ' ' + xy[1] + ') scale(' + easeBack(k) + ')'}>
      <path d="M0 0 C-60 -70 -52 -130 0 -130 C52 -130 60 -70 0 0 Z" fill={col} stroke={INK} strokeWidth={7} strokeLinejoin="round" /><circle cx={0} cy={-84} r={18} fill="#fff" stroke={INK} strokeWidth={5} />
      <rect x={-130} y={18} width={260} height={74} rx={20} fill="#fff" stroke={INK} strokeWidth={5} />
      <InkText x={-130} y={18} w={260} h={74} size={fitSize(label, 230, 46)}>{label}</InkText>
    </g>
  );
  return (
    <div style={ABS}>
      <Bg kind="paper" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <rect width={W} height={H} fill="#e8d6a8" opacity={0.55} />
        <path d={wavePath(W, H * 0.9, 12, 300, local * 0.05, H)} fill="#8fc7e8" opacity={0.7} />
        <path d={'M' + W * 0.05 + ' ' + H * 0.3 + ' q' + W * 0.2 + ' -' + H * 0.12 + ' ' + W * 0.4 + ' ' + H * 0.02 + ' t' + W * 0.5 + ' ' + H * 0.05 + ' L' + W * 0.95 + ' ' + H * 0.8 + ' L' + W * 0.05 + ' ' + H * 0.8 + ' Z'} fill="#cfb27a" opacity={0.45} />
        <Title text={shot.callout} local={local} />
        <path d={'M' + a[0] + ' ' + a[1] + ' Q' + c[0] + ' ' + c[1] + ' ' + b[0] + ' ' + b[1]} stroke="#8a1c1c" strokeWidth={10} strokeDasharray="6 22" strokeLinecap="round" fill="none" />
        {pin(a, shot.mapFrom || '', '#2f8f5b', local / 12)}
        {pin(b, shot.mapTo || '', '#e11d2e', (local - 10) / 12)}
        <g transform={'translate(' + cur[0] + ' ' + cur[1] + ')'}>
          <circle r={26} fill="#ffd23f" stroke={INK} strokeWidth={6} /><circle r={9} fill={INK} />
        </g>
      </svg>
    </div>
  );
};

const StatShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const raw = shot.callout || '';
  const m = raw.match(/^(\D*)([\d.,]+)(\D*)$/);
  let shown = raw;
  if (m) {
    const num = parseFloat(m[2].replace(/,/g, ''));
    if (!isNaN(num)) {
      const cur = num * easeOut(local / 26);
      shown = m[1] + (num >= 1000 ? Math.round(cur).toLocaleString('en-US') : Number.isInteger(num) ? String(Math.round(cur)) : cur.toFixed(1)) + m[3];
    }
  }
  const pop = easeBack(local / 14);
  return (
    <div style={ABS}>
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <defs><Grad id="statbg" c={['#0f1f4a', '#1c3a7a']} /></defs>
        <rect width={W} height={H} fill="url(#statbg)" />
        {Array.from({length: 8}).map((_, i) => <circle key={i} cx={(i * 263 + 90) % W} cy={(i * 191 + 70) % H} r={60 + (i % 3) * 30} fill="#fff" opacity={0.04} />)}
        <g transform={'translate(' + W / 2 + ' ' + H * 0.44 + ') scale(' + pop + ') translate(' + -W / 2 + ' ' + -H * 0.44 + ')'}>
          <InkText x={W * 0.04} y={H * 0.3} w={W * 0.92} h={H * 0.26} size={fitSize(shown, W * 0.92, v ? 230 : 260)} color="#ffd23f" stroke="#0a1230">{shown}</InkText>
        </g>
        {shot.label && <g opacity={easeOut((local - 12) / 10)}><InkText x={W * 0.06} y={H * (v ? 0.56 : 0.6)} w={W * 0.88} h={H * 0.16} size={fitSize(shot.label, W * 0.88, 72)} color="#fff">{shot.label}</InkText></g>}
      </svg>
    </div>
  );
};

const TimelineShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  const ly = H * (v ? 0.56 : 0.6);
  const k = easeOut(local / 22);
  return (
    <div style={ABS}>
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <defs><Grad id="tlbg" c={['#2a1c10', '#6b4a2b']} /></defs>
        <rect width={W} height={H} fill="url(#tlbg)" />
        <g transform={'translate(' + W / 2 + ' ' + H * 0.36 + ') scale(' + easeBack(local / 14) + ') translate(' + -W / 2 + ' ' + -H * 0.36 + ')'}>
          <InkText x={W * 0.04} y={H * 0.24} w={W * 0.92} h={H * 0.24} size={fitSize(shot.callout, W * 0.92, v ? 200 : 230)} color="#ffd23f" stroke="#1a0f08">{shot.callout}</InkText>
        </g>
        <path d={'M' + W * 0.05 + ' ' + ly + ' L' + W * 0.95 + ' ' + ly} stroke="#f4ead2" strokeWidth={8} strokeLinecap="round" />
        {Array.from({length: 17}).map((_, i) => <path key={i} d={'M' + (W * 0.05 + i * W * 0.9 / 16) + ' ' + (ly - (i % 4 === 0 ? 34 : 18)) + ' L' + (W * 0.05 + i * W * 0.9 / 16) + ' ' + (ly + (i % 4 === 0 ? 34 : 18))} stroke="#f4ead2" strokeWidth={i % 4 === 0 ? 7 : 4} />)}
        <circle cx={lerp(W * 0.1, W * 0.55, k)} cy={ly} r={26} fill="#e11d2e" stroke="#fff" strokeWidth={6} />
        {shot.label && <g opacity={easeOut((local - 10) / 10)}><InkText x={W * 0.06} y={ly + H * 0.08} w={W * 0.88} h={H * 0.14} size={fitSize(shot.label, W * 0.88, 70)} color="#fff">{shot.label}</InkText></g>}
      </svg>
    </div>
  );
};

const QuestionShot: React.FC<{shot: Shot; local: number}> = ({shot, local}) => {
  const {W, H, v} = useWorld();
  return (
    <div style={ABS}>
      <Bg kind="cream" local={local} />
      <svg viewBox={'0 0 ' + W + ' ' + H} style={ABS}>
        <g transform={'translate(' + W / 2 + ' ' + H * (v ? 0.5 : 0.58) + ') scale(' + easeBack(local / 16) + ') rotate(' + Math.sin(local * 0.15) * 4 + ')'}>
          <text x={0} y={v ? 270 : 240} textAnchor="middle" fontSize={v ? 760 : 700} fill="#e11d2e" stroke={INK} strokeWidth={16} style={{fontFamily: FONT, fontWeight: 900, paintOrder: 'stroke fill'}}>؟</text>
        </g>
        <Title text={shot.callout} local={local} />
      </svg>
    </div>
  );
};
// ============ عرض المشهد + الكاميرا ============
const HostBox: React.FC<{frame: number; fps: number; envelope: number[]; expression: string; pal: {robe: string; turban: string; skin: string}}> = (p) => (
  <div style={{position: 'absolute', right: 42, bottom: 42, transform: 'scale(1.5)', transformOrigin: 'bottom right'}}>
    <HostInset {...p} />
  </div>
);

const ShotView: React.FC<{shot: Shot; local: number; frame: number; fps: number; envelope: number[]; pal: {robe: string; turban: string; skin: string}; showCaptions: boolean}> = (
  {shot, local, frame, fps, envelope, pal, showCaptions},
) => {
  const w = useWorld();
  const {W, H, v} = w;
  const dur = Math.max(1, shot.to - shot.from);
  const p = clamp01(local / dur);
  const env = envelope[frame] ?? 0;
  let sc = 1;
  let tx = 0;
  let ty = 0;
  const damp = Math.max(0, 1 - local / 18);
  switch (shot.camera) {
    case 'zoom_in': sc = 1 + 0.14 * easeInOut(p); break;
    case 'zoom_out': sc = 1.15 - 0.15 * easeInOut(p); break;
    case 'pan_left': sc = 1.12; tx = (W * 0.03) - W * 0.06 * p; break;
    case 'pan_right': sc = 1.12; tx = -(W * 0.03) + W * 0.06 * p; break;
    case 'shake': sc = 1.06; tx = Math.sin(local * 2.3) * 14 * damp; ty = Math.cos(local * 3.1) * 11 * damp; break;
    default: sc = 1 + 0.03 * p; break;
  }
  let body: React.ReactNode;
  const sn = shot.scene;
  if (sn === 'map') body = <MapShot shot={shot} local={local} dur={dur} />;
  else if (sn === 'stat') body = <StatShot shot={shot} local={local} />;
  else if (sn === 'timeline') body = <TimelineShot shot={shot} local={local} />;
  else if (sn === 'question') body = <QuestionShot shot={shot} local={local} />;
  else if (sn === 'closeup') body = <CloseupShot shot={shot} local={local} />;
  else if (sn === 'bars') body = <BarsShot shot={shot} local={local} />;
  else if (sn === 'calendar') body = <CalendarShot shot={shot} local={local} />;
  else if (sn === 'compare') body = <CompareShot shot={shot} local={local} />;
  else if (sn === 'gauge') body = <GaugeShot shot={shot} local={local} />;
  else if (sn === 'diagram') body = <DiagramShot shot={shot} local={local} />;
  else body = <SceneShot shot={shot} local={local} env={env} />;
  const showTop = !!shot.callout && sn === 'scene';
  const cs = shot.callout.length > 14 ? (v ? 78 : 72) : (v ? 100 : 90);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: 'translate(' + tx + 'px, ' + ty + 'px) scale(' + sc + ')', transformOrigin: '50% 72%'}}>{body}</div>
      {showTop && (
        <div style={{position: 'absolute', top: H * (v ? 0.075 : 0.05), left: 0, right: 0, display: 'flex', justifyContent: 'center', transform: 'scale(' + easeBack((local - 6) / 12) + ') rotate(-1.5deg)'}}>
          <div style={{...INKT, fontSize: cs, background: '#fff', border: '7px solid ' + INK, borderRadius: 36, padding: '10px 44px', boxShadow: '0 10px 0 rgba(0,0,0,0.18)', maxWidth: W * 0.88}}>{shot.callout}</div>
        </div>
      )}
      {shot.host && !v && <HostBox frame={frame} fps={fps} envelope={envelope} expression={shot.expression || 'neutral'} pal={pal} />}
      {showCaptions && !v && (
        <div style={{position: 'absolute', bottom: 40, left: 220, right: shot.host ? 460 : 220, textAlign: 'center', direction: 'rtl',
          color: '#fff', fontSize: 52, fontFamily: FONT, fontWeight: 700, textShadow: '0 3px 12px #000'}}>{shot.text}</div>
      )}
    </div>
  );
};

const pickShot = (shots: Shot[], frame: number) => {
  let si = 0;
  for (let i = 0; i < shots.length; i++) if (frame >= shots[i].from) si = i;
  return si;
};

// ============ الفيديو الطويل (أفقي) ============
const Explainer: React.FC<Props> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const shots = props.shots ?? [];
  const pal = PALETTES[props.narratorStyle] ?? PALETTES.arab;
  const world: World = {W: 1920, H: 1080, v: false};
  const si = pickShot(shots, frame);
  const shot = shots[si];
  const local = frame - shot.from;
  const T = 9;
  const k = easeOut(local / T);
  const prev = si > 0 ? shots[si - 1] : null;
  const trans = !!prev && local < T && shot.transition !== 'cut';
  const prevLocal = prev ? prev.to - prev.from + local : 0;
  const cur: React.CSSProperties = {position: 'absolute', inset: 0};
  const old: React.CSSProperties = {position: 'absolute', inset: 0};
  if (trans) {
    if (shot.transition === 'fade') cur.opacity = k;
    else if (shot.transition === 'slide') { cur.transform = 'translateX(' + (1 - k) * 100 + '%)'; old.transform = 'translateX(' + -k * 30 + '%)'; }
    else if (shot.transition === 'zoom') { old.transform = 'scale(' + (1 + k * 0.5) + ')'; old.opacity = 1 - k; }
    else if (shot.transition === 'wipe') cur.clipPath = 'inset(0 ' + (100 - k * 100) + '% 0 0)';
  }
  const fadeIn = interpolate(frame, [0, 14], [1, 0], {extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 36, durationInFrames - 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const view = (s: Shot, l: number) => (
    <ShotView shot={s} local={l} frame={frame} fps={fps} envelope={props.envelope} pal={pal} showCaptions={props.showCaptions} />
  );
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: 'scale(0.66667)', transformOrigin: '0 0'}}>
        <WorldCtx.Provider value={world}>
          {trans && prev && shot.transition === 'zoom' && <div style={cur}>{view(shot, local)}</div>}
          {trans && prev && <div style={old}>{view(prev, prevLocal)}</div>}
          {!(trans && shot.transition === 'zoom') && <div style={cur}>{view(shot, local)}</div>}
        </WorldCtx.Provider>
        <Watermark scale={1.05} style={{position: 'absolute', left: 40, bottom: 36, opacity: 0.92}} />
      </div>
      <AbsoluteFill style={{background: '#000', opacity: Math.max(fadeIn, fadeOut), pointerEvents: 'none'}} />
      {props.audio && <Audio src={staticFile(props.audio)} />}
    </AbsoluteFill>
  );
};

const Main: React.FC<Props> = (p) => (p.shots && p.shots.length > 0 ? <Explainer {...p} /> : <Scene {...p} />);

// ============ الشورت: عمودي حقيقي بملء الشاشة + ترجمة كلمات كبيرة ============
const OUT = (c: string, px = 14): React.CSSProperties => ({WebkitTextStroke: px + 'px ' + c, paintOrder: 'stroke fill'});
const ShortExplainer: React.FC<ShortProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const shots = props.shots ?? [];
  const pal = PALETTES[props.narratorStyle] ?? PALETTES.arab;
  const world: World = {W: 1080, H: 1920, v: true};
  const si = pickShot(shots, frame);
  const shot = shots[si];
  const local = frame - shot.from;
  const dur = Math.max(1, shot.to - shot.from);
  const words = (shot.text || '').split(/\s+/).filter(Boolean);
  const per = 3;
  const span = dur * 0.9;
  const wi = Math.min(words.length - 1, Math.floor(clamp01(local / span) * words.length));
  const ci = Math.floor(wi / per);
  const chunk = words.slice(ci * per, ci * per + per);
  const chunkStart = (ci * per / Math.max(1, words.length)) * span;
  const capPop = 0.86 + 0.14 * easeBack((local - chunkStart) / 6);
  const hookO = interpolate(frame, [0, 8, 66, 80], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const hookS = easeBack(frame / 10);
  const endStart = durationInFrames - Math.round(fps * 3.4);
  const endO = interpolate(frame, [endStart, endStart + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pulse = 1 + Math.sin(frame * 0.3) * 0.04;
  const fadeIn = interpolate(frame, [0, 5], [1, 0], {extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 10, durationInFrames - 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const T = 6;
  const k = easeOut(local / T);
  const prev = si > 0 ? shots[si - 1] : null;
  const trans = !!prev && local < T && shot.transition !== 'cut';
  const cur: React.CSSProperties = {position: 'absolute', inset: 0};
  if (trans) {
    if (shot.transition === 'fade') cur.opacity = k;
    else if (shot.transition === 'slide') cur.transform = 'translateY(' + (1 - k) * 100 + '%)';
    else if (shot.transition === 'zoom') cur.transform = 'scale(' + (0.7 + 0.3 * k) + ')';
    else if (shot.transition === 'wipe') cur.clipPath = 'inset(0 0 ' + (100 - k * 100) + '% 0)';
  }
  const view = (s0: Shot, l: number) => { const s = frame < 84 && s0.callout && s0.scene === 'scene' ? {...s0, callout: ''} : s0; return <ShotView shot={s} local={l} frame={frame} fps={fps} envelope={props.envelope} pal={pal} showCaptions={false} />; };
  return (
    <AbsoluteFill style={{background: '#101018', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920, transform: 'scale(0.66667)', transformOrigin: '0 0'}}>
        <WorldCtx.Provider value={world}>
          {trans && prev && <div style={{position: 'absolute', inset: 0}}>{view(prev, prev.to - prev.from + local)}</div>}
          <div style={cur}>{view(shot, local)}</div>
        </WorldCtx.Provider>
        <div style={{position: 'absolute', left: 0, top: 0, height: 14, width: (frame / durationInFrames) * 1080, background: '#e11d2e'}} />
        <div style={{position: 'absolute', top: 150, left: 40, right: 40, textAlign: 'center', direction: 'rtl', fontFamily: FONT, fontWeight: 900, fontSize: 124, lineHeight: 1.15,
          color: '#ffd23f', opacity: hookO, transform: 'scale(' + hookS + ')', ...OUT('#16161d', 22), textShadow: '0 10px 0 rgba(0,0,0,0.25)'}}>{props.hookText}</div>
        <div style={{position: 'absolute', left: 30, right: 30, top: 1500, height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', direction: 'rtl', textAlign: 'center',
          fontFamily: FONT, fontWeight: 900, fontSize: 112, lineHeight: 1.12, transform: 'scale(' + capPop + ')'}}>
          {chunk.map((wd, i) => {
            const active = ci * per + i === wi;
            return <span key={i} style={{color: active ? '#ffd23f' : '#fff', margin: '0 14px', ...OUT('#16161d', 22), textShadow: '0 8px 0 rgba(0,0,0,0.25)'}}>{wd}</span>;
          })}
        </div>
        <div style={{position: 'absolute', top: 230, left: 60, right: 60, textAlign: 'center', direction: 'rtl', opacity: endO, transform: 'scale(' + pulse + ')'}}>
          <div style={{display: 'inline-block', background: '#e11d2e', color: '#fff', fontFamily: FONT, fontWeight: 900, fontSize: 92, lineHeight: 1.3,
            padding: '34px 60px', borderRadius: 44, border: '9px solid #fff', boxShadow: '0 14px 0 rgba(0,0,0,0.3)'}}>{props.endText}</div>
        </div>
        <Watermark scale={1.45} style={{position: 'absolute', left: 40, top: 56, opacity: 0.92}} />
      </div>
      <AbsoluteFill style={{background: '#000', opacity: Math.max(fadeIn, fadeOut), pointerEvents: 'none'}} />
      {props.audio && <Audio src={staticFile(props.audio)} />}
    </AbsoluteFill>
  );
};
const Short: React.FC<ShortProps> = (p) => (p.shots && p.shots.length > 0 ? <ShortExplainer {...p} /> : <ShortClassic {...p} />);

// ============ الصورة المصغرة ============
const THUMB_BG: Record<string, string> = {desert: 'desert', ruins: 'ruins', hills: 'hills', sea: 'sea', cave: 'cave', room: 'room'};
const THUMB_PROP: Record<string, string> = {desert: 'pyramid', ruins: 'column', hills: 'tree', sea: 'ship', cave: 'fire', room: 'book'};
const ThumbArt: React.FC<Props> = (props) => {
  const world: World = {W: 1920, H: 1080, v: false};
  const doodle = props.style === 'doodle';
  const pal = PALETTES[props.narratorStyle] ?? PALETTES.arab;
  const bg = doodle ? 'cream' : THUMB_BG[props.thumbSetting] ?? 'desert';
  const icon = props.thumbEmoji && (PROP_ALL[props.thumbEmoji] || EMO2PROP[props.thumbEmoji]) ? iconOf({icon: props.thumbEmoji}) : THUMB_PROP[props.thumbSetting] ?? 'question';
  const n = (props.thumbText || '').length;
  const size = n <= 14 ? 230 : n <= 22 ? 188 : 150;
  const draw = PROP_ALL[icon] ?? PROP_ALL.question;
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: 'scale(0.66667)', transformOrigin: '0 0'}}>
        <WorldCtx.Provider value={world}>
          <Bg kind={bg} local={10} />
          <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.35) 48%, rgba(0,0,0,0) 75%)'}} />
          <svg viewBox="0 0 1920 1080" style={ABS}>
            <g transform="translate(1380 880) scale(2.1)">{draw(0.6)}</g>
            <Stick x={1000} y={900} s={2.3} role={doodle ? 'person' : 'narrator'} action="scared" t={0.6} local={30} flip={false} expr="surprised" />
            <text x={1740} y={250} fontSize={340} textAnchor="middle" fill="#e11d2e" stroke={INK} strokeWidth={12} transform="rotate(10 1740 250)" style={{fontFamily: FONT, fontWeight: 900, paintOrder: 'stroke fill'}}>؟</text>
          </svg>
          <div style={{position: 'absolute', left: 50, top: 80, width: 900, height: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', direction: 'rtl', textAlign: 'center',
            fontFamily: FONT, fontWeight: 900, fontSize: size, lineHeight: 1.18, color: '#ffd23f', ...OUT('#16161d', 26), textShadow: '0 14px 0 rgba(0,0,0,0.35)'}}>{props.thumbText}</div>
          <LogoMark size={230} withText uid="th" style={{position: 'absolute', left: 36, bottom: 30}} />
        </WorldCtx.Provider>
      </div>
    </AbsoluteFill>
  );
};
const Thumb: React.FC<Props> = (props) => <ThumbArt {...props} />;

const DEFAULT: Props = {
  fps: 24,
  totalFrames: 240,
  beats: [
    {from: 0, to: 120, text: 'مرحبا بكم في أوابد', mood: 'story', gesture: 'open', setting: 'cave', expression: 'happy'},
    {from: 120, to: 240, text: 'قبل آلاف السنين', mood: 'wonder', gesture: 'raise', setting: 'sea', expression: 'surprised'},
  ],
  envelope: Array.from({length: 240}, (_, i) => Math.abs(Math.sin(i * 0.5))),
  showCaptions: true,
  title: 'أوابد',
  thumbText: 'من بنى الأهرامات؟',
  thumbSetting: 'ruins',
  narratorStyle: 'arab',
  logoWidth: 88,
  logoOpacity: 0.7,
  audio: null,
};

const calc: CalculateMetadataFunction<Props> = ({props}) => ({
  durationInFrames: props.totalFrames,
  fps: props.fps,
});

const DEFAULT_SHORT: ShortProps = {
  fps: 24,
  totalFrames: 240,
  beats: [
    {from: 0, to: 120, text: 'من هي زنوبيا؟', mood: 'story', gesture: 'raise', setting: 'ruins', expression: 'surprised'},
    {from: 120, to: 240, text: 'القصة كاملة على القناة', mood: 'wonder', gesture: 'open', setting: 'desert', expression: 'happy'},
  ],
  envelope: Array.from({length: 240}, (_, i) => Math.abs(Math.sin(i * 0.5))),
  hookText: 'ملكة تحدت روما',
  endText: 'القصة كاملة على القناة',
  narratorStyle: 'arab',
  logoWidth: 88,
  logoOpacity: 0.7,
  audio: null,
};

const calcShort: CalculateMetadataFunction<ShortProps> = ({props}) => ({
  durationInFrames: props.totalFrames,
  fps: props.fps,
});

export const Root: React.FC = () => (
  <>
    <Composition id="Main" component={Main} width={1280} height={720} fps={24}
      durationInFrames={240} defaultProps={DEFAULT} calculateMetadata={calc} />
    <Composition id="Short" component={Short} width={720} height={1280} fps={24}
      durationInFrames={240} defaultProps={DEFAULT_SHORT} calculateMetadata={calcShort} />
    <Still id="Thumb" component={Thumb} width={1280} height={720} defaultProps={DEFAULT} />
  </>
);

registerRoot(Root);
export {Main, Short, Thumb};
'''


def setup_video():
    """ينشئ ملفات مشروع الفيديو (video/package.json و video/src/index.tsx) من هذا الملف نفسه."""
    d = Path("video")
    (d / "src").mkdir(parents=True, exist_ok=True)
    (d / "package.json").write_text(VIDEO_PACKAGE_JSON, encoding="utf-8")
    (d / "src" / "index.tsx").write_text(VIDEO_INDEX_TSX, encoding="utf-8")
    print("[setup] تم إنشاء ملفات مشروع الفيديو")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["publish", "health", "dry-run", "selftest", "setup"])
    ap.add_argument("--render", action="store_true", help="مع dry-run: يشغل Remotion فعلاً")
    a = ap.parse_args()
    sys.exit({"publish": publish, "health": health, "dry-run": lambda: dry_run(a.render),
              "selftest": selftest, "setup": setup_video}[a.cmd]())


if __name__ == "__main__":
    main()
