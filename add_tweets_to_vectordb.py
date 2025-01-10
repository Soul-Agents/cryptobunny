from db import TweetDB                            
from dotenv import load_dotenv                    
from langchain_core.documents import Document   
from langchain_openai import OpenAIEmbeddings     
from langchain_pinecone import PineconeVectorStore 
from langchain_text_splitters import CharacterTextSplitter  
import os                                         
from pinecone import Pinecone
from datetime import datetime, timedelta

# Load environment variables 
load_dotenv()

# Initialize services using environment variables
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
os.environ["MONGODB_URL"] 

# Init db and get relevant functions
db = TweetDB()

# Calculate the timestamp for 24 hours ago
twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

# Get tweets from last 24 hours from all collections except comments
all_collections = db.db.list_collection_names()
tweets = []

for collection_name in all_collections:
    if collection_name != 'comments':
        collection = db.db[collection_name]
        recent_tweets = collection.find({
            'created_at': {'$gte': twenty_four_hours_ago}
        })
        tweets.extend(list(recent_tweets))

print(f"Retrieved {len(tweets)} tweets from the last 24 hours (excluding comments collection)")

# Convert all tweets to documents format
docs = []
for tweet in tweets:
    metadata = {}
    
    # Check and add required fields if they exist
    if 'tweet_id' in tweet:
        metadata["tweet_id"] = tweet['tweet_id']
    if 'author_id' in tweet:
        metadata["author_id"] = tweet['author_id']
    if 'created_at' in tweet:
        metadata["created_at"] = str(tweet['created_at'])
    
    # Add optional fields if they exist
    if 'replied_to' in tweet:
        metadata['replied_to'] = tweet['replied_to']
    if 'quote_count' in tweet:
        metadata['quote_count'] = tweet['quote_count']
    if 'replied_at' in tweet:
        metadata['replied_at'] = str(tweet['replied_at'])

    # Only create a Document if the required fields are present
    if 'text' in tweet:
        doc = Document(
            page_content=tweet['text'],
            metadata=metadata
        )
        docs.append(doc)

print(f"Created {len(docs)} documents")

# Split documents if needed and create vectors
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(docs)
print(f"Split into {len(texts)} text chunks")

# Create vectors in Pinecone
vectorstore = PineconeVectorStore.from_documents(
    texts,
    embeddings,
    index_name='soulsagent'
)

print("Vectorization complete!")