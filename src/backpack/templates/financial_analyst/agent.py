"""
Financial Analyst agent - uses Backpack-injected credentials and personality.
Run with: backpack run agent.py
"""

import os


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    system_prompt = os.environ.get("AGENT_SYSTEM_PROMPT", "")
    tone = os.environ.get("AGENT_TONE", "formal")

    if not api_key:
        print("OPENAI_API_KEY not found. Add it with: backpack key add OPENAI_API_KEY")
        return

    print(f"Financial Analyst agent ready (tone: {tone})")
    print(f"System prompt: {system_prompt[:80]}...")
    print("\nIn a full implementation, you would:")
    print("  - Call OpenAI/Anthropic with AGENT_SYSTEM_PROMPT as system message")
    print("  - Process financial data (CSV, APIs) and ask the model for analysis")
    print("  - Return structured reports. Customize this script for your use case.")


if __name__ == "__main__":
    main()

