#!/usr/bin/env python3
"""
query_knowledge.py

Search the FAISS index for semantic knowledge, educational rationale,
and 3D specs for the Bubble Sort creature mascots.
"""

import sys
import os
import json
import re
import numpy as np
import faiss

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "specs", "faiss_index")
INDEX_FILE = os.path.join(OUTPUT_DIR, "character_knowledge.index")
METADATA_FILE = os.path.join(OUTPUT_DIR, "documents_metadata.json")

def query_knowledge(query_text, top_k=3):
    if not os.path.exists(INDEX_FILE) or not os.path.exists(METADATA_FILE):
        print("FAISS index not found. Please run build_knowledge_faiss.py first.")
        return []

    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    dim = meta["dim"]
    vocab = meta["vocab"]
    idf = meta["idf"]
    chunks = meta["chunks"]

    # Tokenize with bigrams
    words = re.findall(r"[a-z0-9_]+", query_text.lower())
    tokens = list(words)
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")

    vec = np.zeros(dim, dtype=np.float32)
    for tok in tokens:
        if tok in vocab:
            idx = vocab[tok]
            vec[idx] += idf.get(tok, 1.0)

    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec /= norm
    q_vec = vec.reshape(1, -1).astype(np.float32)

    scores, indices = index.search(q_vec, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(chunks):
            c = dict(chunks[idx])
            c["score"] = float(score)
            results.append(c)

    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "Why does Gaja hop on two legs when sorting numbers?"

    print(f"Query: '{q}'\n")
    matches = query_knowledge(q, top_k=3)
    for i, m in enumerate(matches, 1):
        print(f"[{i}] {m['title']} (Score: {m['score']:.4f})")
        print(f"    Category: {m['category']} | Character: {m['character_id']}")
        print(f"    Content: {m['text']}\n")
