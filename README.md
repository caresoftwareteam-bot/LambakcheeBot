# 👮‍♀️ ผู้ช่วยพูด-ฟัง สน.ลำผักชี (LamPakChee Police Voice Assistant)

ระบบผู้ช่วยอัจฉริยะสำหรับสถานีตำรวจ **สน.ลำผักชี**  
สามารถ “ฟังเสียง – วิเคราะห์ – ตอบกลับ – พูดออกเสียง” ได้โดยอัตโนมัติ  
พัฒนาโดยใช้ **Python + PyQt5 + SpeechRecognition + gTTS + RapidFuzz + PyThaiNLP**

---

## 🧠 ฟีเจอร์หลัก

### 🎙️ ระบบฟังเสียง (Speech Recognition)
- ใช้ไมโครโฟนรับเสียงผู้ใช้
- รองรับภาษาไทย (Google Speech Recognition)
- ปรับเสียงรบกวนอัตโนมัติ (`adjust_for_ambient_noise`)
- จำกัดเวลาพูด (`phrase_time_limit`)

### 💬 ระบบตอบกลับ (ChatBot Logic)
- ใช้ dictionary `police_info` เก็บข้อมูลตำรวจและบริการต่าง ๆ
- ตอบได้ทั้งเรื่อง:
  - เบอร์ติดต่อเจ้าหน้าที่
  - การแจ้งความ / ชำระค่าปรับ / ศูนย์ไกล่เกลี่ย
  - ตำแหน่งห้องในสถานี เช่น ห้องน้ำ ห้องจราจร
- ตรวจจับคำหยาบและคำถามที่กว้างเกินไป
- ใช้ `RapidFuzz` จับคำถามใกล้เคียง
- ใช้ `PyThaiNLP` สำหรับตัดคำภาษาไทย

### 🔊 ระบบเสียงตอบกลับ (Text-to-Speech)
- ใช้ `gTTS` แปลงข้อความเป็นเสียงภาษาไทย
- ปรับความเร็วเสียงได้ด้วย `pydub`
- ลบเสียงเงียบอัตโนมัติ
- พูดแบบแยก thread (`speak_async`) เพื่อไม่ให้บล็อก GUI

### 🧍‍♂️ ระบบตรวจจับผู้คน (Camera Detection)
- ใช้กล้อง WebCam
- ใช้ `YOLOv8` ตรวจจับบุคคลแบบเรียลไทม์
- แจ้งให้ผู้ใช้ทราบเมื่อมีคนเข้ามา
- สามารถส่งสัญญาณไป GUI เพื่อแสดงข้อความหรือ trigger TTS
- Overlay กล้องเล็กบน GUI เพื่อแสดงฟีดกล้อง

### 🧩 GUI (PyQt5)
- หน้าต่าง Fullscreen พร้อมปรับขนาดอัตโนมัติ
- แสดงสถานะ: preparing, listening, processing, idle
- แสดงภาพเคลื่อนไหว GIF และข้อความตอบกลับ
- Overlay กล้องเล็กพร้อม bounding box
- ใช้ `QLabel` และ `QMovie` แสดงภาพ GIF และข้อความ

---

## การติดตั้งและ Library ที่ต้องใช้

### Python Libraries
```bash
pip install PyQt5 opencv-python-headless speechrecognition gTTS pydub pythainlp rapidfuzz ultralytics numpy
```

---

## 🚀 การใช้งาน

รันโปรแกรมหลัก:
```bash
python main.py
```

โปรแกรมจะ:
1. พูดว่า “กำลังเริ่มระบบค่ะ”  
2. รอรับเสียงจากไมโครโฟน  
3. วิเคราะห์ข้อความที่พูด  
4. พูดตอบกลับออกลำโพง

---

## 🗣️ ตัวอย่างการโต้ตอบ

| ผู้ใช้ | ผู้ช่วย |
|--------|-----------|
| “ขอเบอร์ผู้กำกับหน่อยครับ” | “เบอร์ผู้กำกับ สน.ลำผักชี คือ 02-123-4567 ค่ะ” |
| “ห้องน้ำอยู่ไหน” | “ห้องน้ำอยู่หลังอาคารฝ่ายจราจรค่ะ” |
| “ตำรวจอยู่ไหน” | “ขอโทษค่ะ กรุณาระบุชื่อตำแหน่งหรือแผนกให้ชัดเจนกว่านี้ค่ะ” |

---

## 🧩 ส่วนโค้ดที่สำคัญ

### 🔹 ฟังก์ชันหลักสำหรับฟังเสียง
```python
with mic as source:
    while True:
        if stop_event and stop_event.is_set():
            break

        status_callback("listening")
        audio = r.listen(source, timeout=5, phrase_time_limit=6)

        try:
            text = r.recognize_google(audio, language="th-TH")
            answer = ask_bot(text)
            update_text_callback(answer)
            speak_async(answer)
        except sr.UnknownValueError:
            speak_async("ขอโทษค่ะ ไม่ได้ยินชัด กรุณาพูดอีกครั้งค่ะ")
```

---

## 🔐 ตัวอย่างการตรวจจับคำไม่เหมาะสม
```python
def contains_bad_word(text):
    bad_words = ["เหี้ย", "สัส", "แม่ง", "ควาย", "ไอ้"]
    return any(word in text for word in bad_words)
```

---

## 💡 หมายเหตุ

- รองรับการเชื่อมต่อกับ **YOLO** สำหรับตรวจจับบุคคลหรือวัตถุในกล้อง (import ไว้แล้ว)
- สามารถผสานเข้ากับ **PyQt5 GUI** เพื่อเพิ่มปุ่ม “เริ่มฟัง” / “หยุดฟัง” ได้

---

## 👨‍💻 พัฒนา

📍 สน.ลำผักชี — ระบบผู้ช่วยอัจฉริยะต้นแบบ  
🧩 พัฒนาโดยใช้ Python 3.10+

---
