# ⚡ Groq Cloud API Harvester (Automated Tool Calling Keys)

ชุดเครื่องมือสมัครบัญชีและเก็บเกี่ยว **Groq Cloud API Key (`gsk_...`)** อัตโนมัติ 100% เพื่อนำไปใช้งานกับ **9Router**, **One API**, **Claude Code**, **Cursor**, **Cline** โดยรองรับ Native Function Calling / Tool Calling 100%

---

## 📁 โครงสร้างโปรเจกต์

```text
groq-api-harvester/
├── .env                  # การตั้งค่า Gmail IMAP Catch-All (*@thirx.com)
├── register_groq.py      # บอทสมัคร Groq และสร้าง API Key อัตโนมัติ
├── test_keys.py          # สคริปต์ตรวจสอบสถานะคีย์และความเร็ว Latency
├── requirements.txt      # ไลบรารี Python
├── README.md             # คู่มือการใช้งาน
└── keys/
    └── groq_keys.txt     # ที่เก็บคีย์ทั้งหมด (email:api_key)
```

---

## 🚀 วิธีการใช้งาน

### 1. ดึง API Key ใหม่:
```powershell
# ดึง 1 คีย์
python register_groq.py

# ดึงหลายบัญชีต่อเนื่อง (เช่น 5 บัญชี)
python register_groq.py --count 5

# กำหนดหน่วงเวลาระหว่างรอบ (วินาที)
python register_groq.py --count 10 --delay 10
```

### 2. ตรวจสอบสถานะคีย์ทั้งหมด:
```powershell
python test_keys.py
```

---

## ⚙️ การนำไปใส่ใน 9Router / One API

1. ไปที่เมนู **Channels** -> กด **Add Channel**
2. ตั้งค่าตามนี้:
   - **Type:** `Groq` หรือ `OpenAI`
   - **Base URL:** `https://api.groq.com/openai/v1`
   - **Key:** คัดลอกจาก `keys/groq_keys.txt` ไปวางได้ทันที (ฟอร์แมต `name|apiKey` ตรงตามมาตรฐาน 9Router เป๊ะๆ)
   - **Models แนะนำ:**
     - `openai/gpt-oss-120b` (128k context, โมเดลใหญ่ ฉลาดมาก ตอบภาษาไทยได้ดี)
     - `qwen/qwen3.8-27b` (128k context, เก่งเขียนโค้ดและ Refactor)
     - `openai/gpt-oss-20b` (128k context, ตอบสนองไวพิเศษ)
     - `whisper-large-v3-turbo` (Speech to Text)

---

## 💡 ทำไมต้อง Groq สำหรับ Coding Assistant (Claude Code / Cursor)?
- **Native Tool Calling:** แตกต่างจาก Grok Web Chat ที่มโนตอบว่าสร้างโฟลเดอร์ แต่ไม่ได้รันจริง — Groq API ส่ง Function Calling มาตรฐานของ OpenAI ทำให้เครื่องมือรันคำสั่ง bash/powershell และเขียนไฟล์ลงเครื่องได้จริง
- **Ultra-Fast Speed:** รันบนชิป LPU ของ Groq ให้ความเร็วระดับ 300-500 tokens/วินาที
