# def answer_tweet_with_context_tool(tweet_id: str, tweet_text: str, message: str) -> str:
#     """Search for relevant context and reply to a tweet using that context."""
#     try:
#         # Use the tweet text to search for relevant context
#         relevant_docs = retriever.invoke(tweet_text)

#         print("\n=== Retrieved Documents ===")
#         for i, doc in enumerate(relevant_docs):
#             print(f"Document {i + 1}:")
#             print(doc.page_content)
#             print("---")

#         # Extract context from the retrieved documents
#         context = "\n".join([doc.page_content for doc in relevant_docs]) if relevant_docs else ""
#         print("\n=== Assembled Context ===")
#         print(context)
#         print("---")

#         # Enhance the tweet_text with context
#         enhanced_tweet_text = f"""
#                         This is Original Tweet you should reply to: {tweet_text}

#                         This is context, use it only if it is relevant to the tweet.
#                         {context}
#                         """
#         print("\n=== Enhanced Tweet Text ===")
#         print(enhanced_tweet_text)
#         print("---")

#         # Use the existing answer tool to post the reply
#         result = answer_tool._run(tweet_id=tweet_id, tweet_text=enhanced_tweet_text, message=message)

#         if "error" in result:
#             return result["error"]

#         return result.get("message", "Reply sent successfully")
#     except Exception as e:
#         return f"An error occurred replying to tweet with context: {str(e)}"


# # answer_with_context_tool_wrapped = StructuredTool.from_function(
# #    func=answer_tweet_with_context_tool,
# #    name="answer_with_context",
# #    description="Reply to tweets using retrieved context to enhance your answer",
# # )

# # # TWRET PROMPT WIP
# # tweet_prompt = PromptTemplate.from_template("{page_content}")
# # print(tweet_prompt.invoke({"page_content": ""}))
# # print(tweet_prompt)

# retriever_tool = create_retriever_tool(
#     retriever,
#     "search_context",
#     "Search our knowledge base for relevant context about this topic",
# )
