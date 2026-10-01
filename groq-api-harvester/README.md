# Groq Cloud API Harvester (Automated Tool Calling Keys)

ชุดเครื่องมือสมัครบัญชีและเก็บเกี่ยว **Groq Cloud API Key (`gsk_...`)** อัตโนมัติ 100% เพื่อนำไปใช้งานกับ **9Router**, **One API**, **Claude Code**, **Cursor**, **Cline** โดยรองรับ Native Function Calling / Tool Calling 100%

---

## โครงสร้างโปรเจกต์

```text
groq-api-harvester/
├── .env                  # การตั้งค่า Gmail IMAP Catch-All (*@thirx.com)
├── register_groq.py      # บอทสมัคร Groq และสร้าง API Key อัตโนมัติ
├── test_keys.py          # สคริปต์ตรวจสอบสถานะคีย์และความเร็ว Latency
├── requirements.txt      # ไลบรารี Python
├── README.md             # คู่มือการใช้งาน
└── keys/
    └── groq_keys.txt     # ที่เก็บคีย์ทั้งหมด (email|api_key)
```

---

## วิธีการใช้งาน

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

## ฟอร์แมตคีย์สำหรับ 9Router
คีย์จะถูกเซฟอัตโนมัติในไฟล์ `keys/groq_keys.txt` ในรูปแบบ:
```text
email|gsk_xxxxxxxxxxxxxxxxxxxx
```
สามารถคัดลอกไปวางในหน้า Providers ของ 9Router ได้ทันที
