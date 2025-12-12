#!/usr/bin/env python3
# 2_buildSearch.py - Build FAISS and BM25 search indices
import json
import numpy as np
import faiss
import pickle
import nltk
import ssl
from pathlib import Path

# Fix SSL for NLTK downloads
ssl._create_default_https_context = ssl._create_unverified_context

def download_nltk_data():
    """Download required NLTK data"""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print(" Downloading NLTK data...")
        nltk.download('punkt', quiet=True)
        try:
            nltk.download('punkt_tab', quiet=True)
        except:
            pass

def build_search_engine():
    """Build FAISS vector index and BM25 keyword index"""
    print("=" * 70)
    print(" " * 15 + " BUILDING SEARCH ENGINE")
    print("=" * 70)
    
    # Check for chunks file
    chunks_path = Path("index/chunks.json")
    if not chunks_path.exists():
        print("\n ERROR: index/chunks.json not found!")
        print("   Please run: python3 1_buildKnowledge.py first")
        print("=" * 70)
        return False
    
    try:
        # Download NLTK data
        download_nltk_data()
        
        from sentence_transformers import SentenceTransformer
        from rank_bm25 import BM25Okapi
        from nltk.tokenize import word_tokenize
        
        print("\n Loading chunks...")
        with open(chunks_path, 'r') as f:
            chunks = json.load(f)
        
        print(f"   ✓ Found {len(chunks):,} chunks")
        
        if len(chunks) == 0:
            print("\n ERROR: No chunks found in chunks.json!")
            print("=" * 70)
            return False
        
        texts = [c["text"] for c in chunks]
        
        # Build embedding index
        print("\n Loading embedding model (all-MiniLM-L6-v2)...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        print("   ✓ Model loaded")
        
        print("\n Creating embeddings (this may take a few minutes)...")
        embeds = model.encode(texts, batch_size=32, show_progress_bar=True)
        embeds = np.array(embeds).astype("float32")
        
        print(f"   ✓ Embedding shape: {embeds.shape}")
        
        # Build FAISS index
        print("\n Building FAISS vector index...")
        index = faiss.IndexFlatL2(embeds.shape[1])
        index.add(embeds)
        
        faiss_path = "index/faiss.index"
        faiss.write_index(index, faiss_path)
        print(f"   ✓ Saved to: {faiss_path}")
        
        # Build BM25 index
        print("\n Building BM25 keyword index...")
        tokenized = [word_tokenize(t.lower()) for t in texts]
        bm25 = BM25Okapi(tokenized)
        print("   ✓ BM25 index built")
        
        # Save everything
        print("\n Saving search indices...")
        search_pkl_path = "index/search.pkl"
        with open(search_pkl_path, "wb") as f:
            pickle.dump((bm25, chunks, model), f)
        
        print(f"   ✓ Saved to: {search_pkl_path}")
        
        print("\n" + "=" * 70)
        print(" SUCCESS! Search engine ready")
        print("=" * 70)
        print("\n     Next step: python3 chat.py")
        print("=" * 70 + "\n")
        
        return True
    
    except ImportError as e:
        print(f"\n ERROR: Missing required package!")
        print(f"   {e}")
        print("\n   Please run: pip install -r requirements.txt")
        print("=" * 70)
        return False
    
    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = build_search_engine()
    exit(0 if success else 1)