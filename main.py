import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


APP_TITLE = "Fazendinha"
SAVE_DIR = Path(__file__).with_name("saves")


class FarmGameApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x460")
        self.minsize(520, 340)
        self.configure(bg="#f3ead7")
        self.fade_steps = 8
        self.fade_delay = 18
        self.fade_overlay = None

        self.current_screen = None
        self.current_save_path = None
        self.current_save = None
        self.money = 1000
        self.game_canvas = None
        self.pause_panel = None
        self.paused = False
        self.game_loop_id = None
        self.pressed_keys = set()
        self.selected_inventory_slot = None
        self.inventory_slots = []
        self.inventory_items = ["hoe", "watering_can", "lettuce_seed"] + [None] * 7
        self.inventory_counts = [None, None, 20] + [None] * 7
        self.max_seed_stack = 20
        self.dragged_item = None
        self.drag_start_slot = None
        self.drag_current_position = None
        self.drag_press_position = None
        self.drag_has_moved = False
        self.mouse_pressed_game_button = False
        self.tilled_soil_tiles = []
        self.soil_tile_size = 30
        self.watering_can_capacity = 15
        self.watering_can_water = self.watering_can_capacity
        self.week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.day_count = 0
        self.day_index = 0
        self.game_minutes = 6 * 60
        self.total_game_minutes = 0
        self.time_accumulator_ms = 0
        self.real_ms_per_game_tick = 7000 / 3
        self.game_minutes_per_tick = 10
        self.day_start_minutes = 6 * 60
        self.day_end_minutes = 26 * 60
        self.lettuce_stage_2_minutes = 48 * 60
        self.lettuce_stage_3_minutes = 72 * 60
        self.max_harvest_stack = 20
        self.item_use_range = 75
        self.feedback_message = None
        self.feedback_message_id = None
        self.camera_x = 0
        self.camera_y = 0
        self.water_animation_frame = 0
        self.current_area = "farm"
        self.farm_rect = (0, 0, 1160, 670)
        self.house_rect = (440, 105, 570, 205)
        self.shop_rect = (830, 405, 980, 515)
        self.shop_door_rect = (928, 493, 962, 525)
        self.shop_exit_rect = (340, 590, 420, 640)
        self.shop_area_rect = (0, 0, 760, 640)
        self.lake_rect = (145, 470, 315, 610)
        self.player_radius = 11
        self.player_speed = 4
        self.default_player_position = [130, 315]
        self.player_position = self.default_player_position.copy()
        self.show_main_menu()

    def clear_screen(self):
        if self.current_screen is not None:
            self.current_screen.destroy()

    def make_screen(self):
        should_fade = self.current_screen is not None
        if should_fade:
            self.fade_to_black()

        self.clear_screen()
        frame = tk.Frame(self, bg="#f3ead7")
        frame.pack(fill="both", expand=True)
        self.current_screen = frame
        self.update_idletasks()

        if should_fade:
            self.fade_from_black()
        return frame

    def fade_to_black(self):
        overlay = self.create_fade_overlay()
        for step in range(self.fade_steps + 1):
            progress = step / self.fade_steps
            shade = int(255 * (1 - progress))
            overlay.configure(bg=f"#{shade:02x}{shade:02x}{shade:02x}")
            self.update()
            self.after(self.fade_delay)

    def fade_from_black(self):
        overlay = self.create_fade_overlay()
        for step in range(self.fade_steps + 1):
            progress = step / self.fade_steps
            shade = int(255 * progress)
            overlay.configure(bg=f"#{shade:02x}{shade:02x}{shade:02x}")
            self.update()
            self.after(self.fade_delay)
        overlay.destroy()
        self.fade_overlay = None

    def create_fade_overlay(self):
        if self.fade_overlay is not None:
            self.fade_overlay.destroy()
        self.fade_overlay = tk.Frame(self, bg="#ffffff")
        self.fade_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.fade_overlay.lift()
        self.update_idletasks()
        return self.fade_overlay

    def show_main_menu(self):
        screen = self.make_screen()

        container = tk.Frame(screen, bg="#f3ead7")
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            container,
            text="Fazendinha",
            font=("Segoe UI", 34, "bold"),
            bg="#f3ead7",
            fg="#315c2b",
        ).pack(pady=(0, 34))

        self.menu_button(container, "New Game", self.show_new_game).pack(fill="x", pady=8)
        self.menu_button(container, "Continue", self.show_continue).pack(fill="x", pady=8)

    def show_continue(self):
        screen = self.make_screen()

        tk.Label(
            screen,
            text="Jogos Salvos",
            font=("Segoe UI", 26, "bold"),
            bg="#f3ead7",
            fg="#315c2b",
        ).pack(pady=(44, 18))

        saves = self.load_saves()
        list_frame = tk.Frame(screen, bg="#fffaf0", highlightbackground="#bda984", highlightthickness=1)
        list_frame.pack(fill="both", expand=True, padx=80, pady=(0, 24))

        if saves:
            for save_path, save in saves:
                farm_name = save.get("farm_name", "Fazenda sem nome")
                tk.Button(
                    list_frame,
                    text=farm_name,
                    command=lambda path=save_path, data=save: self.start_game(path, data),
                    font=("Segoe UI", 14),
                    anchor="w",
                    bg="#fffaf0",
                    activebackground="#efe0bf",
                    fg="#303030",
                    activeforeground="#303030",
                    relief="flat",
                    cursor="hand2",
                    padx=18,
                    pady=12,
                ).pack(fill="x")
        else:
            tk.Label(
                list_frame,
                text="Nenhum jogo salvo encontrado.",
                font=("Segoe UI", 14),
                bg="#fffaf0",
                fg="#6b5f4a",
            ).place(relx=0.5, rely=0.5, anchor="center")

        self.menu_button(screen, "Back", self.show_main_menu, width=14).pack(pady=(0, 28))

    def show_new_game(self):
        screen = self.make_screen()

        panel = tk.Frame(screen, bg="#f3ead7")
        panel.place(relx=0.5, rely=0.48, anchor="center")

        tk.Label(
            panel,
            text="Nova Fazenda",
            font=("Segoe UI", 26, "bold"),
            bg="#f3ead7",
            fg="#315c2b",
        ).pack(pady=(0, 22))

        tk.Label(
            panel,
            text="Nome da fazenda",
            font=("Segoe UI", 12),
            bg="#f3ead7",
            fg="#4f4637",
            anchor="w",
        ).pack(fill="x")

        self.farm_name_entry = tk.Entry(panel, font=("Segoe UI", 15), width=32)
        self.farm_name_entry.pack(pady=(6, 18), ipady=6)
        self.farm_name_entry.focus_set()

        buttons = tk.Frame(panel, bg="#f3ead7")
        buttons.pack(fill="x")

        self.menu_button(buttons, "Create", self.create_game, width=14).pack(side="left", padx=(0, 10))
        self.menu_button(buttons, "Back", self.show_main_menu, width=14).pack(side="left", padx=(10, 0))

    def create_game(self):
        farm_name = self.farm_name_entry.get().strip()
        if not farm_name:
            messagebox.showwarning(APP_TITLE, "Digite o nome da fazenda.")
            return

        SAVE_DIR.mkdir(exist_ok=True)
        save_path = self.next_save_path()
        self.player_position = self.default_player_position.copy()
        save_data = {
            "farm_name": farm_name,
            "player": {"x": self.player_position[0], "y": self.player_position[1]},
            "area": "farm",
            "inventory_items": self.inventory_items,
            "inventory_counts": self.inventory_counts,
            "money": 1000,
            "tilled_soil": [],
            "watering_can_water": self.watering_can_capacity,
            "time": {"day_count": 0, "day_index": 0, "minutes": self.day_start_minutes, "total_minutes": 0},
        }
        self.write_save(save_path, save_data)
        self.start_game(save_path, save_data)

    def start_game(self, save_path, save_data):
        self.stop_game_loop()
        self.current_save_path = save_path
        self.current_save = save_data
        self.selected_inventory_slot = None
        self.current_area = save_data.get("area", "farm")
        self.money = int(save_data.get("money", 1000))
        self.inventory_items, self.inventory_counts = self.load_inventory(save_data)
        self.watering_can_water = int(save_data.get("watering_can_water", self.watering_can_capacity))
        self.watering_can_water = max(0, min(self.watering_can_water, self.watering_can_capacity))
        self.load_time_state(save_data)
        loaded_soil_tiles = [
            {
                "x": float(tile["x"]),
                "y": float(tile["y"]),
                "watered": bool(tile.get("watered", False)),
                "crop": tile.get("crop"),
                "planted_at": tile.get("planted_at"),
                "growth_minutes": tile.get("growth_minutes"),
            }
            for tile in save_data.get("tilled_soil", [])
            if "x" in tile and "y" in tile
        ]
        self.tilled_soil_tiles = self.normalize_soil_tiles(loaded_soil_tiles)
        player = save_data.get("player", {})
        self.player_position = [
            float(player.get("x", 130)),
            float(player.get("y", 315)),
        ]
        self.paused = False
        self.pressed_keys.clear()

        screen = self.make_screen()
        self.game_canvas = tk.Canvas(screen, bg="#78a85d", highlightthickness=0, takefocus=True)
        self.game_canvas.pack(fill="both", expand=True)
        self.game_canvas.after_idle(self.game_canvas.focus_set)
        self.update_cursor()

        self.game_canvas.bind("<KeyPress>", self.handle_key_press)
        self.game_canvas.bind("<KeyRelease>", self.handle_key_release)
        self.game_canvas.bind("<ButtonPress-1>", self.handle_mouse_press)
        self.game_canvas.bind("<B1-Motion>", self.handle_mouse_drag)
        self.game_canvas.bind("<ButtonRelease-1>", self.handle_mouse_release)
        self.game_canvas.bind("<Button-3>", self.handle_right_click)
        self.game_canvas.bind("<Escape>", lambda event: self.toggle_pause())
        self.game_canvas.bind("<Configure>", lambda event: self.draw_game())

        self.draw_game()
        self.run_game_loop()

    def draw_game(self):
        if self.game_canvas is None:
            return

        canvas = self.game_canvas
        if not self.paused and self.pause_panel is not None:
            self.pause_panel.destroy()
            self.pause_panel = None
        canvas.delete("all")
        if self.current_area == "shop":
            self.draw_shop_interior()
        else:
            self.draw_farm_area()
        self.draw_feedback_message()
        self.draw_time_hud()
        self.draw_game_buttons()
        self.draw_inventory()
        self.draw_dragged_item()

        if self.paused:
            self.draw_pause_menu()

    def draw_farm_area(self):
        canvas = self.game_canvas
        self.update_camera()

        x1, y1, x2, y2 = self.farm_rect
        hx1, hy1, hx2, hy2 = self.house_rect
        sx1, sy1, sx2, sy2 = self.shop_rect
        lx1, ly1, lx2, ly2 = self.lake_rect
        px, py = self.player_position
        r = self.player_radius
        screen_x1, screen_y1 = self.world_to_screen(x1, y1)
        screen_x2, screen_y2 = self.world_to_screen(x2, y2)

        canvas.create_rectangle(screen_x1, screen_y1, screen_x2, screen_y2, fill="#caa56a", outline="#8d6a37", width=4)
        self.draw_lake(lx1, ly1, lx2, ly2)
        self.draw_tilled_soil()

        self.draw_house(hx1, hy1, hx2, hy2)
        self.draw_shop(sx1, sy1, sx2, sy2)

        self.draw_player(px, py)

    def draw_shop_interior(self):
        canvas = self.game_canvas
        self.camera_x = 0
        self.camera_y = 0
        x1, y1, x2, y2 = self.shop_area_rect
        canvas.create_rectangle(x1, y1, x2, y2, fill="#c9a56f", outline="#6f5530", width=4)
        canvas.create_rectangle(70, 58, 690, 150, fill="#a77942", outline="#5f3c1d", width=3)
        canvas.create_rectangle(110, 185, 650, 260, fill="#7b4a25", outline="#4b2d17", width=3)
        canvas.create_rectangle(0, 0, 760, 42, fill="#8c6135", outline="")
        canvas.create_text(380, 26, text="Shop", fill="#fff8e7", font=("Segoe UI", 16, "bold"))

        canvas.create_rectangle(373, 162, 387, 185, fill="#3f6f7f", outline="#284955", width=2)
        canvas.create_oval(370, 138, 390, 158, fill="#d6a77a", outline="#6b4325", width=2)
        canvas.create_oval(375, 143, 378, 146, fill="#2d1d12", outline="")
        canvas.create_oval(382, 143, 385, 146, fill="#2d1d12", outline="")

        ex1, ey1, ex2, ey2 = self.shop_exit_rect
        canvas.create_rectangle(ex1, ey1, ex2, ey2, fill="#5d3b23", outline="#2f1d10", width=3)
        canvas.create_line(ex1, ey1, ex2, ey1, fill="#c9a56f", width=3)
        canvas.create_oval(ex2 - 18, ey1 + 22, ex2 - 12, ey1 + 28, fill="#d8b45f", outline="")
        canvas.create_text((ex1 + ex2) / 2, ey1 - 12, text="Exit", fill="#3c2c1a", font=("Segoe UI", 10, "bold"))
        self.draw_player(self.player_position[0], self.player_position[1])

    def draw_player(self, x, y):
        px, py = self.world_to_screen(x, y)
        r = self.player_radius
        self.game_canvas.create_oval(px - r, py - r, px + r, py + r, fill="#2f65c8", outline="#173b76", width=2)
        self.game_canvas.create_oval(px - 5, py - 8, px - 1, py - 4, fill="white", outline="")
        self.game_canvas.create_oval(px + 1, py - 8, px + 5, py - 4, fill="white", outline="")

    def update_camera(self):
        if self.game_canvas is None:
            return

        canvas_width = self.game_canvas.winfo_width()
        canvas_height = self.game_canvas.winfo_height()
        x1, y1, x2, y2 = self.farm_rect
        target_x = self.player_position[0] - canvas_width / 2
        target_y = self.player_position[1] - canvas_height / 2
        max_x = max(x1, x2 - canvas_width)
        max_y = max(y1, y2 - canvas_height)
        self.camera_x = min(max(target_x, x1), max_x)
        self.camera_y = min(max(target_y, y1), max_y)

    def world_to_screen(self, x, y):
        return x - self.camera_x, y - self.camera_y

    def screen_to_world(self, x, y):
        return x + self.camera_x, y + self.camera_y

    def draw_house(self, x1, y1, x2, y2):
        canvas = self.game_canvas
        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)
        canvas.create_rectangle(sx1, sy1 + 30, sx2, sy2, fill="#b8753a", outline="#6b3f1d", width=3)
        canvas.create_polygon(sx1 - 12, sy1 + 34, (sx1 + sx2) / 2, sy1 - 18, sx2 + 12, sy1 + 34, fill="#7b2f22", outline="#572117")
        canvas.create_rectangle(sx1 + 18, sy1 + 62, sx1 + 48, sy1 + 92, fill="#8fd1e6", outline="#4c7890", width=2)
        canvas.create_rectangle(sx2 - 48, sy1 + 62, sx2 - 18, sy1 + 92, fill="#8fd1e6", outline="#4c7890", width=2)

    def draw_shop(self, x1, y1, x2, y2):
        canvas = self.game_canvas
        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)
        canvas.create_rectangle(sx1, sy1 + 28, sx2, sy2, fill="#c6924b", outline="#6b4a1f", width=3)
        canvas.create_polygon(sx1 - 10, sy1 + 32, (sx1 + sx2) / 2, sy1 - 16, sx2 + 10, sy1 + 32, fill="#3f6f7f", outline="#284955")
        canvas.create_rectangle(sx1 + 18, sy1 + 56, sx1 + 50, sy1 + 94, fill="#7dc7d9", outline="#426d78", width=2)
        canvas.create_rectangle(sx2 - 52, sy1 + 60, sx2 - 18, sy2 + 10, fill="#6a4427", outline="#3d2716", width=2)
        canvas.create_oval(sx2 - 28, sy1 + 91, sx2 - 23, sy1 + 96, fill="#d8b45f", outline="")
        canvas.create_text((sx1 + sx2) / 2, sy1 + 45, text="Shop", fill="#3a2814", font=("Segoe UI", 13, "bold"))

    def draw_lake(self, x1, y1, x2, y2):
        canvas = self.game_canvas
        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)
        wave_phase = self.water_animation_frame / 18
        wave_offset = math.sin(wave_phase) * 10
        second_wave_offset = math.sin(wave_phase + math.pi * 0.75) * 8
        vertical_wave_offset = math.sin(wave_phase + math.pi / 2) * 4
        canvas.create_oval(sx1, sy1, sx2, sy2, fill="#6ec7df", outline="#2c7891", width=4)
        canvas.create_arc(
            sx1 + 18 + wave_offset,
            sy1 + 20,
            sx2 - 18 + wave_offset,
            sy2 - 20,
            start=200,
            extent=120,
            outline="#b9edf5",
            width=3,
            style="arc",
        )
        canvas.create_arc(
            sx1 + 42 + second_wave_offset,
            sy1 + 54,
            sx2 - 38 + second_wave_offset,
            sy2 - 38,
            start=25,
            extent=100,
            outline="#b9edf5",
            width=2,
            style="arc",
        )
        canvas.create_arc(
            sx1 + 32,
            sy1 + 38 + vertical_wave_offset,
            sx2 - 46,
            sy2 - 48 + vertical_wave_offset,
            start=25,
            extent=95,
            outline="#d3f7fb",
            width=2,
            style="arc",
        )

    def draw_tilled_soil(self):
        canvas = self.game_canvas
        half = self.soil_tile_size / 2
        for tile in self.tilled_soil_tiles:
            x = tile["x"]
            y = tile["y"]
            sx, sy = self.world_to_screen(x, y)
            fill = "#7f5631" if tile.get("watered") else "#a77a45"
            stripe = "#4e321b" if tile.get("watered") else "#714d27"
            canvas.create_rectangle(sx - half, sy - half, sx + half, sy + half, fill=fill, outline="#76512a", width=2)
            for offset in (-9, 0, 9):
                canvas.create_line(sx - half + 4, sy + offset, sx + half - 4, sy + offset - 7, fill=stripe, width=2)
            if tile.get("crop") == "lettuce":
                self.draw_lettuce_crop(sx, sy, self.lettuce_stage(tile))

    def draw_lettuce_crop(self, x, y, stage):
        if stage == 1:
            self.draw_lettuce_sprouts(x, y)
        elif stage == 2:
            self.draw_small_lettuce(x, y)
        else:
            self.draw_mature_lettuce(x, y)

    def draw_lettuce_sprouts(self, x, y):
        canvas = self.game_canvas
        for offset_x, offset_y in ((-7, -5), (4, -6), (-2, 5), (8, 4)):
            canvas.create_oval(
                x + offset_x - 3,
                y + offset_y - 3,
                x + offset_x + 3,
                y + offset_y + 3,
                fill="#4fb84a",
                outline="#2e7d32",
                width=1,
            )

    def draw_small_lettuce(self, x, y):
        canvas = self.game_canvas
        for offset_x, offset_y, radius in ((-5, 0, 6), (4, -2, 6), (0, 5, 5)):
            canvas.create_oval(
                x + offset_x - radius,
                y + offset_y - radius,
                x + offset_x + radius,
                y + offset_y + radius,
                fill="#66c94f",
                outline="#2e7d32",
                width=1,
            )

    def draw_mature_lettuce(self, x, y):
        canvas = self.game_canvas
        for offset_x, offset_y, radius in ((-7, -2, 7), (7, -2, 7), (0, 5, 8), (0, -8, 6)):
            canvas.create_oval(
                x + offset_x - radius,
                y + offset_y - radius,
                x + offset_x + radius,
                y + offset_y + radius,
                fill="#7bd85a",
                outline="#2e7d32",
                width=1,
            )

    def draw_inventory(self):
        canvas = self.game_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        slot_size = 42
        gap = 8
        slot_count = 10
        total_width = slot_count * slot_size + (slot_count - 1) * gap
        start_x = (width - total_width) / 2
        y = height - slot_size - 18

        self.inventory_slots = []
        for index in range(slot_count):
            x = start_x + index * (slot_size + gap)
            is_selected = index == self.selected_inventory_slot
            fill = "#8f744b" if is_selected else "#d9bd83"
            outline = "#4c3921" if is_selected else "#7e6741"
            canvas.create_rectangle(x, y, x + slot_size, y + slot_size, fill=fill, outline=outline, width=3)
            if index == self.drag_start_slot and self.dragged_item is not None:
                pass
            elif self.inventory_items[index] == "hoe":
                self.draw_hoe_icon(x, y, slot_size)
            elif self.inventory_items[index] == "watering_can":
                self.draw_watering_can_icon(x, y, slot_size)
                self.draw_watering_can_water_bar(x, y, slot_size)
            elif self.inventory_items[index] == "lettuce_seed":
                self.draw_lettuce_seed_icon(x, y, slot_size)
                self.draw_item_count(index, x, y, slot_size)
            elif self.inventory_items[index] == "lettuce":
                self.draw_lettuce_icon(x, y, slot_size)
                self.draw_item_count(index, x, y, slot_size)
            self.inventory_slots.append((x, y, x + slot_size, y + slot_size))

    def draw_inventory_item_icon(self, item, x, y, size):
        if item == "hoe":
            self.draw_hoe_icon(x, y, size)
        elif item == "watering_can":
            self.draw_watering_can_icon(x, y, size)
        elif item == "lettuce_seed":
            self.draw_lettuce_seed_icon(x, y, size)
        elif item == "lettuce":
            self.draw_lettuce_icon(x, y, size)

    def draw_dragged_item(self):
        if self.dragged_item is None or self.drag_current_position is None:
            return

        x, y = self.drag_current_position
        size = 42
        icon_x = x - size / 2
        icon_y = y - size / 2
        self.game_canvas.create_rectangle(icon_x, icon_y, icon_x + size, icon_y + size, fill="#f2d89a", outline="#4c3921", width=2)
        self.draw_inventory_item_icon(self.dragged_item, icon_x, icon_y, size)
        if self.drag_start_slot is not None and self.inventory_counts[self.drag_start_slot] is not None:
            self.game_canvas.create_text(
                icon_x + size - 5,
                icon_y + size - 6,
                text=str(self.inventory_counts[self.drag_start_slot]),
                anchor="se",
                fill="#2b2116",
                font=("Segoe UI", 9, "bold"),
            )

    def draw_time_hud(self):
        canvas = self.game_canvas
        width = canvas.winfo_width()
        x2 = width - 18
        y1 = 16
        x1 = x2 - 75
        y2 = y1 + 27
        canvas.create_rectangle(x1, y1, x2, y2, fill="#fff8e7", outline="#6f5530", width=2)
        canvas.create_text(
            x1 + 7,
            y1 + 8,
            text=self.week_days[self.day_index % len(self.week_days)],
            anchor="w",
            fill="#3c2c1a",
            font=("Segoe UI", 7, "bold"),
        )
        canvas.create_text(
            x1 + 7,
            y1 + 20,
            text=self.format_game_time(),
            anchor="w",
            fill="#3c2c1a",
            font=("Segoe UI", 8, "bold"),
        )
        money_y1 = y2 + 5
        money_y2 = money_y1 + 22
        canvas.create_rectangle(x1, money_y1, x2, money_y2, fill="#fff8e7", outline="#6f5530", width=2)
        canvas.create_text(
            x1 + 7,
            (money_y1 + money_y2) / 2,
            text=f"${self.money}",
            anchor="w",
            fill="#2f5d24",
            font=("Segoe UI", 9, "bold"),
        )

    def draw_game_buttons(self):
        canvas = self.game_canvas
        width = canvas.winfo_width()
        button_w = 126
        button_h = 28
        x1 = width - button_w - 18
        y1 = 82
        self.draw_canvas_button(x1, y1, button_w, button_h, "+ Lettuce Seed", "add_seed_button")
        self.draw_canvas_button(x1, y1 + button_h + 8, button_w, button_h, "Next Day 6 AM", "next_day_button")

    def draw_canvas_button(self, x, y, width, height, text, tag):
        self.game_canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill="#fff8e7",
            outline="#6f5530",
            width=2,
            tags=(tag, "game_button"),
        )
        self.game_canvas.create_text(
            x + width / 2,
            y + height / 2,
            text=text,
            fill="#3c2c1a",
            font=("Segoe UI", 9, "bold"),
            tags=(tag, "game_button"),
        )

    def format_game_time(self):
        display_minutes = self.game_minutes % (24 * 60)
        hour_24 = display_minutes // 60
        minute = display_minutes % 60
        suffix = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12
        if hour_12 == 0:
            hour_12 = 12
        return f"{hour_12}:{minute:02d} {suffix}"

    def draw_hoe_icon(self, x, y, size):
        canvas = self.game_canvas
        canvas.create_line(x + 13, y + 31, x + 29, y + 13, fill="#5a341e", width=4, capstyle="round")
        canvas.create_line(x + 25, y + 13, x + 34, y + 20, fill="#5a341e", width=3, capstyle="round")
        canvas.create_line(x + 29, y + 11, x + 36, y + 11, fill="#b8c4c4", width=4, capstyle="round")

    def draw_watering_can_icon(self, x, y, size):
        canvas = self.game_canvas
        canvas.create_oval(x + 12, y + 18, x + 31, y + 34, fill="#5d9bb8", outline="#2f5f75", width=2)
        canvas.create_arc(x + 9, y + 15, x + 23, y + 31, start=90, extent=180, outline="#2f5f75", width=3, style="arc")
        canvas.create_line(x + 29, y + 22, x + 37, y + 16, fill="#2f5f75", width=3, capstyle="round")
        canvas.create_line(x + 15, y + 15, x + 27, y + 15, fill="#5d9bb8", width=4, capstyle="round")

    def draw_watering_can_water_bar(self, x, y, size):
        canvas = self.game_canvas
        bar_x1 = x + size + 1
        bar_y1 = y + 4
        bar_x2 = bar_x1 + 6
        bar_y2 = y + size - 4
        fill_ratio = self.watering_can_water / self.watering_can_capacity
        fill_height = (bar_y2 - bar_y1) * fill_ratio
        canvas.create_rectangle(bar_x1, bar_y1, bar_x2, bar_y2, fill="#fffaf0", outline="black", width=1)
        canvas.create_rectangle(bar_x1 + 1, bar_y2 - fill_height, bar_x2 - 1, bar_y2 - 1, fill="#8ddff0", outline="")

    def draw_lettuce_seed_icon(self, x, y, size):
        canvas = self.game_canvas
        canvas.create_oval(x + 12, y + 15, x + 20, y + 23, fill="#6fbf4a", outline="#3f7f2b", width=1)
        canvas.create_oval(x + 22, y + 13, x + 31, y + 22, fill="#7ed35a", outline="#3f7f2b", width=1)
        canvas.create_oval(x + 17, y + 24, x + 27, y + 33, fill="#5ba83e", outline="#3f7f2b", width=1)

    def draw_lettuce_icon(self, x, y, size):
        canvas = self.game_canvas
        canvas.create_oval(x + 11, y + 16, x + 25, y + 31, fill="#7bd85a", outline="#2e7d32", width=1)
        canvas.create_oval(x + 20, y + 12, x + 34, y + 28, fill="#66c94f", outline="#2e7d32", width=1)
        canvas.create_oval(x + 16, y + 23, x + 31, y + 36, fill="#8ee66b", outline="#2e7d32", width=1)

    def draw_item_count(self, index, x, y, size):
        count = self.inventory_counts[index]
        if count is None:
            return
        self.game_canvas.create_text(
            x + size - 5,
            y + size - 6,
            text=str(count),
            anchor="se",
            fill="#2b2116",
            font=("Segoe UI", 9, "bold"),
        )

    def handle_mouse_press(self, event):
        if self.paused:
            return

        button_action = self.game_button_at(event.x, event.y)
        if button_action is not None:
            self.mouse_pressed_game_button = True
            button_action()
            return

        slot_index = self.inventory_slot_at(event.x, event.y)
        if slot_index is not None:
            item = self.inventory_items[slot_index]
            if item is not None:
                self.drag_start_slot = slot_index
                self.drag_press_position = (event.x, event.y)
                self.drag_has_moved = False
            return

        self.mouse_press_position = (event.x, event.y)

    def game_button_at(self, x, y):
        clicked_items = self.game_canvas.find_overlapping(x, y, x, y)
        tags = set()
        for item in clicked_items:
            tags.update(self.game_canvas.gettags(item))
        if "add_seed_button" in tags:
            return self.add_lettuce_seed_to_inventory
        if "next_day_button" in tags:
            return self.advance_to_next_morning
        return None

    def handle_mouse_drag(self, event):
        if self.paused or self.drag_start_slot is None:
            return

        if self.dragged_item is None:
            start_x, start_y = self.drag_press_position
            moved_far_enough = abs(event.x - start_x) >= 4 or abs(event.y - start_y) >= 4
            if not moved_far_enough:
                return
            self.dragged_item = self.inventory_items[self.drag_start_slot]
            self.update_cursor()

        self.drag_current_position = (event.x, event.y)
        self.drag_has_moved = True
        self.draw_game()

    def handle_mouse_release(self, event):
        if self.paused:
            return

        if self.mouse_pressed_game_button:
            self.mouse_pressed_game_button = False
            return

        if self.drag_start_slot is not None:
            self.finish_inventory_drag(event.x, event.y)
            return

        if self.selected_item() == "hoe":
            if self.current_area != "farm":
                return
            world_x, world_y = self.screen_to_world(event.x, event.y)
            self.try_till_soil(world_x, world_y)
        elif self.selected_item() == "watering_can":
            if self.current_area != "farm":
                return
            world_x, world_y = self.screen_to_world(event.x, event.y)
            self.try_water_soil(world_x, world_y)
        elif self.selected_item() == "lettuce_seed":
            if self.current_area != "farm":
                return
            world_x, world_y = self.screen_to_world(event.x, event.y)
            self.try_plant_lettuce(world_x, world_y)

    def handle_right_click(self, event):
        if self.paused:
            return
        if self.current_area != "farm":
            return

        world_x, world_y = self.screen_to_world(event.x, event.y)
        tile = self.find_tilled_soil_at_point(world_x, world_y)
        if tile is None or tile.get("crop") != "lettuce":
            return
        if not self.is_in_item_use_range(tile["x"], tile["y"]):
            self.show_feedback_message("I can't reach it from here.")
            return

        stage = self.lettuce_stage(tile)
        if stage < 3:
            self.show_feedback_message("You need to wait.")
            return

        if not self.add_stackable_item("lettuce", 1, self.max_harvest_stack):
            self.show_feedback_message("Inventory is full.")
            return

        tile["crop"] = None
        tile["planted_at"] = None
        tile["growth_minutes"] = 0
        self.draw_game()

    def finish_inventory_drag(self, x, y):
        target_slot = self.inventory_slot_at(x, y)
        start_slot = self.drag_start_slot

        if target_slot is None:
            self.clear_inventory_drag()
            self.draw_game()
            return

        if target_slot == start_slot and not self.drag_has_moved:
            if self.selected_inventory_slot == start_slot:
                self.selected_inventory_slot = None
            else:
                self.selected_inventory_slot = start_slot
        elif target_slot != start_slot:
            self.inventory_items[start_slot], self.inventory_items[target_slot] = (
                self.inventory_items[target_slot],
                self.inventory_items[start_slot],
            )
            self.inventory_counts[start_slot], self.inventory_counts[target_slot] = (
                self.inventory_counts[target_slot],
                self.inventory_counts[start_slot],
            )
            if self.selected_inventory_slot == start_slot:
                self.selected_inventory_slot = target_slot
            elif self.selected_inventory_slot == target_slot:
                self.selected_inventory_slot = start_slot

        self.clear_inventory_drag()
        self.update_cursor()
        self.draw_game()

    def clear_inventory_drag(self):
        self.dragged_item = None
        self.drag_start_slot = None
        self.drag_current_position = None
        self.drag_press_position = None
        self.drag_has_moved = False

    def inventory_slot_at(self, x, y):
        for index, (x1, y1, x2, y2) in enumerate(self.inventory_slots):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return index
        return None

    def selected_item(self):
        if self.selected_inventory_slot is None:
            return None
        return self.inventory_items[self.selected_inventory_slot]

    def load_inventory(self, save_data):
        saved_items = save_data.get("inventory_items")
        saved_counts = save_data.get("inventory_counts")
        if not isinstance(saved_items, list):
            return ["hoe", "watering_can", "lettuce_seed"] + [None] * 7, [None, None, 20] + [None] * 7

        items = (saved_items + [None] * 10)[:10]
        if isinstance(saved_counts, list):
            counts = (saved_counts + [None] * 10)[:10]
        else:
            counts = [None] * 10
        for required_item in ("hoe", "watering_can"):
            if required_item not in items:
                empty_slot = items.index(None) if None in items else None
                if empty_slot is not None:
                    items[empty_slot] = required_item
                    counts[empty_slot] = None
        if "lettuce_seed" not in items:
            empty_slot = items.index(None) if None in items else None
            if empty_slot is not None:
                items[empty_slot] = "lettuce_seed"
                counts[empty_slot] = 20
        for index, item in enumerate(items):
            if item == "lettuce_seed":
                count = counts[index] if isinstance(counts[index], int) else 20
                counts[index] = max(0, min(count, self.max_seed_stack))
                if counts[index] == 0:
                    items[index] = None
                    counts[index] = None
            elif item == "lettuce":
                count = counts[index] if isinstance(counts[index], int) else 1
                counts[index] = max(0, min(count, self.max_harvest_stack))
                if counts[index] == 0:
                    items[index] = None
                    counts[index] = None
            else:
                counts[index] = None
        return items, counts

    def update_cursor(self):
        if self.game_canvas is None:
            return
        cursor = "crosshair" if not self.paused and self.selected_item() in {"hoe", "watering_can"} else ""
        if self.dragged_item is not None:
            cursor = ""
        self.game_canvas.configure(cursor=cursor)

    def try_till_soil(self, x, y):
        tile_x, tile_y = self.snap_to_soil_tile(x, y)
        if not self.is_in_item_use_range(tile_x, tile_y):
            self.show_feedback_message("I can't reach it from here.")
            return
        if not self.can_till_soil(tile_x, tile_y):
            return

        self.tilled_soil_tiles.append({"x": tile_x, "y": tile_y, "watered": False})
        self.draw_game()

    def try_water_soil(self, x, y):
        if self.is_point_in_lake(x, y):
            self.try_refill_watering_can(x, y)
            return

        tile = self.find_tilled_soil_at_point(x, y)
        if tile is None:
            return
        if not self.is_in_item_use_range(tile["x"], tile["y"]):
            self.show_feedback_message("I can't reach it from here.")
            return
        if tile.get("watered"):
            return
        if self.watering_can_water <= 0:
            self.show_feedback_message("The watering can is empty.")
            return

        tile["watered"] = True
        self.watering_can_water -= 1
        self.draw_game()

    def try_plant_lettuce(self, x, y):
        tile = self.find_tilled_soil_at_point(x, y)
        if tile is None:
            self.show_feedback_message("The soil is not prepared.")
            return
        if not self.is_in_item_use_range(tile["x"], tile["y"]):
            self.show_feedback_message("I can't reach it from here.")
            return
        if tile.get("crop") is not None:
            self.show_feedback_message("Something is already planted here.")
            return

        tile["crop"] = "lettuce"
        tile["planted_at"] = self.current_absolute_minutes()
        tile["growth_minutes"] = 0
        self.consume_selected_seed()
        self.draw_game()

    def lettuce_stage(self, tile):
        age = int(tile.get("growth_minutes") or 0)
        if age >= self.lettuce_stage_3_minutes:
            return 3
        if age >= self.lettuce_stage_2_minutes:
            return 2
        return 1

    def consume_selected_seed(self):
        if self.selected_inventory_slot is None:
            return

        count = self.inventory_counts[self.selected_inventory_slot]
        if count is None:
            return

        count -= 1
        if count <= 0:
            self.inventory_items[self.selected_inventory_slot] = None
            self.inventory_counts[self.selected_inventory_slot] = None
            self.selected_inventory_slot = None
            self.update_cursor()
        else:
            self.inventory_counts[self.selected_inventory_slot] = count

    def add_lettuce_seed_to_inventory(self):
        if self.add_stackable_item("lettuce_seed", 1, self.max_seed_stack):
            self.draw_game()
        else:
            self.show_feedback_message("Inventory is full.")

    def add_stackable_item(self, item_name, amount, max_stack):
        remaining = amount
        for index, item in enumerate(self.inventory_items):
            if item == item_name and self.inventory_counts[index] < max_stack:
                available = max_stack - self.inventory_counts[index]
                added = min(remaining, available)
                self.inventory_counts[index] += added
                remaining -= added
                if remaining == 0:
                    return True

        for index, item in enumerate(self.inventory_items):
            if item is None:
                added = min(remaining, max_stack)
                self.inventory_items[index] = item_name
                self.inventory_counts[index] = added
                remaining -= added
                if remaining == 0:
                    return True

        return False

    def advance_to_next_morning(self):
        self.start_next_day()
        self.draw_game()

    def try_refill_watering_can(self, x, y):
        if not self.is_in_item_use_range(x, y):
            self.show_feedback_message("I can't reach it from here.")
            return

        self.watering_can_water = self.watering_can_capacity
        self.draw_game()

    def is_point_in_lake(self, x, y):
        x1, y1, x2, y2 = self.lake_rect
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        radius_x = (x2 - x1) / 2
        radius_y = (y2 - y1) / 2
        normalized = ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2
        return normalized <= 1

    def find_tilled_soil(self, x, y):
        for tile in self.tilled_soil_tiles:
            if abs(x - tile["x"]) < 1 and abs(y - tile["y"]) < 1:
                return tile
        return None

    def find_tilled_soil_at_point(self, x, y):
        half = self.soil_tile_size / 2
        for tile in self.tilled_soil_tiles:
            if tile["x"] - half <= x <= tile["x"] + half and tile["y"] - half <= y <= tile["y"] + half:
                return tile
        return None

    def is_soil_tile_occupied(self, x, y):
        half = self.soil_tile_size / 2
        for tile in self.tilled_soil_tiles:
            if self.rects_overlap(
                x - half,
                y - half,
                x + half,
                y + half,
                tile["x"] - half,
                tile["y"] - half,
                tile["x"] + half,
                tile["y"] + half,
            ):
                return True
        return False

    def rects_overlap(self, ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def is_in_item_use_range(self, x, y):
        px, py = self.player_position
        distance_squared = (x - px) ** 2 + (y - py) ** 2
        return distance_squared <= self.item_use_range ** 2

    def show_feedback_message(self, text):
        self.feedback_message = text
        if self.feedback_message_id is not None:
            self.after_cancel(self.feedback_message_id)
        self.feedback_message_id = self.after(900, self.clear_feedback_message)
        self.draw_game()

    def clear_feedback_message(self):
        self.feedback_message = None
        self.feedback_message_id = None
        self.draw_game()

    def draw_feedback_message(self):
        if not self.feedback_message:
            return

        width = self.game_canvas.winfo_width()
        height = self.game_canvas.winfo_height()
        box_x1 = 90
        box_y1 = height - 118
        box_x2 = width - 90
        box_y2 = height - 72
        self.game_canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2, fill="#fff8e7", outline="#6f5530", width=3)
        self.game_canvas.create_text(
            box_x1 + 18,
            (box_y1 + box_y2) / 2,
            text=self.feedback_message,
            anchor="w",
            fill="#3c2c1a",
            font=("Segoe UI", 12, "bold"),
        )

    def snap_to_soil_tile(self, x, y):
        x1, y1, _, _ = self.farm_rect
        size = self.soil_tile_size
        tile_x = x1 + size / 2 + int((x - x1) / size) * size
        tile_y = y1 + size / 2 + int((y - y1) / size) * size
        return tile_x, tile_y

    def normalize_soil_tiles(self, tiles):
        normalized = {}
        for tile in tiles:
            tile_x, tile_y = self.snap_to_soil_tile(tile["x"], tile["y"])
            key = (tile_x, tile_y)
            if key not in normalized:
                normalized[key] = {
                    "x": tile_x,
                    "y": tile_y,
                    "watered": False,
                    "crop": None,
                    "planted_at": None,
                    "growth_minutes": 0,
                }
            normalized[key]["watered"] = normalized[key]["watered"] or tile.get("watered", False)
            if normalized[key]["crop"] is None and tile.get("crop") is not None:
                normalized[key]["crop"] = tile.get("crop")
                planted_at = self.normalize_planted_at(tile.get("planted_at"))
                normalized[key]["planted_at"] = planted_at
                normalized[key]["growth_minutes"] = self.normalize_growth_minutes(tile.get("growth_minutes"), planted_at)
        return list(normalized.values())

    def normalize_planted_at(self, planted_at):
        if planted_at is None:
            return self.current_absolute_minutes()

        planted_at = int(planted_at)
        if planted_at > self.current_absolute_minutes():
            return self.current_absolute_minutes()
        return planted_at

    def normalize_growth_minutes(self, growth_minutes, planted_at):
        if growth_minutes is not None:
            return max(0, int(growth_minutes))
        return max(0, self.current_absolute_minutes() - int(planted_at))

    def can_till_soil(self, x, y):
        half = self.soil_tile_size / 2
        x1, y1, x2, y2 = self.farm_rect
        hx1, hy1, hx2, hy2 = self.house_rect
        sx1, sy1, sx2, sy2 = self.shop_rect
        lx1, ly1, lx2, ly2 = self.lake_rect
        px, py = self.player_position
        player_radius = self.player_radius

        inside_farm = x1 <= x - half and x + half <= x2 and y1 <= y - half and y + half <= y2
        tile_x1 = x - half
        tile_y1 = y - half
        tile_x2 = x + half
        tile_y2 = y + half
        overlaps_house = self.rects_overlap(tile_x1, tile_y1, tile_x2, tile_y2, hx1, hy1, hx2, hy2)
        overlaps_shop = self.rects_overlap(tile_x1, tile_y1, tile_x2, tile_y2, sx1, sy1, sx2, sy2)
        overlaps_lake = self.rects_overlap(tile_x1, tile_y1, tile_x2, tile_y2, lx1, ly1, lx2, ly2)
        overlaps_player = self.rects_overlap(
            tile_x1,
            tile_y1,
            tile_x2,
            tile_y2,
            px - player_radius,
            py - player_radius,
            px + player_radius,
            py + player_radius,
        )
        already_tilled = self.is_soil_tile_occupied(x, y)
        return inside_farm and not overlaps_house and not overlaps_shop and not overlaps_lake and not overlaps_player and not already_tilled

    def handle_key_press(self, event):
        key = event.keysym.lower()
        if key in {"w", "a", "s", "d"}:
            self.pressed_keys.add(key)

    def handle_key_release(self, event):
        key = event.keysym.lower()
        if key in {"w", "a", "s", "d"}:
            self.pressed_keys.discard(key)

    def run_game_loop(self):
        if self.game_canvas is None:
            return

        if not self.paused:
            self.water_animation_frame += 1
            self.advance_time(16)
            self.update_player_position()
            self.draw_game()
        self.game_loop_id = self.after(16, self.run_game_loop)

    def advance_time(self, elapsed_ms):
        self.time_accumulator_ms += elapsed_ms
        while self.time_accumulator_ms >= self.real_ms_per_game_tick:
            self.time_accumulator_ms -= self.real_ms_per_game_tick
            self.game_minutes += self.game_minutes_per_tick
            self.total_game_minutes += self.game_minutes_per_tick
            self.advance_crop_growth(self.game_minutes_per_tick)
            if self.game_minutes >= self.day_end_minutes:
                self.start_next_day()

    def start_next_day(self):
        minutes_until_next_morning = (24 * 60 - self.game_minutes) + self.day_start_minutes
        if minutes_until_next_morning <= 0:
            minutes_until_next_morning = 24 * 60
        self.total_game_minutes += minutes_until_next_morning
        self.advance_crop_growth(minutes_until_next_morning)
        self.day_count += 1
        self.day_index = (self.day_index + 1) % len(self.week_days)
        self.game_minutes = self.day_start_minutes
        self.time_accumulator_ms = 0

    def advance_crop_growth(self, minutes):
        for tile in self.tilled_soil_tiles:
            if tile.get("crop") is not None:
                tile["growth_minutes"] = int(tile.get("growth_minutes") or 0) + minutes

    def load_time_state(self, save_data):
        time_state = save_data.get("time", {})
        self.day_count = int(time_state.get("day_count", 0))
        self.day_index = int(time_state.get("day_index", 0)) % len(self.week_days)
        self.game_minutes = int(time_state.get("minutes", self.day_start_minutes))
        fallback_total_minutes = self.day_count * 24 * 60 + self.game_minutes
        planted_times = [
            int(tile["planted_at"])
            for tile in save_data.get("tilled_soil", [])
            if tile.get("planted_at") is not None
        ]
        if planted_times:
            fallback_total_minutes = max(fallback_total_minutes, max(planted_times))
        self.total_game_minutes = int(time_state.get("total_minutes", fallback_total_minutes))
        if self.game_minutes < self.day_start_minutes or self.game_minutes >= self.day_end_minutes:
            self.game_minutes = self.day_start_minutes
        self.time_accumulator_ms = 0

    def current_absolute_minutes(self):
        return self.total_game_minutes

    def stop_game_loop(self):
        if self.game_loop_id is not None:
            self.after_cancel(self.game_loop_id)
            self.game_loop_id = None

    def update_player_position(self):
        dx = 0
        dy = 0
        if "w" in self.pressed_keys:
            dy -= 1
        if "s" in self.pressed_keys:
            dy += 1
        if "a" in self.pressed_keys:
            dx -= 1
        if "d" in self.pressed_keys:
            dx += 1
        if dx == 0 and dy == 0:
            return

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        next_x = self.player_position[0] + dx * self.player_speed
        next_y = self.player_position[1] + dy * self.player_speed
        if self.can_player_move_to(next_x, self.player_position[1]):
            self.player_position[0] = next_x
        if self.can_player_move_to(self.player_position[0], next_y):
            self.player_position[1] = next_y
        self.check_area_transition()

    def can_player_move_to(self, x, y):
        r = self.player_radius
        if self.current_area == "shop":
            x1, y1, x2, y2 = self.shop_area_rect
            inside_shop = x1 + r <= x <= x2 - r and y1 + r <= y <= y2 - r
            counter_blocked = 100 - r <= x <= 660 + r and 185 - r <= y <= 260 + r
            npc_blocked = 370 - r <= x <= 390 + r and 138 - r <= y <= 185 + r
            return inside_shop and not counter_blocked and not npc_blocked

        x1, y1, x2, y2 = self.farm_rect
        hx1, hy1, hx2, hy2 = self.house_rect
        sx1, sy1, sx2, sy2 = self.shop_rect
        lx1, ly1, lx2, ly2 = self.lake_rect

        inside_farm = x1 + r <= x <= x2 - r and y1 + r <= y <= y2 - r
        inside_house = hx1 - r <= x <= hx2 + r and hy1 - r <= y <= hy2 + r
        inside_shop = sx1 - r <= x <= sx2 + r and sy1 - r <= y <= sy2 + r
        inside_shop_door = self.is_player_touching_rect(x, y, self.shop_door_rect)
        inside_lake = lx1 - r <= x <= lx2 + r and ly1 - r <= y <= ly2 + r and self.is_point_in_lake(x, y)
        return inside_farm and not inside_house and (not inside_shop or inside_shop_door) and not inside_lake

    def check_area_transition(self):
        if self.current_area == "farm" and self.is_player_touching_rect(
            self.player_position[0],
            self.player_position[1],
            self.shop_door_rect,
        ):
            self.enter_shop()
        elif self.current_area == "shop" and self.is_player_touching_rect(
            self.player_position[0],
            self.player_position[1],
            self.shop_exit_rect,
        ):
            self.exit_shop()

    def enter_shop(self):
        self.current_area = "shop"
        self.player_position = [380, 535]
        self.pressed_keys.clear()
        self.show_area_transition()

    def exit_shop(self):
        self.current_area = "farm"
        self.player_position = [945, 542]
        self.pressed_keys.clear()
        self.show_area_transition()

    def show_area_transition(self):
        self.fade_to_black()
        self.draw_game()
        self.fade_from_black()

    def is_player_touching_rect(self, x, y, rect):
        r = self.player_radius
        x1, y1, x2, y2 = rect
        return x + r >= x1 and x - r <= x2 and y + r >= y1 and y - r <= y2

    def toggle_pause(self):
        self.paused = not self.paused
        self.pressed_keys.clear()
        self.update_cursor()
        self.draw_game()

    def draw_pause_menu(self):
        canvas = self.game_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        panel_w = 260
        panel_h = 210

        if self.pause_panel is not None:
            self.pause_panel.destroy()
        canvas.create_rectangle(0, 0, width, height, fill="#000000", stipple="gray50", outline="")
        self.pause_panel = tk.Frame(canvas, bg="#fff8e7", highlightbackground="#7e6741", highlightthickness=2)
        canvas.create_window(width / 2, height / 2, window=self.pause_panel, width=panel_w, height=panel_h)

        tk.Label(
            self.pause_panel,
            text="Pause",
            font=("Segoe UI", 22, "bold"),
            bg="#fff8e7",
            fg="#315c2b",
        ).pack(pady=(22, 16))
        self.menu_button(self.pause_panel, "Save", self.save_current_game, width=16).pack(pady=7)
        self.menu_button(self.pause_panel, "Quit Game", self.quit_game, width=16).pack(pady=7)

    def save_current_game(self):
        if self.current_save_path is None or self.current_save is None:
            return

        self.current_save["player"] = {
            "x": self.player_position[0],
            "y": self.player_position[1],
        }
        self.current_save["area"] = self.current_area
        self.current_save["inventory_items"] = self.inventory_items
        self.current_save["inventory_counts"] = self.inventory_counts
        self.current_save["money"] = self.money
        self.current_save["tilled_soil"] = [
            {
                "x": tile["x"],
                "y": tile["y"],
                "watered": tile.get("watered", False),
                "crop": tile.get("crop"),
                "planted_at": tile.get("planted_at"),
                "growth_minutes": tile.get("growth_minutes", 0),
            }
            for tile in self.tilled_soil_tiles
        ]
        self.current_save["watering_can_water"] = self.watering_can_water
        self.current_save["time"] = {
            "day_count": self.day_count,
            "day_index": self.day_index,
            "minutes": self.game_minutes,
            "total_minutes": self.total_game_minutes,
        }
        self.write_save(self.current_save_path, self.current_save)
        messagebox.showinfo(APP_TITLE, "Jogo salvo.")
        self.game_canvas.focus_set()

    def quit_game(self):
        self.stop_game_loop()
        if self.feedback_message_id is not None:
            self.after_cancel(self.feedback_message_id)
            self.feedback_message_id = None
        self.current_save_path = None
        self.current_save = None
        self.game_canvas = None
        self.pause_panel = None
        self.paused = False
        self.selected_inventory_slot = None
        self.inventory_slots = []
        self.clear_inventory_drag()
        self.tilled_soil_tiles = []
        self.feedback_message = None
        self.pressed_keys.clear()
        self.show_main_menu()

    def load_saves(self):
        if not SAVE_DIR.exists():
            return []

        saves = []
        for path in sorted(SAVE_DIR.glob("*.json")):
            try:
                saves.append((path, json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError):
                continue
        return saves

    def next_save_path(self):
        index = 1
        while True:
            path = SAVE_DIR / f"save_{index}.json"
            if not path.exists():
                return path
            index += 1

    def write_save(self, save_path, save_data):
        save_path.write_text(
            json.dumps(save_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def menu_button(self, parent, text, command, width=22):
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            font=("Segoe UI", 14, "bold"),
            bg="#6a994e",
            fg="white",
            activebackground="#5d8844",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=14,
            pady=10,
        )


if __name__ == "__main__":
    app = FarmGameApp()
    app.mainloop()
