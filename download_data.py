import os
import urllib.request
import urllib.parse
from tqdm import tqdm

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_quickdraw_data(categories, output_dir="data"):
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    base_url = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"
    
    for category in categories:
        # URL encode the category name (e.g., "ice cream" -> "ice%20cream" if we ever have spaces)
        encoded_category = urllib.parse.quote(category)
        file_url = f"{base_url}{encoded_category}.npy"
        output_path = os.path.join(output_dir, f"{category}.npy")
        
        # Check if the dataset already exists
        if os.path.exists(output_path):
            print(f"Dataset for '{category}' already exists. Skipping...")
            continue
            
        print(f"Downloading dataset for '{category}'...")
        try:
            with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=category) as t:
                urllib.request.urlretrieve(file_url, filename=output_path, reporthook=t.update_to)
        except Exception as e:
            print(f"Failed to download {category}. Error: {e}")

if __name__ == "__main__":
    word_bank = [
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
    
    # Sort alphabetically to guarantee label mapping consistency later
    word_bank.sort()
    
    print(f"Starting Quick, Draw! dataset downloads for {len(word_bank)} categories...")
    download_quickdraw_data(word_bank)
    print("\nDownload process complete. Verifying files...")
    
    # Verification
    missing_files = []
    for word in word_bank:
        if not os.path.exists(os.path.join("data", f"{word}.npy")):
            missing_files.append(word)
            
    if missing_files:
        print(f"Warning: Missing files for {missing_files}")
    else:
        print(f"Success! All {len(word_bank)} dataset files have been downloaded and verified.")
