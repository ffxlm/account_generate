# OpenRouter Automated API Key Harvester

ระบบสมัครสมาชิกและสร้าง API Key อัตโนมัติสำหรับ **OpenRouter** แยกโฟลเดอร์ทำงานเป็นอิสระ 100% พร้อมระบบดึงลิงก์ยืนยันตัวตน Clerk Magic Link ผ่าน Gmail IMAP และบันทึกคีย์ลงในรูปแบบพร้อม Import เข้า **9Router** ทันที (`name|apiKey`)

---

## โครงสร้างโปรเจกต์
```text
openrouter-api-harvester/
├── keys/
│   └── openrouter_keys.txt   # ไฟล์เก็บคีย์สำหรับ 9Router (name|apiKey)
├── .env                      # ข้อมูล Gmail IMAP และ Catch-all Domain
├── register_openrouter.py    # สคริปต์ฟาร์มคีย์อัตโนมัติ (รองรับ --count N)
├── test_keys.py              # สคริปต์ทดสอบและเช็คความเร็วของ API Key
├── requirements.txt          # รายการไลบรารีที่จำเป็น
└── README.md                 # คู่มือการใช้งาน
```

---

## การตั้งค่า (.env)
```ini
GMAIL_BASE_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
CUSTOM_DOMAIN=thirx.com
```

---

## วิธีการใช้งาน

### 1. ติดตั้ง Dependencies
```powershell
pip install -r requirements.txt
```

### 2. รันเก็บคีย์ OpenRouter อัตโนมัติ
```powershell
# ฟาร์ม 1 คีย์
python register_openrouter.py --count 1

# ฟาร์ม 5 คีย์ต่อเนื่อง
python register_openrouter.py --count 5
```

### 3. ตรวจสอบคีย์ที่เก็บมาได้ (Validator)
```powershell
# ตรวจสอบกับโมเดลฟรีค่าเริ่มต้น (openrouter/free)
python test_keys.py

# หรือระบุโมเดลเฉพาะเจาะจง
python test_keys.py --model cohere/north-mini-code:free
```

---

## คีย์ที่พร้อมใช้งานสำหรับ 9Router
ไฟล์จะถูกบันทึกอยู่ที่ `keys/openrouter_keys.txt` ในฟอร์แมต:
```text
email|sk-or-v1-xxxxxx
```
คัดลอกทั้งบรรทัดไปวางในหน้า Providers ของ **9Router** ได้ทันที

---

## โมเดลฟรีเด่นๆ บน OpenRouter สำหรับการเขียนโค้ด

| Model Slug | คำอธิบาย / จุดเด่น | Context |
| :--- | :--- | :--- |
| `openrouter/free` | Auto-Router อัตโนมัติไปยังโมเดลฟรีที่ว่างและเร็วที่สุด | Auto |
| `cohere/north-mini-code:free` | สายเขียนโค้ดโดยเฉพาะ เก่งเรื่อง Debugging, Syntax, Refactor | 256K |
| `poolside/laguna-s-2.1:free` | Coding Agent 118B ออกแบบมาสำหรับงาน Software Engineering | 128K |
| `qwen/qwen3.8-27b:free` | ภาษาและ Logic ครบเครื่อง ตอบคำถามไทยได้ดีมาก | 128K |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | โมเดลขนาดยักษ์ 550B สำหรับ Deep Reasoning | 1M |
| `google/gemma-4-31b-it:free` | โมเดล Open-Weights ตัวล่าสุดจาก Google | 128K |
