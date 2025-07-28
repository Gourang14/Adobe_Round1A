# src/extract_outline.py (updated to handle empty outlines and invalid PDFs)
import json
import os
import time
import traceback
from pdf_utils import load_pdf, extract_text_blocks, calculate_document_stats, extract_title, build_outline
from multiprocess import Pool

def flatten_outline(outline):
    """Flatten nested outline to list if needed (for flat JSON spec)."""
    flat = []
    for entry in outline:
        flat.append(entry)  # Add parent
        flat.extend(flatten_outline(entry.get('children', [])))  # Recurse children
        entry.pop('children', None)  # Remove nesting for output
    return flat

def process_single_pdf(args):
    filename, input_dir, output_dir = args
    try:
        pdf_path = os.path.join(input_dir, filename)
        doc = load_pdf(pdf_path)
        blocks = extract_text_blocks(doc)
        stats = calculate_document_stats(blocks)
        title = extract_title(blocks)
        outline = build_outline(blocks, stats)
        if outline:  # Check if not empty before accessing [0]
            flat_outline = flatten_outline(outline) if (len(outline) > 0 and isinstance(outline[0], dict) and 'children' in outline[0]) else outline
        else:
            flat_outline = []  # Empty outline fallback
        output = {"title": title, "outline": flat_outline}
        json_filename = filename.replace('.pdf', '.json')
        with open(os.path.join(output_dir, json_filename), 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
        doc.close()
        return f"Processed {filename} (Headings found: {len(flat_outline)})"
    except Exception as e:
        return f"Error processing {filename}: {str(e)} - {traceback.format_exc()} (Skipping invalid PDF)"

def process_all_pdfs(input_dir, output_dir):
    start_time = time.time()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No PDFs found in input/.")
        return
    processes = max(1, os.cpu_count() // 2)
    with Pool(processes=processes) as pool:
        results = pool.map(process_single_pdf, [(f, input_dir, output_dir) for f in pdf_files])
    total_headings = 0
    for res in results:
        print(res)
        if "Headings found" in res:
            total_headings += int(res.split("Headings found: ")[1].split(")")[0])
    print(f"Total headings found: {total_headings}")
    print(f"Total processing time: {time.time() - start_time:.2f} seconds")

if __name__ == '__main__':
    process_all_pdfs('input/', 'output/')
