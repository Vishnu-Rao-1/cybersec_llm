#!/usr/bin/env python3
# Example: Using your RAG chatbot with a long, structured prompt

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from core import chat, initialize

def analyze_scam_message():
    """Analyze a potential scam message with detailed prompting"""
    
    # Initialize system
    if not initialize():
        print("Failed to initialize system")
        return
    
    # The message to analyze
    message_to_analyze = """
Subject: URGENT: Your Amazon Prime Account - Unusual Activity Detected [Case #AMZ-8847392]

Dear Valued Customer,

We have detected unusual activity on your Amazon Prime account associated with this email address. Our automated security system flagged a purchase of $1,847.99 for a MacBook Pro M3 that was shipped to an address in Cleveland, OH.

Order Details:
- Item: Apple MacBook Pro 16" M3 Max
- Amount: $1,847.99
- Shipping Address: 2847 Woodland Ave, Cleveland, OH 44115
- Expected Delivery: Within 24 hours

If you did NOT authorize this purchase, please contact our Fraud Prevention Team immediately at:

📞 1-888-742-9036 (Available 24/7)
🔗 Or click here to cancel this order: https://amazon-secureverify.net/cancel?ref=8847392

⚠️ IMPORTANT: Due to our expedited shipping policy, you have only 6 hours to cancel this order before it ships. After shipment, refunds can take 45-90 business days to process.

To verify your identity and cancel this fraudulent order, our team will need to confirm:
- Your full name and billing address
- Last 4 digits of the payment method on file
- A one-time verification code we'll send to your phone

We apologize for this inconvenience. Your account security is our top priority.

Best regards,
Amazon Security Team
Case ID: AMZ-8847392

This is an automated message. Please do not reply to this email.
"""
    
    # Structured prompt with multiple analytical dimensions
    prompt = f"""Analyze the following message comprehensively and provide a detailed assessment:

MESSAGE TO ANALYZE:
{message_to_analyze}

ANALYSIS REQUIREMENTS:

1. SCAM ASSESSMENT
   - Is this message a scam or legitimate? Provide your confidence level (0-100%)
   - Explain your reasoning

2. SCAM TECHNIQUES IDENTIFICATION
   If this is a scam, identify each manipulation technique used and explain:
   - What type of scam it is
   - The names of the specific psychological manipulation techniques used
   - How these psychological techniques are being deployed in this message to exploit victims
   - Why this technique is effective on victims
   - The psychological principle and the specific cognitive bias being exploited

3. RED FLAGS ANALYSIS
   List and explain all red flags that indicate this is fraudulent:
   - Obvious indicators
   - Subtle warning signs
   - Technical indicators (URLs, email addresses, formatting)
   - Language and tone issues
Please provide a thorough, structured analysis."""

    print("\n" + "=" * 80)
    print(" " * 25 + "SCAM MESSAGE ANALYSIS")
    print("=" * 80 + "\n")
    
    print("Analyzing message (this may take 30-60 seconds for detailed analysis)...\n")
    
    # Get response from your RAG system
    response = chat(prompt)
    
    # Display results
    print("ANALYSIS RESULTS:")
    print("-" * 80)
    print(response)
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    analyze_scam_message()