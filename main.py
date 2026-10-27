#!/usr/bin/env python3
"""
أوابد: أتمتة كاملة في ملف واحد.
  python main.py publish     # ينتج فيديو ويرفعه مجدول (يشتغل من GitHub Actions)
  python main.py health      # فحص صحي (توكن يوتيوب، مفتاح Gemini، ffmpeg، الصوت)
  python main.py dry-run     # اختبار بمكونات وهمية بدون شبكة (--render لتشغيل Remotion)
  python main.py selftest    # اختبارات الوحدات
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["publish", "health", "dry-run", "selftest"])
    ap.add_argument("--render", action="store_true", help="مع dry-run: يشغل Remotion فعلاً")
    a = ap.parse_args()
    sys.exit({"publish": publish, "health": health, "dry-run": lambda: dry_run(a.render),
              "selftest": selftest}[a.cmd]())


if __name__ == "__main__":
    main()
