"""MR STAR RGB Controller • Modern Windows BLE color controller (Python/Tkinter)."""
from __future__ import annotations
import argparse
from datetime import datetime
import os
from pathlib import Path
import queue
import sys
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

from ble_manager import BLEManager
from protocol import (hex_to_rgb, rgb_to_hex, matched_brightness, brightness_to_raw, applied_brightness,
                      EFFECT_PRESETS, EFFECT_FAMILIES)

APP_NAME = "MR STAR RGB Controller"
VERSION = "1.1.2"
BG = "#0A111E"
SIDE = "#101B2B"
CARD = "#142135"
CARD_SOFT = "#192A41"
BORDER = "#27364B"
TEXT = "#F1F5FC"
MUTED = "#8DA0BB"
ACCENT = "#4A92FF"
SUCCESS = "#22C55E"
DANGER = "#F87171"

PALETTE = [
    ("Red", "#FF0000"), ("Orange", "#FF8000"), ("Yellow", "#FFFF00"),
    ("Lime", "#80FF00"), ("Green", "#00FF00"), ("Teal", "#00FF80"),
    ("Cyan", "#00FFFF"), ("Sky", "#0080FF"), ("Blue", "#0000FF"),
    ("Violet", "#8000FF"), ("Magenta", "#FF00FF"), ("White", "#FFFFFF"),
]
STATUSES = [
    ("STANDBY", "#0000FF", "Ready / Idle"),
    ("RUNNING", "#00FF00", "Test in progress"),
    ("WARNING", "#FFFF00", "Attention needed"),
    ("ERROR", "#FF0000", "Test failed"),
    ("COMPLETE", "#FF00FF", "Test finished"),
]


def resource_path(relative: str) -> str:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return str(root / relative)


def label(parent, value: str, size: int = 11, color: str = TEXT, bold: bool = False,
          bg: str | None = None, **kwargs):
    return tk.Label(parent, text=value, bg=bg or parent.cget("bg"), fg=color,
                    font=("Segoe UI", size, "bold" if bold else "normal"), **kwargs)


def button(parent, title: str, command, primary=False, danger=False, **kwargs):
    color = ACCENT if primary else ("#532D39" if danger else CARD_SOFT)
    active = "#71AAFF" if primary else ("#6B3A48" if danger else "#2A3D57")
    return tk.Button(parent, text=title, command=command, bg=color, fg=TEXT,
                     activebackground=active, activeforeground="#FFFFFF",
                     relief="flat", bd=0, highlightthickness=0, cursor="hand2",
                     font=("Segoe UI", 10, "bold"), padx=15, pady=9, **kwargs)


def card(parent, **kwargs):
    return tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                    highlightthickness=1, bd=0, **kwargs)


class MRStarGUI(tk.Tk):
    def __init__(self, demo: bool = False):
        super().__init__()
        self.demo = demo
        self.title(f"{APP_NAME}  |  v{VERSION}" + ("  |  DEMO" if demo else ""))
        self.geometry("1190x860")
        self.minsize(940, 665)
        self.configure(bg=BG)
        self.events: queue.Queue = queue.Queue()
        self.manager = BLEManager(self.events, demo=demo)
        self.status = "DISCONNECTED"
        self.selected_color = "#00FF00"
        self.brightness = 100
        self.hue_offset = 0
        self.effect_forward = True
        self.power = True
        self.device_map: dict[str, str] = {}
        self.device_var = tk.StringVar(value="No BLE device selected")
        self.hex_var = tk.StringVar(value=self.selected_color)
        self.auto_var = tk.BooleanVar(value=True)
        self.primary_fix_var = tk.BooleanVar(value=True)
        self._closing = False
        try:
            self.iconbitmap(resource_path("assets/app.ico"))
        except Exception:
            pass
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(120, self._poll_events)
        self.after(500, self.scan_devices)

    def _build(self):
        self.sidebar = tk.Frame(self, bg=SIDE, width=302)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", expand=True, fill="both")
        top = tk.Frame(right, bg=BG)
        top.pack(fill="x", padx=28, pady=(24, 15))
        label(top, "Light control", 23, bold=True, bg=BG).pack(side="left")
        label(top, "MODI LIFE  /  MR STAR BLE", 10, color=MUTED, bg=BG).pack(side="right", pady=8)

        outer = tk.Frame(right, bg=BG)
        outer.pack(fill="both", expand=True, padx=(23, 12), pady=(0, 18))
        self.scroll = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self.scroll.yview)
        self.scroll.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.scroll.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.scroll, bg=BG)
        self.window_id = self.scroll.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.scroll.configure(scrollregion=self.scroll.bbox("all")))
        self.scroll.bind("<Configure>", self._scroll_width)
        self.scroll.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", self._scroll_wheel))
        self.scroll.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))
        self._build_preview()
        self._build_statuses()
        self._build_palette()
        self._build_custom()
        self._build_effects()

    def _scroll_width(self, event):
        self.scroll.itemconfigure(self.window_id, width=event.width)

    def _scroll_wheel(self, event):
        self.scroll.yview_scroll(int(-event.delta / 120), "units")

    def _build_sidebar(self):
        logo = tk.Frame(self.sidebar, bg=SIDE)
        logo.pack(fill="x", padx=23, pady=(28, 15))
        orb = tk.Canvas(logo, width=49, height=49, bg=SIDE, highlightthickness=0)
        orb.pack(side="left", padx=(0, 12))
        for x, y, col in [(4, 4, "#277AF3"), (24, 4, "#22C55E"),
                          (4, 24, "#FBBF24"), (24, 24, "#D65CFA")]:
            orb.create_rectangle(x, y, x+19, y+19, fill=col, width=0)
        t = tk.Frame(logo, bg=SIDE)
        t.pack(side="left", pady=3)
        label(t, "MR STAR", 16, bold=True, bg=SIDE).pack(anchor="w")
        label(t, "RGB CONTROLLER", 9, color=ACCENT, bold=True, bg=SIDE).pack(anchor="w")
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=23, pady=(0, 24))

        label(self.sidebar, "BLUETOOTH CONNECTION", 10, color=MUTED, bold=True, bg=SIDE).pack(anchor="w", padx=23)
        state_row = tk.Frame(self.sidebar, bg=SIDE)
        state_row.pack(fill="x", padx=23, pady=(13, 4))
        self.status_dot = label(state_row, "●", 19, color=DANGER, bg=SIDE)
        self.status_dot.pack(side="left")
        self.status_text = label(state_row, "Disconnected", 15, bold=True, bg=SIDE)
        self.status_text.pack(side="left", padx=7)
        self.status_detail = label(self.sidebar, "Ready to scan for GATT--DEMO", 9,
                                   color=MUTED, bg=SIDE, anchor="w", wraplength=248, justify="left")
        self.status_detail.pack(fill="x", padx=23, pady=(0, 25))
        label(self.sidebar, "DEVICE", 10, color=MUTED, bold=True, bg=SIDE).pack(anchor="w", padx=23, pady=(0, 7))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("MR.TCombobox", fieldbackground="#22334C", background="#22334C",
                        foreground="#F5F8FF", bordercolor="#33445B", arrowcolor="#FFFFFF",
                        padding=7)
        self.devices_box = ttk.Combobox(self.sidebar, textvariable=self.device_var,
                                        style="MR.TCombobox", state="readonly", width=25)
        self.devices_box.pack(fill="x", padx=23, pady=(0, 12))
        self.devices_box.configure(values=["No BLE device selected"])

        actions = tk.Frame(self.sidebar, bg=SIDE)
        actions.pack(fill="x", padx=23)
        self.scan_button = button(actions, "⟳  Scan", self.scan_devices)
        self.scan_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.connect_button = button(actions, "Connect", self.connect_device, primary=True)
        self.connect_button.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.disconnect_button = button(self.sidebar, "Disconnect", self.disconnect_device, danger=True)
        self.disconnect_button.pack(fill="x", padx=23, pady=(10, 0))

        auto_line = tk.Checkbutton(self.sidebar, text="Auto reconnect if connection drops",
                                   variable=self.auto_var, command=self.on_auto_changed,
                                   bg=SIDE, fg=MUTED, selectcolor=SIDE, activebackground=SIDE,
                                   activeforeground=TEXT, font=("Segoe UI", 9),
                                   highlightthickness=0)
        auto_line.pack(anchor="w", padx=19, pady=(17, 28))
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=23)
        header = tk.Frame(self.sidebar, bg=SIDE)
        header.pack(fill="x", padx=23, pady=(26, 10))
        label(header, "ACTIVITY LOG", 10, color=MUTED, bold=True, bg=SIDE).pack(side="left")
        tk.Button(header, text="Clear", command=self._clear_log, bg=SIDE, fg=ACCENT,
                  activebackground=SIDE, activeforeground=TEXT, bd=0, relief="flat",
                  cursor="hand2", font=("Segoe UI", 9)).pack(side="right")
        self.log_text = tk.Text(self.sidebar, bg=SIDE, fg="#B5C9E0", bd=0,
                                font=("Consolas", 9), height=15, state="disabled", wrap="word",
                                padx=4, pady=6, highlightthickness=0)
        self.log_text.pack(fill="both", expand=True, padx=19, pady=(0, 10))
        footer = tk.Frame(self.sidebar, bg=SIDE)
        footer.pack(side="bottom", fill="x", padx=23, pady=(8, 18))
        label(footer, f"VERSION {VERSION}", 9, color=MUTED, bg=SIDE).pack(side="left")
        label(footer, "BLE GATT / FFF3", 9, color=MUTED, bg=SIDE).pack(side="right")
        self._log("Controller initialized")
        if self.demo:
            self._log("DEMO mode: simulated commands only")

    def _section(self, title_text, subtitle, frame):
        header = tk.Frame(frame, bg=CARD)
        header.pack(fill="x", padx=21, pady=(16, 11))
        label(header, title_text, 13, bold=True).pack(side="left")
        label(header, subtitle, 9, color=MUTED).pack(side="right", pady=4)

    def _build_preview(self):
        p = card(self.inner)
        p.pack(fill="x", padx=(3, 9), pady=(2, 15))
        self._section("LIVE COLOR PREVIEW", "Selected color / output estimate", p)
        self.preview = tk.Canvas(p, height=212, bg="#0F1B2A", highlightthickness=0)
        self.preview.pack(fill="x", padx=20, pady=(0, 17))
        self.preview.bind("<Configure>", lambda e: self._paint_preview())
        self._paint_preview()

    def _rounded(self, canvas, x0, y0, x1, y1, radius, fill, outline=""):
        coords = [x0+radius,y0, x1-radius,y0, x1,y0, x1,y0+radius, x1,y1-radius,
                  x1,y1, x1-radius,y1, x0+radius,y1, x0,y1, x0,y1-radius,
                  x0,y0+radius, x0,y0]
        return canvas.create_polygon(coords, smooth=True, splinesteps=12,
                                     fill=fill, outline=outline)

    def _paint_preview(self):
        c = self.preview
        if not c.winfo_exists():
            return
        w = max(380, c.winfo_width())
        h = max(212, c.winfo_height())
        c.delete("all")
        self._rounded(c, 0, 0, w, h, 15, "#0C1727")
        col = self.selected_color
        rgb = hex_to_rgb(col)
        intensity = self.brightness / 100
        glow = tuple(int(v * intensity + 10 * (1-intensity)) for v in rgb)
        dim = "#{:02X}{:02X}{:02X}".format(*glow)
        # A layered glow and glowing light panel to visualize selected color.
        for inset, factor in [(28, .11), (34, .18), (40, .29)]:
            mixed = tuple(int(15*(1-factor) + val*factor*intensity) for val in rgb)
            shaded = "#{:02X}{:02X}{:02X}".format(*mixed)
            self._rounded(c, w*.11-inset*.14, 52-inset*.17,
                          w*.42+inset*.14, 161+inset*.17, 16, shaded)
        self._rounded(c, w*.13, 49, w*.4, 164, 15, dim)
        self._rounded(c, w*.15, 64, w*.38, 149, 12, col if intensity >= .5 else dim)
        c.create_text(w*.17, 182, text="LED STRIP PREVIEW", anchor="w", fill="#7185A3",
                      font=("Segoe UI", 9, "bold"))
        right_x = max(w*.49, 255)
        c.create_text(right_x, 53, text="CURRENT SELECTION", anchor="w", fill="#91A2BB",
                      font=("Segoe UI", 9, "bold"))
        c.create_text(right_x, 94, text=col, anchor="w", fill="#F5F8FF",
                      font=("Segoe UI", 25, "bold"))
        c.create_text(right_x, 127, text=f"RGB {rgb[0]} / {rgb[1]} / {rgb[2]}", anchor="w",
                      fill="#BDCAE0", font=("Consolas", 11))
        sent_pct = applied_brightness(rgb, self.brightness, self.primary_fix_var.get())
        fix_label = " [RGB cap]" if sent_pct != matched_brightness(rgb, self.brightness) else ""
        c.create_text(right_x, 154, text=f"Master {self.brightness}% | sent ~{sent_pct}%{fix_label}", anchor="w",
                      fill="#91A2BB", font=("Segoe UI", 10))
        c.create_text(w-15, 192, text="Preview only · device has no color readback",
                      anchor="e", fill="#7185A3", font=("Segoe UI", 9))

    def _build_statuses(self):
        p = card(self.inner)
        p.pack(fill="x", padx=(3, 9), pady=(0, 15))
        self._section("QUICK STATUS", "Chamber / test equipment presets", p)
        grid = tk.Frame(p, bg=CARD)
        grid.pack(fill="x", padx=21, pady=(0, 19))
        for col in range(5):
            grid.columnconfigure(col, weight=1, uniform="statuses")
        for col, (name, color, caption) in enumerate(STATUSES):
            cell = tk.Frame(grid, bg=CARD_SOFT, cursor="hand2")
            cell.grid(row=0, column=col, sticky="nsew", padx=4)
            dot = tk.Label(cell, text="●", fg=color, bg=CARD_SOFT,
                           font=("Segoe UI", 16))
            dot.pack(pady=(8, 0))
            label(cell, name, 9, bold=True, bg=CARD_SOFT).pack(pady=(0, 2))
            label(cell, caption, 8, color=MUTED, bg=CARD_SOFT).pack(pady=(0, 10))
            for widget in (cell, dot, *cell.winfo_children()):
                widget.bind("<Button-1>", lambda e, c=color, n=name: self.select_color(c, n))

    def _build_palette(self):
        p = card(self.inner)
        p.pack(fill="x", padx=(3, 9), pady=(0, 15))
        self._section("COLOR PALETTE", "Click to change LED color", p)
        grid = tk.Frame(p, bg=CARD)
        grid.pack(fill="x", padx=19, pady=(0, 17))
        for col in range(6):
            grid.columnconfigure(col, weight=1, uniform="colors")
        for index, (name, color) in enumerate(PALETTE):
            row, col = divmod(index, 6)
            cell = tk.Frame(grid, bg=CARD_SOFT, cursor="hand2")
            cell.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
            dot = tk.Label(cell, text="●", bg=CARD_SOFT, fg=color, font=("Segoe UI", 24))
            dot.pack(pady=(7, 0))
            t = label(cell, name, 9, bg=CARD_SOFT)
            t.pack(pady=(0, 9))
            for wd in (cell, dot, t):
                wd.bind("<Button-1>", lambda e, c=color, n=name: self.select_color(c, n))

    def _build_custom(self):
        p = card(self.inner)
        p.pack(fill="x", padx=(3, 9), pady=(0, 15))
        self._section("CUSTOM COLOR & BRIGHTNESS", "HEX / HSV + LED dimmer", p)
        line = tk.Frame(p, bg=CARD)
        line.pack(fill="x", padx=21, pady=(1, 15))
        label(line, "HEX COLOR", 10, color=MUTED, bold=True).pack(side="left")
        self.hex_entry = tk.Entry(line, textvariable=self.hex_var, bg="#203047",
                                  fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                                  font=("Consolas", 12), justify="center", width=12)
        self.hex_entry.pack(side="left", padx=(13, 8), ipady=9)
        self.hex_entry.bind("<Return>", lambda e: self.apply_hex())
        button(line, "Apply", self.apply_hex, primary=True).pack(side="left", padx=(0, 8))
        button(line, "Choose color…", self.choose_custom_color).pack(side="left")
        self.power_button = button(line, "●  Turn OFF", self.toggle_power, danger=True)
        self.power_button.pack(side="right")

        slider_line = tk.Frame(p, bg=CARD)
        slider_line.pack(fill="x", padx=21, pady=(0, 21))
        label(slider_line, "BRIGHTNESS", 10, color=MUTED, bold=True).pack(side="left")
        self.brightness_label = label(slider_line, "100%", 11, bold=True)
        self.brightness_label.pack(side="right")
        self.brightness_scale = tk.Scale(slider_line, from_=3, to=100, orient="horizontal",
                                         resolution=1, bg=CARD, fg=TEXT, troughcolor="#31445F",
                                         activebackground=ACCENT, highlightthickness=0,
                                         sliderrelief="flat", showvalue=False,
                                         bd=0, command=self._brightness_preview)
        self.brightness_scale.set(self.brightness)
        self.brightness_scale.pack(side="left", fill="x", expand=True, padx=16)
        self.brightness_scale.bind("<ButtonRelease-1>", self._brightness_send)
        self.brightness_scale.bind("<KeyRelease>", self._brightness_send)

        info = label(p,
            "Tested device: pure RED / GREEN / BLUE dim at 99–100% but are bright at 98%. "
            "Compatibility mode sends 98% (BLE 1003) for these colors only. Other colors: unchanged.",
            9, color=MUTED, bg=CARD, wraplength=640, justify='left')
        info.pack(anchor='w', padx=21, pady=(0, 8))
        primary_fix = tk.Checkbutton(p, text="RGB primary brightness fix (recommended)",
            variable=self.primary_fix_var, command=self._on_primary_fix_changed,
            bg=CARD, fg=TEXT, selectcolor=CARD_SOFT, activebackground=CARD,
            activeforeground=TEXT, font=("Segoe UI", 10, "bold"),
            highlightthickness=0, bd=0)
        primary_fix.pack(anchor='w', padx=20, pady=(0, 11))
        cal = tk.Frame(p, bg=CARD)
        cal.pack(fill='x', padx=21, pady=(0, 18))
        label(cal, "HUE CALIBRATION", 10, color=MUTED, bold=True).pack(side='left')
        self.hue_label = label(cal, "+0°", 10, bold=True)
        self.hue_label.pack(side='right')
        self.hue_scale = tk.Scale(cal, from_=-30, to=30, orient='horizontal',
                                  bg=CARD, fg=TEXT, troughcolor='#31445F', showvalue=False,
                                  activebackground=ACCENT, highlightthickness=0,
                                  sliderrelief='flat', bd=0, command=self._hue_preview)
        self.hue_scale.set(0)
        self.hue_scale.pack(side='left', expand=True, fill='x', padx=12)
        self.hue_scale.bind('<ButtonRelease-1>', self._hue_send)
        self.hue_scale.bind('<KeyRelease>', self._hue_send)

    def _build_effects(self):
        p = card(self.inner)
        p.pack(fill='x', padx=(3, 9), pady=(0, 16))
        self._section('EFFECTS & RUNNING LIGHT', 'Controller-native effects (IDs 1–117)', p)
        label(p, 'Native patterns run on the BLE controller after a single command. Movement depends on LED strip hardware.',
              9, color=MUTED, bg=CARD, wraplength=670, justify='left').pack(anchor='w', padx=21, pady=(0, 12))

        presets = tk.Frame(p, bg=CARD)
        presets.pack(fill='x', padx=17)
        for i in range(3):
            presets.columnconfigure(i, weight=1, uniform='effects')
        for i, (name, index) in enumerate(EFFECT_PRESETS):
            button(presets, f'{index:03d}  {name}', lambda ix=index: self.play_native_effect(ix)).grid(
                row=i//3, column=i%3, padx=4, pady=4, sticky='ew')

        row = tk.Frame(p, bg=CARD)
        row.pack(fill='x', padx=21, pady=(15, 12))
        label(row, 'EFFECT ID', 10, color=MUTED, bold=True).pack(side='left')
        self.effect_id = tk.IntVar(value=91)
        self.effect_spin = tk.Spinbox(row, from_=1, to=117, textvariable=self.effect_id,
                                       width=6, bg=CARD_SOFT, fg=TEXT, insertbackground=TEXT,
                                       buttonbackground=CARD_SOFT, relief='flat', justify='center')
        self.effect_spin.pack(side='left', padx=(10, 8), ipady=7)
        button(row, 'Play ID', self.play_manual_effect, primary=True).pack(side='left')
        self.reverse_button = button(row, 'Direction: Forward', self.toggle_direction)
        self.reverse_button.pack(side='right')

        speedrow = tk.Frame(p, bg=CARD)
        speedrow.pack(fill='x', padx=21, pady=(0, 12))
        label(speedrow, 'EFFECT SPEED', 10, color=MUTED, bold=True).pack(side='left')
        self.speed_var = tk.IntVar(value=50)
        self.speed_lbl = label(speedrow, '50%', 10, bold=True)
        self.speed_lbl.pack(side='right')
        scale = tk.Scale(speedrow, from_=0, to=100, orient='horizontal',
                         variable=self.speed_var, bg=CARD, fg=TEXT,
                         showvalue=False, troughcolor='#31445F',
                         activebackground=ACCENT, highlightthickness=0,
                         sliderrelief='flat', bd=0,
                         command=lambda x: self.speed_lbl.configure(text=f'{int(float(x))}%'))
        scale.pack(side='left', expand=True, fill='x', padx=12)
        scale.bind('<ButtonRelease-1>', self.send_speed)
        scale.bind('<KeyRelease>', self.send_speed)

        blinkrow = tk.Frame(p, bg=CARD)
        blinkrow.pack(fill='x', padx=21, pady=(0, 14))
        label(blinkrow, 'PC SOFTWARE BLINK', 10, color=MUTED, bold=True).pack(side='left')
        self.blink_interval = tk.StringVar(value='500')
        ttk.Combobox(blinkrow, state='readonly', textvariable=self.blink_interval,
                     values=['250','500','1000','2000'], width=6, style='MR.TCombobox').pack(
                         side='left', padx=10)
        label(blinkrow, 'ms ON / ms OFF', 9, color=MUTED, bg=CARD).pack(side='left')
        button(blinkrow, 'Start Blink', self.start_blink).pack(side='right', padx=(6, 0))

        footer = tk.Frame(p, bg=CARD)
        footer.pack(fill='x', padx=21, pady=(0, 19))
        button(footer, 'Stop effects / Solid color', self.stop_effects, primary=True).pack(side='left')
        button(footer, 'MAX WHITE / Compare', self.max_white).pack(side='right')
        families = ' | '.join(f'{name} {lo}-{hi}' for name,(lo,hi) in EFFECT_FAMILIES.items())
        label(p, f'Effect ID groups: {families}', 8, color=MUTED, bg=CARD,
              wraplength=685, justify='left').pack(anchor='w', padx=21, pady=(0, 19))

    def _hue_preview(self, value):
        self.hue_offset = int(float(value))
        self.hue_label.configure(text=f'{self.hue_offset:+d}°')

    def _hue_send(self, event=None):
        self.manager.send_color(hex_to_rgb(self.selected_color), self.brightness, self.hue_offset)
        self._log(f'Hue calibration {self.hue_offset:+d} degrees')

    def play_native_effect(self, index: int):
        self.effect_id.set(index)
        self.manager.send_mode(index, self.speed_var.get(), self.effect_forward)
        self._log(f'Native effect {index} queued (appearance depends on firmware)')

    def play_manual_effect(self):
        try:
            idx = int(self.effect_id.get())
            if not (1 <= idx <= 117):
                raise ValueError()
        except (tk.TclError, ValueError):
            messagebox.showwarning('Invalid effect', 'Choose native effect ID 1–117.')
            return
        self.play_native_effect(idx)

    def toggle_direction(self):
        self.effect_forward = not self.effect_forward
        self.reverse_button.configure(text='Direction: '+('Forward' if self.effect_forward else 'Reverse'))
        self.manager.send_direction(self.effect_forward)
        self._log('Direction command queued')

    def send_speed(self, event=None):
        self.manager.send_speed(self.speed_var.get())
        self._log('Native effect speed queued')

    def start_blink(self):
        self.power = True
        self._update_power_button()
        self.manager.start_software_blink(hex_to_rgb(self.selected_color), self.brightness,
                                          self.hue_offset, int(self.blink_interval.get()))
        self._log('PC blink requested: current color / interval '+self.blink_interval.get()+'ms')

    def stop_effects(self):
        self.power = True
        self._update_power_button()
        self.manager.stop_effects(hex_to_rgb(self.selected_color), self.brightness, self.hue_offset)
        self._log('Switching to solid color / canceling effects')

    def max_white(self):
        self.selected_color = '#FFFFFF'
        self.hex_var.set(self.selected_color)
        self.brightness = 100
        self.brightness_scale.set(100)
        self._brightness_preview('100')
        self.power = True
        self._update_power_button()
        self._paint_preview()
        self.manager.send_white()
        self._log('Dedicated WHITE command at 100% sent for comparison')

    def _log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}]  {message}\n")
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 150:
            self.log_text.delete("1.0", f"{lines-130}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def scan_devices(self):
        self._log("Scanning nearby BLE devices…")
        self.manager.scan()

    def connect_device(self):
        label_text = self.device_var.get()
        address = self.device_map.get(label_text)
        if not address:
            self._log("Select a device after scanning")
            messagebox.showinfo("Select device", "Click Scan and select your GATT--DEMO light first.")
            return
        self._log(f"Connecting: {label_text}")
        self.manager.connect(address)

    def disconnect_device(self):
        self.manager.disconnect()

    def on_auto_changed(self):
        self.manager.set_auto_reconnect(self.auto_var.get())
        self._log("Auto reconnect " + ("enabled" if self.auto_var.get() else "disabled"))

    def select_color(self, new_color: str, name: str = "Custom"):
        self.selected_color = new_color.upper()
        self.hex_var.set(self.selected_color)
        self.power = True
        self._update_power_button()
        self._paint_preview()
        self._brightness_preview(str(self.brightness))
        self.manager.send_color(hex_to_rgb(self.selected_color), self.brightness, self.hue_offset)
        self._log(f"Sending {name} · {self.selected_color}")

    def apply_hex(self):
        try:
            rgb = hex_to_rgb(self.hex_var.get())
        except ValueError as exc:
            messagebox.showwarning("Invalid color", str(exc))
            return
        self.select_color(rgb_to_hex(rgb))

    def choose_custom_color(self):
        result = colorchooser.askcolor(color=self.selected_color, parent=self, title="Choose RGB color")
        if result[1]:
            self.select_color(result[1])

    def _on_primary_fix_changed(self):
        enabled = self.primary_fix_var.get()
        self.manager.set_primary_rgb_fix(enabled)
        self._brightness_preview(str(self.brightness))
        self._log('RGB primary brightness fix ' + ('ON: caps at 98%' if enabled else 'OFF: original 99–100% values'))
        if self.status == 'CONNECTED' and self.power:
            self.manager.send_color(hex_to_rgb(self.selected_color), self.brightness, self.hue_offset)

    def _brightness_preview(self, value):
        self.brightness = int(float(value))
        rgb = hex_to_rgb(self.selected_color)
        actual = applied_brightness(rgb, self.brightness, self.primary_fix_var.get())
        requested = matched_brightness(rgb, self.brightness)
        suffix = " (RGB fix → 98%)" if actual < requested else ""
        self.brightness_label.configure(text=f"{self.brightness}%{suffix}")
        self._paint_preview()

    def _brightness_send(self, event=None):
        self.manager.send_brightness(self.brightness, hex_to_rgb(self.selected_color), self.hue_offset)
        rgb = hex_to_rgb(self.selected_color)
        actual = applied_brightness(rgb, self.brightness, self.primary_fix_var.get())
        self._log(f"Sending brightness GUI {self.brightness}% → BLE {brightness_to_raw(actual)}/1024"
                  + (" [RGB compatibility cap]" if actual < matched_brightness(rgb, self.brightness) else ""))

    def toggle_power(self):
        self.power = not self.power
        self._update_power_button()
        self.manager.send_power(self.power)
        self._log("Sending power " + ("ON" if self.power else "OFF"))

    def _update_power_button(self):
        if self.power:
            self.power_button.configure(text="●  Turn OFF", bg="#532D39", activebackground="#6B3A48")
        else:
            self.power_button.configure(text="●  Turn ON", bg="#24543D", activebackground="#33764F")

    def _set_status(self, value: str, detail: str):
        self.status = value
        display = {"CONNECTED": "Connected", "DISCONNECTED": "Disconnected",
                   "SCANNING": "Scanning…", "CONNECTING": "Connecting…",
                   "RECONNECTING": "Reconnecting…"}.get(value, value.title())
        color = SUCCESS if value == "CONNECTED" else (ACCENT if value != "DISCONNECTED" else DANGER)
        self.status_dot.configure(fg=color)
        self.status_text.configure(text=display)
        self.status_detail.configure(text=detail)
        self.connect_button.configure(state="disabled" if value == "CONNECTED" else "normal")
        self.disconnect_button.configure(state="normal" if value == "CONNECTED" else "disabled")

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event["kind"]
                if kind == "state":
                    self._set_status(event["value"], event.get("detail", ""))
                    self._log(event["value"].title() + (": " + event["detail"] if event.get("detail") else ""))
                elif kind == "devices":
                    all_items = event["values"]
                    self.device_map.clear()
                    choices = []
                    for item in all_items:
                        prefix = "★ " if item["target"] else "   "
                        name = f"{prefix}{item['name']} | {item['address']}"
                        choices.append(name)
                        self.device_map[name] = item["address"]
                    self.devices_box.configure(values=choices or ["No devices found"])
                    if choices:
                        self.device_var.set(choices[0])
                        count = len([i for i in all_items if i["target"]])
                        self._log(f"Found {len(choices)} BLE device(s); {count} likely MR STAR")
                        if self.demo:
                            self.connect_device()
                    else:
                        self.device_var.set("No devices found")
                        self._log("No BLE devices found; check power and phone connection")
                elif kind == "error":
                    self._log("ERROR: " + event["message"])
                elif kind == "sent":
                    self._log("TX OK: " + event["message"])
                elif kind == "log":
                    self._log(event["message"])
        except queue.Empty:
            pass
        if not self._closing:
            self.after(150, self._poll_events)

    def on_close(self):
        if self._closing:
            return
        self._closing = True
        self.manager.shutdown()
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--demo", action="store_true", help="Simulated Bluetooth, for UI preview")
    args = parser.parse_args()
    MRStarGUI(demo=args.demo).mainloop()


if __name__ == "__main__":
    main()
