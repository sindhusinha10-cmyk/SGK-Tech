#!/usr/bin/env python3
"""
build_knowledge_faiss.py

Generates dense vector embeddings for character specifications, cultural heritage,
and Bubble Sort CS educational concepts, indexing them into a FAISS vector index.
Supports the full 6-character Sanskritik & Native Wildlife roster.
"""

import json
import os
import re
import numpy as np
import faiss

KNOWLEDGE_JSON = os.path.join(os.path.dirname(__file__), "..", "specs", "character_knowledge.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "specs", "faiss_index")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INDEX_FILE = os.path.join(OUTPUT_DIR, "character_knowledge.index")
METADATA_FILE = os.path.join(OUTPUT_DIR, "documents_metadata.json")

def load_chunks():
    with open(KNOWLEDGE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for item in data:
        cid = item["id"]
        cname = item["name"]
        ctitle = item["title"]
        ch = item["cultural_heritage"]
        pm = item["powers_and_mechanics"]
        sp = item["3d_specs"]
        hm = item.get("height_m", 1.0)

        # Chunk 1: Identity & Overview
        chunks.append({
            "chunk_id": f"{cid}_overview",
            "character_id": cid,
            "category": "character_identity",
            "title": f"{cname} Overview: {ctitle}",
            "text": f"Character: {cname} ({cid}). Title: {ctitle}. Cultural Motif: {ch['motif']}. "
                    f"Significance: {ch['significance']} Height: {hm}m. "
                    f"Superpower: {pm['superpower']} Jump physics: {pm['jump_physics']}"
        })

        # Chunk 2: Cultural Heritage & Symbolism
        chunks.append({
            "chunk_id": f"{cid}_culture",
            "character_id": cid,
            "category": "cultural_heritage",
            "title": f"{cname} Cultural Heritage & Motif",
            "text": f"{cname} ({cid}) is inspired by {ch['motif']}. Significance: {ch['significance']} "
                    f"This character connects authentic Indian heritage and biodiversity with computer science education."
        })

        # Chunk 3: Computer Science & Bubble Sort Power Mechanics
        chunks.append({
            "chunk_id": f"{cid}_algorithm",
            "character_id": cid,
            "category": "bubble_sort_pedagogy",
            "title": f"{cname} Bubble Sort Superpower & Jump Mechanics",
            "text": f"In Bubble Sort, {cname} ({cid}) wields the superpower: '{pm['superpower']}'. "
                    f"Unique Jump Physics: {pm['jump_physics']} Height in simulation: {hm} meters."
        })

        # Chunk 4: 3D Asset & Technical Rigging Specifications
        chunks.append({
            "chunk_id": f"{cid}_3d_specs",
            "character_id": cid,
            "category": "3d_technical_specs",
            "title": f"{cname} 3D Asset & Rigging Specs",
            "text": f"{cname} ({cid}) 3D Model Specifications: mesh={sp['mesh']}, height={hm}m, "
                    f"accessory bones={', '.join(sp['accessory_bones'])}, "
                    f"materials={', '.join(sp['materials'])}. "
                    f"Includes blank runtime badge plate for dynamic number projection."
        })

    # Global Algorithm & Family Overview Chunk
    chunks.append({
        "chunk_id": "global_bubblesort_squad",
        "character_id": "all",
        "category": "algorithm_overview",
        "title": "Indian Heritage & Native Wildlife Bubble Sort Squad",
        "text": "The complete roster contains 6 unique Indian cultural and wildlife characters: "
                "Gaja (Elephant heavyweight stomp), Diya (Terracotta lamp flame burst), "
                "Kumbha (Kalasha boundary buffer), Grantha (Vedic book memory logger), "
                "Dhanesh (Great Indian Hornbill comparator), and Salya (Indian Pangolin stability shield). "
                "Each character features tailored jump physics, distinct heights, and individual sorting powers."
    })

    return chunks

class VocabularyTFIDFEncoder:
    def __init__(self, max_features=512):
        self.max_features = max_features
        self.vocab = {}
        self.idf = {}

    def _tokenize(self, text):
        words = re.findall(r"[a-z0-9_]+", text.lower())
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens

    def fit_transform(self, texts):
        doc_tokens = [self._tokenize(t) for t in texts]
        df = {}
        for tokens in doc_tokens:
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1

        sorted_terms = sorted(df.items(), key=lambda x: x[1], reverse=True)
        top_terms = [term for term, count in sorted_terms[:self.max_features]]
        self.vocab = {term: idx for idx, term in enumerate(top_terms)}

        N = len(texts)
        self.idf = {term: np.log(1.0 + (N + 1.0) / (df[term] + 1.0)) for term in self.vocab}

        dim = len(self.vocab)
        vectors = []
        for tokens in doc_tokens:
            vec = np.zeros(dim, dtype=np.float32)
            for tok in tokens:
                if tok in self.vocab:
                    idx = self.vocab[tok]
                    vec[idx] += self.idf[tok]
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec /= norm
            vectors.append(vec)

        return np.vstack(vectors)

    def transform(self, query):
        tokens = self._tokenize(query)
        dim = len(self.vocab)
        vec = np.zeros(dim, dtype=np.float32)
        for tok in tokens:
            if tok in self.vocab:
                idx = self.vocab[tok]
                vec[idx] += self.idf[tok]
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec.reshape(1, -1).astype(np.float32)

def main():
    print("Building FAISS knowledge index for 6-Character Squad...")
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} knowledge chunks.")

    texts = [c["text"] for c in chunks]
    encoder = VocabularyTFIDFEncoder(max_features=512)
    embeddings = encoder.fit_transform(texts)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"Built FAISS IndexFlatIP with {index.ntotal} vectors of dimension {dim}.")

    faiss.write_index(index, INDEX_FILE)
    print(f"Saved FAISS index to {INDEX_FILE}")

    payload = {
        "dim": dim,
        "vocab": encoder.vocab,
        "idf": encoder.idf,
        "chunks": chunks
    }
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved metadata & vocabulary to {METADATA_FILE}")

if __name__ == "__main__":
    main()
