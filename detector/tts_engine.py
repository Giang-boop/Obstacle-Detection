# ======================================================================
#  FILE: detector/tts_engine.py
#  CHUC NANG: Giọng SAPI tiếng Việt (Microsoft An) qua comtypes, hàng đợi ưu tiên 1 chỗ, ngắt giữa câu, bỏ câu lỗi thời.
# ======================================================================

import math
import threading
import queue
import time

import comtypes
import comtypes.client
import pyttsx3

from config import (
    MAX_MESSAGE_AGE,
    INTERRUPT_CLOSER_STEP,
    INTERRUPT_MIN_SPEAK_SECONDS
)

from runtime_settings import settings

speech_queue = queue.Queue(
    maxsize=1
)

queue_lock = threading.Lock()

current_speech = {
    "message": None,
    "interrupt": False,
    "start_time": None,
}

speech_callback = None

def set_speech_callback(callback):

    global speech_callback

    speech_callback = callback

def set_tts_volume(volume):

    settings.tts_volume = volume

def set_tts_muted(muted):

    settings.muted = bool(muted)

def notify(event, message):

    if speech_callback is None or message is None:
        return

    try:
        speech_callback(
            event,
            message,
            time.perf_counter()
        )
    except Exception as e:
        print("[TTS CALLBACK ERROR]", e)

def find_vietnamese_voice(engine):

    voices = engine.getProperty(
        "voices"
    )

    for voice in voices:

        text = (
            str(getattr(voice, "id", "")) + " " +
            str(getattr(voice, "name", "")) + " " +
            str(getattr(voice, "languages", ""))
        ).lower()

        if "mstts_v110_vivn_an" in text:

            return voice.id

    for voice in voices:

        text = (
            str(getattr(voice, "id", "")) + " " +
            str(getattr(voice, "name", "")) + " " +
            str(getattr(voice, "languages", ""))
        ).lower()

        if (
            "vi-vn" in text
            or "vivn" in text
            or "vietnam" in text
            or "vietnamese" in text
        ):

            return voice.id

    return None

SVSF_ASYNC = 1

SVSF_PURGE_BEFORE_SPEAK = 2

SRSE_IS_SPEAKING = 2

voice_cache = {
    "checked": False,
    "voice_id": None,
}

def prepare_voice():

    try:

        voice = comtypes.client.CreateObject(
            "SAPI.SpVoice"
        )

        tokens = voice.GetVoices()

        voice_id = None

        for i in range(tokens.Count):

            token = tokens.Item(i)

            text = (
                str(token.Id) + " " +
                str(token.GetDescription())
            ).lower()

            if "mstts_v110_vivn_an" in text:

                voice_id = token.Id

                break

        if voice_id is None:

            for i in range(tokens.Count):

                token = tokens.Item(i)

                text = (
                    str(token.Id) + " " +
                    str(token.GetDescription())
                ).lower()

                if (
                    "vi-vn" in text
                    or "vivn" in text
                    or "vietnam" in text
                    or "vietnamese" in text
                ):

                    voice_id = token.Id

                    break

        if voice_id:

            voice_cache["voice_id"] = voice_id

            print(
                "[TTS] Đã chọn voice tiếng Việt."
            )

        else:

            print(
                "[TTS] SAPI không thấy voice tiếng Việt, "
                "tìm tiếp trong kho giọng OneCore..."
            )

    except Exception as e:

        print(
            "[TTS ERROR]",
            e
        )

def sapi_rate_from_wpm(wpm):

    rate = int(math.log(wpm / 156.63, 1.11))

    return max(-10, min(10, rate))

ONECORE_VOICES = (
    r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices"
)

def find_onecore_vietnamese_token():

    try:

        category = comtypes.client.CreateObject(
            "SAPI.SpObjectTokenCategory"
        )

        category.SetId(ONECORE_VOICES, False)

        tokens = category.EnumerateTokens()

    except Exception:

        return None

    vietnamese = []

    for i in range(tokens.Count):

        token = tokens.Item(i)

        text = (
            token.Id + " " + token.GetDescription()
        ).lower()

        if "vivn_an" in text:
            return token

        if "vivn" in text or "vietnam" in text:
            vietnamese.append(token)

    return vietnamese[0] if vietnamese else None

def create_sapi_voice():

    voice = comtypes.client.CreateObject(
        "SAPI.SpVoice"
    )

    selected = False

    if voice_cache["voice_id"]:

        tokens = voice.GetVoices()

        for i in range(tokens.Count):

            token = tokens.Item(i)

            if token.Id == voice_cache["voice_id"]:

                voice.Voice = token

                selected = True

                break

    if not selected:

        token = find_onecore_vietnamese_token()

        if token is not None:

            voice.Voice = token

            print(
                "[TTS] Đã chọn voice tiếng Việt (OneCore):",
                token.GetDescription()
            )

        else:

            print(
                "[TTS WARNING] Không tìm thấy voice tiếng Việt. "
                "Cài: Settings > Time & Language > Language > "
                "thêm Tiếng Việt, tick Text-to-speech."
            )

    voice.Rate = sapi_rate_from_wpm(settings.tts_rate)

    return voice

def speak_now(voice, message):

    voice.Volume = int(round(settings.effective_volume() * 100))

    voice.Rate = sapi_rate_from_wpm(
        settings.tts_rate_danger
        if message.get("priority", 1) >= 2
        else settings.tts_rate
    )

    print(
        "[VOICE]",
        message["text"]
    )

    voice.Speak(
        message["text"],
        SVSF_ASYNC
    )

    started = False

    while True:

        if not started:

            status = voice.Status

            if status.RunningState == SRSE_IS_SPEAKING:

                started = True

                notify("start", message)

        if voice.WaitUntilDone(20):

            if not started:
                notify("start", message)

            return True

        if current_speech["interrupt"]:

            voice.Speak(
                "",
                SVSF_ASYNC | SVSF_PURGE_BEFORE_SPEAK
            )

            return False

def tts_worker():

    comtypes.CoInitialize()

    prepare_voice()

    voice = None

    try:

        voice = create_sapi_voice()

    except Exception as e:

        print(
            "[TTS ERROR]",
            e
        )

    voice_cache["checked"] = True

    while True:

        message = speech_queue.get()

        if message is None:

            speech_queue.task_done()

            break

        try:

            waited = time.perf_counter() - message["created_time"]

            if waited > MAX_MESSAGE_AGE:

                print(
                    "[TTS] Bỏ câu đã cũ:",
                    message["text"]
                )

                notify("dropped_stale", message)

                continue

            if voice is None:

                voice = create_sapi_voice()

            current_speech["message"] = message
            current_speech["interrupt"] = False
            current_speech["start_time"] = time.perf_counter()

            finished = speak_now(
                voice,
                message
            )

            if finished:

                notify("done", message)

            else:

                notify("interrupted", message)

        except Exception as e:

            print(
                "[TTS ERROR]",
                e
            )

            voice = None

        finally:

            current_speech["message"] = None
            current_speech["interrupt"] = False
            current_speech["start_time"] = None

            speech_queue.task_done()

tts_thread = threading.Thread(
    target=tts_worker,
    daemon=True
)

tts_thread.start()

def speak(
    message,
    priority=1,
    created_time=None,
    alert_id=None,
    distance=None
):

    item = {
        "text": message,
        "priority": priority,
        "created_time": (
            created_time
            if created_time is not None
            else time.perf_counter()
        ),
        "alert_id": alert_id,
        "distance": distance,
    }

    with queue_lock:

        try:

            pending = speech_queue.get_nowait()

            speech_queue.task_done()

        except queue.Empty:

            pending = None

        if (
            pending is not None
            and pending["priority"] > priority
        ):

            speech_queue.put_nowait(pending)

            notify("dropped_lower", item)

            return False

        if pending is not None:

            notify("replaced", pending)

        speech_queue.put_nowait(item)

        speaking = current_speech["message"]

        spoke_long_enough = (
            current_speech.get("start_time") is None
            or time.perf_counter() - current_speech["start_time"]
            >= INTERRUPT_MIN_SPEAK_SECONDS
        )

        should_interrupt = (
            speaking is not None
            and (
                priority > speaking["priority"]
                or (
                    spoke_long_enough
                    and distance is not None
                    and speaking.get("distance") is not None
                    and distance
                    <= speaking["distance"] - INTERRUPT_CLOSER_STEP
                )
            )
        )

        if should_interrupt:

            current_speech["interrupt"] = True

    return True

def stop_tts():

    with queue_lock:

        try:

            speech_queue.get_nowait()

            speech_queue.task_done()

        except queue.Empty:

            pass

        current_speech["interrupt"] = True

        try:

            speech_queue.put_nowait(
                None
            )

        except Exception:

            pass

