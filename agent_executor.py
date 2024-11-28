# Create an agent executor by passing in the agent and tools

# Create an agent executor by passing in the agent and tools
agent_executor = AgentExecutor(
    agent=agent, tools=tools, verbose=True, handle_parsing_errors=True
)

# Execute the agent and await the result
search_output = agent_executor.invoke({"input": ask_agent_crypto_question})
print(search_output)