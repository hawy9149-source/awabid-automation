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
    }
    FALLBACK_TOPICS = [(c, t) for c, ts in CATEGORIES.items() for t in ts]

    # ---- الصوت ----
    VOICES = ["ar-SA-HamedNeural", "ar-AE-HamdanNeural", "ar-EG-ShakirNeural", "fr-FR-RemyMultilingualNeural"]
    TTS_RATE = "-4%"
    TTS_PITCH = "-2Hz"
    LEAD_SEC = 1.0        # سكوت قبل أول كلمة
    SENT_GAP = 0.32       # وقفة بين الجمل
    BEAT_GAP = 0.55       # وقفة بين المقاطع
    TAIL_SEC = 4.0        # نهاية الفيديو (موسيقى فقط)

    # ---- الفيديو ----
    FPS = 24
    WIDTH, HEIGHT = 1280, 720
    SHOW_CAPTIONS = False
    RENDER_CONCURRENCY = 2
    LOGO_WIDTH = 88        # بكسل (من 1280)
    LOGO_OPACITY = 0.7

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


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        return json.loads(t)
    except Exception:
        a, b = t.find("{"), t.rfind("}")
        if a != -1 and b > a:
            return json.loads(t[a:b + 1])
        raise


class Gemini:
    def __init__(self, key=None):
        self.key = key or get_key()
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

    def generate(self, prompt, system=None, json_mode=False, temperature=0.8):
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
                    out = self._call(m, prompt, system, json_mode, temperature)
                    self.last_model = m
                    return out
                except _Dead as e:
                    self.dead.add(m)
                    last = e
                except _Retry as e:
                    last = e
        raise GeminiError(f"فشل Gemini بعد كل المحاولات: {last}")

    def _call(self, model, prompt, system, json_mode, temperature, _mime=True):
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192}}
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
                text = "".join(p.get("text", "") for p in cand["content"]["parts"]).strip()
            except Exception:
                raise _Retry(f"{model}: رد فاضي أو محجوب")
            if not text:
                raise _Retry(f"{model}: نص فاضي")
            return text
        if s == 404:
            raise _Dead(f"{model}: 404 (الموديل ما عاد موجود)")
        if s == 400 and json_mode and _mime:
            return self._call(model, prompt, system, json_mode, temperature, _mime=False)
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
          "opens with a mystery or a 'why/how' question and keeps a thread of suspense. You rely on mainstream "
          "historical and archaeological consensus and never invent facts: when something is uncertain or debated "
          "you say so plainly (e.g. 'يرجح المؤرخون' or 'لا أحد يعرف بالتأكيد'). You treat every people and religion "
          "with respect and never discuss modern politics.")


def clean_text(t):
    t = _TASHKEEL.sub("", t or "")
    t = re.sub(r"[*#_`>\[\]{}|~^]", "", t)
    t = digits_to_words(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pick_category(state):
    """تدوير عادل: التصنيف الأقل استخداماً في آخر 40 فيديو (فيه عشوائية بين المتساويين)."""
    recent = Counter(h.get("category") for h in state.get("history", [])[-40:])
    cats = list(C.CATEGORIES)
    low = min(recent.get(c, 0) for c in cats)
    return random.choice([c for c in cats if recent.get(c, 0) == low])


def pick_topic(state, gem=None):
    """يرجع (التصنيف, الموضوع)."""
    cat = pick_category(state)
    used = [h.get("topic", "") for h in state.get("history", [])][-120:]
    if gem is not None:
        try:
            out = gem.generate(
                f"Suggest ONE fresh video topic for a 7-minute Arabic documentary in this category: «{cat}». "
                "Phrase it as a curious Arabic question that creates mystery, starting with one of: لماذا، كيف، "
                "من، ما سر، ماذا حدث. It must be a real, well-documented historical or archaeological subject "
                f"(no modern politics). Do NOT repeat or closely resemble any of these used topics: {used}. "
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


def _prompt(cat, topic):
    lo, hi = C.TARGET_WORDS
    return f"""Write the full narration script for a YouTube documentary video in Arabic.
Category: {cat}
Topic: "{topic}"

Script rules:
- Modern Standard Arabic, NO diacritics (no tashkeel). Total {lo}-{hi} words in 18-26 beats; each beat 30-65 words.
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
    sc["narrator_style"] = sc.get("narrator_style") if sc.get("narrator_style") in C.NARRATOR_STYLES else "arab"
    sc["description"] = (sc.get("description") or "").strip()
    sc["tags"] = [str(t).strip() for t in sc.get("tags", []) if str(t).strip()][:15]
    tags = [str(h).strip() for h in sc.get("hashtags", []) if str(h).strip()]
    sc["hashtags"] = [("#" + h.lstrip("#").replace(" ", "_")) for h in tags][:3] or ["#أوابد", "#تاريخ", "#وثائقي"]
    beats = []
    for b in sc.get("beats", []):
        text = clean_text(b.get("text", ""))
        if not text:
            continue
        beats.append({
            "text": text,
            "mood": b.get("mood") if b.get("mood") in C.MOODS else infer_mood(text),
            "gesture": b.get("gesture") if b.get("gesture") in C.GESTURES else "none",
            "setting": b.get("setting") if b.get("setting") in C.SETTINGS else "ruins",
            "expression": b.get("expression") if b.get("expression") in C.EXPRESSIONS else "neutral",
            "chapter": clean_text(b.get("chapter", ""))[:40],
        })
    sc["beats"] = beats
    return sc


def word_count(sc):
    return sum(len(b["text"].split()) for b in sc["beats"])


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
        if len(b["text"].split()) > C.BEAT_WORDS_MAX:
            p.append(f"المقطع {i + 1} طويل ({len(b['text'].split())} كلمة)")
    blob = " ".join([sc["title"], sc["description"]] + [b["text"] for b in sc["beats"]])
    for w in C.BANNED_WORDS:
        if w in blob:
            p.append(f"فيه كلمة ممنوعة: {w}")
    if re.search(r"\d", " ".join(b["text"] for b in sc["beats"])):
        p.append("فيه أرقام بالأرقام، اكتبها بالحروف")
    if not sc["title"]:
        p.append("العنوان فاضي")
    if len(sc["title"]) > 70:
        p.append("العنوان أطول من 60 حرف، اختصره وخل الكلمة المفتاحية أول شي")
    return p


def build_script(cat, topic, gem, max_rounds=3):
    sc, problems = None, []
    for rnd in range(max_rounds):
        if rnd == 0 or sc is None:
            raw = gem.generate(_prompt(cat, topic), system=SYSTEM, json_mode=True)
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
    parts.append("اشترك في قناة أوابد وفعّل الجرس لتصلك رحلات جديدة في التاريخ والحضارات والألغاز كل أسبوع.")
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


async def _edge(text, voice):
    import edge_tts
    buf = bytearray()
    async for ch in edge_tts.Communicate(text, voice, rate=C.TTS_RATE, pitch=C.TTS_PITCH).stream():
        if ch["type"] == "audio":
            buf += ch["data"]
    if not buf:
        raise RuntimeError("edge-tts رجع صوت فاضي")
    return bytes(buf)


def make_edge_synth():
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
                return asyncio.run(_edge(text, voice))
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


def tts_build(beats, outdir, synth, fps=None):
    fps = fps or C.FPS
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    chunks, pos, starts = [_sil(C.LEAD_SEC)], int(C.LEAD_SEC * SR), []
    for b in beats:
        starts.append(pos)
        sents = split_sentences(clean_text(b["text"]))
        for i, s in enumerate(sents):
            a = _trim(decode(synth(s)))
            chunks.append(a)
            pos += len(a)
            if i < len(sents) - 1:
                g = _sil(C.SENT_GAP)
                chunks.append(g)
                pos += len(g)
        g = _sil(C.BEAT_GAP)
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
    manifest = {"fps": fps, "totalFrames": total_frames, "totalSec": total_sec, "beats": out_beats}
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
def mix(narration_wav, music, out_mp3):
    """music: مصفوفة (2, N) من render_timeline."""
    narration_wav, out_mp3 = Path(narration_wav), Path(out_mp3)
    music_wav = narration_wav.parent / "music.wav"
    wavfile.write(str(music_wav), SR, (np.clip(music.T, -1, 1) * 32767).astype(np.int16))
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    g = C.MUSIC_GAIN
    fc = (f"[0:a]aformat=channel_layouts=stereo,asplit=2[nar][sc];"
          f"[1:a]volume={g}[m];"
          f"[m][sc]sidechaincompress=threshold=0.02:ratio=12:attack=30:release=700:makeup=1[duck];"
          f"[nar][duck]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[mx];"
          f"[mx]loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(narration_wav), "-i", str(music_wav),
                    "-filter_complex", fc, "-map", "[out]", "-ar", "44100", "-b:a", "192k", str(out_mp3)],
                   check=True)
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


def write_props(manifest, envelope, script, path=None):
    path = path or VIDEO_DIR / "public" / "props.json"
    props = {"fps": manifest["fps"], "totalFrames": manifest["totalFrames"], "beats": manifest["beats"],
             "envelope": envelope, "showCaptions": C.SHOW_CAPTIONS, "title": script["title"],
             "thumbText": script["thumb_text"], "thumbSetting": script["thumb_setting"],
             "narratorStyle": script["narrator_style"], "logoWidth": C.LOGO_WIDTH, "logoOpacity": C.LOGO_OPACITY,
             "audio": "audio/mix.mp3"}
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


def produce(cat, topic, gem, synth, do_render=True):
    """موضوع -> سكربت -> صوت -> موسيقى -> مزج -> (رندر). يرجع (script, manifest, mp4, thumb)."""
    script = build_script(cat, topic, gem)
    manifest, envelope, narr = tts_build(script["beats"], WORK, synth)
    print(f"[tts] المدة {manifest['totalSec'] / 60:.1f} دقيقة، {manifest['totalFrames']} فريم")
    bed, segs = render_timeline(manifest["beats"], manifest["totalSec"], C.MOOD_STYLE)
    print("[music] الأقسام:", [(s, round(a), round(b)) for s, a, b in segs])
    mix(narr, bed, VIDEO_DIR / "public" / "audio" / "mix.mp3")
    write_props(manifest, envelope, script)
    if not do_render:
        return script, manifest, None, None
    mp4 = WORK / "video.mp4"
    render_video(mp4)
    thumb = render_thumb(WORK / "thumb.jpg") or frame_thumbnail(mp4, WORK / "thumb.jpg")
    return script, manifest, mp4, thumb


def publish():
    state = load_state()
    now = datetime.now(timezone.utc)
    state["last_run"] = now.isoformat()
    try:
        creds = check_token()                       # أهم نقطة: نفشل بسرعة لو التوكن ميت
        yt = yt_client(creds)
        slot = pick_slot(now, state, existing_scheduled(yt))
        if slot is None:
            rest = [k for k in resting_slots(now, state) if k not in state["alerted"]]
            if rest:
                state["alerted"].extend(rest)
                save_state(state)
                summary(f"❌ مواعيد فشلت محاولاتها وتنتظر إعادة المحاولة: {rest}\nراجع آخر خطأ: {state.get('last_error')}")
                return 1
            save_state(state)
            summary("✅ ما فيه موعد يحتاج فيديو الحين (الرصيد مكتمل).")
            return 0
        k = slot_key(slot)
        n = register_attempt(state, k, now)
        save_state(state)                           # نسجل المحاولة قبل أي شغل ثقيل
        print(f"[run] الموعد {k} (محاولة {n}/{C.MAX_ATTEMPTS})")

        gem = Gemini()
        cat, topic = pick_topic(state, gem)
        print(f"[run] التصنيف: {cat} | الموضوع: {topic}")
        script, manifest, mp4, thumb = produce(cat, topic, gem, make_edge_synth())
        vid, locked = yt_upload(
            yt, mp4, {"title": script["title"], "description": build_description(script, manifest),
                      "tags": script["tags"]}, slot, thumb)
        state["done"].append(k)
        state["history"].append({"category": cat, "topic": topic, "title": script["title"], "slot": k,
                                 "video_id": vid, "at": now.isoformat()})
        state["last_error"] = None
        save_state(state)
        summary(f"### ✅ تم\n- العنوان: {script['title']}\n- التصنيف: {cat}\n- الموضوع: {topic}\n"
                f"- الموعد: {slot.astimezone(C.TZ):%Y-%m-%d %H:%M} (الرياض)\n- الرابط: https://youtu.be/{vid}\n"
                f"- موديل Gemini: {gem.last_model}\n- الكلمات: {word_count(script)}\n"
                f"- الصورة المصغرة: {'نعم' if thumb else 'لا (تخطيناها والنشر كمل)'}")
        if locked:
            summary("### ⚠️ الفيديو انرفع لكن الجدولة ما انحفظت\nغالباً مشروع Google Cloud غير موثّق فيوتيوب يقفل الفيديو خاص. "
                    "افتح YouTube Studio وتأكد، وإذا كان مقفل قدّم نموذج YouTube API Services Audit (التفاصيل في README).")
            return 1
        return 0
    except Exception as e:
        traceback.print_exc()
        state["last_error"] = f"{type(e).__name__}: {str(e)[:400]}"
        save_state(state)
        summary(f"### ❌ فشل\n```\n{state['last_error']}\n```")
        return 1


def health():
    md, bad = report(run_checks())
    summary("### الفحص الصحي\n" + md)
    return 1 if bad else 0


# ---------------- اختبار كامل بمكونات وهمية (بدون شبكة) ----------------
class FakeGemini:
    last_model = "fake"

    def generate(self, prompt, **kw):
        if "Suggest ONE" in prompt:
            return json.dumps({"topic": "لماذا بنيت مدينة تجريبية قديمة؟"}, ensure_ascii=False)
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


def dry_run(do_render=False):
    gem = FakeGemini()
    cat, topic = pick_topic({"history": []}, gem)
    script, manifest, mp4, thumb = produce(cat, topic, gem, fake_synth, do_render=do_render)
    sr, nar = wavfile.read(WORK / "narration.wav")
    nar = nar.astype(np.float32) / 32768
    _, m = wavfile.read(WORK / "music.wav")
    m = m.astype(np.float32) / 32768 * C.MUSIC_GAIN
    v = nar[np.abs(nar) > 0.01]
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    print(f"[dry] صوت المعلق {db(v):.1f} dB | الموسيقى {db(m):.1f} dB | الفرق {db(v) - db(m):.1f} dB")
    print(f"[dry] {len(script['beats'])} مقطع، {word_count(script)} كلمة، {manifest['totalSec']:.0f} ثانية")
    desc = build_description(script, manifest)
    print("[dry] الوصف:\n" + desc)
    assert db(v) - db(m) > 12, "الموسيقى عالية نسبة لصوت المعلق"
    assert not any(ch.isdigit() for b in script["beats"] for ch in b["text"]), "بقيت أرقام"
    assert "00:00" not in desc and "0:00" in desc, "الفصول لازم تبدأ من 0:00"
    print("[dry] الموعد القادم:", pick_slot(datetime.now(timezone.utc), load_state("/tmp/none.json")))
    print("[dry] OK")
    return 0


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
    h = {"history": [{"category": c} for c in list(C.CATEGORIES)[:-1]]}
    assert pick_category(h) == list(C.CATEGORIES)[-1]
    assert len(split_sentences("جملة أولى طويلة هنا. جملة ثانية طويلة هنا؟ نعم.")) == 2
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
};

// الشعار مدموج بالكود (ما تحتاج ترفع صورة)
const LOGO = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAMAAACahl6sAAABgFBMVEUdEyeskF775ItqWEqiXDnqvYGdW0HbkiCbgTn013cfIjUgXGRJPUBcUTbCXj/HYUGBPjTatF4AAAD1oVMPRlYyWVnseErztzQRCCXpsW4dEigiFSk1ZGLynFO7d0b+wTQOO0zrtk3GiFMxJi/jpzo0YF4TU2LWp3FPNy/Sly8HAxz1g03lrm1rRzTZpDgsSE0UUF5GKy71x4eNZjKyhjNyVTMFAjoeESjxyWfMnGnFfEcXJjmYdDPQZ0IeEiiIWDlXRDMAAFUpOUKKZkoeEShsODOoejDdsHZyV0eyh1P1w1j613KNRjcoXGEdEShMSEbPlkvVpUodEigdESjPjCayVzyna0IxMzj96IWTdU8jESl2ZTgwATK2lDkRLUHkmycAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACx9IwAAAAYHRSTlMg//////////////////////8A//////////z+//////////////////////////////////8Gzf///////3P//wP//47///////////+t////MVD///////8U/wf///+s6VvNAAAj5klEQVR42s2dC1/iOtrAcZwze+bs2bP7jlRiC1gJagG5dABRQUERBmbU8e441+//Ld4nT5I2bVMuwnn3zdnfjgLS/PvckzRJvFtm+37K/00kbu9Ozq9aLVNprdbV+cndbSLBP3P6famXTiztm/Z5974CAQJYlhlp+FqrBTxfT5U/+n8Egh36enty1YLOSgQr0vzXzdbVye3XJbIsAwRvLkB4UsAuE20zPVD2/wDjfcF/G2QfTeK8Zfrdwx5bFnV6zWa93sFWrzebZcelluDhNEwy52g0+/8PJIIUAgIR3HJ9WKjkU6nNUEul8pXCsF52LAGDf8VY/rsS2UeN4hQcAhg6hXwK+xzX2Jv5QqeJNBwGWFDH9v8rIKDY+3dXPoVJm8NKahJCECdVaTRd02e5uttfxFoSC2CctFgfkMJy6oUghJBKpVIoFCqsiRc3AzCFTs8SLJbVOlkAJfFSjK/nQhjQD6cDolD7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';

const FONT = "'Noto Sans Arabic','Noto Naskh Arabic','Cairo','Tajawal',sans-serif";

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
export const Room: React.FC = () => {
  const f = useCurrentFrame();
  const flicker = 0.85 + Math.sin(f * 0.37) * 0.06 + Math.sin(f * 1.13) * 0.04;
  const lampX = 1500;
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
      <rect x={1380} y={640} width={240} height={20} rx={6} fill="#5a3d26" />
      <rect x={1490} y={660} width={20} height={170} fill="#4a301d" />
      <rect x={1488} y={560} width={24} height={80} fill="#3a3a3a" />
      <path d="M 1450 560 L 1550 560 L 1530 470 L 1470 470 Z" fill="#c98b2b" />
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
export const Desert: React.FC<{ruins?: boolean}> = ({ruins}) => {
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
      <circle cx={1380} cy={600} r={380 * glow} fill="url(#sunGlow)" />
      <circle cx={1380} cy={600} r={100} fill="#fff0c2" />
      <g transform={`translate(${sway2} 0)`}>
        <path d="M -200 760 Q 200 640 620 740 T 1420 700 T 2200 760 L 2200 1080 L -200 1080 Z" fill="#b8704a" />
      </g>
      {ruins && (
        <g>
          <Column x={250} h={300} />
          <Column x={470} h={190} broken />
          <Column x={1650} h={340} />
        </g>
      )}
      <g transform={`translate(${sway1} 0)`}>
        <path d="M -200 840 Q 300 760 800 830 T 1700 810 T 2200 850 L 2200 1080 L -200 1080 Z" fill="#d79a62" />
      </g>
      <path d="M 0 890 Q 480 850 960 888 T 1920 870 L 1920 1080 L 0 1080 Z" fill="#e8b97a" />
    </svg>
  );
};


// كهف ونار ورسومات جدارية: كلها كود
export const Cave: React.FC = () => {
  const f = useCurrentFrame();
  const fl = 0.85 + Math.sin(f * 0.31) * 0.07 + Math.sin(f * 0.97) * 0.05;
  const h = 150 * fl;
  const fx = 1520;
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
      <Hand x={330} y={420} r={-8} />
      <Hand x={430} y={470} r={10} />
      <Hand x={250} y={520} r={-15} />
      <g transform="translate(560 360)" fill="#7a2f20" opacity={0.7}>
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
export const Hills: React.FC = () => {
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
      <circle cx={1500} cy={260} r={260} fill="url(#hSun)" />
      <circle cx={1500} cy={260} r={64} fill="#fffbe0" />
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
export const Sea: React.FC = () => {
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
      <circle cx={1350} cy={560} r={110} fill="#fff0c2" />
      <rect y={620} width={1920} height={460} fill="url(#sSea)" />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={1350 - 130 + i * 8} y={630 + i * 34} width={260 - i * 16} height={7} rx={3} fill="#ffe3a3" opacity={0.55 - i * 0.08} />
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

export const Backdrop: React.FC<{setting: string}> = ({setting}) => {
  if (setting === 'room') return <Room />;
  if (setting === 'cave') return <Cave />;
  if (setting === 'hills') return <Hills />;
  if (setting === 'sea') return <Sea />;
  return <Desert ruins={setting === 'ruins'} />;
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
      <Img src={LOGO}
        style={{position: 'absolute', left: 24, bottom: 22, width: props.logoWidth, opacity: props.logoOpacity}} />

      <AbsoluteFill style={{background: '#000', opacity: Math.max(fadeIn, fadeOut), pointerEvents: 'none'}} />
      {props.audio && <Audio src={staticFile(props.audio)} />}
    </AbsoluteFill>
  );
};

const THUMB_POSE: Pose = {headAngle: -4, armL: 150, armR: -35, bob: 0, mouth: 0.6, blink: 0, brow: 1, mood: 'surprised'};

// الصورة المصغرة: نص كبير غامض، علامة استفهام حمراء، شخصية مندهشة، تعتيم يسار لوضوح النص
export const Thumb: React.FC<Props> = (props) => {
  const pal = PALETTES[props.narratorStyle] ?? PALETTES.arab;
  const n = (props.thumbText || '').length;
  const size = n <= 14 ? 138 : n <= 22 ? 116 : 96;
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Backdrop setting={props.thumbSetting} />
      <div style={{position: 'absolute', inset: 0,
        background: 'linear-gradient(90deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.4) 45%, rgba(0,0,0,0) 72%)'}} />
      <div style={{position: 'absolute', right: 20, top: -70, fontSize: 560, fontWeight: 900, color: '#ff3b30',
        opacity: 0.9, fontFamily: FONT, lineHeight: 1, textShadow: '0 0 50px rgba(0,0,0,0.8)'}}>؟</div>
      <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
        <Character pose={THUMB_POSE} x={1400} y={240} scale={1.6} robe={pal.robe} turban={pal.turban} skin={pal.skin} />
      </svg>
      <div style={{position: 'absolute', left: 34, top: 60, width: 720, height: 540, display: 'flex',
        alignItems: 'center', justifyContent: 'center', direction: 'rtl', textAlign: 'center',
        fontFamily: FONT, fontWeight: 900, fontSize: size, lineHeight: 1.22, color: '#ffd23f',
        WebkitTextStroke: '12px #140a14', paintOrder: 'stroke fill', textShadow: '0 8px 24px rgba(0,0,0,0.7)'}}>
        {props.thumbText}
      </div>
      <Img src={LOGO} style={{position: 'absolute', left: 30, bottom: 26, width: props.logoWidth * 1.7}} />
    </AbsoluteFill>
  );
};

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

export const Root: React.FC = () => (
  <>
    <Composition id="Main" component={Scene} width={1280} height={720} fps={24}
      durationInFrames={240} defaultProps={DEFAULT} calculateMetadata={calc} />
    <Still id="Thumb" component={Thumb} width={1280} height={720} defaultProps={DEFAULT} />
  </>
);

registerRoot(Root);
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
