#!/usr/bin/env python3
# core.py - Core RAG engine with LLM
import faiss
import numpy as np
import pickle
from pathlib import Path
from llama_cpp import Llama
from nltk.tokenize import word_tokenize
import sys

# Auto-detect project root
PROJECT_ROOT = Path(__file__).parent.resolve()

# Paths
INDEX_DIR = PROJECT_ROOT / "index"
MODEL_PATH = PROJECT_ROOT / "models" / "Phi-3-mini-4k-instruct-q4.gguf"

# Global variables (loaded once, shared across modules)
llm = None
index = None
bm25 = None
chunks = []
embedder = None

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        INDEX_DIR / "faiss.index",
        INDEX_DIR / "search.pkl",
        MODEL_PATH
    ]
    
    missing = [f for f in required_files if not f.exists()]
    
    if missing:
        print("\n" + "!" * 70)
        print(" " * 20 + "  MISSING REQUIRED FILES")
        print("!" * 70)
        for f in missing:
            try:
                rel_path = f.relative_to(PROJECT_ROOT)
            except:
                rel_path = f
            print(f"    {rel_path}")
        
        print("\n    Setup Instructions:")
        print("   " + "-" * 66)
        print("   1. Ensure 'testmenow.jsonl' is in the project folder")
        print("   2. Run: python3 1_buildKnowledge.py")
        print("   3. Run: python3 2_buildSearch.py")
        print("\n    For the model file:")
        print(f"      • Download Phi-3-mini GGUF from HuggingFace")
        print(f"      • Suggested: microsoft/Phi-3-mini-4k-instruct-gguf")
        print(f"      • Place it in: {MODEL_PATH.parent}/")
        print(f"      • Or update MODEL_PATH in core.py")
        print("!" * 70 + "\n")
        return False
    
    return True

def initialize():
    """Initialize the RAG system (load model and indices)"""
    global llm, index, bm25, chunks, embedder
    
    if llm is not None:
        return True  # Already initialized
    
    if not check_requirements():
        return False
    
    try:
        print("\n" + "=" * 70)
        print(" " * 20 + " INITIALIZING RAG SYSTEM")
        print("=" * 70)
        
        # Load search index
        print("\n Loading search indices...")
        index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
        
        with open(INDEX_DIR / "search.pkl", "rb") as f:
            bm25, chunks, embedder = pickle.load(f)
        
        print(f"   ✓ Loaded {len(chunks):,} knowledge chunks")
        
        # Load LLM
        print(f"\n Loading LLM (this may take 5-15 seconds)...")
        print(f"   • Model: {MODEL_PATH.name}")
        
        llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=4096,           # Context window
            n_threads=6,          # CPU threads (adjust for your system)
            n_gpu_layers=-1,      # Use ALL layers on Metal/CUDA if available
            n_batch=512,          # Batch size for prompt processing
            verbose=False
        )
        
        print("   ✓ LLM loaded successfully")
        print("\n" + "=" * 70)
        print(" " * 25 + " SYSTEM READY!")
        print("=" * 70 + "\n")
        
        return True
    
    except Exception as e:
        print(f"\n Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70 + "\n")
        return False

def retrieve_context(query: str, top_k: int = 5) -> list:
    """
    Retrieve relevant context using hybrid search (semantic + keyword)
    
    Args:
        query: User's question
        top_k: Number of context chunks to return
    
    Returns:
        List of relevant text chunks with metadata
    """
    if not initialize():
        return []
    
    try:
        # Semantic search using FAISS
        query_embedding = embedder.encode([query])[0].astype("float32")
        _, semantic_indices = index.search(
            np.array([query_embedding]).reshape(1, -1), 
            top_k * 3
        )
        semantic_candidates = [
            chunks[i] for i in semantic_indices[0] 
            if i < len(chunks)
        ]
        
        # Keyword search using BM25
        query_tokens = word_tokenize(query.lower())
        bm25_scores = bm25.get_scores(query_tokens)
        bm25_indices = sorted(
            range(len(chunks)), 
            key=lambda i: bm25_scores[i], 
            reverse=True
        )[:top_k * 3]
        bm25_candidates = [chunks[i] for i in bm25_indices]
        
        # Combine and deduplicate
        seen = set()
        context = []
        
        for candidate in semantic_candidates + bm25_candidates:
            if candidate["chunk_id"] not in seen and len(context) < top_k:
                seen.add(candidate["chunk_id"])
                context.append(candidate)
        
        return context
    
    except Exception as e:
        print(f" Error retrieving context: {e}")
        return []

def generate_response(query: str, context: list = None, max_tokens: int = 800) -> str:
    """
    Generate a response using the LLM with retrieved context
    
    Args:
        query: User's question
        context: Pre-retrieved context (if None, will retrieve automatically)
        max_tokens: Maximum tokens in response
    
    Returns:
        Generated response text
    """
    if not initialize():
        return "Error: System not initialized."
    
    # Retrieve context if not provided
    if context is None:
        context = retrieve_context(query)
    
    # Format context
    if context:
        context_text = "\n\n".join([
            f"[Source {c['chunk_id']} - {c.get('title', 'Unknown')[:80]} ({c.get('year', 'N/A')})]:\n{c['text'][:800]}"
            for c in context
        ])
    else:
        context_text = "No specific context found in the knowledge base."
    
    # Build prompt
    prompt = f"""You are a helpful AI assistant with access to a knowledge base of research papers.

Context from knowledge base:
{context_text}

User question: {query}

Instructions:
- Answer the question based on the provided context
- If the context doesn't contain relevant information, say so honestly
- Be concise but informative
- Cite sources when possible (e.g., "According to Source X...")

Answer:"""
    
    try:
        # Generate response
        response = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            stop=["User question:", "\n\nUser:", "\n\nContext:"],
            echo=False
        )
        
        result = response["choices"][0]["text"].strip()
        return result if result else "I couldn't generate a response. Please try rephrasing your question."
    
    except Exception as e:
        return f"Error generating response: {e}"

def chat(message: str) -> str:
    """
    Main chat function - retrieve context and generate response
    
    Args:
        message: User's message
    
    Returns:
        AI response
    """
    if not initialize():
        return "Error: Failed to initialize the system. Please check the setup."
    
    # Retrieve relevant context
    context = retrieve_context(message, top_k=5)
    
    # Generate response with context
    response = generate_response(message, context)
    
    return response

# Export all public functions
__all__ = [
    "initialize",
    "chat",
    "retrieve_context", 
    "generate_response",
    "llm",
    "embedder",
    "index",
    "bm25",
    "chunks"
]