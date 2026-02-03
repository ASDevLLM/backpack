"""
Twitter Bot agent - uses Backpack-injected credentials and personality.
Run with: backpack run agent.py
"""

import os


def main():
    openai_key = os.environ.get("OPENAI_API_KEY")
    twitter_token = os.environ.get("TWITTER_BEARER_TOKEN")
    system_prompt = os.environ.get("AGENT_SYSTEM_PROMPT", "")
    tone = os.environ.get("AGENT_TONE", "friendly")

    missing = [k for k in ("OPENAI_API_KEY", "TWITTER_BEARER_TOKEN") if not os.environ.get(k)]
    if missing:
        print(f"Missing credentials: {', '.join(missing)}")
        print("Add them with: backpack key add <KEY_NAME>")
        return

    print("Twitter Bot agent ready")
    print(f"Personality: {system_prompt[:60]}...")
    print("\nIn a full implementation, you would:")
    print("  - Use OPENAI_API_KEY for generating tweet text or replies")
    print("  - Use TWITTER_BEARER_TOKEN with Twitter API v2 to post/read tweets")
    print("  - Respect rate limits and Twitter rules. Customize this script for your bot.")


if __name__ == "__main__":
    main()

