from db import TweetDB                            
from dotenv import load_dotenv                    
from langchain_core.documents import Document   
from langchain_openai import OpenAIEmbeddings     
from langchain_pinecone import PineconeVectorStore 
from langchain_text_splitters import CharacterTextSplitter  
import os                                         
from pinecone import Pinecone  

# Load environment variables 
load_dotenv()

# Initialize services using environment variables
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
os.environ["MONGODB_URL"] 

# Init db and get relevant fuctions
db = TweetDB()
most_recent_id = db.get_most_recent_tweet_id()
tweets = db.get_all_tweets()

# check new tweets
new_tweets = [tweet for tweet in tweets if int(tweet['tweet_id']) > int(most_recent_id)]

#if no new tweets, add them to vector db
if not new_tweets:
    print("No new tweets to vectorize")
else:
    print(f"Found {len(new_tweets)} new tweets to vectorize")
    
    # Convert only new tweets to documents format
    docs = []
    for tweet in new_tweets:
        metadata = {
            "tweet_id": tweet['tweet_id'],
            "author_id": tweet['author_id'],
            "created_at": str(tweet['created_at'])
        }
        
        # Add optional fields if they exist
        if 'replied_to' in tweet:
            metadata['replied_to'] = tweet['replied_to']
        if 'quote_count' in tweet:
            metadata['quote_count'] = tweet['quote_count']
        if 'replied_at' in tweet:
            metadata['replied_at'] = str(tweet['replied_at'])

        doc = Document(
            page_content=tweet['text'],
            metadata=metadata
        )
        docs.append(doc)

    # Only process if we have new documents
    if docs:
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.split_documents(docs)

        vectorstore_from_docs = PineconeVectorStore.from_documents(
            texts,
            index_name='soulsagent',
            embedding=embeddings
        )