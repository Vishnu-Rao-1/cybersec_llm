#THIS IS THE ONE YOU RUN IF YOU WANNA CHAT


#!/usr/bin/env python3
# chat.py - Interactive terminal chat interface
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core import chat, initialize
except ImportError as e:
    print(f"Error importing core module: {e}")
    print("\nMake sure core.py is in the stelame directory as chat.py")
    sys.exit(1)

def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 70)
    print(" " * 15 + " RAG-POWERED AI CHAT ASSISTANT")
    print("=" * 70)
    print("\n Chat with the AI:")
    print("\n Commands:")
    print("   • Type your question and press Enter to chat")
    print("   • Type 'quit', 'exit', or 'q' to exit")
    print("   • Type 'clear' to clear the screen")
    print("   • Type 'help' for more information")
    print("\n" + "=" * 70 + "\n")

def print_help():
    """Print help information"""
    print("\n" + "=" * 70)
    print(" " * 30 + "HELP")
    print("=" * 70)
    print("\n About This System:")
    print("   This is a RAG (Retrieval-Augmented Generation) chatbot.")
    print("   It searches through a knowledge base of research papers")
    print("   to provide informed, contextual answers to your questions.")
    print("\n How to Use:")
    print("   • Ask questions naturally, as you would to a human expert")
    print("   • The AI will search for relevant information in the papers")
    print("   • Responses are based on the knowledge base content")
    print("   • Sources are cited when available")
    print("\n Example Questions:")
    print("   • 'What is machine learning?'")
    print("   • 'Explain how neural networks work'")
    print("   • 'What are the latest developments in AI?'")
    print("   • 'Summarize the key findings about [topic]'")
    print("\n⚡ Tips for Better Results:")
    print("   • Be specific in your questions")
    print("   • Ask follow-up questions for clarity")
    print("   • If the answer seems off-topic, try rephrasing")
    print("   • The AI will indicate when info isn't in the knowledge base")
    print("\n" + "=" * 70 + "\n")

def clear_screen():
    """Clear the terminal screen"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    """Main chat loop"""
    # Initialize the system
    if not initialize():
        print("\n Failed to initialize the system.")
        print("\n Please complete the setup steps:")
        print("   1. Run: python3 1_buildKnowledge.py")
        print("   2. Run: python3 2_buildSearch.py")
        print("   3. Ensure the model file is in the correct location")
        print("\n" + "=" * 70 + "\n")
        sys.exit(1)
    
    # Print banner
    print_banner()
    
    # Chat loop
    conversation_count = 0
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Handle empty input
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n" + "=" * 70)
                print(" " * 20 + " Thanks for chatting!")
                print("=" * 70 + "\n")
                break
            
            elif user_input.lower() == 'clear':
                clear_screen()
                print_banner()
                continue
            
            elif user_input.lower() == 'help':
                print_help()
                continue
            
            # Generate response
            print("\n Thinking", end="", flush=True)
            for i in range(3):
                import time
                time.sleep(0.3)
                print(".", end="", flush=True)
            print("\n")
            
            response = chat(user_input)
            
            # Print response
            print(f"AI: {response}\n")
            print("-" * 70 + "\n")
            
            conversation_count += 1
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 70)
            print(" " * 20 + " Chat interrupted. Goodbye!")
            print("=" * 70 + "\n")
            break
        
        except Exception as e:
            print(f"\n  Error: {e}")
            print("Please try again or type 'quit' to exit.\n")

if __name__ == "__main__":
    main()
