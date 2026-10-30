# Lab Beacon Demo — CANoe + MR STAR RGB

โปรแกรมสาธิตแยกจาก MR STAR RGB Controller สำหรับ Windows ใช้ไฟ BLE แจ้งสถานะงานในแลป พร้อม Debug กดทดสอบไฟได้โดยไม่ต้องมี CANoe

**เวอร์ชัน 1.0.5-demo — Windows x64 Portable EXE**

สำหรับชุด Windows portable: แตก ZIP ทั้งหมด แล้วดับเบิลคลิก `Lab_Beacon_Demo.exe` ไม่ต้องติดตั้ง Python ไม่ใช้ BAT และโปรแกรมไม่ร้องขอ Administrator ต้องเก็บโฟลเดอร์ `_internal` ไว้ข้าง EXE เสมอ

ไป Debug / Test เพื่อกดทดสอบไฟ และกด **Save CANoe diagnostic report...** เพื่อบันทึกข้อมูลวินิจฉัยจากใน GUI โดยตรง หากไม่มีไฟ ให้ใช้โหมด Debug เพื่อดู preview ได้ (การส่ง BLE ต้องมีอุปกรณ์จริง) ตัวเลือกจำลอง BLE ใช้ผ่าน `--simulate-led` หรือการทดสอบ CI

คำแนะนำติดตั้ง Python/BAT ด้านล่างสำหรับผู้ที่รันจาก source เท่านั้น ไม่ต้องทำบนเครื่องแลปที่ใช้ EXE

## สถานะและลำดับความสำคัญ

| ลำดับ | สถานะ | HEX | ค่าเริ่มต้น |
|---|---|---|---|
| 1 | CANoe error ที่อ่านจาก System Variable / error ที่ค้างไว้ | `#FF0000` | Blink 500 ms |
| 2 | DI water ใน chamber ใกล้หมด | `#00FFFF` | Blink 500 ms |
| 3 | Disk เหลือน้อย | `#FFFF00` | Blink 500 ms |
| 4 | CANoe Measurement กำลัง Running | `#00FF00` | Solid |
| — | Stop ปกติ / Unknown | ปิดไฟ | มีข้อความแยกสถานะบนหน้าจอ |

เมื่อหลาย alarm พร้อมกัน แสดง alarm ที่มีลำดับสูงสุด เมื่อ alarm นั้นหาย ไฟกลับไปแสดงสถานะถัดไปเอง Error จะค้างจนกด **Acknowledge error** และ source ไม่มี error แล้ว ปิด rule ที่ไม่ต้องการได้ แต่อย่าปิดถ้ายังต้องการเห็น alarm นั้น

## ติดตั้งและเริ่มใช้งาน

1. แตก ZIP ไปยังโฟลเดอร์ที่เขียนไฟล์ได้ ติดตั้ง Python 3.11 ขึ้นไปบน Windows พร้อม Python Launcher (`py`) และ Tcl/Tk
2. รัน `INSTALL_WINDOWS.bat` ครั้งแรก ต้องมีอินเทอร์เน็ตสำหรับติดตั้ง `bleak` และ `pywin32`
3. รัน `RUN_WINDOWS.bat` สำหรับใช้งาน BLE จริง เปิด Bluetooth ของ PC
4. ปิดแอป MR STAR บนมือถือ/โปรแกรมอื่นที่กำลังจับไฟดวงเดียวกัน กด **Scan BLE** เลือกชื่อ/Address ของไฟ แล้วกด **Connect**
5. เปิด CANoe และ Config ที่ต้องการด้วยตัวเอง แล้วเลือก **Enable CANoe monitor** ในโปรแกรม Beacon
6. เริ่ม Measurement ใน CANoe เมื่อสถานะและแหล่งข้อมูลที่เปิดใช้พร้อมแล้ว ไฟจะเป็นสีเขียว

ไม่มีการเปิด CANoe, โหลด Config, Start/Stop Measurement หรือ Quit CANoe จากโปรแกรมนี้ ใช้ COM `GetActiveObject` เพื่อเกาะ instance ที่เปิดอยู่เท่านั้น ถ้าปิด CANoe โปรแกรมรอจนเปิดขึ้นใหม่และจะลองเชื่อมต่อเอง รองรับการเชื่อมต่อ COM โดยไม่ต้องสร้าง wrapper เฉพาะเวอร์ชัน แต่ยังต้องทดสอบกับ CANoe เวอร์ชันจริงของแลป หากเปิดหลาย instance การเลือก instance ตาม COM ROT อาจไม่ตรงตัวที่ต้องการ แนะนำเปิดตัวเดียว

หาก COM ไม่เจอ ให้รัน CANoe และ Beacon ภายใต้ Windows user เดียวกันและระดับสิทธิ์เดียวกัน ตรวจสอบว่า CANoe ลงทะเบียน COM server แล้วตามคู่มือ Vector ของเวอร์ชันที่ใช้

## Debug และทดสอบโดยไม่มีอุปกรณ์

- ถ้าไม่มีไฟ BLE ใช้ `RUN_SIMULATED_LED.bat` แทน แถบด้านบนจะแสดง **SIMULATED LED**
- กด Scan → เลือก DEMO → Connect เพื่อดูคำสั่งจำลองใน log
- ไปแท็บ **Debug / Test** กด Running, Error, Disk, DI Water หรือ Idle/Off
- ปุ่มเหล่านี้เปลี่ยนโหมดเป็น Debug อัตโนมัติ และสั่งไฟจริงถ้าเปิดด้วย `RUN_WINDOWS.bat` และเชื่อมต่อไฟจริงอยู่
- กลับไป **Auto** เพื่อใช้สถานะจริง Debug ไม่เขียนค่าเข้า CANoe และไม่เปลี่ยน alarm latch จริง
- โหมดจำลองไฟยังเลือกเปิด CANoe monitor จริงได้ จึงตรวจ COM ได้แม้ยังไม่มีไฟ

## Solid / Blink / เปิดปิด

ในแท็บ **Settings** ตั้งแยกแต่ละสถานะ แล้วกด **Apply & Save settings**

- **Enabled**: เปิด/ปิดการแสดงสถานะนั้น หากปิดจะเลือกสถานะลำดับถัดไป
- **Solid**: ติดค้าง
- **Blink**: ติด/ดับสลับกัน ใช้ ON และ OFF เท่ากัน ตั้งได้ **250–3,000 ms ต่อช่วง**
- ตัวอย่าง `500` = ON 0.5 s + OFF 0.5 s = รอบละ 1 วินาที ส่วน `1000` = ON 1 s + OFF 1 s
- **LED output enabled** ด้านบน: ปิดเพื่อสั่งไฟ OFF แต่ยังติดตามสถานะในหน้าจอ
- ความสว่างเริ่มต้น 98% และคงตัวแก้ปัญหา pure RGB ที่เคยพบหรี่ผิดปกติที่ 99–100% ไว้ หากตั้ง 100% สี pure red/green/blue จะส่งจริงไม่เกิน 98%

Blink ทำโดย PC ผ่าน BLE ไม่ใช่ hardware timer เวลาอาจคลาดเคลื่อนตาม Windows/Bluetooth หน้าจอแสดง preview จังหวะโดยประมาณ ไม่ใช่ feedback จากหลอดไฟ เมื่อเชื่อมต่อใหม่โปรแกรมจะส่งสถานะล่าสุดให้อีกครั้ง

## Stop ปกติกับ Stop เพราะ Error

`Measurement.Running` บอกได้เพียง Run/Stop จึงไม่ตีความ Stop ทุกครั้งว่าเป็น Error

**วิธีแนะนำ:** เปิด `Enable error System Variable` กำหนด path และค่า active เช่น `LabBeacon::Error` เท่ากับ `1` จากนั้นให้ test sequence/CAPL ตั้งค่านี้เมื่อมีความผิดปกติ และค้างค่าไว้จนโปรแกรมอ่านทัน โปรแกรมอ่านประมาณทุก 250 ms และเก็บ Error latch ไว้แม้ Measurement หยุดหรือ CANoe หลุด กด Acknowledge หลังแก้สาเหตุแล้ว โปรแกรมไม่เขียน reset ให้ CANoe

การตั้ง Error เพียงชั่วครู่แล้ว Stop ทันทีอาจถูก polling พลาดได้ ควรตั้งก่อน Stop อย่างน้อย 1 วินาทีในการสาธิต หรือคงค่าจน acknowledge ผ่านขั้นตอนของแลป และต้องทดสอบพฤติกรรมค่า System Variable หลัง Stop ใน Config จริง

**วิธีง่ายสำหรับทดลอง:** เลือก `Treat every observed Running → Stop as error` จะทำให้การ Stop ปกติขึ้นสีแดงด้วย เฉพาะเมื่อโปรแกรมเห็น Running มาก่อน การตัด COM ไม่ถูกนับเป็น Stop

Error source และ DI source ปิดไว้เริ่มต้น เพื่อให้ทดลอง Running ได้ก่อนโดยไม่ต้องแก้ Config ห้ามคาดหวังการตรวจ error จริงจนกว่าจะเปิดและผูกสัญญาณเหล่านี้

## เชื่อมสถานะ DI water จาก chamber

เปิด `Enable DI water System Variable` และใส่ path เช่น `LabBeacon::DIWaterLow` ค่า active `1`

ให้โปรแกรม chamber controller หรือ CAPL ที่ได้รับ alarm ของ chamber จริงเขียนค่าลง System Variable นี้ โปรแกรม Beacon อ่านผ่าน CANoe เท่านั้น ในเวอร์ชันสาธิตนี้ยังไม่มีการเชื่อม RS232/Modbus ของ chamber หรืออ่าน alarm จาก chamber โดยตรง หากชื่อจริงต่างกัน ให้เปลี่ยน path เป็นชื่อจริง รวมถึง namespace ซ้อนได้ เช่น `Chamber26::Alarm::DIWaterLow`

DI alarm จะตามค่าปัจจุบันของ source และไม่ latch เมื่อค่าเปลี่ยนกลับจะกลับไปแสดงสถานะที่ยัง active หากอ่าน source ที่เปิดใช้ไม่ได้ จะแสดง Unknown และไม่แสดงไฟเขียวจากข้อมูลที่ไม่ครบ

## ตัวอย่าง CAPL

1. เปิด Environment → System Variables ใน CANoe สร้าง Integer สองตัวใน namespace `LabBeacon`: `Error` และ `DIWaterLow` ค่า initial 0, minimum 0, maximum 1
2. เพิ่ม program node และใช้ `examples/LabBeacon_Demo.can` แล้ว Compile
3. ใน Beacon เปิด error source และ water source → Apply & Save → Enable monitor → Start CANoe
4. ใน CANoe กด `w` → ฟ้า, `r` → clear water, `e` → แดง, `c` → clear error จากนั้นกด Acknowledge ใน Beacon
5. ทดสอบ error stop: กด `e` รออย่างน้อย 1 วินาที แล้ว Stop CANoe ไฟแดงต้องค้าง
6. ทดสอบ normal stop: clear error, acknowledge, Start แล้ว Stop โดยไม่ตั้ง Error ไฟดับ (เมื่อไม่มี alarm อื่น)

ตัวอย่างใช้คีย์บอร์ดเป็นแหล่งข้อมูลจำลองเท่านั้น ต้องปรับเข้ากับ logic/สัญญาณจริง และ Compile ตรวจสอบกับ CANoe รุ่นที่ใช้งาน

## Disk warning

ระบุ drive หรือโฟลเดอร์ที่เก็บ logging จริง เช่น `D:\\CANoeLogs` ค่า default `C:\\` ตรวจประมาณทุก 2 วินาที เตือนเมื่อ free space น้อยกว่าหรือเท่ากับ **GB หรือ percent** ที่ตั้ง ค่าเริ่มต้น 10 GB หรือ 5% หากเลือก path ผิดจะแสดง Unknown แยกจาก disk warning

ทดสอบได้โดยเพิ่ม threshold GB ให้สูงกว่าพื้นที่ว่างจริงชั่วคราว จากนั้นตั้งกลับ เมื่อใช้งานจริงระบบติดตามต่อเนื่องตลอดที่เปิดโปรแกรม ไม่อิงเวลาแจ้งเตือน 07:00/16:00 ของ RedDetect

## โครงสร้างและการจัดเก็บ

- `app.py`: Tkinter UI, alarm arbitration, disk worker, COM watchdog
- `monitor.py`: COM reader ใน process แยก เพื่อให้หน้าจอ/BLE ไม่ติดค้างตาม RPC
- `core.py`: policy / settings / latch / System Variable reader
- `protocol.py`, `ble_manager.py`: พัฒนาต่อจาก MR STAR Controller เดิม ใช้ GATT FFF3 และ serialize คำสั่ง Solid/Blink/OFF
- `tests/test_beacon.py`: tests สำหรับ policy, mocked COM และ simulated BLE
- ค่าตั้งเก็บที่ `%LOCALAPPDATA%\LabBeaconDemo\settings.json` กด Apply แล้วคงค่าเมื่อเปิดใหม่
- ไม่บันทึก BLE address และไม่ auto-connect ไฟตอนเปิดโปรแกรม ผู้ใช้เลือกไฟก่อนทุกครั้ง
- ปิดโปรแกรมจะพยายามสั่ง OFF ก่อน disconnect ถ้าลิงก์หลุดอยู่สั่งไม่ได้ และไฟอาจค้างสถานะสุดท้าย

เมื่อ COM ไม่ตอบกลับเกิน 4 วินาทีจะถือว่าข้อมูล stale และไม่ใช้ Running เก่ามาแสดงเขียว Watchdog เริ่ม observer process ใหม่เมื่อค้างเกิน 6 วินาที โดยไม่ปิดหรือเปิด CANoe

## สร้าง EXE และทดสอบ

รัน `BUILD_EXE.bat` บน Windows จะสร้าง `dist\Lab_Beacon_Demo\Lab_Beacon_Demo.exe` แจกทั้งโฟลเดอร์ร่วมกับไฟล์ dependency ภายใน ไม่ใช่เฉพาะ EXE ตัวเดียว

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ตรวจแล้ว: build EXE บน Windows x64, เปิด packaged GUI และสั่งไฟจำลองผ่าน พร้อม Python compile/import และ 20 automated tests ผ่าน รวม alarm priority ทุกกรณี, latch, disk boundary, nested namespace, attach-only COM mock และ Blink → Solid/OFF ผ่าน simulated BLE ยังไม่ได้ทดสอบ COM กับ CANoe จริง, Compile CAPL ด้วย CANoe หรือ Bluetooth กับหลอดจริง จึงควรทำ acceptance checklist ด้านล่างก่อนใช้ในแลป

## Acceptance checklist บนเครื่องแลป

- Debug ได้ไฟทั้ง 4 สีตรงตามตาราง ทั้ง Solid และ Blink 500/1000 ms
- ปิด LED output แล้วดับทันทีที่ BLE ส่งคำสั่งสำเร็จ
- Start/Stop CANoe ปกติได้เขียว/ดับ และไม่ได้เปิด CANoe กลับมาเองเมื่อปิด
- Error source active แล้ว Stop ได้แดงค้าง; clear source + acknowledge แล้วหาย
- Water และ disk พร้อมกันแสดงฟ้า; clear water กลับมาเหลือง; error แทรกได้แดง
- Disconnect BLE / ปิด CANoe / ใช้ path ผิด มีข้อความบอก และไม่ค้างเขียวจากข้อมูลเก่าใน preview
- เปิดไฟใหม่/กลับมาเชื่อมต่อ BLE แสดงสถานะปัจจุบัน และเลิก Blink เมื่อเปลี่ยนเป็น Solid/OFF

## Credits / References

- Base controller, BLE transport and protocol: [TOPTUBBY/Python-MR_STAR_RGB_Controller](https://github.com/TOPTUBBY/Python-MR_STAR_RGB_Controller) — MIT, Copyright 2026 Patiphan Phakdeeburi. `protocol.py` reused; `ble_manager.py` adapted with serialized external operations. Original files fetched from main on 30 October 2026.
- Community MR STAR BLE protocol research: [labsensacional/mrstar-ble-light](https://github.com/labsensacional/mrstar-ble-light). Credit for protocol reference; this demo uses the user's controller implementation, not a copy of that repository's source.
- [Bleak documentation](https://bleak.readthedocs.io/) — Python Bluetooth transport.
- [pywin32 GetActiveObject](https://timgolden.me.uk/pywin32-docs/pythoncom__GetActiveObject_meth.html) — attach to existing COM object.
- [Vector CANoe Test Feature Set Tutorial](https://support.vector.com/sys_attachment.do?sys_id=b1d992aa1bcca094d2cd97de1d4bcb4b) — creating user System Variables. Exact COM object details should be checked in CANoe Help → COM Interface on the installed version.

การทำงานผ่าน BLE เป็นไฟแสดงสถานะเสริมสำหรับงานสาธิต ไม่ควรใช้แทน safety interlock ของชุดทดสอบ


## v1.0.1 — แก้ไขการค้นหา active CANoe และเพิ่ม Diagnostic

ข้อความ `0x800401E3 / Operation unavailable` หมายถึง GetActiveObject หา active COM object ไม่พบ ไม่ได้ยืนยันว่า CANoe ปิดอยู่ และยังบอกสาเหตุเดียวแน่นอนไม่ได้

1. เปิด CANoe และ Config ให้พร้อม แล้วเปิด Beacon โดยใช้ Windows user เดียวกัน แนะนำเริ่มจากเปิดทั้งคู่แบบปกติ ไม่ใช้ Run as administrator
2. หากจำเป็นต้องรัน CANoe แบบ administrator ให้เปิด Beacon ในระดับเดียวกันด้วย (เปิด Command Prompt แบบ administrator แล้วเรียก RUN_WINDOWS.bat)
3. เลือก Enable CANoe monitor ใหม่ เวอร์ชันนี้ลอง GetActiveObject แล้วค้นหา moniker ของ CANoe ใน Running Object Table เพิ่ม โดยไม่สั่งเปิด CANoe หาก fallback พบหลาย object จะหยุดและแจ้งให้เหลือ instance เดียว
4. ถ้ายังไม่สำเร็จ รัน DIAGNOSE_CANOE.bat ภายใต้สิทธิ์เดียวกับ Beacon เก็บผลที่ `%LOCALAPPDATA%\LabBeaconDemo\canoe_diagnostic.json` รายงานมีชื่อ user, path โปรแกรม, process CANoe, registry COM ทั้ง 32/64 bit และผล attach เพื่อช่วยวินิจฉัย ไม่มีการเปลี่ยน registry หรือเปิด CANoe จาก diagnostic
5. หากรายงานชี้ไปยัง COM registration รุ่นอื่น/ไม่มี registration ให้ตรวจคู่มือ CANoe Help → Technical References → COM Interface → Computer Configuration ของรุ่นที่ติดตั้งก่อนใช้ RegisterComponents.exe ของรุ่นนั้น ไม่เปลี่ยน registration อัตโนมัติ

ข้อความเริ่มต้นเปลี่ยนจาก Waiting / COM timeout เป็น Connecting to active CANoe เพื่อไม่ทำให้สับสนระหว่างช่วงเริ่มต้นกับ COM ที่ค้างจริง เพิ่ม mocked tests 6 รายการ รวมทั้งหมด 20 tests ผ่าน ยังต้องตรวจสอบกับ CANoe จริง และ ROT fallback ไม่สามารถแก้ปัญหาสิทธิ์หรือการลงทะเบียนที่หายไปได้ทุกกรณี

แหล่งอ้างอิงเพิ่มเติม: [Microsoft COM HRESULT codes](https://learn.microsoft.com/en-us/windows/win32/com/com-error-codes-1), [GetActiveObject](https://learn.microsoft.com/en-us/windows/win32/api/oleauto/nf-oleauto-getactiveobject)

## v1.0.2 — ซ่อม Python environment ที่ชี้ไปยัง executable ที่หายไป

ข้อความ `did not find executable at ...Python314\python.exe` เกิดก่อนเริ่ม Beacon: `.venv` อ้างถึง Python installation ที่ไม่มีใน path นั้นแล้ว อาจเกิดจากย้ายโฟลเดอร์โปรเจกต์, ถอน/เปลี่ยน Python หรือใช้คนละ Windows account จึงไม่ใช่ผลทดสอบ COM รอบใหม่

1. แตก ZIP v1.0.2 ลงโฟลเดอร์ใหม่ที่เขียนไฟล์ได้ แล้วรัน INSTALL_WINDOWS.bat ภายใต้ Windows account ที่จะใช้งานจริง
2. ตัวติดตั้งจะใช้ environment ที่ยังทำงานได้ หรือเลือก Python 64-bit ที่เรียกใช้งานได้จริง โดยลอง 3.13, 3.12, 3.11, 3.14 ตามลำดับ แล้วลอง python จาก PATH
3. ถ้า environment เดิมเสีย จะเปลี่ยนชื่อเป็น `.venv_backup_<random>` ก่อนสร้างใหม่ ไม่ลบของเดิม ค่าตั้ง Beacon ยังคงอยู่ใน LOCALAPPDATA
4. หากต้องยกระดับสิทธิ์ Beacon ให้ใช้ Run as administrator ภายใต้ account เดิม การใส่ credentials ของ account อื่นอาจทำให้ Python ที่มองเห็นและ LOCALAPPDATA เปลี่ยนไป
5. รัน RUN_WINDOWS.bat อีกครั้ง Launcher ทุกตัวตรวจว่า environment และ dependency เรียกใช้งานได้ก่อนเริ่มงาน ถ้าเสียจะแนะนำให้ใช้ตัวติดตั้งซ่อม

ทดสอบ Python source compile และ automated tests เดิม 20 รายการผ่าน ตรวจสคริปต์ batch ด้วยการอ่านโค้ดแล้ว แต่ยังไม่ได้รันตัวติดตั้งหรือ launcher ใหม่นี้บน Windows จริง การแก้ environment ไม่ได้ยืนยันว่าปัญหา COM 0x800401E3 ก่อนหน้าหายแล้ว ต้องตรวจอีกครั้งหลังเปิดโปรแกรมได้

อ้างอิง: [Python venv documentation](https://docs.python.org/3.13/library/venv.html) อธิบายว่า virtual environment ไม่ใช่สิ่งที่ย้ายข้าม path/เครื่องได้โดยทั่วไป และควรสร้างใหม่เมื่อย้าย


## v1.0.3 — Portable Windows EXE

Build ด้วย GitHub Actions บน Windows + Python 3.13 x64; ทดสอบเปิด packaged GUI และ simulated BLE ได้ก่อนแจก ชุด portable รวม Python/Tk/COM/BLE dependency แล้ว เพิ่มปุ่มบันทึก CANoe diagnostic ใน GUI และแก้ตัวตรวจ process ให้เก็บ return code/error แทนการตีความ output ว่างว่า CANoe ไม่เปิด ปัญหา COM ก่อนหน้ายังต้องทดสอบบนเครื่องแลปจริง


## v1.0.4 — Manual COM activation และตรวจระดับสิทธิ์ CANoe

สำหรับกรณีที่เห็น CANoe process และ registry ถูกต้อง แต่ GetActiveObject/ROT ไม่พบ:

1. เปิด CANoe และ Config ให้พร้อม ไปแท็บ Debug / Test
2. กด **Connect via COM activation (may open CANoe)** หนึ่งครั้ง โปรแกรมจะกลับไป Auto และลองเกาะ instance เดิมก่อน หากไม่พบจะขอ COM activation ผ่าน class factory หนึ่งครั้ง
3. COM activation อาจทำให้ Windows เปิด CANoe เพิ่มหากไม่ reuse instance เดิม ปุ่มระบุผลนี้ไว้ชัดเจน โปรแกรมไม่โหลด Config และไม่สั่ง Start/Stop/Quit
4. เก็บ proxy ที่เชื่อมต่อสำเร็จไว้เพื่ออ่านสถานะต่อเนื่อง ไม่เรียก activation ทุก 250 ms
5. หาก CANoe ปิด/COM หลุดหรือ activation ล้มเหลว จะกลับไป attach-only ไม่ activate ซ้ำจนกดปุ่มใหม่ แม้ watchdog เริ่ม observer ใหม่ก็ไม่ activate ซ้ำ
6. กด Save CANoe diagnostic report เพื่อเก็บรายงานใหม่ มี `canoe_process_details` ระบุ elevated/session/path ของ CANoe หาก Windows ปฏิเสธการอ่าน token จะแสดง error และค่า null แทนการเดาว่าเป็น false

รายงานยังมี snapshot จาก monitor ของ Beacon เพื่อแยกกรณีที่ manual activation เชื่อมต่ออยู่แต่ GetActiveObject ยังหาไม่พบ ปัญหา COM ของเครื่องแลปยังไม่ถือว่าแก้สำเร็จจนได้รับผลทดสอบจริง การเรียก activation ไม่ได้ข้ามสิทธิ์ Windows หรือเปลี่ยน registry

## v1.0.5 — แก้ปุ่ม COM activation

แก้การเรียก pythoncom.CLSIDFromProgID ที่ไม่มีอยู่ ให้ใช้ pywintypes.IID พร้อมทดสอบ API จริงบน Windows โดยไม่ต้องติดตั้ง CANoe การเชื่อมต่อ CANoe จริงยังต้องยืนยันที่เครื่องแลป
