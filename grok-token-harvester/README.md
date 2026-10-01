# Grok CLI / 9Router Automated Token Harvester

ระบบสมัครบัญชี Grok (xAI) และทำ **OAuth2 Device Code Flow** เพื่อดึง `access_token`, `refresh_token`, `id_token` อัตโนมัติ 100% บันทึกออกเป็นไฟล์ **JSON** พร้อมคัดลอกหรือลากวาง (Drag & Drop) เข้า **9Router** ทันที เพื่อนำไปใช้งานกับ **Claude Code** และเครื่องมืออื่นๆ ได้ลื่นไหล

---

## โครงสร้างโฟลเดอร์
```text
grok-token-harvester/
├── grok_accounts.json         # ไฟล์ JSON สำหรับโยนเข้า 9Router (Batch Import)
├── .env                       # ตั้งค่า Gmail IMAP และ Catch-all Domain
├── register_grok_tokens.py    # สคริปต์สมัคร Grok + ดึง OAuth Tokens อัตโนมัติ
├── test_grok_tokens.py        # สคริปต์ทดสอบความสดใหม่และสถานะ Grok Code ของ Token
├── requirements.txt           # Dependencies
└── README.md                  # คู่มือการใช้งาน
```

---

## รูปแบบไฟล์ JSON (`grok_accounts.json`)
ระบบจะสร้างไฟล์ JSON ในฟอร์แมตมาตรฐานของ 9Router:
```json
[
  {
    "access_token": "eyJ0eXAiOiJhdCtqd3Qi...",
    "refresh_token": "onFBwYpXQpAp6Rz7...",
    "id_token": "eyJ0eXAiOiJKV1QiLCJh...",
    "email": "grok_xxxx@thirx.com"
  }
]
```

---

## วิธีการใช้งาน

### 1. ติดตั้ง Dependencies
```powershell
pip install -r requirements.txt
```

### 2. รันสมัครและดึง Token อัตโนมัติ
```powershell
# ฟาร์ม 1 บัญชี (เบื้องหลัง)
python register_grok_tokens.py --count 1

# ฟาร์ม 5 บัญชีรวดเดียว
python register_grok_tokens.py --count 5
```

### 3. ตรวจสอบสถานะ Token
```powershell
python test_grok_tokens.py
```

---

## วิธีนำเข้า 9Router ในคลิกเดียว
1. เปิดหน้าแดชบอร์ดของ **9Router** -> เข้าไปที่แท็บ **Providers** -> เลือก **Grok CLI** (หรือคลิก Add Connection)
2. กดปุ่ม **Import** (หรือเปิดกล่อง Batch Import)
3. **ลากไฟล์ `grok_accounts.json` ไปหย่อนลงในกล่อง** หรือเปิดไฟล์แล้วก็อปปี้เนื้อหา JSON ทั้งหมดไปวาง
4. กดบันทึก (Save) ระบบ 9Router จะเชื่อมต่อ Grok ทุกบัญชี พร้อมตั้งระบบ Auto Refresh Token ให้ทันที
