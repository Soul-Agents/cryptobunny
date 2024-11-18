import os

# Set the API key as an environment variable
os.environ["TAVILY_API_KEY"] = "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"

# additional tool
browse_internet = TavilySearchResults(
    max_results=1  # No need to pass the API key if it's set as an environment variable
)

# Setup agent tools
tools = [
    browse_internet,
    tweet_tool_wrapped,    
    answer_tool_wrapped,        
    read_tweets_tool_wrapped,
]