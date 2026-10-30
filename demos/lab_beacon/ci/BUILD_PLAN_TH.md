# แผนสร้าง Windows EXE — พร้อมรออนุมัติ upload

ผลลัพธ์ที่ต้องสร้าง: Lab_Beacon_Demo_v1.0.3_Windows_x64.zip ภายในเป็นโฟลเดอร์ portable มี Lab_Beacon_Demo.exe และ _internal รวม Python, Tk, pywin32 และ BLE dependency ผู้ใช้แตก ZIP แล้วดับเบิลคลิก EXE ไม่ใช้ BAT, pip หรือ Python ในเครื่องแลป และ EXE ไม่ร้องขอยกระดับสิทธิ์ (manifest asInvoker)

สภาพแวดล้อมปัจจุบันเป็น Linux และไม่มี Windows runtime จึงยังไม่มี EXE ที่ build สำเร็จในชุดนี้ ไฟล์ ZIP ชุดเตรียม build เป็น source เท่านั้น

## การเปลี่ยนแปลงบน GitHub ที่เสนอ

- Repository: TOPTUBBY/Python-MR_STAR_RGB_Controller
- Branch ใหม่: feature/lab-beacon-exe จาก main ล่าสุด
- นำ source ของ demo ที่อยู่ใน git เท่านั้นเข้า demos/lab_beacon/ ไม่รวม .venv, backup, user settings หรือ canoe_diagnostic.json ที่ผู้ใช้ส่งมา
- เพิ่ม workflow ที่ .github/workflows/lab-beacon-windows.yml จาก ci/windows-build.yml
- ไม่แก้โปรแกรม MR STAR เดิมที่ root และไม่ merge เข้า main
- Push เข้า branch นี้จะเริ่ม GitHub Actions บน Windows runner

## ขั้นตอน build ที่เตรียมไว้

1. ติดตั้ง Python 3.13 x64 และ dependencies บน runner
2. Compile และรัน automated tests 20 รายการ
3. PyInstaller onedir + windowed + manifest asInvoker
4. เปิด EXE ที่ build จริงในโหมด simulated LED, เปิด UI, ขอแสดง 4 สี และ Off แล้วปิด UI ตรวจรายงานและ exit code ภายใน 45 วินาที
5. ทำ portable ZIP พร้อมคู่มือภาษาไทย, example CAPL, build dependency versions, smoke report และ SHA256
6. เก็บผลเป็น GitHub Actions artifact 14 วัน แล้วดาวน์โหลดไฟล์สำเร็จมาส่งผู้ใช้

## การตรวจที่ทำแล้ว

Python compile และ 20 unit tests ผ่านใน Linux ตรวจ manifest XML และ workflow configuration ด้วยการอ่านโค้ด ยังไม่ได้รัน Windows build หรือ packaged GUI smoke test ต้องทำบน Windows runner หลังได้รับอนุมัติ upload

EXE packaging ไม่ได้แก้หรือยืนยันว่าปัญหา COM 0x800401E3 ก่อนหน้าหายแล้ว ต้องทดสอบต่อบนเครื่อง CANoe จริง
