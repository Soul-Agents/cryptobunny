from main import browse_internet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_browse_internet():
    print("Testing browse_internet tool...")
    
    # Test queries
    queries = [
        "Latest Layer 2 developments in Ethereum",
        "Recent MEV patterns in validator behavior",
        "New cross-chain bridge security measures",
        "Emerging DeFi protocol innovations"
    ]
    
    for query in queries:
        print(f"\nSearching for: {query}")
        try:
            results = browse_internet(query)
            print("\nResults:")
            print(results[:500] + "..." if len(results) > 500 else results)  # Truncate long results
            print("\n" + "-"*50)
        except Exception as e:
            print(f"Error searching for '{query}': {str(e)}")

if __name__ == "__main__":
    test_browse_internet() 