import pandas as pd
from datasets import load_dataset
import random
import os

# Load the All Beauty category from the Amazon-Reviews-2023 dataset
print("Loading the All Beauty category from McAuley-Lab/Amazon-Reviews-2023 dataset...")
dataset = load_dataset("McAuley-Lab/Amazon-Reviews-2023", "raw_review_Handmade_Products", trust_remote_code=True)

# Print the first sample to confirm the structure
print("\nSample review:")
print(dataset["full"][0])

# Get dataset information
print(f"\nDataset loaded. Total samples in 'full' split: {len(dataset['full'])}")

def extract_and_save_text_reviews(dataset, train_size=25000, test_size=5000, output_dir="./"):

    # Get the 'full' split which contains all reviews
    full_dataset = dataset["full"]
        
    # Get all indices and shuffle them
    all_indices = list(range(len(full_dataset)))
    random.shuffle(all_indices)
    
    # Split indices for train and test
    train_indices = all_indices[:train_size]
    test_indices = all_indices[train_size:train_size+test_size]
    
    # Create train dataframe
    train_samples = full_dataset.select(train_indices)
    train_texts = [item["text"] for item in train_samples]  # Using "text" as the field name
    train_df = pd.DataFrame({
        'review_text': train_texts
    })
    
    # Create test dataframe
    test_samples = full_dataset.select(test_indices)
    test_texts = [item["text"] for item in test_samples]  # Using "text" as the field name
    test_df = pd.DataFrame({
        'review_text': test_texts
    })
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to CSV files
    train_path = os.path.join(output_dir, "amazon_handmade_train.csv")
    test_path = os.path.join(output_dir, "amazon_handmade_test.csv")
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    print(f"Successfully saved {len(train_df)} training reviews to {train_path}")
    print(f"Successfully saved {len(test_df)} testing reviews to {test_path}")
    
    return train_df, test_df

# Extract and save text reviews to train and test CSV files
train_df, test_df = extract_and_save_text_reviews(
    dataset, 
    train_size=25000, 
    test_size=5000,
    output_dir="./"
)