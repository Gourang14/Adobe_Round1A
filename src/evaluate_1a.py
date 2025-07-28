# src/evaluate_1a.py
import json
import os

def compute_precision_recall(your_json, gt_json):
    """
    Safely computes precision and recall.
    Handles cases where 'outline' key is missing or not a list.
    """
    your_outline_list = your_json.get('outline', [])
    gt_outline_list = gt_json.get('outline', [])

    # Ensure the items are dicts with 'text' keys before creating sets
    your_outline = set(o['text'] for o in your_outline_list if isinstance(o, dict) and 'text' in o)
    gt_outline = set(o['text'] for o in gt_outline_list if isinstance(o, dict) and 'text' in o)
    
    true_pos = len(your_outline.intersection(gt_outline))
    
    precision = true_pos / len(your_outline) if your_outline else 0
    recall = true_pos / len(gt_outline) if gt_outline else 0
    
    return precision, recall

# --- Main script ---
gt_dir = 'samples/ground_truth/'
output_dir = 'output/'

for i in range(1, 6):
    filename = f'file{i:02d}.json'  # e.g., file01.json
    output_filepath = os.path.join(output_dir, filename)
    gt_filepath = os.path.join(gt_dir, filename)

    # 1. Check if the generated output file exists. If not, skip it.
    if not os.path.exists(output_filepath):
        print(f"Warning: Output file not found, skipping: {output_filepath}")
        continue # Move to the next iteration of the loop
    
    # 2. Use a try/except block to handle other potential errors
    try:
        with open(output_filepath, 'r') as f_your:
            your_data = json.load(f_your)
        
        with open(gt_filepath, 'r') as f_gt:
            gt_data = json.load(f_gt)
            
        p, r = compute_precision_recall(your_data, gt_data)
        print(f"{filename}: Precision={p:.2f}, Recall={r:.2f}")

    except FileNotFoundError:
        # This handles the case where the ground truth file is missing
        print(f"Warning: Ground truth file not found, skipping evaluation for {filename}")
    except json.JSONDecodeError:
        # This handles files that are empty or not valid JSON
        print(f"Warning: Failed to read {filename} as JSON. File may be corrupt. Skipping.")