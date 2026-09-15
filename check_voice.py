import pyttsx3

engine = pyttsx3.init("sapi5")

voices = engine.getProperty("voices")

for i, voice in enumerate(voices):
    print(i, voice.name)
    print(voice.id)
    print()

# Tìm Microsoft An
an_voice = None

for voice in voices:
    if "MSTTS_V110_viVN_An" in voice.id:
        an_voice = voice
        break

if an_voice is None:
    print("KHÔNG tìm thấy Microsoft An")
    exit()

print("Đã chọn:", an_voice.name)
print("ID:", an_voice.id)

engine.setProperty("voice", an_voice.id)
engine.setProperty("rate", 150)
engine.setProperty("volume", 1.0)

engine.say("Xin chào. Đây là giọng nói tiếng Việt Microsoft An.")
engine.runAndWait()

engine.stop()