from __future__ import annotations
import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from core import Config, COLORS, LABELS, select_status, disk_warning, ErrorLatch
from monitor import canoe_worker
from ble_manager import BLEManager
from protocol import hex_to_rgb

VERSION = '1.0.3-demo'
STATE_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LabBeaconDemo'


class BeaconApp:
    def __init__(self, root, simulate_led=False):
        self.root = root
        root.title('Lab Beacon | CANoe + MR STAR | ' + VERSION)
        root.geometry('1060x790')
        root.minsize(920, 720)
        self.config = Config()
        self.load_error = ''
        try:
            path = STATE_DIR / 'settings.json'
            if path.exists():
                self.config = Config(**json.loads(path.read_text(encoding='utf-8'))).validate()
        except Exception as exc:
            self.load_error = 'Settings reset to defaults: ' + str(exc)
        self.events = queue.Queue()
        self.ble = BLEManager(self.events, demo=simulate_led)
        self.simulate_led = simulate_led
        self.ble_connected = False
        self.devices = []
        self.proc = None
        self.cq = None
        self.stop_event = None
        self.last_sample = None
        self.started_at = 0
        self.next_restart = 0
        self.next_disk_check = 0
        self.latch = ErrorLatch()
        self.live_error = False
        self.last_output = None
        self.closed = False
        self.disk_sample = None
        self.disk_generation = 0
        self.disk_stop = threading.Event()
        self.disk_requests = queue.Queue(maxsize=1)
        self.disk_thread = threading.Thread(target=self.disk_loop, daemon=True)
        self.disk_thread.start()
        self.last_log = {}
        self.mode = tk.StringVar(value='Auto')
        self.monitoring = tk.BooleanVar(value=False)
        self.output_enabled = tk.BooleanVar(value=True)
        self.debug_status = 'idle'
        self.build()
        if self.load_error:
            self.log(self.load_error)
        self.log('Ready. ' + ('SIMULATED LED transport; no Bluetooth commands.' if simulate_led else 'Real BLE transport. Scan and connect to the lamp.'))
        self.log('CANoe monitoring starts only after Enable CANoe monitor is selected.')
        self.request_disk()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.tick)

    def build(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'))
        style.configure('TButton', padding=5)
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='LAB BEACON  /  CANoe status light', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Demo v1.0.3  •  ' + ('SIMULATED LED' if self.simulate_led else 'REAL BLUETOOTH LED') + '  •  Error > DI water > Disk > Running').pack(anchor='w', pady=(3, 12))
        ble = ttk.LabelFrame(outer, text='MR STAR / GATT--DEMO', padding=8)
        ble.pack(fill='x')
        ttk.Button(ble, text='Scan BLE', command=self.ble.scan).pack(side='left')
        self.device_box = ttk.Combobox(ble, state='readonly', width=45)
        self.device_box.pack(side='left', padx=8)
        ttk.Button(ble, text='Connect', command=self.connect_led).pack(side='left')
        ttk.Button(ble, text='Disconnect', command=self.ble.disconnect).pack(side='left', padx=6)
        self.ble_text = tk.StringVar(value='Disconnected')
        ttk.Label(ble, textvariable=self.ble_text).pack(side='left')
        controls = ttk.Frame(outer)
        controls.pack(fill='x', pady=10)
        ttk.Checkbutton(controls, text='Enable CANoe monitor', variable=self.monitoring, command=self.toggle_monitor).pack(side='left')
        ttk.Checkbutton(controls, text='LED output enabled', variable=self.output_enabled, command=self.invalidate).pack(side='left', padx=15)
        ttk.Label(controls, text='Mode:').pack(side='left')
        box = ttk.Combobox(controls, textvariable=self.mode, values=['Auto', 'Debug'], state='readonly', width=9)
        box.pack(side='left', padx=8)
        box.bind('<<ComboboxSelected>>', lambda e: self.invalidate())
        ttk.Button(controls, text='Acknowledge error', command=self.ack).pack(side='right')
        book = ttk.Notebook(outer)
        book.pack(fill='both', expand=True)
        dash = ttk.Frame(book, padding=14)
        settings = ttk.Frame(book, padding=12)
        debug = ttk.Frame(book, padding=18)
        book.add(dash, text='  Dashboard  ')
        book.add(settings, text='  Settings  ')
        book.add(debug, text='  Debug / Test  ')
        self.canvas = tk.Canvas(dash, width=150, height=150, highlightthickness=0, bg='#172333')
        self.canvas.grid(row=0, column=0, rowspan=3, padx=(0, 20))
        self.lamp = self.canvas.create_oval(25, 25, 125, 125, fill='#303b4a', outline='#65758b', width=2)
        self.status_text = tk.StringVar(value='Idle')
        ttk.Label(dash, textvariable=self.status_text, font=('Segoe UI', 18, 'bold')).grid(row=0, column=1, sticky='w')
        self.canoe_text = tk.StringVar(value='CANoe: monitor disabled')
        self.disk_text = tk.StringVar(value='Disk: checking...')
        self.source_text = tk.StringVar(value='')
        ttk.Label(dash, textvariable=self.canoe_text, wraplength=680).grid(row=1, column=1, sticky='w')
        ttk.Label(dash, textvariable=self.disk_text).grid(row=2, column=1, sticky='w')
        ttk.Label(dash, textvariable=self.source_text, wraplength=900).grid(row=3, column=0, columnspan=2, sticky='w', pady=14)
        ttk.Label(dash, text='Preview = requested output. BLE SENT confirms a write, not physical lamp readback.').grid(row=4, column=0, columnspan=2, sticky='w')
        self.log_widget = tk.Text(dash, height=11, bg='#172333', fg='#d3e4f6', font=('Consolas', 9), state='disabled', wrap='word')
        self.log_widget.grid(row=5, column=0, columnspan=2, sticky='nsew', pady=10)
        dash.rowconfigure(5, weight=1)
        dash.columnconfigure(1, weight=1)
        self.vars = {}
        fields = [('disk_enabled', 'Enable disk warning', bool), ('disk_path', 'Disk / logging folder', str), ('disk_free_gb', 'Warn when free <= GB', float), ('disk_free_percent', 'OR free <= percent', float), ('error_enabled', 'Enable error System Variable', bool), ('error_variable', 'Error variable', str), ('error_value', 'Error active value', float), ('water_enabled', 'Enable DI water System Variable', bool), ('water_variable', 'DI water variable', str), ('water_value', 'DI water active value', float), ('any_stop_error', 'Treat every observed Running → Stop as error', bool), ('brightness', 'LED brightness 1..100%', int)]
        for row, (key, label, kind) in enumerate(fields):
            val = getattr(self.config, key)
            var = tk.BooleanVar(value=val) if kind is bool else tk.StringVar(value=str(val))
            self.vars[key] = (var, kind)
            if kind is bool:
                ttk.Checkbutton(settings, text=label, variable=var).grid(row=row, column=0, columnspan=2, sticky='w')
            else:
                ttk.Label(settings, text=label).grid(row=row, column=0, sticky='w', pady=2)
                ttk.Entry(settings, textvariable=var, width=38).grid(row=row, column=1, sticky='w', padx=8)
        rules = ttk.LabelFrame(settings, text='Per-status output', padding=8)
        rules.grid(row=0, column=2, rowspan=12, sticky='n', padx=24)
        for col, text in enumerate(('Enabled / Color', 'Mode', 'ON / OFF ms')):
            ttk.Label(rules, text=text).grid(row=0, column=col, padx=5)
        self.rule_vars = {}
        for row, key in enumerate(('error', 'water', 'disk', 'running'), 1):
            rule = self.config.rules[key]
            enabled, mode, ms = tk.BooleanVar(value=rule['enabled']), tk.StringVar(value=rule['mode']), tk.StringVar(value=str(rule['interval_ms']))
            self.rule_vars[key] = (enabled, mode, ms)
            ttk.Checkbutton(rules, text=key.title() + ' ' + COLORS[key], variable=enabled).grid(row=row, column=0, sticky='w', pady=6)
            ttk.Combobox(rules, textvariable=mode, values=['Solid', 'Blink'], state='readonly', width=7).grid(row=row, column=1)
            ttk.Entry(rules, textvariable=ms, width=8).grid(row=row, column=2, padx=6)
        ttk.Label(rules, text='250–3000 ms per phase\n500 ms ON + 500 ms OFF = 1 s cycle\nPrimary RGB compatibility cap: 98%', justify='left').grid(row=5, column=0, columnspan=3, sticky='w', pady=12)
        ttk.Button(settings, text='Apply & Save settings', command=self.apply).grid(row=12, column=0, columnspan=2, sticky='w', pady=12)
        ttk.Label(settings, text='Sysvar example: LabBeacon::DIWaterLow = 1\nDisabled sources do not require a CANoe variable. Read failures are shown as Unknown.').grid(row=13, column=0, columnspan=3, sticky='w')
        ttk.Label(debug, text='Manual LED test', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(debug, text='Buttons switch to Debug mode and override Auto. CANoe is read-only.\nSelect Auto to resume live alarms. Rule enable / Solid / Blink settings also apply here.').pack(anchor='w', pady=12)
        for key in ('running', 'error', 'disk', 'water', 'idle'):
            ttk.Button(debug, text=LABELS[key] + '  ' + COLORS[key], command=lambda k=key: self.debug(k)).pack(fill='x', pady=6)
        ttk.Button(debug, text='Return to Auto', command=self.auto).pack(anchor='w', pady=12)

    def log(self, message):
        # Bound UI history; repeated COM errors are deduplicated by caller.
        self.log_widget.configure(state='normal')
        self.log_widget.insert('end', time.strftime('%H:%M:%S ') + message + '\n')
        if int(self.log_widget.index('end-1c').split('.')[0]) > 300:
            self.log_widget.delete('1.0', '50.0')
        self.log_widget.see('end')
        self.log_widget.configure(state='disabled')

    def changed_log(self, channel, message):
        if self.last_log.get(channel) != message:
            self.last_log[channel] = message
            self.log(message)

    def invalidate(self):
        self.last_output = None

    def connect_led(self):
        i = self.device_box.current()
        if i < 0:
            messagebox.showinfo('BLE', 'Scan and select a device first.')
            return
        self.ble.connect(self.devices[i]['address'])

    def debug(self, key):
        self.mode.set('Debug')
        self.debug_status = key
        self.invalidate()

    def auto(self):
        self.mode.set('Auto')
        self.invalidate()

    def ack(self):
        if self.live_error is None:
            self.log('Cannot acknowledge: live error input is unavailable. Restore monitoring first.')
            return
        self.latch.acknowledge(self.live_error)
        self.log('Error acknowledged.' if not self.latch.active else 'Error remains active at source; clear source first.')

    def apply(self):
        try:
            data = {k: typ(v.get()) for k, (v, typ) in self.vars.items()}
            data['rules'] = {k: {'enabled': e.get(), 'mode': m.get(), 'interval_ms': int(t.get())} for k, (e, m, t) in self.rule_vars.items()}
            config = Config(**data).validate()
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            temp = STATE_DIR / 'settings.tmp'
            temp.write_text(json.dumps(config.to_dict(), indent=2), encoding='utf-8')
            temp.replace(STATE_DIR / 'settings.json')
            self.config = config
            self.disk_sample = None
            self.disk_generation += 1
            self.request_disk()
            if self.monitoring.get():
                self.stop_monitor()
                self.start_monitor()
            self.invalidate()
            self.log('Settings saved and applied. Existing error latch retained.')
        except Exception as exc:
            messagebox.showerror('Settings not applied', str(exc))

    def toggle_monitor(self):
        if self.monitoring.get():
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        self.last_sample = None
        self.latch.previous_running = None
        self.started_at = time.monotonic()
        self.cq = mp.Queue()
        self.stop_event = mp.Event()
        self.proc = mp.Process(target=canoe_worker, args=(self.cq, self.stop_event, self.config.to_dict()), daemon=True)
        self.proc.start()
        self.log('Monitoring active CANoe. Automatic attach retry; never starts CANoe.')

    def stop_monitor(self):
        if self.proc:
            self.stop_event.set()
            self.proc.join(timeout=0.05)
            if self.proc.is_alive():
                self.proc.terminate()
                self.proc.join(timeout=0.1)
            self.cq.close()
            self.proc = None
            self.cq = None
        self.last_sample = None
        self.latch.previous_running = None

    def request_disk(self):
        if not self.config.disk_enabled:
            return
        try:
            self.disk_requests.put_nowait((self.disk_generation, self.config.disk_path, self.config.to_dict()))
        except queue.Full:
            pass

    def disk_loop(self):
        while not self.disk_stop.is_set():
            try:
                generation, path, data = self.disk_requests.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                usage = shutil.disk_usage(path)
                result = {'kind': 'disk', 'generation': generation, 'free': usage.free, 'total': usage.total, 'warning': disk_warning(usage.free, usage.total, Config(**data)), 'error': ''}
            except Exception as exc:
                result = {'kind': 'disk', 'generation': generation, 'warning': False, 'error': str(exc)}
            self.events.put(result)

    def process_events(self):
        for _ in range(100):
            try:
                e = self.events.get_nowait()
            except queue.Empty:
                break
            kind = e['kind']
            if kind == 'devices':
                self.devices = e['values']
                self.device_box['values'] = [d['name'] + ' | ' + d['address'] for d in self.devices]
                if self.devices:
                    self.device_box.current(0)
            elif kind == 'state':
                was = self.ble_connected
                self.ble_connected = e['value'] == 'CONNECTED'
                self.ble_text.set(e['value'])
                self.changed_log('ble', 'BLE: ' + e.get('detail', e['value']))
                if was != self.ble_connected:
                    self.invalidate()
            elif kind == 'disk':
                if e['generation'] == self.disk_generation:
                    e['time'] = time.monotonic()
                    self.disk_sample = e
            elif kind in ('log', 'sent', 'error'):
                self.log(kind.upper() + ': ' + e['message'])
                if kind == 'error':
                    # Retry desired output after transient write errors, throttled in tick.
                    self.last_output = None
        if self.cq:
            while True:
                try:
                    e = self.cq.get_nowait()
                except queue.Empty:
                    break
                self.last_sample = e
                self.live_error = e.get('error')
                self.latch.update(e['running'], e.get('error') is True, self.config.any_stop_error)

    def tick(self):
        if self.closed:
            return
        self.process_events()
        now = time.monotonic()
        sample = self.last_sample
        fresh = sample is not None and now - sample['time'] < 4
        connected = bool(self.monitoring.get() and fresh and sample['connected'])
        if not connected:
            self.live_error = None if self.config.error_enabled else False
        warnings = sample.get('warnings', []) if connected else []
        if self.monitoring.get():
            detail = sample['detail'] if fresh else ('Connecting to active CANoe...' if now - self.started_at < 4 else 'COM reader not responding / data stale')
            self.canoe_text.set('CANoe: ' + detail[:170])
            self.changed_log('canoe', 'CANoe: ' + detail[:300] + (' | ' + '; '.join(warnings)[:300] if warnings else ''))
            # Recreate only our observer process, never the CANoe application.
            if (not self.proc or not self.proc.is_alive() or (not fresh and now - self.started_at > 6)) and now >= self.next_restart:
                self.stop_monitor()
                self.start_monitor()
                self.next_restart = now + 8
        else:
            self.canoe_text.set('CANoe: monitor disabled')
        ds = self.disk_sample
        disk_known = not self.config.disk_enabled or (ds is not None and not ds['error'] and now - ds['time'] < 10)
        if not self.config.disk_enabled:
            self.disk_text.set('Disk: monitoring disabled')
        elif disk_known:
            self.disk_text.set(f"Disk {self.config.disk_path}  |  Free {ds['free']/1024**3:.1f} GB ({ds['free']/ds['total']*100:.1f}%)" + ('  WARNING' if ds['warning'] else '  OK'))
        else:
            self.disk_text.set('Disk: UNKNOWN — ' + (ds['error'][:120] if ds and ds['error'] else 'checking / stale'))
        if now >= self.next_disk_check:
            self.request_disk()
            self.next_disk_check = now + 2
        active_disk = bool(self.config.disk_enabled and disk_known and ds and ds['warning'])
        active_water = bool(connected and sample.get('water'))
        known = connected and not warnings and disk_known
        if self.mode.get() == 'Debug':
            key = self.debug_status
            if key in self.config.rules and not self.config.rules[key]['enabled']:
                key = 'idle'
        else:
            key = select_status(self.config, error=self.latch.active, water=active_water, disk=active_disk, running=bool(connected and sample['running']), known=known)
        rule = self.config.rules.get(key, {'mode': 'Solid', 'interval_ms': 500})
        output_key = key if self.output_enabled.get() else 'idle'
        color = COLORS[output_key]
        self.status_text.set(self.mode.get().upper() + '  |  ' + (LABELS[key] if self.output_enabled.get() else 'LED output disabled'))
        self.source_text.set(f"Error latch: {self.latch.active}  |  DI water: {active_water}  |  Disk warning: {active_disk}\n" + ('; '.join(warnings)[:250] if warnings else f"{color}  •  {rule['mode']}  •  {rule['interval_ms']} ms per phase"))
        on = rule['mode'] != 'Blink' or int(now * 1000 / rule['interval_ms']) % 2 == 0
        self.canvas.itemconfigure(self.lamp, fill=color if on and color != '#000000' else '#303b4a')
        desired = (output_key, rule['mode'], rule['interval_ms'], self.config.brightness)
        if self.ble_connected and desired != self.last_output and now >= getattr(self, 'send_after', 0):
            self.last_output = desired
            self.send_after = now + 0.5
            if color == '#000000':
                self.ble.send_power(False)
            elif rule['mode'] == 'Blink':
                self.ble.start_software_blink(hex_to_rgb(color), self.config.brightness, 0, rule['interval_ms'])
            else:
                self.ble.send_color(hex_to_rgb(color), self.config.brightness)
        self.root.after(100, self.tick)

    def close(self):
        self.closed = True
        self.disk_stop.set()
        self.stop_monitor()
        # Stop blink and request OFF before disconnect. Never close CANoe.
        self.root.withdraw()
        future = self.ble.submit(self.ble._send_power(False)) if self.ble_connected else None
        def finish():
            if future:
                try:
                    future.result(timeout=2)
                except Exception:
                    pass
            self.ble.shutdown()
            self.events.put({'kind': 'shutdown'})
        threading.Thread(target=finish, daemon=True).start()
        def poll():
            try:
                while self.events.get_nowait()['kind'] != 'shutdown':
                    pass
                self.root.destroy()
            except queue.Empty:
                self.root.after(100, poll)
        poll()


def main():
    mp.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument('--simulate-led', action='store_true', help='Use simulated BLE; CANoe monitoring remains available')
    parser.add_argument('--smoke-test-report', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.smoke_test_report and not args.simulate_led:
        parser.error('Smoke tests require --simulate-led')
    root = tk.Tk()
    app = BeaconApp(root, args.simulate_led)
    if args.smoke_test_report:
        # Run only in CI with a simulated lamp. No CANoe controls are sent.
        def begin():
            app.ble.connect('DEMO:01')
        def finish():
            success = app.ble_connected and app.mode.get() == 'Debug'
            args.smoke_test_report.write_text(json.dumps({
                'success': success, 'version': VERSION,
                'packaged': bool(getattr(__import__('sys'), 'frozen', False)),
                'tk_version': str(tk.TkVersion),
                'simulated_led_connected': app.ble_connected,
                'debug_colors_requested': ['running', 'error', 'disk', 'water', 'idle'],
            }, indent=2), encoding='utf-8')
            app.close()
        root.after(100, begin)
        for delay, key in ((2000, 'running'), (3000, 'error'), (4000, 'disk'), (5000, 'water'), (6000, 'idle')):
            root.after(delay, lambda k=key: app.debug(k))
        root.after(7500, finish)
    root.mainloop()

if __name__ == '__main__':
    main()
