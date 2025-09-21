import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageTk
import torch
import torch.nn as nn
from torchvision import transforms
import numpy as np
import win32com.client
import pythoncom
import threading
import random
import time
import socket
from network import PictionaryNetwork

# Aesthetic Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
BG_COLOR = "#1e1e2f"
PANEL_COLOR = "#2a2a3b"
ACCENT_BLUE = "#3498db"
ACCENT_GREEN = "#2ecc71"
ACCENT_RED = "#e74c3c"
ACCENT_YELLOW = "#f1c40f"
TEXT_COLOR = "#ecf0f1"

class QuickDrawCNN(nn.Module):
    def __init__(self, num_classes):
        super(QuickDrawCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),  # 32 x 14 x 14
        
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),  # 64 x 7 x 7
        
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)   # 128 x 3 x 3
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 3 * 3, 512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )
    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

class AIPictionaryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Real-Time AI Pictionary - MultiPlayer Edition")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=BG_COLOR)
        
        # Audio System Setup
        pythoncom.CoInitialize()
        try:
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self.speaker.Rate = 0
        except:
            self.speaker = None
        self.last_spoken_guess = None

        # Game State
        self.word_bank = [
            "airplane", "alarm clock", "ambulance", "angel", "ant", "anvil", "apple", "arm", 
            "backpack", "banana", "barn", "basketball", "bat", "bear", "bed", "bee", "bicycle", "book", "broom", "bus", "butterfly", 
            "cactus", "cake", "camel", "camera", "candle", "car", "cat", "chair", "circle", "clock", "cloud", "coffee cup", "computer", "cookie", 
            "diamond", "dog", "dolphin", "donut", "door", "dragon", "drill", "drums", "duck", "dumbbell", 
            "ear", "elbow", "elephant", "envelope", "eraser", "eye", "eyeglasses", 
            "face", "fan", "fence", "firetruck", "fish", "flamingo", "flower", "frog", 
            "garden", "giraffe", "goatee", "golf club", "grapes", "grass", "guitar", 
            "hamburger", "hammer", "hand", "hat", "helicopter", "horse", "hospital", "house", 
            "ice cream", "jacket", "jail", "kangaroo", "key", "keyboard", "knee", "knife", 
            "ladder", "lantern", "laptop", "leaf", "leg", "light bulb", "lighthouse", "lightning", 
            "mailbox", "map", "marker", "megaphone", "mermaid", "microphone", "monkey", "moon", "mouse", "mug", "mushroom", 
            "nail", "necklace", "nose", "ocean", "octagon", "octopus", "onion", "oven", "owl", 
            "paintbrush", "palm tree", "panda", "pants", "paper clip", "parachute", "parrot", "peanut", "pear", "pencil", "penguin", "piano", "pig", "pillow", "pizza", "potato", 
            "rabbit", "raccoon", "radio", "rain", "rainbow", "rake", "rhinoceros", "river", "roller coaster", 
            "sailboat", "sandwich", "saw", "saxophone", "school bus", "scissors", "sea turtle", "shark", "sheep", "shoe", "shorts", "shovel", "sink", "skateboard", "sleeping bag", "snail", "snake", "snowflake", "snowman", "spider", "spoon", "skyscraper", "square", "star", "submarine", "sun", "swan", "sword", 
            "t-shirt", "table", "teapot", "teddy-bear", "telephone", "television", "tent", "tiger", "toaster", "toe", "toilet", "tooth", "toothbrush", "tractor", "train", "tree", "triangle", "truck", "trumpet", "umbrella", "underwear", 
            "van", "vase", "violin", 
            "washing machine", "watermelon", "waterslide", "whale", "wheel", "windmill", "wine bottle", "wine glass", "wristwatch", 
            "yoga", "zebra", "zigzag"
        ]
        self.word_bank.sort()
        
        self.current_word = None
        self.time_left = 60
        self.timer_running = False
        
        # Round Settings
        self.max_rounds = 5
        self.current_round = 1
        self.round_time = 60
        
        # Player States
        self.username = "Player"
        self.players = {} # {username: score}
        
        # AI Model State
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_loaded = False
        
        # Network State
        self.network = PictionaryNetwork(self.on_network_message)
        self.is_multiplayer = False
        self.is_host = False
        
        self.show_loading_screen()
        threading.Thread(target=self.load_model_bg, daemon=True).start()
        self.check_loading_status()

    def show_loading_screen(self):
        self.loading_frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.loading_frame.pack(fill="both", expand=True)
        
        title = ctk.CTkLabel(self.loading_frame, text="Real-Time AI Pictionary", font=("Inter", 56, "bold"), text_color=ACCENT_BLUE)
        title.pack(expand=True, side="top", pady=(150, 10))
        
        self.loading_label = ctk.CTkLabel(self.loading_frame, text="Loading AI Engine into VRAM...", font=("Inter", 20), text_color=TEXT_COLOR)
        self.loading_label.pack(expand=True, side="top", pady=(0, 200))

    def load_model_bg(self):
        try:
            model = QuickDrawCNN(len(self.word_bank)).to(self.device)
            model.load_state_dict(torch.load("pictionary_model_v4.pth", map_location=self.device))
            model.eval()
            self.model = model
            print("Successfully loaded AI model (v4 - 200 classes).")
        except Exception as e:
            print(f"Failed to load AI model: {e}")
        finally:
            self.model_loaded = True

    def check_loading_status(self):
        if self.model_loaded:
            self.loading_frame.destroy()
            self.show_main_menu()
        else:
            text = self.loading_label.cget("text")
            if text.endswith("..."):
                self.loading_label.configure(text="Loading AI Engine into VRAM")
            else:
                self.loading_label.configure(text=text + ".")
            self.after(300, self.check_loading_status)

    def show_main_menu(self):
        self.menu_frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.menu_frame.pack(fill="both", expand=True)
        
        container = ctk.CTkFrame(self.menu_frame, fg_color=PANEL_COLOR, corner_radius=20)
        container.pack(expand=True, padx=50, pady=50)
        
        title = ctk.CTkLabel(container, text="AI Pictionary", font=("Inter", 64, "bold"), text_color=ACCENT_BLUE)
        title.pack(pady=(50, 30))
        
        self.name_entry = ctk.CTkEntry(container, placeholder_text="Enter Your Username", font=("Inter", 24), width=350, height=60, justify="center")
        self.name_entry.pack(pady=20)
        
        btn_single = ctk.CTkButton(container, text="Single Player", font=("Inter", 20, "bold"), height=55, width=350, fg_color=ACCENT_GREEN, hover_color="#27ae60", command=self.start_single_player)
        btn_single.pack(pady=10)
        
        btn_host = ctk.CTkButton(container, text="Host Multiplayer", font=("Inter", 20, "bold"), height=55, width=350, fg_color=ACCENT_YELLOW, text_color="black", hover_color="#f39c12", command=self.host_game)
        btn_host.pack(pady=10)
        
        join_frame = ctk.CTkFrame(container, fg_color="transparent")
        join_frame.pack(pady=10)
        self.ip_entry = ctk.CTkEntry(join_frame, placeholder_text="Host IP Address", font=("Inter", 20), width=240, height=55)
        self.ip_entry.pack(side="left", padx=(0, 10))
        btn_join = ctk.CTkButton(join_frame, text="Join", font=("Inter", 20, "bold"), height=55, width=100, fg_color=ACCENT_BLUE, hover_color="#2980b9", command=self.join_game)
        btn_join.pack(side="left")

        self.menu_status = ctk.CTkLabel(container, text="", font=("Inter", 16), text_color=ACCENT_RED)
        self.menu_status.pack(pady=(20, 40))

    def get_username(self):
        name = self.name_entry.get().strip()
        if not name:
            name = f"Player_{random.randint(1000,9999)}"
        return name

    def start_single_player(self):
        self.username = self.get_username()
        self.players = {self.username: 0}
        self.client_id_to_username = {}
        self.is_multiplayer = False
        self.max_rounds = 5
        self.round_time = 60
        self.current_round = 1
        self.menu_frame.destroy()
        self.setup_game_ui()
        self.start_new_round()
        self.run_inference_loop()

    def host_game(self):
        self.username = self.get_username()
        self.players = {self.username: 0}
        self.client_id_to_username = {}
        self.menu_status.configure(text="Starting server...", text_color=ACCENT_YELLOW)
        self.is_multiplayer = True
        self.is_host = True
        self.network.start_server(5555)
        self.show_waiting_room()

    def join_game(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            self.menu_status.configure(text="Please enter an IP address.", text_color=ACCENT_RED)
            return
        self.username = self.get_username()
        self.menu_status.configure(text=f"Connecting to {ip}...", text_color=ACCENT_YELLOW)
        self.is_multiplayer = True
        self.is_host = False
        
        def connect_task():
            success = self.network.connect_to_server(ip, 5555)
            if not success:
                self.after(0, lambda: self.menu_status.configure(text="Connection failed.", text_color=ACCENT_RED))
                
        threading.Thread(target=connect_task, daemon=True).start()

    def show_waiting_room(self):
        if hasattr(self, 'menu_frame'):
            self.menu_frame.destroy()
            
        self.wait_frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.wait_frame.pack(fill="both", expand=True)
        
        title = ctk.CTkLabel(self.wait_frame, text="Waiting Room", font=("Inter", 48, "bold"), text_color=ACCENT_BLUE)
        title.pack(pady=(20, 10))
        
        self.wait_status = ctk.CTkLabel(self.wait_frame, text="Connected!", font=("Inter", 20), text_color=ACCENT_GREEN)
        self.wait_status.pack(pady=5)
        
        if self.is_host:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
            ip_lbl = ctk.CTkLabel(self.wait_frame, text=f"Tell your friends to join: {local_ip}", font=("Inter", 24, "bold"), text_color=ACCENT_YELLOW)
            ip_lbl.pack(pady=5)
            
            # Host Settings Panel
            settings_frame = ctk.CTkFrame(self.wait_frame, fg_color=PANEL_COLOR, corner_radius=15)
            settings_frame.pack(pady=10, padx=20)
            
            ctk.CTkLabel(settings_frame, text="Game Settings", font=("Inter", 20, "bold"), text_color=TEXT_COLOR).pack(pady=(10, 5))
            
            self.rounds_var = tk.IntVar(value=5)
            rounds_lbl = ctk.CTkLabel(settings_frame, text=f"Rounds: {self.rounds_var.get()}", font=("Inter", 16))
            rounds_lbl.pack(pady=(5, 0))
            def update_rounds(val):
                self.rounds_var.set(int(val))
                rounds_lbl.configure(text=f"Rounds: {int(val)}")
            rounds_slider = ctk.CTkSlider(settings_frame, from_=1, to=20, number_of_steps=19, command=update_rounds)
            rounds_slider.set(5)
            rounds_slider.pack(padx=40, pady=5)
            
            self.time_var = tk.IntVar(value=60)
            time_lbl = ctk.CTkLabel(settings_frame, text=f"Time per Round: {self.time_var.get()}s", font=("Inter", 16))
            time_lbl.pack(pady=(5, 0))
            def update_time(val):
                self.time_var.set(int(val))
                time_lbl.configure(text=f"Time per Round: {int(val)}s")
            time_slider = ctk.CTkSlider(settings_frame, from_=30, to=120, number_of_steps=9, command=update_time)
            time_slider.set(60)
            time_slider.pack(padx=40, pady=10)
        
        self.player_list_frame = ctk.CTkScrollableFrame(self.wait_frame, width=400, height=150, fg_color=PANEL_COLOR, corner_radius=15)
        self.player_list_frame.pack(pady=10)
        
        self.update_player_list_ui()
        
        if self.is_host:
            start_btn = ctk.CTkButton(self.wait_frame, text="Start Game", font=("Inter", 24, "bold"), height=60, width=300, fg_color=ACCENT_GREEN, hover_color="#27ae60", command=self.host_start_game)
            start_btn.pack(pady=10)
        else:
            wait_lbl = ctk.CTkLabel(self.wait_frame, text="Waiting for host to start...", font=("Inter", 20, "italic"))
            wait_lbl.pack(pady=20)
            
        leave_btn = ctk.CTkButton(self.wait_frame, text="Leave / Back", font=("Inter", 20, "bold"), height=50, width=300, fg_color=ACCENT_RED, hover_color="#c0392b", command=self.leave_game)
        leave_btn.pack(pady=10)

    def update_player_list_ui(self):
        if hasattr(self, 'player_list_frame') and self.player_list_frame.winfo_exists():
            for widget in self.player_list_frame.winfo_children():
                widget.destroy()
            for player in self.players.keys():
                color = ACCENT_YELLOW if player == self.username else TEXT_COLOR
                lbl = ctk.CTkLabel(self.player_list_frame, text=f"• {player}", font=("Inter", 24), text_color=color)
                lbl.pack(pady=5, anchor="w", padx=20)

    def host_start_game(self):
        self.max_rounds = self.rounds_var.get()
        self.round_time = self.time_var.get()
        self.current_round = 1
        self.wait_frame.destroy()
        self.setup_game_ui()
        self.start_new_round()
        self.run_inference_loop()

    def end_game(self):
        if self.is_multiplayer and self.is_host:
            self.network.send({'type': 'GAME_OVER'})
        self.show_game_over()
        
    def show_game_over(self):
        self.timer_running = False
        if hasattr(self, 'main_container') and self.main_container.winfo_exists():
            self.main_container.destroy()
        if hasattr(self, 'header_frame') and self.header_frame.winfo_exists():
            self.header_frame.destroy()
            
        self.game_over_frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.game_over_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(self.game_over_frame, text="Game Over!", font=("Inter", 64, "bold"), text_color=ACCENT_RED).pack(pady=(100, 20))
        
        winner_name = max(self.players, key=self.players.get)
        winner_score = self.players[winner_name]
        
        ctk.CTkLabel(self.game_over_frame, text=f"Winner: {winner_name} with {winner_score} pts", font=("Inter", 36, "bold"), text_color=ACCENT_YELLOW).pack(pady=20)
        
        board_frame = ctk.CTkFrame(self.game_over_frame, fg_color=PANEL_COLOR, corner_radius=15)
        board_frame.pack(pady=30, padx=50)
        
        sorted_players = sorted(self.players.items(), key=lambda item: item[1], reverse=True)
        for i, (player, score) in enumerate(sorted_players):
            color = ACCENT_YELLOW if player == self.username else TEXT_COLOR
            ctk.CTkLabel(board_frame, text=f"{i+1}. {player} - {score} pts", font=("Inter", 24), text_color=color).pack(pady=5, padx=20)
            
        btn_menu = ctk.CTkButton(self.game_over_frame, text="Return to Main Menu", font=("Inter", 20, "bold"), height=50, command=self.return_to_menu)
        btn_menu.pack(pady=30)
        
    def return_to_menu(self):
        if self.is_multiplayer:
            self.network.close()
            self.network = PictionaryNetwork(self.on_network_message)
        self.game_over_frame.destroy()
        self.show_main_menu()

    def on_network_message(self, msg):
        self.after(0, self._process_network_message, msg)

    def _process_network_message(self, msg):
        mtype = msg.get('type')
        if mtype == 'CONNECTED_TO_SERVER':
            self.network.send({'type': 'JOIN_ROOM', 'username': self.username})
            self.show_waiting_room()
            
        elif mtype == 'JOIN_ROOM':
            if self.is_host:
                new_user = msg['username']
                original_user = new_user
                counter = 1
                while new_user in self.players:
                    new_user = f"{original_user}_{counter}"
                    counter += 1
                self.players[new_user] = 0
                if '_client_id' in msg:
                    self.client_id_to_username[msg['_client_id']] = new_user
                self.network.send({'type': 'ROOM_UPDATE', 'players': self.players})
                self.update_player_list_ui()
                self.update_leaderboard_ui()
                
        elif mtype == 'ROOM_UPDATE':
            if not self.is_host:
                if self.username not in msg['players'] and len(msg['players']) > len(self.players):
                    for name in msg['players']:
                        if name.startswith(self.username) and name not in self.players:
                            self.username = name
                            break
            self.players = msg['players']
            self.update_player_list_ui()
            self.update_leaderboard_ui()
            
        elif mtype == 'START_ROUND':
            if not self.is_host:
                if hasattr(self, 'wait_frame') and self.wait_frame.winfo_exists():
                    self.wait_frame.destroy()
                    self.setup_game_ui()
                    self.run_inference_loop()
                self.current_word = msg['word']
                self.time_left = msg['time']
                self.round_time = msg.get('round_time', 60)
                self.current_round = msg.get('current_round', 1)
                self.max_rounds = msg.get('max_rounds', 5)
                self.clear_canvas()
                
                self.word_label.configure(text=f"Round {self.current_round}/{self.max_rounds} | Word: {self.current_word}")
                self.timer_running = True
                self.update_timer()
                self.status_label.configure(text="Draw!", text_color=TEXT_COLOR)
                
        elif mtype == 'SCORE_UPDATE':
            if self.is_host:
                user = msg['username']
                self.players[user] = msg['score']
                self.network.send({'type': 'ROOM_UPDATE', 'players': self.players})
                self.update_leaderboard_ui()
                
        elif mtype == 'I_WON':
            if self.is_host:
                winner = msg['username']
                pts = msg['points']
                self.players[winner] += pts
                self.network.send({'type': 'ROOM_UPDATE', 'players': self.players})
                self.network.send({'type': 'PLAYER_WIN', 'username': winner, 'points': pts})
                
                self.update_leaderboard_ui()
                
                self.status_label.configure(text=f"{winner} guessed it!", text_color=ACCENT_RED)
                self.timer_running = False
                self.speak(f"{winner} won this round")
                self.after(3000, self.start_new_round)
                
        elif mtype == 'PLAYER_WIN':
            if not self.is_host:
                winner = msg['username']
                self.status_label.configure(text=f"{winner} guessed it! Round over.", text_color=ACCENT_RED)
                self.timer_running = False
                self.speak(f"{winner} won this round")
                
        elif mtype == 'GAME_OVER':
            if not self.is_host:
                self.show_game_over()
                
        elif mtype == 'CLIENT_DISCONNECTED':
            if self.is_host:
                cid = msg.get('_client_id')
                if cid and cid in self.client_id_to_username:
                    user_to_remove = self.client_id_to_username[cid]
                    if user_to_remove in self.players:
                        del self.players[user_to_remove]
                    del self.client_id_to_username[cid]
                    self.network.send({'type': 'ROOM_UPDATE', 'players': self.players})
                    self.update_player_list_ui()
                    self.update_leaderboard_ui()
                    
        elif mtype == 'DISCONNECTED_FROM_SERVER':
            if not self.is_host:
                self.leave_game()
                self.menu_status.configure(text="Disconnected from Host.", text_color=ACCENT_RED)

    def speak(self, text):
        if not self.speaker: return
        try:
            self.speaker.Speak(text, 1 | 2)
        except Exception:
            pass

    def setup_game_ui(self):
        self.header_frame = ctk.CTkFrame(self, height=80, fg_color=PANEL_COLOR, corner_radius=0)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)
        
        self.word_label = ctk.CTkLabel(self.header_frame, text=f"Round {self.current_round}/{self.max_rounds} | Word: Waiting...", font=("Inter", 32, "bold"), text_color=ACCENT_BLUE)
        self.word_label.pack(side="left", padx=30, pady=20)
        
        self.time_label = ctk.CTkLabel(self.header_frame, text="Time: 60s", font=("Inter", 32, "bold"), text_color=ACCENT_RED)
        self.time_label.pack(side="right", padx=30, pady=20)
        
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        if self.is_multiplayer:
            self.leaderboard_frame = ctk.CTkFrame(self.main_container, width=250, fg_color=PANEL_COLOR, corner_radius=15)
            self.leaderboard_frame.pack(side="left", fill="y", padx=(0, 20))
            self.leaderboard_frame.pack_propagate(False)
            
            ctk.CTkLabel(self.leaderboard_frame, text="Leaderboard", font=("Inter", 24, "bold"), text_color=ACCENT_YELLOW).pack(pady=(20, 10))
            self.leaderboard_content = ctk.CTkScrollableFrame(self.leaderboard_frame, fg_color="transparent")
            self.leaderboard_content.pack(fill="both", expand=True, padx=5, pady=5)
            self.update_leaderboard_ui()
        else:
            self.score_frame = ctk.CTkFrame(self.main_container, width=200, fg_color=PANEL_COLOR, corner_radius=15)
            self.score_frame.pack(side="left", fill="y", padx=(0, 20))
            self.score_frame.pack_propagate(False)
            ctk.CTkLabel(self.score_frame, text="Score", font=("Inter", 24, "bold"), text_color=ACCENT_GREEN).pack(pady=20)
            self.single_score_label = ctk.CTkLabel(self.score_frame, text="0", font=("Inter", 48, "bold"), text_color=TEXT_COLOR)
            self.single_score_label.pack(pady=20)
            
        self.canvas_container = ctk.CTkFrame(self.main_container, fg_color="#ffffff", corner_radius=15, border_width=4, border_color=ACCENT_BLUE)
        self.canvas_container.pack(side="left", fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.canvas_container, bg="white", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        
        self.canvas.bind("<ButtonPress-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.reset)
        
        # Keyboard Shortcuts
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)
        
        self.old_x, self.old_y = None, None
        self.color = "black"
        self.brush_size = 12
        self.eraser_size = 20
        self.active_tool = "brush"
        
        self.image = Image.new("RGB", (3000, 3000), "white")
        self.draw = ImageDraw.Draw(self.image)
        
        self.history = []
        self.stroke_history = []
        self.current_stroke_items = []
        
        self.toolbar_frame = ctk.CTkFrame(self.main_container, width=280, fg_color=PANEL_COLOR, corner_radius=15)
        self.toolbar_frame.pack(side="right", fill="y", padx=(20, 0))
        self.toolbar_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.toolbar_frame, text="Colors", font=("Inter", 20, "bold")).pack(pady=(20, 10))
        
        colors = ["black", "red", "green", "blue", "yellow", "orange", "purple", "white"]
        color_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        color_frame.pack(pady=5)
        for i, c in enumerate(colors):
            btn = tk.Button(color_frame, bg=c, activebackground=c, width=3, height=1, relief="flat", bd=1, command=lambda col=c: self.change_color(col))
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)
            
        ctk.CTkLabel(self.toolbar_frame, text="Brush Size", font=("Inter", 18, "bold")).pack(pady=(20, 5))
        self.size_slider = ctk.CTkSlider(self.toolbar_frame, from_=1, to=20, command=self.change_size, button_color=ACCENT_BLUE)
        self.size_slider.set(self.brush_size)
        self.size_slider.pack(padx=20)
        
        ctk.CTkLabel(self.toolbar_frame, text="Eraser Size", font=("Inter", 18, "bold")).pack(pady=(20, 5))
        self.eraser_slider = ctk.CTkSlider(self.toolbar_frame, from_=5, to=50, command=self.change_eraser_size)
        self.eraser_slider.set(self.eraser_size)
        self.eraser_slider.pack(padx=20)
        
        ctk.CTkLabel(self.toolbar_frame, text="Tools", font=("Inter", 20, "bold")).pack(pady=(30, 10))
        tools_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        tools_frame.pack()
        
        ctk.CTkButton(tools_frame, text="Brush", width=90, fg_color=ACCENT_BLUE, command=self.use_brush).grid(row=0, column=0, padx=5)
        ctk.CTkButton(tools_frame, text="Eraser", width=90, fg_color="#7f8c8d", hover_color="#95a5a6", command=self.use_eraser).grid(row=0, column=1, padx=5)
        
        ctk.CTkButton(tools_frame, text="Undo", width=190, fg_color=ACCENT_YELLOW, text_color="black", hover_color="#f39c12", command=self.undo).grid(row=1, column=0, columnspan=2, pady=10)
        
        ctk.CTkLabel(self.toolbar_frame, text="Actions", font=("Inter", 20, "bold")).pack(pady=(20, 10))
        ctk.CTkButton(self.toolbar_frame, text="Clear Canvas", fg_color=ACCENT_RED, hover_color="#c0392b", command=self.clear_canvas).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.toolbar_frame, text="Submit/Guess", fg_color=ACCENT_GREEN, hover_color="#27ae60", command=self.submit_drawing).pack(pady=5, padx=20, fill="x")
        
        skip_btn = ctk.CTkButton(self.toolbar_frame, text="Skip Word", fg_color=ACCENT_YELLOW, text_color="black", hover_color="#f39c12", command=self.skip_word)
        skip_btn.pack(pady=5, padx=20, fill="x")
        if self.is_multiplayer:
            skip_btn.configure(state="disabled", fg_color="#555", text_color="#aaa")
            
        leave_btn = ctk.CTkButton(self.toolbar_frame, text="Leave Game", fg_color=ACCENT_RED, hover_color="#c0392b", command=self.leave_game)
        leave_btn.pack(pady=5, padx=20, fill="x")
        
        self.status_label = ctk.CTkLabel(self.toolbar_frame, text="AI is waiting...", font=("Inter", 16, "italic"), text_color="#bdc3c7")
        self.status_label.pack(side="bottom", pady=20)

    def update_leaderboard_ui(self):
        if not hasattr(self, 'leaderboard_content') or not self.leaderboard_content.winfo_exists():
            if hasattr(self, 'single_score_label') and self.single_score_label.winfo_exists():
                self.single_score_label.configure(text=str(self.players.get(self.username, 0)))
            return
            
        for widget in self.leaderboard_content.winfo_children():
            widget.destroy()
            
        sorted_players = sorted(self.players.items(), key=lambda item: item[1], reverse=True)
        
        for i, (player, score) in enumerate(sorted_players):
            color = ACCENT_YELLOW if player == self.username else TEXT_COLOR
            medal = "🏆 " if i == 0 and score > 0 else "   "
            lbl = ctk.CTkLabel(self.leaderboard_content, text=f"{medal}{player}\n{score} pts", font=("Inter", 18, "bold"), text_color=color, justify="left")
            lbl.pack(pady=10, anchor="w", padx=10)

    def start_stroke(self, event):
        self.old_x = event.x
        self.old_y = event.y
        self.current_stroke_items = []
        if len(self.history) > 15:
            self.history.pop(0)
            self.stroke_history.pop(0)
        self.history.append(self.image.copy())

    def paint(self, event):
        active_color = 'white' if self.active_tool == 'eraser' else self.color
        active_size = self.eraser_size if self.active_tool == 'eraser' else self.brush_size

        if self.old_x and self.old_y:
            # Interpolate intermediate points
            steps = max(1, int(((event.x - self.old_x)**2 + (event.y - self.old_y)**2) ** 0.5 / 3))
            for i in range(steps + 1):
                t = i / steps
                x = int(self.old_x + t * (event.x - self.old_x))
                y = int(self.old_y + t * (event.y - self.old_y))
                r = active_size // 2
                item_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=active_color, outline="")
                self.current_stroke_items.append(item_id)
                self.draw.ellipse([x-r, y-r, x+r, y+r], fill=active_color)
                            
        self.old_x = event.x
        self.old_y = event.y

    def reset(self, event):
        self.old_x, self.old_y = None, None
        if hasattr(self, 'current_stroke_items') and self.current_stroke_items:
            self.stroke_history.append(self.current_stroke_items)
            self.current_stroke_items = []
            
    def undo(self, event=None):
        if not hasattr(self, 'history') or not hasattr(self, 'stroke_history'):
            return
        if not self.history or not self.stroke_history:
            return
        self.image = self.history.pop()
        self.draw = ImageDraw.Draw(self.image)
        items_to_remove = self.stroke_history.pop()
        for item in items_to_remove:
            self.canvas.delete(item)

    def leave_game(self):
        self.timer_running = False
        if self.is_multiplayer:
            self.network.close()
            self.network = PictionaryNetwork(self.on_network_message)
        
        if hasattr(self, 'wait_frame') and self.wait_frame.winfo_exists():
            self.wait_frame.destroy()
        if hasattr(self, 'main_container') and self.main_container.winfo_exists():
            self.main_container.destroy()
        if hasattr(self, 'header_frame') and self.header_frame.winfo_exists():
            self.header_frame.destroy()
            
        self.show_main_menu()

    def change_color(self, new_color):
        self.color = new_color
        if self.active_tool == 'eraser':
            self.use_brush()

    def change_size(self, val):
        self.brush_size = int(val)

    def change_eraser_size(self, val):
        self.eraser_size = int(val)
        
    def use_brush(self):
        self.active_tool = 'brush'
        self.canvas.config(cursor="cross")
        
    def use_eraser(self):
        self.active_tool = 'eraser'
        self.canvas.config(cursor="dotbox")

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (3000, 3000), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.history = []
        self.stroke_history = []
        self.current_stroke_items = []
        self.status_label.configure(text="Canvas Cleared", text_color="#bdc3c7")
        
    def start_new_round(self):
        self.clear_canvas()
        if self.is_host or not self.is_multiplayer:
            if self.current_round > self.max_rounds:
                self.end_game()
                return
                
            self.current_word = random.choice(self.word_bank).capitalize()
            self.time_left = self.round_time
            if self.is_multiplayer:
                self.network.send({
                    'type': 'START_ROUND', 
                    'word': self.current_word, 
                    'time': self.time_left,
                    'round_time': self.round_time,
                    'current_round': self.current_round,
                    'max_rounds': self.max_rounds
                })
            
            self.current_round += 1
        
        # UI update for both Host and Single Player
        if hasattr(self, 'word_label') and self.word_label.winfo_exists():
            round_display = self.current_round - 1 if (self.is_host or not self.is_multiplayer) else self.current_round
            self.word_label.configure(text=f"Round {round_display}/{self.max_rounds} | Word: {self.current_word}")
            self.time_label.configure(text=f"Time: {self.time_left}s", text_color=ACCENT_RED)
            self.status_label.configure(text="Draw!", text_color=TEXT_COLOR)
        
        self.last_spoken_guess = None
        self.speak(f"Please draw {self.current_word}")
        
        self.timer_running = True
        self.use_brush()
        self.update_timer()

    def run_inference_loop(self):
        if self.timer_running and self.time_left > 0:
            if not getattr(self, 'is_inferencing', False):
                self.is_inferencing = True
                img_copy = self.image.copy()
                threading.Thread(target=self.predict_drawing_bg, args=(img_copy, False), daemon=True).start()
        self.after(1000, self.run_inference_loop)

    def predict_drawing_bg(self, img_copy, manual_submit=False):
        try:
            img_gray = ImageOps.grayscale(img_copy)
            bbox = ImageOps.invert(img_gray).getbbox()
            if not bbox:
                self.after(0, self.handle_prediction_result, None, 0.0, 0.0, manual_submit)
                return
                
            x1, y1, x2, y2 = bbox
            pad = int(max(x2 - x1, y2 - y1) * 0.1)
            x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
            x2, y2 = min(img_gray.width, x2 + pad), min(img_gray.height, y2 + pad)
            bbox = (x1, y1, x2, y2)
                
            img_cropped = img_gray.crop(bbox)
            max_dim = max(img_cropped.size)
            img_square = Image.new("L", (max_dim, max_dim), "white")
            offset = ((max_dim - img_cropped.size[0]) // 2, (max_dim - img_cropped.size[1]) // 2)
            img_square.paste(img_cropped, offset)
            
            img_inverted = ImageOps.invert(img_square)
            img_255 = img_inverted.resize((255, 255), Image.Resampling.BILINEAR)
            img_dilated = img_255.filter(ImageFilter.MaxFilter(9))
            img_resized = img_dilated.resize((28, 28), Image.Resampling.LANCZOS)
            
            img_array = np.array(img_resized, dtype=np.float32)
            max_val = np.max(img_array)
            if max_val > 0:
                img_array = (img_array / max_val) * 255.0
                
            img_array = img_array / 255.0
            tensor = torch.tensor(img_array).unsqueeze(0).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
                top_prob, top_idx = torch.max(probabilities, 0)
                confidence = top_prob.item() * 100
                guess = self.word_bank[top_idx.item()].capitalize()
                
                # Dynamic Confidence Calculation
                time_passed = self.round_time - self.time_left
                if time_passed < self.round_time / 3:
                    required_conf = 80.0
                elif time_passed < (2 * self.round_time) / 3:
                    required_conf = 70.0
                else:
                    required_conf = 60.0
                
                self.after(0, self.handle_prediction_result, guess, confidence, required_conf, manual_submit)
        except Exception as e:
            print(f"Inference error: {e}")
        finally:
            self.is_inferencing = False

    def handle_prediction_result(self, guess, confidence, required_conf, manual_submit):
        if not self.timer_running: return
        
        if guess is None:
            if manual_submit:
                self.status_label.configure(text="Draw something before submitting!", text_color=ACCENT_RED)
            else:
                self.status_label.configure(text="Draw something!", text_color="#bdc3c7")
            return
            
        self.status_label.configure(text=f"AI guess: {guess} ({confidence:.1f}% / Req: {required_conf}%)", text_color=ACCENT_YELLOW)
        
        if confidence > 30.0 and guess != self.last_spoken_guess:
            self.speak(f"I see {guess}")
            self.last_spoken_guess = guess
        
        if manual_submit:
            if guess == self.current_word:
                self.process_win()
            else:
                self.players[self.username] = max(0, self.players.get(self.username, 0) - 10)
                self.update_leaderboard_ui()
                self.status_label.configure(text=f"AI guessed '{guess}'. -10 pts.", text_color=ACCENT_RED)
                if self.is_multiplayer:
                    if self.is_host:
                        self.network.send({'type': 'ROOM_UPDATE', 'players': self.players})
                    else:
                        self.network.send({'type': 'SCORE_UPDATE', 'username': self.username, 'score': self.players[self.username]})
        else:
            if guess == self.current_word and confidence >= required_conf:
                self.process_win()

    def update_timer(self):
        if not self.timer_running:
            return
            
        if self.time_left > 0:
            self.time_left -= 1
            self.time_label.configure(text=f"Time: {self.time_left}s")
            self.after(1000, self.update_timer)
        else:
            self.timer_running = False
            self.status_label.configure(text="Time's up!", text_color=ACCENT_RED)
            self.time_label.configure(text="Time: 0s", text_color=ACCENT_RED)
            if self.is_host or not self.is_multiplayer:
                self.after(2000, self.start_new_round)

    def submit_drawing(self):
        if not self.timer_running: return
        if getattr(self, 'is_inferencing', False): return
        
        self.is_inferencing = True
        img_copy = self.image.copy()
        threading.Thread(target=self.predict_drawing_bg, args=(img_copy, True), daemon=True).start()

    def process_win(self):
        points_earned = self.time_left * 10 
        self.players[self.username] = self.players.get(self.username, 0) + points_earned
        self.update_leaderboard_ui()
        self.status_label.configure(text=f"WIN! +{points_earned} pts", text_color=ACCENT_GREEN)
        
        self.speak(f"Got it! That's {self.current_word}")
        
        self.timer_running = False
        
        if self.is_multiplayer:
            if self.is_host:
                self.network.send({'type': 'ROOM_UPDATE', 'players': self.players})
                self.network.send({'type': 'PLAYER_WIN', 'username': self.username, 'points': points_earned})
                self.after(3000, self.start_new_round)
            else:
                self.network.send({'type': 'I_WON', 'username': self.username, 'points': points_earned})
        else:
            self.after(3000, self.start_new_round)

    def skip_word(self):
        if not self.timer_running: return
        if self.is_multiplayer: return # Disabled in UI
        self.status_label.configure(text="Word Skipped! -50 pts", text_color=ACCENT_RED)
        self.players[self.username] = max(0, self.players.get(self.username, 0) - 50)
        self.update_leaderboard_ui()
        
        self.speak("Skipped word")
        self.timer_running = False
        if self.is_host or not self.is_multiplayer:
            self.after(1000, self.start_new_round)

    def destroy(self):
        self.network.close()
        super().destroy()

if __name__ == "__main__":
    app = AIPictionaryApp()
    app.mainloop()
