# Real-Time AI Pictionary - MultiPlayer Edition

A modern, fast-paced, real-time multiplayer Pictionary game where your opponent is a Neural Network! Draw the given word on the canvas and race against the clock (and other players) to see who can get the AI to guess their drawing first.

## Features

- **N-Player Hub-and-Spoke Multiplayer:** Host a game and let an unlimited number of friends join over your local network. The host acts as the server, flawlessly syncing scores, waiting rooms, and rounds.
- **Real-Time PyTorch AI Inference:** The game uses a custom CNN trained on Google's QuickDraw dataset (200 classes) to guess your drawings in real-time. Inference is fully multi-threaded, ensuring your drawing experience remains buttery smooth.
- **Dynamic AI Acceptance:** The AI dynamically drops its required confidence threshold as time runs out (from 80% to 70% to 60%), making it easier to score as the clock ticks down!
- **Customizable Game Settings:** Hosts can easily adjust the number of rounds (1-20) and the time per round (30-120 seconds) directly from the Waiting Room UI.
- **Premium Dark Mode UI:** Built using `customtkinter`, featuring glassmorphism elements, vibrant accents, real-time dynamic leaderboards, and an elegant Waiting Room.
- **Quality of Life Tools:** Features a brush, an eraser, an undo button (or `Ctrl+Z`), and 8 color choices.
- **Text-to-Speech Integration:** Windows SAPI is utilized to vocalize the AI's guesses in real-time, bringing the game to life.

## Prerequisites

Ensure you have Python 3.8+ installed. You can install all required dependencies by running:

```bash
pip install -r requirements.txt
```

### Core Dependencies
- `customtkinter` (Modern UI framework)
- `torch` & `torchvision` (AI Inference engine)
- `Pillow` (Image manipulation)
- `numpy` (Array processing)
- `pywin32` (Windows Text-to-Speech)

*Note: The game requires the pre-trained model file `pictionary_model_v4.pth` to be located in the same directory as the script.*

## How to Play

### Starting the Application
Simply run the main script to launch the application:
```bash
python main.py
```

### Game Modes
1. **Single Player:** Practice your drawing skills against the AI without any networking.
2. **Host Multiplayer:** Start a server on your machine. You'll be placed in a Waiting Room where your local IP address is displayed. Tell your friends to enter this IP to join!
3. **Join Game:** Enter a Host's IP address to instantly connect to their Waiting Room.

### Gameplay Rules
- A random word is assigned at the start of each round.
- Everyone draws simultaneously on their own screen.
- If the AI confidently guesses your drawing before time runs out, you win the round! 
- **Points Awarded:** `10 points × Time Remaining`
- **Manual Submission:** You can manually ask the AI to guess by clicking "Submit/Guess". However, if the AI is wrong, you will lose **10 points**.
- The player with the most points at the end of the final round wins the game!

## Architecture

- **`main.py`**: The core application housing the Tkinter game loop, PyTorch inference thread, and Canvas rendering logic.
- **`network.py`**: Handles all TCP socket networking. Implements a robust JSON-based protocol allowing the Host to broadcast `ROOM_UPDATE`, `START_ROUND`, and `PLAYER_WIN` packets.
- **`train_model.py`**: The training script used to generate the `.pth` model from raw `.npy` QuickDraw datasets. 

## Troubleshooting

- **UI Freezing:** Ensure you have the latest version of the code where AI inference is successfully offloaded to a daemon thread.
- **Can't Connect:** Ensure all players are on the same WiFi/Local Network. The Host might need to allow Python through their Windows Defender Firewall.
- **No Sound:** Text-to-Speech is restricted to Windows OS environments using `pywin32`. If you are on Linux/Mac, the game will still run perfectly, just without audio.
