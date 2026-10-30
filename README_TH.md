# MR STAR RGB Controller — v1.1.2 (30 October 2026)

Windows GUI สำหรับไฟ MODI LIFE MD-NEON-U5 ECO RGB และอุปกรณ์ MR STAR BLE ที่พบชื่อ **GATT--DEMO**

## Hotfix V1.1.2 — RGB Primary 99–100% dimming
- จากผลการทดสอบกับไฟจริง: Red / Green / Blue ที่ 98% สว่างปกติ แต่ 99 และ 100% กลับมืดลงมาก สีผสมอื่นไม่มีอาการ
- เพิ่ม **RGB primary brightness fix** (เปิดใช้งานเริ่มต้น): หากเลือกแม่สี Red, Green, Blue และระดับที่คำนวณได้เกิน 98% โปรแกรมจะส่งค่า 98% (`0x03EB` หรือ 1003) แทน โดย GUI ยังคงเลื่อนถึง 100% ได้
- สีผสม Yellow / Cyan / Magenta / White / Orange และสีอื่นไม่ถูกจำกัด ทั้งหมดทำงานแบบเดิม
- มี Checkbox ให้เปิดปิดโหมดเพื่อเปรียบเทียบกับคำสั่งเดิม และ Activity Log แสดงค่าที่ส่งจริง
- วิธีทดสอบ: เปิด Fix, ตั้ง Red 100%, ดูว่า Log ระบุ sent 98% raw 1003 จากนั้นเปลี่ยน Yellow 100% ต้องเห็น raw 1024
- สาเหตุใน Firmware ยังไม่ยืนยัน เป็น workaround ตามผลการทดสอบจริง ไม่ใช่การแก้ Controller Firmware

## Hotfix V1.1.1 — แก้ความสว่างสั่งผ่าน BLE
- **สาเหตุที่พบ:** V1.1.0 แปลง GUI 100% เป็นค่า BLE `100` (hex `0x0064`) แต่ไลบรารี MR STAR อีกชุดหนึ่งกำหนด brightness เป็นช่วง **0–1024** โดย `set_brightness(1.0)` ส่ง `1024` (hex `0x0400`). ค่าจากโปรแกรมเดิมจึงคิดเป็นเพียง ~9.8% ของสเกลใหม่นี้
- **แก้ไข:** GUI 100% → 1024 (`BC 05 06 04 00 00 00 00 00 55`); 50% → 512; 25% → 256. เปลี่ยนที่ `protocol.py` ฟังก์ชัน `brightness_to_raw` และ `brightness_frame` เพื่อให้ทุกปุ่มใช้ค่าที่แก้แล้ว ทั้งสีปกติ, Custom HEX, Brightness, และ MAX WHITE
- เพิ่ม Unit Test ยืนยัน 100%, 50%, 25%, 0% และค่าที่เกิน 100% พร้อมแสดง raw BLE value ใน Activity Log
- ตรวจสอบข้อมูลอ้างอิง: https://github.com/mishamyrt/mr-star-ble/blob/main/mr_star_ble/commands.py (ใช้ `int(1024 * brightness)`)
- ยังไม่ได้ยืนยันกับ LED ตัวจริง: หากไฟไม่เปลี่ยนแปลง ให้เทียบการใช้ **แหล่งจ่าย USB 5V ที่รองรับกระแสตามสเปก** และผลความสว่างจากแอป MR STAR โดยใช้สีเดียวกัน; หลีกเลี่ยงการทดลองส่งค่าเกิน 1024

## สิ่งที่เปลี่ยนจาก V1.0.0
1. **แก้พรีเซ็ตสีให้เป็น RGB/HEX มาตรฐาน** โดยเฉพาะ Red `#FF0000` แทน `#FF343F`; Green `#00FF00`, Blue `#0000FF`, Yellow `#FFFF00`, Cyan `#00FFFF`, Magenta `#FF00FF` และสถานะ Standby/Running/Warning/Error/Completed ใช้สีเต็มค่าด้วย
2. **ความสว่างเริ่มต้น 100%**; เมื่อกดสีแต่ละสี โปรแกรมส่ง `Power ON + HSV Color + Brightness` เสมอ จึงไม่ใช้ค่าหรี่แสงค้างจากแอปเดิมโดยไม่ได้ตั้งใจ
3. **HEX Value support:** Controller รับ HSV Hue/Saturation แยกจาก Brightness; HEX `#800000` จะประมาณความสว่าง 50% เมื่อ Master=100%, `#FF0000` ประมาณ 100%; เป็นการแปลงตามสูตร ไม่ใช่การยืนยันว่าสีจริงบน LED จะตรงมาตรฐาน sRGB
4. เพิ่ม **Hue Calibration -30° ถึง +30°** สำหรับชดเชยความต่างของเฉดไฟจริง (ค่าเริ่ม 0°)
5. เพิ่มปุ่ม **MAX WHITE / Compare** ส่ง White Mode แยกที่มีใน MR STAR Protocol แล้วตามด้วยความสว่าง 100% เพื่อเปรียบเทียบกับ White ของ RGB ปกติ
6. เพิ่ม **Native Effect Presets 15 แบบ** ได้แก่ Auto, Symphony, Energy, Color Jump, Strobe, Gradient, Flutter, RGB Flutter, Brush, Opening, Light/Dark, Running Water, Flow, Trailing และ Seven-color Running
7. เลือก **Effect ID เองได้ 1–117**, ปรับ Speed 0–100 และ Direction Forward/Reverse
8. เพิ่ม **PC Software Blink** สำหรับสีที่เลือก (ระยะเวลา ON/OFF 250, 500, 1000, 2000ms) พร้อม Stop effects / Solid color
9. ยังคง BLE Status, Scan/Connect/Disconnect, Auto Reconnect, Custom HEX, Color Palette, Status Preset และ Activity Log

## การติดตั้งบน Windows
- ติดตั้ง Python 3.10 ขึ้นไป พร้อม Python Launcher (`py`)
- แตก ZIP แล้วดับเบิลคลิก `INSTALL_WINDOWS.bat` (ครั้งแรกต้องใช้อินเทอร์เน็ตติดตั้ง `bleak`)
- เปิด `RUN_WINDOWS.bat` เพื่อใช้ GUI
- เมื่อใช้ได้แล้ว สามารถเปิด `BUILD_EXE.bat` บน Windows เพื่อสร้าง EXE จากเครื่องคุณเอง (`dist\\MR_STAR_RGB_Controller.exe`)
- ยังไม่มี EXE ที่คอมไพล์จาก Windows ให้ในแพ็กเกจนี้; ไฟล์ ZIP เป็น Source Project

## วิธีใช้ไฟจริง
1. เสียบสายไฟ USB 5V ของ LED; PC ต้องรองรับ Bluetooth LE
2. ปิดแอป MR STAR และตัดการเชื่อมต่อ Bluetooth จากมือถือ
3. บน GUI กด **Scan → เลือก GATT--DEMO → Connect**
4. ทดสอบปุ่มสี **Red** (ส่ง `#FF0000` + Brightness 100%) และสีมาตรฐานอื่น ๆ
5. หากต้องการพิจารณาความสว่างสูงสุด เลือก White ใน Palette แล้วเทียบกับ **MAX WHITE / Compare**
6. เลื่อนลงไปที่ **EFFECTS & RUNNING LIGHT**, คลิก Preset เช่น **007 Strobe / Flash** หรือ **091 Seven-color running**
7. หากเอฟเฟกต์แสดงถูกต้องแล้วค่อยปรับ **Speed**, **Direction**, หรือเลือก **Effect ID 1–117**
8. คลิก **Stop effects / Solid color** เพื่อยกเลิก Pattern และกลับไปใช้สีที่เลือก
9. ปุ่ม **Start Blink** จะส่งคำสั่งเปิด/ปิดสลับกันจาก PC จึงต้องมี BLE ต่ออยู่ตลอด และเวลาการกระพริบอาจคลาดเคลื่อนจากเวลาที่เลือก
10. ใช้ **Hue Calibration** เฉพาะเมื่อสีพื้นฐานไม่ตรงบนไฟจริง และรีเซ็ตกลับ 0° ได้ทุกเมื่อ

## ข้อจำกัดและการตรวจสอบความสว่าง
- ค่าความสว่าง **100% ใน V1.1.1 = BLE raw 1024** (ใน V1.1.2 จะ cap ที่ 1003 เฉพาะ pure RGB เมื่อเปิด compatibility mode) (`BC 05 06 04 00 ...`) ซึ่งเป็นค่าที่พบจากไลบรารี MR STAR อีกชุดหนึ่ง ส่วนการยืนยันกับ MODI LIFE รุ่นนี้ต้องทดสอบจริง หากยังสว่างน้อย อาจเป็นแหล่งจ่าย USB 5V, Mode/Firmware, ชนิด LED หรือข้อจำกัดทางฮาร์ดแวร์
- RGB จริงขึ้นกับการผสมแสง, Calibration และ Driver; การส่ง `#FF0000` ไม่เท่ากับรับประกันว่าสีแสงที่ตาเห็นจะเป็น sRGB #FF0000
- White แบบ Dedicated ใช้ Command ที่พบในชุมชน แต่ยังไม่ยืนยันว่า Controller MODI LIFE ของคุณรองรับหรือให้แสงที่สว่างกว่า
- **เอฟเฟกต์ 1–117** มาจากการ reverse engineer แอป MR STAR บนอุปกรณ์ GATT-DEMO รุ่นอื่น; อาจทำงานต่างกันหรือไม่รองรับบางหมายเลขบน MD-NEON-U5 ECO
- ลักษณะ **ไฟวิ่งเป็นจุดตามความยาว (chasing)** ต้องใช้ไฟ Strip ที่ควบคุมแต่ละ Segment/Pixel ได้จริง ถ้าเป็น Strip RGB แบบทั้งเส้นใช้ชุดสีเดียว แม้ส่ง Effect Running ได้ ก็อาจแสดงได้เพียงการเปลี่ยนสีพร้อมกันทั้งเส้น
- Activity Log บันทึกคำสั่งที่ BLE API ส่งออกสำเร็จ **ไม่ใช่การยืนยันการเปลี่ยนสีจากไฟจริง**; อุปกรณ์ไม่มี RGB readback ที่ยืนยันได้
- หากกระพริบด้วย PC แล้ว Bluetooth หลุด การทำงานของ Blink จะหยุด ไม่เหมาะเป็นสัญญาณเตือนด้านความปลอดภัยของ Chamber

## ไฟล์โปรเจกต์
- `app.py`: GUI Tkinter
- `ble_manager.py`: BLE manager แบบ asyncio background thread, command serialization และ software Blink
- `protocol.py`: Frames พร้อม HSV/Value mapping และ Native Effects
- `tests/test_protocol.py`: Unit Tests
- `RUN_WINDOWS.bat`, `INSTALL_WINDOWS.bat`, `BUILD_EXE.bat`: Script สำหรับ Windows
- `GUI_Preview_TOP.png`, `GUI_Preview_EFFECTS.png`: รูป GUI ทดสอบในโหมด DEMO

## เปิดทดสอบแบบไม่มีไฟจริง
```powershell
py app.py --demo
py -m unittest discover -s tests -v
```

## เอกสารอ้างอิง
- MR STAR / GATT-DEMO reverse-engineering: https://github.com/labsensacional/mrstar-ble-light (MIT)
- BLE protocol details: https://github.com/labsensacional/mrstar-ble-light/blob/main/docs/ble_reverse_engineering.md
- Bleak Python BLE library: https://bleak.readthedocs.io/

**การใช้กับ Chamber**: ไฟ MR STAR BLE นี้ใช้สำหรับแสดงสถานะทั่วไป ไม่ควรใช้แทน Hardware Interlock, E-Stop หรือ Safety Alarm
