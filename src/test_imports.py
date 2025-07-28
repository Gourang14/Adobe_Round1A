# src/test_imports.py
import fitz  # pymupdf
import re
import statistics
from collections import namedtuple
from multiprocess import Pool
import unicodedata
from sentence_transformers import SentenceTransformer  # For 1B, but test now
from sklearn.feature_extraction.text import TfidfVectorizer

print("All imports successful!")