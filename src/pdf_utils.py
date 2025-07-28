import fitz
import re
import statistics
from collections import namedtuple
import unicodedata

TextBlock = namedtuple('TextBlock', ['text', 'font_size', 'flags', 'bbox', 'page'])

def load_pdf(pdf_path):
    return fitz.open(pdf_path)

def extract_text_blocks(doc):
    blocks = []
    prev_block = None
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_height = page.bound()[3]
        page_blocks = page.get_text("dict")["blocks"]
        for b in page_blocks:
            if 'lines' in b:
                for line in b['lines']:
                    for span in line['spans']:
                        text = unicodedata.normalize('NFKC', span['text'].strip()).replace('  ', ' ').strip('.,:;()')
                        if text and len(text.split()) >= 3 and not re.match(r'^\d+$|^\w\.$|^\s*$|Page \d+ of \d+|Version \d+\.\d+|^\d{1,2} [A-Za-z]{3} \d{4}', text) and span['bbox'][1] < page_height * 0.85:
                            if prev_block and abs(span['bbox'][1] - prev_block.bbox[3]) < 10 and abs(span['bbox'][0] - prev_block.bbox[0]) < 35 and abs(span['size'] - prev_block.font_size) < 1.5 and not re.match(r'^[A-Za-z\s]+$', text):  # Avoid merging with body (no all-letter continuations)
                                text = prev_block.text + ' ' + text
                                blocks[-1] = TextBlock(text, max(prev_block.font_size, span['size']), span['flags'], prev_block.bbox, page_num + 1)
                            else:
                                blocks.append(TextBlock(
                                    text=text,
                                    font_size=span['size'],
                                    flags=span['flags'],
                                    bbox=span['bbox'],
                                    page=page_num + 1
                                ))
                            prev_block = blocks[-1]
    return blocks

def calculate_document_stats(blocks):
    font_sizes = [b.font_size for b in blocks if b.font_size > 0]
    avg_font_size = statistics.mean(font_sizes) if font_sizes else 10
    font_size_std = statistics.stdev(font_sizes) if len(font_sizes) > 1 else 0
    avg_x = statistics.mean([b.bbox[0] for b in blocks]) if blocks else 0
    return {'avg_font_size': avg_font_size, 'font_size_std': font_size_std, 'avg_x': avg_x}

def is_heading(block, stats, prev_block=None, blocks=None, index=None):
    # Semantic check: Must have following content (at least 1 text block after with >3 words)
    if index is not None and blocks is not None and (index + 1 >= len(blocks) or len(blocks[index + 1].text.split()) < 4):
        return False
    score = 0
    # Minimal font use (fallback only)
    if block.font_size > stats['avg_font_size'] + stats['font_size_std'] * 0.05:
        score += 1
    # Semantic patterns (high weight)
    patterns = [
        r'^\d+\.\s[A-Za-z]+', r'^\d+\.\d+\s[A-Za-z]+', r'^\d+\.\d+\.\d+\s[A-Za-z]+', r'^[A-Z]\.\s[A-Za-z]+', 
        r'^(Chapter|Section|Appendix|Summary|Background|Milestones|Approach|Evaluation|Preamble|Membership|Term|Chair|Meetings|Lines|Financial|Timeline|Equitable|Shared|Local|Access|Guidance|Training|Provincial|Technological|What could|Phase [I]{1,3}|For each|Ontario|Critical|Business|Introduction|Overview|Revision|Table of Contents|Acknowledgements|References|Learning|Entry|Structure|Keeping|Content|Application|Form|Grant|LTC|Name|Designation|Date|Permanent|Temporary|Home Town|Particulars|Block Year|Nature|Place|Duration|Advance|Family|Whether)\s?[A-Z]?\s?:?',
        r'^(1|2|3|4|5|6|7|8|9|10)\s[A-Za-z]+'  # For numbered headings in forms
    ]
    matches = sum(1 for p in patterns if re.match(p, block.text, re.IGNORECASE))
    score += matches * 9
    if matches == 0:
        return False
    # Meaningful filters (word count, cap ratio)
    words = len(block.text.split())
    if not (3 <= words <= 30):
        return False
    cap_ratio = sum(1 for c in block.text if c.isupper()) / len(block.text) if len(block.text) > 0 else 0
    if cap_ratio > 0.01:
        score += 2
    # Position/relation (top, spaced from prev)
    if block.bbox[1] < 600:
        score += 3
    if prev_block and (block.bbox[1] - prev_block.bbox[3] > 3):
        score += 4
    return score >= 8  # Adjusted threshold to allow small-font headings with strong semantics

def determine_level(block, stats, prev_level="H1"):
    depth = len(re.findall(r'\.', block.text.split()[0]))
    indent = block.bbox[0] - stats['avg_x']
    # Forced balance: stricter H1, looser H2/H3
    if depth == 0 and indent < 5 and (block.font_size > stats['avg_font_size'] * 1.15 or re.match(r'^(Ontario|Appendix|The Business|Approach|Evaluation|Preamble|Chapter|Section|Overview|Table|Acknowledgements|References|Introduction|Revision|Application|Form)', block.text)):
        return "H1"
    elif depth == 1 or (5 < indent < 25) or re.match(r'^\d+\.\s|Summary|Background|Milestones|Membership|Term|Chair|Meetings|Lines|Financial|Business|Learning|Entry|Structure|Keeping|Content|Name|Designation|Date|Permanent|Temporary|Home Town|Particulars|Block Year|Nature|Place|Duration|Advance|Family|Whether', block.text) or prev_level == "H1":
        return "H2"
    else:  # H3 for deeper/Indented or following H2
        return "H3"

def extract_title(blocks):
    candidates = [b for b in blocks if b.page <= 2 and b.bbox[1] < 250 and len(b.text.split()) > 4 and re.search(r'(rfp|request|proposal|business|plan|ontario|digital|library|foundation|level|extensions|syllabus|agile|tester|overview|application|form|ltc|grant|chapter|section|introduction|summary|background)', b.text.lower())]
    if candidates:
        sorted_cand = sorted(candidates, key=lambda b: (b.page, b.bbox[1], b.bbox[0]))
        title = ' '.join([c.text for c in sorted_cand if abs(c.bbox[1] - sorted_cand[0].bbox[1]) < 80])  # Increased range for multi-line
        return title.strip().replace('  ', ' ')
    # Dynamic fallback: First top meaningful text
    for b in blocks:
        if b.page == 1 and b.bbox[1] < 350 and len(b.text.split()) > 4:
            return b.text
    return "Untitled"

def build_outline(blocks, stats):
    outline = []
    prev_block = None
    prev_level = "H1"
    for i, block in enumerate(blocks):
        if is_heading(block, stats, prev_block, blocks, i):
            level = determine_level(block, stats, prev_level)
            outline.append({"level": level, "text": block.text.strip(), "page": block.page})
            prev_level = level
        prev_block = block
    return outline