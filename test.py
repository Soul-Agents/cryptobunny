from app.utils.db import get_db
from main import set_global_agent_variables, run_crypto_agent
def run_agent():
    db = get_db()
        
    # Get all active and paid agents
    active_agents = db.get_all_active_paid_agents()
    # print(active_agents, "active_agents")

    agent = active_agents[3]
    print(agent, "agent")
    # twitter_auth = db.get_twitter_auth(agent["client_id"])
    # print(twitter_auth, "twitter_auth")
    set_global_agent_variables(agent)
    run_crypto_agent(agent)
    # agent_config = db.get_agent_config(agent["client_id"])
    # print(agent_config, "agent_config")
    
    
run_agent()

