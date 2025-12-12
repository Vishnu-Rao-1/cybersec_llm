#!/usr/bin/env python3
# batch_analyze.py - Batch analyze scam messages from Google Sheets CSV

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import re

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core import initialize, generate_response, retrieve_context

def analyze_scam_batch(input_file: str, output_file: str = None):
    """
    Analyze scam messages from a CSV exported from Google Sheets
    Shows real-time progress as responses are generated
    
    Args:
        input_file: Path to CSV file (must have 'scam_messages' column)
        output_file: Path to save results (optional, auto-generated if not provided)
    """
    
    # Initialize system
    print("\n" + "=" * 70)
    print(" " * 25 + "BATCH SCAM ANALYSIS")
    print("=" * 70 + "\n")
    
    if not initialize():
        print("[ERROR] Failed to initialize system")
        return
    
    # Auto-generate output filename if not provided
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(input_file).stem
        output_file = f"{base_name}_analyzed_{timestamp}.csv"
    
    # Load spreadsheet
    print(f"[LOADING] {input_file}")
    
    try:
        df = pd.read_csv(input_file)
        print(f"[OK] Loaded {len(df)} rows")
        print(f"[OK] Columns found: {', '.join(df.columns)}\n")
        
    except Exception as e:
        print(f"[ERROR] Error loading file: {e}")
        return
    
    # Validate required column
    if 'scam_messages' not in df.columns:
        print("[ERROR] CSV must have a 'scam_messages' column")
        print(f"\n   Found columns: {', '.join(df.columns)}")
        print("\n   [TIP] In Google Sheets, name your column 'scam_messages'")
        print("   Then: File -> Download -> Comma Separated Values (.csv)")
        return
    
    # Add ai_responses column if it doesn't exist
    if 'ai_responses' not in df.columns:
        df['ai_responses'] = ''
    
    # Check message lengths
    df['message_length'] = df['scam_messages'].astype(str).str.len()
    long_messages = df[df['message_length'] > 2000]
    
    if len(long_messages) > 0:
        print(f"[WARNING] {len(long_messages)} messages exceed 2000 characters")
        print(f"   Longest: {df['message_length'].max()} characters")
        print("   These will be truncated to prevent token overflow\n")
    
    # Process each message with real-time display
    print("[INFO] Analyzing messages...\n")
    print("=" * 70)
    
    for idx in range(len(df)):
        message = df.loc[idx, 'scam_messages']
        
        # Display progress header
        print(f"\n[Message {idx + 1}/{len(df)}]")
        print("-" * 70)
        
        # Skip empty messages
        if pd.isna(message) or str(message).strip() == '':
            df.loc[idx, 'ai_responses'] = '[SKIPPED: Empty message]'
            print("[SKIPPED] Empty message")
            continue
        
        # Show message preview
        message_preview = str(message)[:150].replace('\n', ' ')
        print(f"Message: {message_preview}...")
        
        # Build analysis prompt (3 sections only)
        prompt = f"""Analyze the following message comprehensively and provide a detailed assessment:

MESSAGE TO ANALYZE:
{message}

ANALYSIS REQUIREMENTS:

1. SCAM ASSESSMENT
   - Is this message a scam or legitimate? Provide your confidence level (0-100%)
   - Explain your reasoning

2. SCAM TECHNIQUES IDENTIFICATION
   If this is a scam, identify each manipulation technique used and explain:
   - The specific technique name
   - How it's being deployed in this message
   - The psychological principle and the specific cognitive bias it exploits
   - Why this technique is effective on victims

3. RED FLAGS ANALYSIS
   List and explain all red flags that indicate this is fraudulent:
   - Obvious indicators
   - Subtle warning signs
   - Technical indicators (URLs, email addresses, formatting)
   - Language and tone issues

Please provide a thorough, structured analysis."""

        try:
            print("[ANALYZING] This may take 30-60 seconds...", end='', flush=True)
            
            # Generate analysis
            context = retrieve_context(prompt, top_k=5)
            analysis = generate_response(prompt, context, max_tokens=700)
            
            # Store result
            df.loc[idx, 'ai_responses'] = analysis
            
            print(" [DONE]")
            
            # Show response preview
            response_preview = analysis[:200].replace('\n', ' ')
            print(f"Response: {response_preview}...")
            
            # Save incrementally (so you can see progress in the file)
            df.to_csv(output_file, index=False)
            print(f"[SAVED] to: {output_file}")
            
        except Exception as e:
            error_msg = f'[ERROR: {str(e)}]'
            df.loc[idx, 'ai_responses'] = error_msg
            print(f" [ERROR] {e}")
            # Still save on error
            df.to_csv(output_file, index=False)
    
    # Final summary
    print("\n" + "=" * 70)
    print(" " * 32 + "SUMMARY")
    print("=" * 70)
    
    completed = len([r for r in df['ai_responses'] if r and not r.startswith('[ERROR')])
    errors = len([r for r in df['ai_responses'] if r and r.startswith('[ERROR')])
    skipped = len([r for r in df['ai_responses'] if r and r.startswith('[SKIPPED')])
    
    print(f"\n  Total messages: {len(df)}")
    print(f"  [OK] Successfully analyzed: {completed}")
    print(f"  [ERROR] Errors: {errors}")
    print(f"  [SKIPPED] Skipped: {skipped}")
    print(f"\n  Results saved to: {output_file}")
    print("\n  [TIP] Import this CSV back into Google Sheets to see results!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Hardcoded version - change the filename below to your CSV file
    analyze_scam_batch("test.csv")
