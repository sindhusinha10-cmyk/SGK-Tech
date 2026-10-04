#!/usr/bin/env python3
"""
build_knowledge_faiss.py

Generates dense vector embeddings for character specifications, cultural heritage,
and Bubble Sort CS educational concepts, indexing them into a FAISS vector index.
Uses an exact Bag-of-Words / TF-IDF sparse-to-dense projection with bigram weighting.
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
        cp = item["bubble_sort_pedagogy"]
        sp = item["3d_asset_specs"]

        # Chunk 1: Identity & Overview
        chunks.append({
            "chunk_id": f"{cid}_overview",
            "character_id": cid,
            "category": "character_identity",
            "title": f"{cname} Overview: {ctitle}",
            "text": f"Character: {cname} ({cid}). Title: {ctitle}. Cultural Motif: {ch['motif']}. "
                    f"Visual Design: {ch['visual_design']} Role in Bubble Sort: {cp['algorithm_role']}. "
                    f"3D Mesh: {sp['mesh']}, Height: {sp['height_m']}m."
        })

        # Chunk 2: Cultural Heritage & Symbolism
        chunks.append({
            "chunk_id": f"{cid}_culture",
            "character_id": cid,
            "category": "cultural_heritage",
            "title": f"{cname} Cultural Heritage & Motif",
            "text": f"{cname} ({cid}) is inspired by {ch['motif']}. Cultural Significance: {ch['cultural_significance']}. "
                    f"Visual characteristics: {ch['visual_design']} The character connects computer science education "
                    f"with India's rich intellectual and craft traditions."
        })

        # Chunk 3: Computer Science & Bubble Sort Algorithm Role
        reactions = " ".join([f"{k}: {v}" for k, v in cp["runtime_state_reactions"].items()])
        chunks.append({
            "chunk_id": f"{cid}_algorithm",
            "character_id": cid,
            "category": "bubble_sort_pedagogy",
            "title": f"{cname} Bubble Sort Algorithm & Educational Function",
            "text": f"In Bubble Sort, {cname} ({cid}) acts as the {cp['algorithm_role']}. "
                    f"Sorting behavior: {cp['sorting_behavior']} "
                    f"Animation reactions during execution: {reactions}"
        })

        # Chunk 4: 3D Asset & Technical Rigging Specifications
        chunks.append({
            "chunk_id": f"{cid}_3d_specs",
            "character_id": cid,
            "category": "3d_technical_specs",
            "title": f"{cname} 3D Asset & Rigging Specs",
            "text": f"{cname} ({cid}) 3D Model Specifications: mesh={sp['mesh']}, height={sp['height_m']} meters, "
                    f"base armature='{sp['base_armature']}', accessory bones={', '.join(sp['accessory_bones'])}, "
                    f"materials={', '.join(sp['materials'])}, triangle budget={sp['triangle_budget']} triangles. "
                    f"Includes blank runtime badge plate for dynamic number projection."
        })

    # Global Algorithm & Family Overview Chunk
    chunks.append({
        "chunk_id": "global_bubblesort_squad",
        "character_id": "all",
        "category": "algorithm_overview",
        "title": "Bubble Sort Squad Educational Framework",
        "text": "The Bubble Sort Squad consists of 5 original Indian-heritage mascots: "
                "Gaja (the elephant heavyweight anchor), Mayur (the peacock comparator), "
                "Diya (the terracotta lamp active traversal pointer), Patra (the scroll memory index), "
                "and Kumbha (the kalasha boundary buffer). Together they illustrate adjacent comparison, "
                "in-place swapping, and partition convergence in O(n^2) worst/average case and O(1) auxiliary space."
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
        # Bigrams
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens

    def fit_transform(self, texts):
        doc_tokens = [self._tokenize(t) for t in texts]
        df = {}
        for tokens in doc_tokens:
            for tok in set(tokens):
                df[tok] = df.get(tok, 0) + 1

        # Keep top terms sorted by frequency
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
    print("Building FAISS knowledge index for 3D Mascot Squad...")
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
