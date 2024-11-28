#libraries
import os
import getpass
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from dotenv import dotenv_values
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from typing import Dict
from typing import Literal, Optional
import asyncio
import json
import os