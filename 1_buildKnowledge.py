#!/usr/bin/env python3
# 1_buildKnowledge.py - Build knowledge base from JSONL papers
import json
import os
from pathlib import Path
from tqdm import tqdm

def build_knowledge_base():
    """Extract and chunk papers from .jsonl file"""
    print("=" * 70)
    print(" " * 15 + " BUILDING KNOWLEDGE BASE")
    print("=" * 70)
    
    # Check if input file exists
    path = "useme.jsonl"
    if not os.path.exists(path):
        print(f"\n ERROR: {path} not found in current directory!")
        print("\nPlease ensure your jsonl file is in the same fucking folder as this script.")
        print("=" * 70)
        return False
    
    chunks = []
    total_papers = 0
    skipped = 0
    
    print(f"\n Loading papers from {path}...")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in tqdm(lines, desc="Processing your papers", unit="paper"):
            try:
                data = json.loads(line.strip())
                total_papers += 1
                
                # Combine title, abstract, and sections
                full_text = (data.get("title", "") + " " + 
                            data.get("abstract", "") + " ")
                
                for sec in data.get("sections", []):
                    text = sec.get("text") or sec.get("content") or str(sec)
                    full_text += text + " "
                
                full_text = full_text.strip()
                
                # Skip papers that are too short
                if len(full_text) < 500:
                    skipped += 1
                    continue
                
                # Chunk the text (overlap for context preservation)
                words = full_text.split()
                chunk_size = 250  # words per chunk
                overlap = 50     # word overlap between chunks
                
                for i in range(0, len(words), chunk_size - overlap):
                    chunk_text = " ".join(words[i:i + chunk_size])
                    
                    # Only keep substantial chunks
                    if len(chunk_text.split()) > 80:
                        chunks.append({
                            "chunk_id": len(chunks),
                            "text": chunk_text,
                            "paper_id": data.get("paper_id", "unknown"),
                            "title": data.get("title", "Untitled")[:200],
                            "year": data.get("year", "N/A"),
                            "authors": data.get("authors", [])[:3]  # First 3 authors
                        })
            
            except json.JSONDecodeError:
                continue
            except Exception as e:
                continue
        
        # Save chunks
        os.makedirs("index", exist_ok=True)
        output_path = "index/chunks.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2)
        
        print("\n" + "=" * 70)
        print("SUCCESS! Knowledge base built")
        print("=" * 70)
        print(f"    Statistics:")
        print(f"      • Papers processed: {total_papers:,}")
        print(f"      • Papers skipped (too short): {skipped:,}")
        print(f"      • Total chunks created: {len(chunks):,}")
        print(f"      • Saved to: {output_path}")
        print("\n   Next step: python3 2_buildSearch.py")
        print("=" * 70 + "\n")
        
        return True
    
    except Exception as e:
        print(f"\n ERROR: {e}")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = build_knowledge_base()
    exit(0 if success else 1)