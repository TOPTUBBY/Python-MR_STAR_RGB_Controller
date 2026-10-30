"""Thread-isolated BLE transport; Tkinter must never be used from this thread."""
from __future__ import annotations
import asyncio
import queue
import threading
from typing import Any
from protocol import (WRITE_UUID, power_frame, rgb_frame, brightness_frame,
                      matched_brightness, white_frame, mode_frame, speed_frame, direction_frame, brightness_to_raw, applied_brightness)


def is_target(name: str) -> bool:
    normalized = "".join(ch for ch in name.upper() if ch.isalnum())
    return "GATTDEMO" in normalized or "MRSTAR" in normalized


class BLEManager:
    def __init__(self, events: queue.Queue, demo: bool = False):
        self.events = events
        self.demo = demo
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="MRStarBLE")
        self._client = None
        self._char = None
        self._write_response = False
        self._devices: dict[str, Any] = {}
        self._chosen_address: str | None = None
        self._auto = True
        self._wanted = False
        self._reconnect_task = None
        self._known_power: bool | None = None
        self._closed = False
        self._blink_task = None
        self._last_color = (0, 255, 0)
        self._last_master = 100
        self._last_hue_offset = 0
        self._primary_rgb_fix = True  # user-tested 98% safe cap for pure RGB
        self._effect = None
        self.thread.start()
        self.ready.wait(timeout=5)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self._send_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self.ready.set()
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for task in pending:
            task.cancel()
        if pending:
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def emit(self, kind: str, **fields):
        if not self._closed:
            self.events.put(dict(kind=kind, **fields))

    def submit(self, coroutine):
        if self._closed:
            coroutine.close()
            return
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)

        def handle_result(f):
            try:
                f.result()
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self.emit("error", message=f"{type(exc).__name__}: {exc}")
        future.add_done_callback(handle_result)
        return future

    def scan(self):
        self.submit(self._scan())

    async def _scan(self):
        self.emit("state", value="SCANNING", detail="Searching BLE devices…")
        try:
            if self.demo:
                await asyncio.sleep(0.6)
                results = [{"name": "GATT--DEMO", "address": "DEMO:01", "target": True}]
            else:
                from bleak import BleakScanner
                discovered = await BleakScanner.discover(timeout=7, return_adv=True)
                results = []
                self._devices.clear()
                for address, (device, adv) in discovered.items():
                    name = adv.local_name or device.name or "Unknown device"
                    self._devices[address] = device
                    results.append({"name": name, "address": address,
                                    "target": is_target(name)})
                results.sort(key=lambda item: (not item["target"], item["name"].lower()))
            self.emit("devices", values=results)
            if self._client and self._client.is_connected:
                self.emit("state", value="CONNECTED", detail="Connected")
            else:
                self.emit("state", value="DISCONNECTED", detail="Scan complete")
        except Exception as exc:
            is_still_connected = self._client is not None and self._client.is_connected
            self.emit("state", value="CONNECTED" if is_still_connected else "DISCONNECTED",
                      detail="Scan failed" if not is_still_connected else "Connected (scan failed)")
            raise RuntimeError(f"Bluetooth scan failed: {exc}") from exc

    def connect(self, address: str):
        self.submit(self._connect(address))

    async def _connect(self, address: str, reconnect: bool = False):
        if not address:
            raise ValueError("Scan and select a BLE device first")
        if not reconnect:
            self._wanted = True
            task = self._reconnect_task
            if task and not task.done():
                task.cancel()
        async with self._connect_lock:
            if self._client and self._client.is_connected and self._chosen_address == address:
                self.emit("state", value="CONNECTED", detail=f"{address}")
                return
            if self._client is not None:
                stale = self._client
                self._client = None
                try:
                    await stale.disconnect()
                except Exception:
                    pass
            self.emit("state", value="CONNECTING" if not reconnect else "RECONNECTING",
                      detail=f"Connecting {address}…")
            self._chosen_address = address
            if self.demo:
                await asyncio.sleep(0.5)
                self._client = DemoClient()
                self._char = WRITE_UUID
                self._known_power = None
                self.emit("state", value="CONNECTED", detail=f"Demo · {address}")
                return
            from bleak import BleakClient, BleakScanner
            device = self._devices.get(address)
            if reconnect:
                device = await BleakScanner.find_device_by_address(address, timeout=7)
            target = device if device is not None else address
            client = BleakClient(target, disconnected_callback=self._on_disconnected, timeout=15)
            try:
                await client.connect()
                characteristic = client.services.get_characteristic(WRITE_UUID)
                if characteristic is None:
                    raise RuntimeError("FFF3 write characteristic not found; wrong LED controller?")
                props = list(characteristic.properties)
                if "write-without-response" not in props and "write" not in props:
                    raise RuntimeError(f"FFF3 cannot be written (properties={props})")
                self._char = characteristic
                self._write_response = "write-without-response" not in props
                self._client = client
                self._known_power = None
                self.emit("state", value="CONNECTED", detail=f"{address}")
                self.emit("log", message="GATT FFF3 ready · LED state not readable")
            except Exception:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                self.emit("state", value="DISCONNECTED", detail="Connection failed")
                raise

    def _on_disconnected(self, client):
        if self._client is not client:
            return
        self._client = None
        self._char = None
        self._known_power = None
        self._stop_blink_task()
        self.emit("state", value="DISCONNECTED", detail="Bluetooth link lost")
        if self._auto and self._wanted and not self._closed:
            self._reconnect_task = asyncio.create_task(self._auto_reconnect())

    async def _auto_reconnect(self):
        while self._auto and self._wanted and not self._closed:
            await asyncio.sleep(4)
            if not self._wanted or not self._auto:
                return
            try:
                if self._chosen_address:
                    await self._connect(self._chosen_address, reconnect=True)
                    return
            except Exception as exc:
                self.emit("log", message=f"Reconnect retry: {exc}")

    def disconnect(self):
        self.submit(self._disconnect())

    async def _disconnect(self):
        self._wanted = False
        task = self._reconnect_task
        if task and not task.done():
            task.cancel()
        async with self._connect_lock:
            old = self._client
            self._client = None
            self._char = None
            self._known_power = None
            self._stop_blink_task()
            if old:
                await old.disconnect()
            self.emit("state", value="DISCONNECTED", detail="Disconnected manually")

    def set_auto_reconnect(self, enabled: bool):
        self.loop.call_soon_threadsafe(setattr, self, "_auto", enabled)

    def _stop_blink_task(self):
        task = self._blink_task
        self._blink_task = None
        if task and not task.done():
            task.cancel()

    def set_primary_rgb_fix(self, enabled: bool):
        """Apply GUI preference on BLE event loop without thread races."""
        self.loop.call_soon_threadsafe(setattr, self, '_primary_rgb_fix', bool(enabled))

    def send_color(self, rgb: tuple[int, int, int], master: int = 100,
                   hue_offset: int = 0):
        self.submit(self._send_color(rgb, master, hue_offset))

    async def _send_color(self, rgb: tuple[int, int, int], master: int, hue_offset: int):
        self._stop_blink_task()
        self._effect = None
        self._last_color, self._last_master, self._last_hue_offset = rgb, master, hue_offset
        requested = matched_brightness(rgb, master)
        effective = applied_brightness(rgb, master, self._primary_rgb_fix)
        packets = ([power_frame(False)] if effective == 0 else
                   [power_frame(True), rgb_frame(rgb, hue_offset), brightness_frame(effective)])
        correction = ' [RGB primary 98% compatibility cap]' if effective != requested else ''
        await self._send_many(
            f"HEX color {rgb}; GUI {master}%; requested LED {requested}%; "
            f"sent LED {effective}% (BLE raw {brightness_to_raw(effective)}/1024){correction}",
            packets
        )

    def send_brightness(self, pct: int, rgb: tuple[int, int, int] | None = None,
                        hue_offset: int | None = None):
        """Brightness must also update with RGB value or the HEX color is wrong."""
        self.send_color(rgb if rgb is not None else self._last_color, pct,
                        hue_offset if hue_offset is not None else self._last_hue_offset)

    def send_white(self):
        self.submit(self._send_white())

    async def _send_white(self):
        self._stop_blink_task()
        self._effect = None
        await self._send_many('Dedicated White at brightness 100%',
                              [power_frame(True), white_frame(), brightness_frame(100)])

    def send_mode(self, index: int, speed: int = 50, forward: bool = True):
        self.submit(self._send_mode(index, speed, forward))

    async def _send_mode(self, index: int, speed: int, forward: bool):
        self._stop_blink_task()
        self._effect = index
        await self._send_many(f'Native effect {index}, speed {speed}, '+
                              ('forward' if forward else 'reverse'),
                              [power_frame(True), mode_frame(index),
                               speed_frame(speed), direction_frame(forward)])

    def send_speed(self, speed: int):
        self.submit(self._send('Effect speed '+str(speed), speed_frame(speed), ensure_on=False))

    def send_direction(self, forward: bool):
        self.submit(self._send('Effect direction '+('Forward' if forward else 'Reverse'),
                               direction_frame(forward), ensure_on=False))

    def start_software_blink(self, rgb: tuple[int, int, int], master: int,
                             hue_offset: int, interval_ms: int):
        self.submit(self._start_software_blink(rgb, master, hue_offset, interval_ms))

    async def _start_software_blink(self, rgb, master, hue_offset, interval_ms):
        self._stop_blink_task()
        interval = max(250, min(3000, int(interval_ms))) / 1000
        await self._send_color(rgb, master, hue_offset)
        self._blink_task = asyncio.create_task(self._blink_loop(rgb, master, hue_offset, interval))
        self.emit('log', message=f'Software blink enabled: {interval:.2f}s on/off (PC dependent)')

    async def _blink_loop(self, rgb, master, hue_offset, interval):
        try:
            while True:
                await asyncio.sleep(interval)
                await self._send_many('Blink OFF', [power_frame(False)], quiet=True)
                await asyncio.sleep(interval)
                await self._send_many('Blink ON', [power_frame(True)], quiet=True)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self.emit('error', message='Blink stopped: ' + str(exc))

    def stop_effects(self, rgb: tuple[int, int, int], master: int, hue_offset: int):
        self.send_color(rgb, master, hue_offset)

    def send_power(self, enabled: bool):
        self.submit(self._send_power(enabled))

    async def _send_power(self, enabled: bool):
        self._stop_blink_task()
        self._effect = None
        await self._send('Power ON' if enabled else 'Power OFF', power_frame(enabled),
                         ensure_on=False, power_value=enabled)

    async def _send_many(self, label: str, packets: list[bytes], quiet=False):
        """Serialize an entire logical command to prevent BLE interleaving."""
        async with self._send_lock:
            client = self._client
            if not client or not client.is_connected:
                raise RuntimeError('Not connected. Click Scan → Connect first.')
            for i, packet in enumerate(packets):
                await client.write_gatt_char(self._char, packet,
                                             response=self._write_response)
                if i != len(packets)-1:
                    await asyncio.sleep(0.065)
            if packets and packets[-1] == power_frame(False):
                self._known_power = False
            else:
                self._known_power = True
            if not quiet:
                self.emit('sent', message=f'{label} · '+ ' | '.join(x.hex(' ').upper() for x in packets))

    async def _send(self, label: str, packet: bytes, ensure_on: bool, power_value=None):
        async with self._send_lock:
            client = self._client
            if not client or not client.is_connected:
                raise RuntimeError("Not connected. Click Scan → Connect first.")
            if ensure_on and self._known_power is not True:
                await client.write_gatt_char(self._char, power_frame(True), response=self._write_response)
                await asyncio.sleep(0.15)
                self._known_power = True
            await client.write_gatt_char(self._char, packet, response=self._write_response)
            if power_value is not None:
                self._known_power = power_value
            self.emit("sent", message=f"{label} · {packet.hex(' ').upper()}")

    def shutdown(self):
        if self._closed:
            return
        async def cleanup():
            self._wanted = False
            self._auto = False
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
            self._stop_blink_task()
            if self._client:
                try:
                    await asyncio.wait_for(self._client.disconnect(), timeout=2)
                except Exception:
                    pass
            self._client = None
        try:
            future = asyncio.run_coroutine_threadsafe(cleanup(), self.loop)
            future.result(timeout=3)
        except Exception:
            pass
        self._closed = True
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=2)


class DemoClient:
    is_connected = True
    async def write_gatt_char(self, characteristic, packet, response=False):
        await asyncio.sleep(0.04)
    async def disconnect(self):
        self.is_connected = False
