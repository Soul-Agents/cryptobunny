from variables import *


def test_neoai_config():
    # Set environment variable
    os.environ["AGENT_NAME"] = "NEOAI"

    # Print key configurations
    print("=== Basic Configuration ===")
    print(f"Agent Name: {CURRENT_AGENT_NAME}")
    print(f"User ID: {USER_ID}")
    print(f"Username: {USER_NAME}")

    print("\n=== Personality & Strategy ===")
    print(f"Personality Sample:\n{USER_PERSONALITY[:200]}...")
    print(f"\nStrategy: {STRATEGY}")
    print(f"Mission: {MISSION}")
    print(f"Remember: {REMEMBER}")
    print(f"Question: {QUESTION}")

    print("\n=== Rules ===")
    print(f"Style Rules Sample:\n{STYLE_RULES[:200]}...")
    print(f"\nContent Restrictions Sample:\n{CONTENT_RESTRICTIONS[:200]}...")

    print("\n=== Target Accounts ===")
    print(f"AI & Agents: {len(AI_AND_AGENTS)} accounts")
    print(f"Web3 Builders: {len(WEB3_BUILDERS)} accounts")
    print(f"DeFi Experts: {len(DEFI_EXPERTS)} accounts")
    print(f"Thought Leaders: {len(THOUGHT_LEADERS)} accounts")
    print(f"Traders & Analysts: {len(TRADERS_AND_ANALYSTS)} accounts")
    print(f"Total Famous Accounts: {len(FAMOUS_ACCOUNTS)} unique accounts")

    print("\n=== Knowledge Base ===")
    print(f"Knowledge Base Sample:\n{KNOWLEDGE_BASE[:200]}...")


if __name__ == "__main__":
    test_neoai_config()
