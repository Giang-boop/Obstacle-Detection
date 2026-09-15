import threading
import queue
import pyttsx3


# ============================================================
# SPEECH QUEUE
# ============================================================

speech_queue = queue.Queue(
    maxsize=1
)


# ============================================================
# FIND VIETNAMESE VOICE
# ============================================================

def find_vietnamese_voice(engine):

    voices = engine.getProperty(
        "voices"
    )

    # --------------------------------------------------------
    # Ưu tiên Microsoft An
    # --------------------------------------------------------

    for voice in voices:

        text = (
            str(getattr(voice, "id", "")) + " " +
            str(getattr(voice, "name", "")) + " " +
            str(getattr(voice, "languages", ""))
        ).lower()

        if "mstts_v110_vivn_an" in text:

            return voice.id

    # --------------------------------------------------------
    # Tìm voice tiếng Việt khác
    # --------------------------------------------------------

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


# ============================================================
# TTS WORKER
# ============================================================

def tts_worker():

    while True:

        message = speech_queue.get()

        if message is None:

            speech_queue.task_done()

            break

        try:

            engine = pyttsx3.init(
                "sapi5"
            )

            vietnamese_voice = (
                find_vietnamese_voice(
                    engine
                )
            )

            if vietnamese_voice:

                engine.setProperty(
                    "voice",
                    vietnamese_voice
                )

                print(
                    "[TTS] Đã chọn voice tiếng Việt."
                )

            else:

                print(
                    "[TTS WARNING] "
                    "Không tìm thấy voice tiếng Việt."
                )

            engine.setProperty(
                "rate",
                165
            )

            engine.setProperty(
                "volume",
                1.0
            )

            print(
                "[VOICE]",
                message
            )

            engine.say(
                message
            )

            engine.runAndWait()

            engine.stop()

            del engine

        except Exception as e:

            print(
                "[TTS ERROR]",
                e
            )

        finally:

            speech_queue.task_done()


# ============================================================
# START TTS
# ============================================================

tts_thread = threading.Thread(
    target=tts_worker,
    daemon=True
)

tts_thread.start()


# ============================================================
# SPEAK
# ============================================================

def speak(message):

    if speech_queue.empty():

        try:

            speech_queue.put_nowait(
                message
            )

        except queue.Full:

            pass


# ============================================================
# STOP TTS
# ============================================================

def stop_tts():

    try:

        speech_queue.put(
            None
        )

    except Exception:

        pass