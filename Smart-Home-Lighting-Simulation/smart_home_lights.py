"""
=============================================================
  SMART HOME LIGHT CONTROL SYSTEM
  Python + Tkinter GUI Application
=============================================================
  Run modes (Windows / Cross-platform):
    python smart_home_lights.py          → Terminal demo
    python smart_home_lights.py --gui    → Full Tkinter GUI
    (or using Python launcher: py smart_home_lights.py [--gui])
=============================================================
"""

import json
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────
#  DATA MODEL
# ─────────────────────────────────────────────

class Light:
    """Represents a single smart bulb."""

    def __init__(self, light_id, name, room,
                 is_on=False, brightness=75, color_temp=4000, color="#FFFFFF"):
        self.light_id   = light_id
        self.name       = name
        self.room       = room
        self.is_on      = is_on
        self.brightness = max(0, min(100, int(float(brightness))))       # 0–100%
        self.color_temp = max(2200, min(6500, int(float(color_temp))))    # 2200K–6500K
        self.color      = color

    def turn_on(self):  self.is_on = True
    def turn_off(self): self.is_on = False

    def set_brightness(self, v):
        self.brightness = max(0, min(100, int(float(v))))

    def set_color_temp(self, v):
        self.color_temp = max(2200, min(6500, int(float(v))))

    def to_dict(self):
        return {"id": self.light_id, "name": self.name, "room": self.room,
                "on": self.is_on, "brightness": self.brightness,
                "color_temp": self.color_temp, "color": self.color}


class SmartHomeController:
    """Core controller — manages all lights and scenes."""

    SCENES = {
        "Morning":  {"brightness": 80,  "color_temp": 5000, "color": "#FFF5C0"},
        "Focus":    {"brightness": 100, "color_temp": 6500, "color": "#DDEEFF"},
        "Relax":    {"brightness": 40,  "color_temp": 2700, "color": "#FFD0A0"},
        "Movie":    {"brightness": 15,  "color_temp": 2200, "color": "#C0A0FF"},
        "Dinner":   {"brightness": 60,  "color_temp": 2700, "color": "#FFE0A0"},
        "Night":    {"brightness": 5,   "color_temp": 2200, "color": "#FF9090"},
        "Energize": {"brightness": 100, "color_temp": 6500, "color": "#FFFFFF"},
    }

    def __init__(self):
        self.lights  = {}
        self.history = []
        self._seed_data()

    def _seed_data(self):
        seed = [
            ("L1",  "Main Light",    "Living Room", True,  75, 4200, "#FFE08A"),
            ("L2",  "Floor Lamp",    "Living Room", True,  50, 3000, "#FFD080"),
            ("L3",  "Ceiling",       "Bedroom",     False, 40, 2700, "#FFCCAA"),
            ("L4",  "Bedside Lamp",  "Bedroom",     True,  30, 2500, "#FFA070"),
            ("L5",  "Counter Light", "Kitchen",     False, 100,5500, "#FFFFFF"),
            ("L6",  "Dining Light",  "Kitchen",     False, 70, 4000, "#FFE8C0"),
            ("L7",  "Desk Lamp",     "Office",      True,  90, 6500, "#CCE8FF"),
            ("L8",  "Ambient LED",   "Office",      True,  60, 5000, "#DDEEFF"),
            ("L9",  "Mirror Light",  "Bathroom",    False, 80, 4500, "#FFFFFF"),
            ("L10", "Garage Light",  "Garage",      False, 100,4000, "#DDDDDD"),
        ]
        for row in seed:
            lid, name, room, on, br, ct, col = row
            self.lights[lid] = Light(lid, name, room, on, br, ct, col)

    def get_rooms(self):
        return sorted(set(l.room for l in self.lights.values()))

    def get_lights_in_room(self, room):
        return [l for l in self.lights.values() if l.room == room]

    def turn_all_on(self):
        for l in self.lights.values(): l.turn_on()
        self._log("All lights turned ON")

    def turn_all_off(self):
        for l in self.lights.values(): l.turn_off()
        self._log("All lights turned OFF")

    def apply_scene(self, scene_name, room=None):
        if scene_name not in self.SCENES:
            return
        s = self.SCENES[scene_name]
        targets = (self.lights.values() if room is None
                   else self.get_lights_in_room(room))
        for l in targets:
            l.turn_on()
            l.set_brightness(s["brightness"])
            l.set_color_temp(s["color_temp"])
            l.color = s["color"]
        scope = room if room else "all rooms"
        self._log(f"Scene '{scene_name}' applied to {scope}")

    def energy_usage(self):
        """Estimate watts (each bulb max 10 W)."""
        return round(sum((l.brightness / 100) * 10
                         for l in self.lights.values() if l.is_on), 1)

    def summary(self):
        on  = sum(1 for l in self.lights.values() if l.is_on)
        off = len(self.lights) - on
        return {"total": len(self.lights), "on": on, "off": off,
                "watts": self.energy_usage()}

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.history.append(f"[{ts}] {msg}")
        if len(self.history) > 50:
            self.history.pop(0)

    def export_state(self):
        return json.dumps([l.to_dict() for l in self.lights.values()], indent=2)

    def export_to_file(self, file_path=None):
        """Export current state to a JSON file using a portable path."""
        if file_path is None:
            file_path = Path(__file__).resolve().parent / "lights_state.json"
        else:
            file_path = Path(file_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.export_state())
        self._log(f"State exported to {file_path.name}")
        return file_path


# ─────────────────────────────────────────────
#  TKINTER GUI
# ─────────────────────────────────────────────

class SmartHomeApp:

    # Colour palette
    DARK_BG  = "#1a1a2e"
    PANEL_BG = "#16213e"
    CARD_BG  = "#0f3460"
    ACCENT   = "#a78bfa"
    TEXT     = "#e2e8f0"
    MUTED    = "#94a3b8"
    ON_COL   = "#fbbf24"
    BTN_BG   = "#334155"

    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk, messagebox
        self.tk  = tk
        self.ttk = ttk
        self.mb  = messagebox
        self.root = root
        self.ctrl = SmartHomeController()

        self.selected_room  = tk.StringVar(value=self.ctrl.get_rooms()[0])
        self.selected_light = None
        self.var_brightness = tk.IntVar(value=75)
        self.var_temp       = tk.IntVar(value=4000)

        root.title("Smart Home Light Control")
        root.geometry("920x660")
        root.minsize(800, 580)
        root.configure(bg=self.DARK_BG)

        self._style()
        self._build_ui()
        self._refresh_all()

    # ── Styles ──────────────────────────────
    def _style(self):
        ttk = self.ttk
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("TFrame",       background=self.DARK_BG)
        s.configure("Panel.TFrame", background=self.PANEL_BG)
        s.configure("Card.TFrame",  background=self.CARD_BG)
        s.configure("TLabel",       background=self.DARK_BG,
                    foreground=self.TEXT, font=("Segoe UI", 10))
        s.configure("TScale",       background=self.PANEL_BG,
                    troughcolor=self.BTN_BG, sliderlength=18)
        s.configure("TNotebook",    background=self.DARK_BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=self.BTN_BG,
                    foreground=self.TEXT, padding=[12, 5],
                    font=("Segoe UI", 10))
        s.map("TNotebook.Tab",
              background=[("selected", self.ACCENT)],
              foreground=[("selected", "#fff")])
        s.configure("Treeview", background=self.PANEL_BG,
                    foreground=self.TEXT, fieldbackground=self.PANEL_BG,
                    rowheight=26, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background=self.CARD_BG,
                    foreground=self.TEXT, font=("Segoe UI", 10, "bold"))
        s.map("Treeview", background=[("selected", self.ACCENT)])

    # ── Top-level layout ────────────────────
    def _build_ui(self):
        tk = self.tk

        # Header
        hdr = tk.Frame(self.root, bg=self.PANEL_BG, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🏠  Smart Home Light Control",
                 bg=self.PANEL_BG, fg=self.TEXT,
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=16, pady=12)
        self.lbl_status = tk.Label(hdr, text="", bg=self.PANEL_BG,
                                   fg=self.MUTED, font=("Segoe UI", 10))
        self.lbl_status.pack(side="right", padx=16)

        body = self.ttk.Frame(self.root)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)

        right = self.ttk.Frame(body, style="Panel.TFrame")
        right.pack(side="left", fill="both", expand=True)

        nb = self.ttk.Notebook(right)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_lights = self.ttk.Frame(nb, style="Panel.TFrame")
        self.tab_scenes = self.ttk.Frame(nb, style="Panel.TFrame")
        self.tab_stats  = self.ttk.Frame(nb, style="Panel.TFrame")
        self.tab_log    = self.ttk.Frame(nb, style="Panel.TFrame")

        nb.add(self.tab_lights, text="💡  Lights")
        nb.add(self.tab_scenes, text="🎨  Scenes")
        nb.add(self.tab_stats,  text="📊  Usage")
        nb.add(self.tab_log,    text="📋  Log")

        self._build_lights_tab()
        self._build_scenes_tab()
        self._build_stats_tab()
        self._build_log_tab()

    # ── Sidebar ─────────────────────────────
    def _build_sidebar(self, parent):
        tk = self.tk
        sb = tk.Frame(parent, bg=self.PANEL_BG, width=185)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="ROOMS", bg=self.PANEL_BG, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(14, 4))

        self.room_buttons = {}
        for room in self.ctrl.get_rooms():
            btn = tk.Button(sb, text=f"  {room}",
                            bg=self.CARD_BG, fg=self.TEXT,
                            font=("Segoe UI", 10), bd=0, anchor="w",
                            relief="flat", cursor="hand2",
                            activebackground=self.ACCENT,
                            command=lambda r=room: self._select_room(r))
            btn.pack(fill="x", padx=8, pady=2, ipady=8)
            self.room_buttons[room] = btn

        tk.Frame(sb, bg=self.BTN_BG, height=1).pack(fill="x", padx=8, pady=10)

        tk.Label(sb, text="MASTER", bg=self.PANEL_BG, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(0, 4))

        tk.Button(sb, text="☀  All ON", bg="#166534", fg="#bbf7d0",
                  font=("Segoe UI", 10, "bold"), bd=0, relief="flat",
                  cursor="hand2", command=self._all_on
                  ).pack(fill="x", padx=8, pady=2, ipady=7)

        tk.Button(sb, text="🌙  All OFF", bg="#7f1d1d", fg="#fecaca",
                  font=("Segoe UI", 10, "bold"), bd=0, relief="flat",
                  cursor="hand2", command=self._all_off
                  ).pack(fill="x", padx=8, pady=2, ipady=7)

    # ── Lights Tab ──────────────────────────
    def _build_lights_tab(self):
        tk  = self.tk
        tab = self.tab_lights

        self.lbl_room = tk.Label(tab, text="", bg=self.PANEL_BG, fg=self.TEXT,
                                 font=("Segoe UI", 13, "bold"))
        self.lbl_room.pack(anchor="w", padx=10, pady=(10, 4))

        cols = ("Name", "Status", "Brightness", "Temp")
        self.tree = self.ttk.Treeview(tab, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.column("Name",       width=140)
        self.tree.column("Status",     width=65)
        self.tree.column("Brightness", width=95)
        self.tree.column("Temp",       width=85)
        self.tree.pack(fill="x", padx=10, pady=(0, 6))
        self.tree.bind("<<TreeviewSelect>>", self._on_light_select)

        ctrl = tk.Frame(tab, bg=self.CARD_BG)
        ctrl.pack(fill="x", padx=10, pady=4)

        tk.Label(ctrl, text="Light Controls", bg=self.CARD_BG, fg=self.ACCENT,
                 font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=8)

        self.btn_toggle = tk.Button(ctrl, text="Turn ON", bg="#166534",
                                    fg="#bbf7d0", font=("Segoe UI", 10, "bold"),
                                    bd=0, width=10, relief="flat", cursor="hand2",
                                    command=self._toggle_light)
        self.btn_toggle.grid(row=1, column=0, padx=12, pady=6, sticky="w")

        # Brightness row
        tk.Label(ctrl, text="Brightness:", bg=self.CARD_BG, fg=self.TEXT,
                 font=("Segoe UI", 10)).grid(row=2, column=0, padx=12, pady=4, sticky="w")
        self.ttk.Scale(ctrl, from_=0, to=100, orient="horizontal", length=260,
                       variable=self.var_brightness,
                       command=self._on_brightness
                       ).grid(row=2, column=1, padx=4, pady=4)
        self.lbl_brightness = tk.Label(ctrl, text="75%", bg=self.CARD_BG,
                                       fg=self.ON_COL, font=("Segoe UI", 10, "bold"), width=5)
        self.lbl_brightness.grid(row=2, column=2, padx=4)

        # Color temp row (allowing warm 2200K up to daylight 6500K)
        tk.Label(ctrl, text="Color Temp:", bg=self.CARD_BG, fg=self.TEXT,
                 font=("Segoe UI", 10)).grid(row=3, column=0, padx=12, pady=4, sticky="w")
        self.ttk.Scale(ctrl, from_=2200, to=6500, orient="horizontal", length=260,
                       variable=self.var_temp,
                       command=self._on_temp
                       ).grid(row=3, column=1, padx=4, pady=4)
        self.lbl_temp = tk.Label(ctrl, text="4000K", bg=self.CARD_BG,
                                 fg="#93c5fd", font=("Segoe UI", 10, "bold"), width=6)
        self.lbl_temp.grid(row=3, column=2, padx=4)

        # Color picker
        tk.Label(ctrl, text="Color:", bg=self.CARD_BG, fg=self.TEXT,
                 font=("Segoe UI", 10)).grid(row=4, column=0, padx=12, pady=(4, 12), sticky="w")
        cf = tk.Frame(ctrl, bg=self.CARD_BG)
        cf.grid(row=4, column=1, sticky="w", pady=(4, 12))
        palette = ["#FFFFFF", "#FFF5C0", "#FFD080", "#FFA070", "#FF7070",
                   "#FF90C0", "#C0A0FF", "#90C0FF", "#90FFD0", "#FFE080"]
        for i, col in enumerate(palette):
            tk.Button(cf, bg=col, width=2, height=1, bd=1,
                       relief="raised", cursor="hand2",
                       command=lambda c=col: self._set_color(c)
                       ).grid(row=0, column=i, padx=2)

    # ── Scenes Tab ──────────────────────────
    def _build_scenes_tab(self):
        tk  = self.tk
        tab = self.tab_scenes

        tk.Label(tab, text="Quick Scenes", bg=self.PANEL_BG, fg=self.TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        tk.Label(tab, text="Apply to current room or all rooms",
                 bg=self.PANEL_BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 8))

        grid = tk.Frame(tab, bg=self.PANEL_BG)
        grid.pack(fill="x", padx=12)

        scene_meta = {
            "Morning":  ("🌅", "Warm energising start"),
            "Focus":    ("🧠", "Cool daylight for work"),
            "Relax":    ("😌", "Soft warm glow"),
            "Movie":    ("🎬", "Dim violet ambiance"),
            "Dinner":   ("🍽", "Golden dinner warmth"),
            "Night":    ("🌙", "Ultra-dim for sleep"),
            "Energize": ("⚡", "Full bright daylight"),
        }

        for i, (name, (icon, desc)) in enumerate(scene_meta.items()):
            r, c = divmod(i, 3)
            card = tk.Frame(grid, bg=self.CARD_BG)
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew", ipadx=4, ipady=4)
            grid.columnconfigure(c, weight=1)

            tk.Label(card, text=icon,  bg=self.CARD_BG, font=("Segoe UI", 20)).pack(pady=(8, 2))
            tk.Label(card, text=name,  bg=self.CARD_BG, fg=self.TEXT,
                     font=("Segoe UI", 11, "bold")).pack()
            tk.Label(card, text=desc,  bg=self.CARD_BG, fg=self.MUTED,
                     font=("Segoe UI", 8), wraplength=110).pack(pady=(2, 6))

            row_btn = tk.Frame(card, bg=self.CARD_BG)
            row_btn.pack(pady=(0, 8))
            tk.Button(row_btn, text="This Room", bg=self.ACCENT, fg="#fff",
                      font=("Segoe UI", 9, "bold"), bd=0, relief="flat",
                      cursor="hand2",
                      command=lambda n=name: self._apply_scene(n, room=True)
                      ).pack(side="left", padx=3, ipady=3, ipadx=4)
            tk.Button(row_btn, text="All", bg=self.BTN_BG, fg=self.TEXT,
                      font=("Segoe UI", 9), bd=0, relief="flat",
                      cursor="hand2",
                      command=lambda n=name: self._apply_scene(n, room=False)
                      ).pack(side="left", padx=3, ipady=3, ipadx=4)

    # ── Stats Tab ───────────────────────────
    def _build_stats_tab(self):
        tk  = self.tk
        tab = self.tab_stats

        tk.Label(tab, text="Energy & Usage", bg=self.PANEL_BG, fg=self.TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

        cards_row = tk.Frame(tab, bg=self.PANEL_BG)
        cards_row.pack(fill="x", padx=12, pady=(0, 12))

        self.stat_labels = {}
        for i, (key, title, unit) in enumerate([
            ("on",    "Lights On",   ""),
            ("off",   "Lights Off",  ""),
            ("watts", "Power Usage", "W"),
        ]):
            card = tk.Frame(cards_row, bg=self.CARD_BG)
            card.grid(row=0, column=i, padx=6, sticky="nsew", ipadx=10, ipady=8)
            cards_row.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=self.CARD_BG, fg=self.MUTED,
                     font=("Segoe UI", 9)).pack(pady=(6, 2))
            lbl = tk.Label(card, text="—", bg=self.CARD_BG, fg=self.ACCENT,
                           font=("Segoe UI", 22, "bold"))
            lbl.pack()
            tk.Label(card, text=unit, bg=self.CARD_BG, fg=self.MUTED,
                     font=("Segoe UI", 9)).pack(pady=(0, 6))
            self.stat_labels[key] = lbl

        tk.Label(tab, text="Per-Room Breakdown", bg=self.PANEL_BG, fg=self.MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(0, 4))

        self.usage_canvas = tk.Canvas(tab, bg=self.PANEL_BG, bd=0,
                                      highlightthickness=0, height=200)
        self.usage_canvas.pack(fill="x", padx=12)

    def _draw_usage_bars(self):
        c = self.usage_canvas
        c.delete("all")
        w = c.winfo_width() or 500
        rooms = self.ctrl.get_rooms()
        bar_colors = ["#a78bfa", "#60a5fa", "#fbbf24", "#34d399", "#f97316", "#f472b6"]
        row_h = 32
        for i, room in enumerate(rooms):
            lights   = self.ctrl.get_lights_in_room(room)
            on_count = sum(1 for l in lights if l.is_on)
            pct      = on_count / len(lights) if lights else 0
            y        = 10 + i * row_h
            c.create_text(8, y + 10, text=room, anchor="w",
                          fill=self.TEXT, font=("Segoe UI", 9))
            bar_x = 120
            bar_w = int((w - bar_x - 80) * pct)
            c.create_rectangle(bar_x, y + 2, w - 80, y + 20,
                               fill=self.BTN_BG, outline="")
            if bar_w > 0:
                c.create_rectangle(bar_x, y + 2, bar_x + bar_w, y + 20,
                                   fill=bar_colors[i % len(bar_colors)], outline="")
            c.create_text(w - 70, y + 10,
                          text=f"{on_count}/{len(lights)} on",
                          anchor="w", fill=self.MUTED, font=("Segoe UI", 9))

    # ── Log Tab ─────────────────────────────
    def _build_log_tab(self):
        tk  = self.tk
        tab = self.tab_log

        tk.Label(tab, text="Activity Log", bg=self.PANEL_BG, fg=self.TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(12, 4))

        frm = tk.Frame(tab, bg=self.PANEL_BG)
        frm.pack(fill="both", expand=True, padx=12, pady=4)

        self.log_box = tk.Text(frm, bg=self.CARD_BG, fg="#94a3b8",
                               font=("Courier New", 10), bd=0,
                               state="disabled", relief="flat", wrap="word")
        scroll = self.ttk.Scrollbar(frm, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scroll.set)
        self.log_box.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btn_bar = tk.Frame(tab, bg=self.PANEL_BG)
        btn_bar.pack(anchor="e", padx=12, pady=6)

        tk.Button(btn_bar, text="💾  Export JSON", bg=self.BTN_BG, fg=self.TEXT,
                  font=("Segoe UI", 9), bd=0, relief="flat", cursor="hand2",
                  command=self._export_json
                  ).pack(side="left", padx=(0, 8), ipadx=8, ipady=4)

        tk.Button(btn_bar, text="Clear Log", bg=self.BTN_BG, fg=self.TEXT,
                  font=("Segoe UI", 9), bd=0, relief="flat", cursor="hand2",
                  command=self._clear_log
                  ).pack(side="left", ipadx=8, ipady=4)

    # ── Event Handlers ──────────────────────
    def _update_toggle_button(self):
        """Update toggle button label and colors to match selected light state."""
        if self.selected_light and self.selected_light.is_on:
            self.btn_toggle.configure(
                text="Turn OFF",
                bg="#7f1d1d",
                fg="#fecaca"
            )
        else:
            self.btn_toggle.configure(
                text="Turn ON",
                bg="#166534",
                fg="#bbf7d0"
            )

    def _select_room(self, room):
        self.selected_room.set(room)
        self.selected_light = None
        for r, btn in self.room_buttons.items():
            btn.configure(bg=self.ACCENT if r == room else self.CARD_BG)
        self._refresh_light_list()
        self.lbl_room.configure(text=f"Room: {room}")
        self._update_toggle_button()

    def _refresh_light_list(self):
        self.tree.delete(*self.tree.get_children())
        room = self.selected_room.get()
        for l in self.ctrl.get_lights_in_room(room):
            status = "ON ✓" if l.is_on else "OFF"
            self.tree.insert("", "end", iid=l.light_id,
                             values=(l.name, status,
                                     f"{l.brightness}%",
                                     f"{l.color_temp}K"))
        # Preserve selection highlight if selected light is in the current room
        if self.selected_light and self.selected_light.room == room:
            if self.tree.exists(self.selected_light.light_id):
                self.tree.selection_set(self.selected_light.light_id)

    def _on_light_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        l = self.ctrl.lights.get(sel[0])
        if not l:
            return
        self.selected_light = l
        self.var_brightness.set(l.brightness)
        self.var_temp.set(l.color_temp)
        self.lbl_brightness.configure(text=f"{l.brightness}%")
        self.lbl_temp.configure(text=f"{l.color_temp}K")
        self._update_toggle_button()

    def _toggle_light(self):
        if not self.selected_light:
            self.mb.showinfo("Select a light", "Click a light in the list first.")
            return
        l = self.selected_light
        if l.is_on:
            l.turn_off()
        else:
            l.turn_on()
        self.ctrl._log(f"{l.name} turned {'ON' if l.is_on else 'OFF'}")
        self._refresh_all()
        self._update_toggle_button()

    def _on_brightness(self, val):
        v = int(float(val))
        self.lbl_brightness.configure(text=f"{v}%")
        if self.selected_light:
            self.selected_light.set_brightness(v)
            self._refresh_light_list()
            # Immediately update power usage and status stats
            self._refresh_status()
            self._refresh_stats()

    def _on_temp(self, val):
        v = int(float(val))
        self.lbl_temp.configure(text=f"{v}K")
        if self.selected_light:
            self.selected_light.set_color_temp(v)
            self._refresh_light_list()

    def _set_color(self, color):
        if not self.selected_light:
            self.mb.showinfo("Select a light", "Click a light in the list first.")
            return
        self.selected_light.color = color
        self.ctrl._log(f"{self.selected_light.name} color → {color}")
        # Immediately refresh the activity log view
        self._refresh_log()

    def _apply_scene(self, name, room=True):
        target = self.selected_room.get() if room else None
        self.ctrl.apply_scene(name, room=target)
        self._refresh_all()
        # Keep control panel in sync if selected light was modified
        if self.selected_light:
            self.var_brightness.set(self.selected_light.brightness)
            self.var_temp.set(self.selected_light.color_temp)
            self.lbl_brightness.configure(text=f"{self.selected_light.brightness}%")
            self.lbl_temp.configure(text=f"{self.selected_light.color_temp}K")
            self._update_toggle_button()
        scope = target if target else "all rooms"
        self.mb.showinfo("Scene Applied", f"'{name}' applied to {scope}.")

    def _all_on(self):
        self.ctrl.turn_all_on()
        self._refresh_all()
        self._update_toggle_button()

    def _all_off(self):
        self.ctrl.turn_all_off()
        self._refresh_all()
        self._update_toggle_button()

    def _clear_log(self):
        self.ctrl.history.clear()
        self._refresh_log()

    def _export_json(self):
        export_path = self.ctrl.export_to_file()
        self._refresh_log()
        self.mb.showinfo("State Exported", f"Current lighting state saved to:\n{export_path}")

    # ── Refresh helpers ─────────────────────
    def _refresh_all(self):
        self._refresh_light_list()
        self._refresh_status()
        self._refresh_stats()
        self._refresh_log()
        self.lbl_room.configure(text=f"Room: {self.selected_room.get()}")
        self.root.after(100, self._draw_usage_bars)

    def _refresh_status(self):
        s = self.ctrl.summary()
        self.lbl_status.configure(
            text=f"{s['on']} lights on  ·  {s['off']} off  ·  {s['watts']} W")

    def _refresh_stats(self):
        s = self.ctrl.summary()
        self.stat_labels["on"].configure(text=str(s["on"]))
        self.stat_labels["off"].configure(text=str(s["off"]))
        self.stat_labels["watts"].configure(text=str(s["watts"]))

    def _refresh_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        for line in reversed(self.ctrl.history):
            self.log_box.insert("end", line + "\n")
        self.log_box.configure(state="disabled")


# ─────────────────────────────────────────────
#  TERMINAL DEMO
# ─────────────────────────────────────────────

def run_terminal_demo():
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        from rich.text import Text
    except ImportError:
        print("Install rich:  python -m pip install rich (or: py -m pip install rich)")
        return

    console = Console()
    ctrl    = SmartHomeController()

    console.print(Panel.fit(
        "[bold #a78bfa]🏠  Smart Home Light Control[/]\n[dim]Python Terminal Demo[/]",
        border_style="#a78bfa"
    ))

    # All lights table
    table = Table(title="All Lights", box=box.ROUNDED,
                  header_style="bold #a78bfa", border_style="#334155")
    for col in ("ID", "Name", "Room", "Status", "Brightness", "Temp"):
        table.add_column(col, justify="left" if col in ("Name","Room") else "center")

    for l in ctrl.lights.values():
        status = Text("ON ✓", style="bold #fbbf24") if l.is_on else Text("OFF", style="dim")
        table.add_row(l.light_id, l.name, l.room, status,
                      f"{l.brightness}%", f"{l.color_temp}K")
    console.print(table)

    # Apply scene
    console.print("\n[bold]Applying 'Movie' scene to Living Room...[/]")
    ctrl.apply_scene("Movie", room="Living Room")

    after = Table(title="Living Room (After 'Movie' scene)", box=box.SIMPLE,
                  header_style="bold #60a5fa")
    after.add_column("Light")
    after.add_column("Status", justify="center")
    after.add_column("Brightness", justify="right")
    after.add_column("Temp", justify="right")

    for l in ctrl.get_lights_in_room("Living Room"):
        st = "[bold #fbbf24]ON[/]" if l.is_on else "[dim]OFF[/]"
        after.add_row(l.name, st, f"{l.brightness}%", f"{l.color_temp}K")
    console.print(after)

    # Summary
    s = ctrl.summary()
    console.print(Panel(
        f"[bold]Total lights:[/]  {s['total']}\n"
        f"[bold #fbbf24]Lights ON:[/]     {s['on']}\n"
        f"[dim]Lights OFF:[/]    {s['off']}\n"
        f"[bold #34d399]Power usage:[/]   {s['watts']} W",
        title="[bold]Summary[/]", border_style="#334155"
    ))

    # Log
    console.print("\n[bold #a78bfa]Activity Log[/]")
    for entry in ctrl.history:
        console.print(f"  [dim]{entry}[/]")

    # Export JSON using portable standard library path
    json_path = ctrl.export_to_file()
    console.print(f"\n[green]✓[/] State exported → {json_path}")
    console.print("\n[dim]Launch the GUI with:[/] [bold #a78bfa]python smart_home_lights.py --gui[/] [dim](or: py smart_home_lights.py --gui)[/]")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--gui" in sys.argv:
        import tkinter as tk
        root = tk.Tk()
        app  = SmartHomeApp(root)
        root.mainloop()
    else:
        run_terminal_demo()
