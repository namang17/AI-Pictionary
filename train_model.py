import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt


# ==========================================
# Hyperparameters & Settings
# ==========================================
BATCH_SIZE = 512
EPOCHS = 50
MAX_ITEMS_PER_CLASS = 15000
DATA_DIR = "data"

CATEGORIES = [
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
CATEGORIES.sort()
NUM_CLASSES = len(CATEGORIES)

# ==========================================
# Model Definition
# ==========================================
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

# ==========================================
# Main Processing & Training
# ==========================================
def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # 1. Load Data Securely (CPU)
    data_list = []
    label_list = []

    print("Loading raw dataset into memory...")
    for idx, category in enumerate(CATEGORIES):
        file_path = os.path.join(DATA_DIR, f"{category}.npy")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Missing data file: {file_path}")

        # Memory map to avoid RAM crashing
        class_data = np.load(file_path, mmap_mode='r')
        class_data = class_data[:MAX_ITEMS_PER_CLASS].copy()

        data_list.append(class_data)
        label_list.extend([idx] * len(class_data))

    # Combine all and reshape to (N, 1, 28, 28)
    all_data_np = np.vstack(data_list).reshape(-1, 1, 28, 28)
    all_labels_np = np.array(label_list)

    # 2. Global Shuffle before Splitting
    print("Shuffling and splitting dataset...")
    num_samples = len(all_labels_np)
    shuffle_idx = np.random.permutation(num_samples)

    all_data_np = all_data_np[shuffle_idx]
    all_labels_np = all_labels_np[shuffle_idx]

    train_size = int(0.8 * num_samples)

    # 3. Push Directly to GPU VRAM as uint8
    print("Pushing entire dataset to GPU VRAM...")
    train_data = torch.tensor(all_data_np[:train_size], dtype=torch.uint8, device=device)
    train_labels = torch.tensor(all_labels_np[:train_size], dtype=torch.long, device=device)

    val_data = torch.tensor(all_data_np[train_size:], dtype=torch.uint8, device=device)
    val_labels = torch.tensor(all_labels_np[train_size:], dtype=torch.long, device=device)

    # Free up system RAM
    del all_data_np, all_labels_np, data_list, label_list

    print(f"Training set size: {len(train_labels)}")
    print(f"Validation set size: {len(val_labels)}")

    # 4. Initialize Model, Loss, Optimizer
    model = QuickDrawCNN(NUM_CLASSES).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=3
    )

    # GPU-Native Batched Transforms
    gpu_transform = transforms.Compose([
        transforms.RandomRotation(15),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
    ])

    # 5. Native GPU Training Loop
    print("\nStarting Fast GPU Training...")
    best_val_loss = float('inf')
    patience = 5
    patience_counter = 0

    history_train_loss = []
    history_val_loss = []
    history_val_acc = []

    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0

        # Fast GPU shuffling: Create an array of random indices directly on the GPU
        rand_indices = torch.randperm(train_size, device=device)

        # Calculate number of batches for tqdm
        num_batches = (train_size + BATCH_SIZE - 1) // BATCH_SIZE
        train_bar = tqdm(range(num_batches), desc=f"Epoch {epoch+1}/{EPOCHS} [Train]")

        for i in train_bar:
            # Slice batch indices
            start_idx = i * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, train_size)
            batch_idx = rand_indices[start_idx:end_idx]

            # Fetch entire batch instantly on GPU, cast, and normalize
            inputs = train_data[batch_idx].float() / 255.0
            labels = train_labels[batch_idx]

            # Apply augmentations to the whole batch instantly
            inputs = gpu_transform(inputs)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            train_loss += loss.item() * inputs.size(0)
            train_bar.set_postfix(loss=loss.item())

        train_loss /= train_size

        # Validation Loop
        model.eval()
        val_loss = 0.0
        correct = 0

        with torch.no_grad():
            num_val_batches = (len(val_labels) + BATCH_SIZE - 1) // BATCH_SIZE
            for i in range(num_val_batches):
                start_idx = i * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, len(val_labels))

                # Fetch validation batch
                inputs = val_data[start_idx:end_idx].float() / 255.0
                labels = val_labels[start_idx:end_idx]

                outputs = model(inputs)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * inputs.size(0)
                _, predicted = torch.max(outputs.data, 1)
                correct += (predicted == labels).sum().item()

        val_loss /= len(val_labels)
        val_acc = 100 * correct / len(val_labels)

        history_train_loss.append(train_loss)
        history_val_loss.append(val_loss)
        history_val_acc.append(val_acc)

        print(f"Epoch {epoch+1} Results -> Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%")

        scheduler.step(val_loss)

        # --- Early Stopping & Model Saving Logic ---
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0  # Reset counter since we found a better model

            torch.save(model.state_dict(), "pictionary_model_v4.pth")
            print(f"  [*] Saved new best model to pictionary_model_v4.pth")
        else:
            patience_counter += 1
            print(f"  [!] No improvement in validation loss for {patience_counter} epoch(s).")

            if patience_counter >= patience:
                print(f"\n[🛑] Early stopping triggered at epoch {epoch+1}!")
                print(f"Halted training to prevent overfitting. Best weights are already saved.")
                break # Exit the training loop entirely

    print("\nTraining complete. Generating plots...")
    epochs_range = range(1, len(history_train_loss) + 1)
    plt.figure(figsize=(12, 5))

    # Plot Loss
    plt.subplot(1, 2, 1)
    plt.plot(epochs_range, history_train_loss, label='Train Loss')
    plt.plot(epochs_range, history_val_loss, label='Val Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    # Plot Accuracy
    plt.subplot(1, 2, 2)
    plt.plot(epochs_range, history_val_acc, label='Val Accuracy', color='green')
    plt.title('Validation Accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy (%)')
    plt.legend()

    plt.tight_layout()
    plt.savefig('training_history.png')
    plt.close()
    print("Saved training history plot to 'training_history.png'.")

if __name__ == "__main__":
    main()
