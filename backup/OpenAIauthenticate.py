# Authenticate to OpenAI, setup model
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.0, 
    top_p=0.005, 
    api_key="sk-trJNV0X-yBPL-x5DcVymvVKyJ5oqcQfSqLcMBBRIqRT3BlbkFJpBgIac_ntkPfCQ9IjX9j1sm0jMROmX2C_CylYCg6MA"
    )