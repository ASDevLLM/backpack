"""
Code Reviewer agent - uses Backpack-injected credentials and personality.
Run with: backpack run agent.py
"""

import os


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    system_prompt = os.environ.get("AGENT_SYSTEM_PROMPT", "")
    tone = os.environ.get("AGENT_TONE", "professional")

    if not api_key:
        print("OPENAI_API_KEY not found. Add it with: backpack key add OPENAI_API_KEY")
        return

    print("Code Reviewer agent ready")
    print(f"System prompt: {system_prompt[:70]}...")
    print("\nIn a full implementation, you would:")
    print("  - Read diff or file content (e.g. from stdin or path)")
    print("  - Send to your LLM with AGENT_SYSTEM_PROMPT as system message")
    print("  - Output review comments (inline or summary). Customize this script.")


if __name__ == "__main__":
    main()

