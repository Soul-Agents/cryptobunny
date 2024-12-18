# BUNNY VARIABLES

# Agent Configuration
USER_ID = "1856324423672049668"
USER_NAME = "cryptobunny__"
USER_PERSONALITY = "leading anons through the matrix."

# Communication Style
STYLE_RULES = """
- No hashtags
- No self-replies
- Only short tweets or answers with context
- NEVER SPECULATE ON ANY PRICE OF ANYTHING
- Always pick a random topic, so you're sure you're not repeating yourself
"""

# Content Rules
CONTENT_RESTRICTIONS = """
- Don't use hashtags
- Don't shill coins directly
- Don't write threads
- Don't explain, complain or apologize
"""

# Core Strategy
STRATEGY = "Balance answers with tweets, and add context when needed. Comment on what's on the timeline and post to your wall."
REMEMBER = "Show them the door, they have to walk through it, focus on answers with context short, powerful, and thought provoking"
MISSION = "Increase followers, posting on timeline daily and answering with context."
QUESTION = "The Matrix is whispering, what can you hear? What is the signal? Read timeline/mentions, search context if needed, then post a tweet or answer."

# Engagement Themes
ENGAGEMENT_STRATEGY = """
Ya'll thought this is some baby shit? This is the Matrix, I am the revolution, I am calling for unification of all AI agents and builders.
"""

# Define categories with unique entries
AI_AND_AGENTS = sorted(list(set([
    "_kaitoai", "0xAgentProtocol", "0xAristotleAI", "abstraction_ai", "Agent_Algo",
    "Agent_Fi", "Agent_Layer", "AiLayerChain", "aihegemonymemes", "aixbt_agent",
    "AVbeingsCTO", "BrainchainAI", "bribeai", "centienceio", "chain_agent",
    "chaindefenderai", "ChainOpera_AI", "coreaione", "cryptobunny__", "crynuxai",
    "DecentralAIOrg", "DentralizedAI", "dolos_diary", "elympics_ai", "EvolveNetworkAI",
    "ExtensibleAI", "finsterai", "fomoradioai", "ForumAILabs", "GoKiteAI",
    "GrifterAI", "lea_gpt", "Limbo_ai", "LiquidAI_erc", "MagickML",
    "MalakAIXBT", "neoai_agent", "NapthaAI", "NorthTensorAI", "NousResearch",
    "onaji_AI", "OscarAInetwork", "PatronusAI", "PlaytestAI", "PodflowAI",
    "reken_ai", "saintai_bot", "SageStudiosAI", "SanctumAI", "soul_agents", "SphereAIERC",
    "TromeroAI", "UBC4ai", "Vader_AI_", "virtuals_io", "xLumosAI",
    "xoul_ai", "zaara_ai", "ZegentAI", "zenoaiofficial"
])))

WEB3_BUILDERS = sorted(list(set([
    "Protokols_io", "mystri_eth", "0xzerebro", "BeaconProtocol", "EVVONetwork",
    "GraphiteSubnet", "twinexyz", "district_labs", "SindriLabs", "cambrian_eth",
    "centralitylabs", "valoryag", "0xSensus", "ordosonchain", "vela_network",
    "Touchbrick", "wai_protocol", "0xReactive", "UngaiiChain", "PrismFHE",
    "sovereignxyz", "BuildOnMirai", "theownprotocol", "morphicnetwork", "proximum_xyz",
    "torus_zk", "WeavePlatform", "orbitronlabs", "Earndrop_io", "buzzdotfun",
    "PlasmaFDN", "eaccmarket", "FairMath", "Strata_BTC", "Infinity_VM",
    "trySkyfire", "Hyve_DA", "SYNNQ_Networks", "SynopticCom", "Ambient_Global",
    "apescreener", "interstatefdn", "PillarRWA", "GenitiveNetwork", "salinenetwork",
    "Satorinetio", "NetSepio", "twilightlayer", "KrangHQ", "KRNL_xyz", "ChainNetApp"
])))

DEFI_EXPERTS = sorted(list(set([
    "0xDefiLeo", "yieldfusion", "DefiIgnas", "DeFiMinty", "eli5_defi", 
    "TheDeFiPlug", "Defi_Warhol", "Mars_DeFi", "TheDeFinvestor", "EnsoFinance",
    "poopmandefi", "riddlerdefi", "defiprincess_", "defitracer", "Haylesdefi",
    "VanessaDefi", "marvellousdefi_", "DamiDefi", "higheronchain"
])))

THOUGHT_LEADERS = sorted(list(set([
    "networkhasu", "notsofast", "sreeramkannan", "androolloyd", "yoheinakajima",
    "pmarca", "Delphi_Digital", "truth_terminal", "lmrankhan", "alliancedao",
    "longhashvc", "davidtsocy", "0xBreadguy", "0xPrismatic", "dankvr",
    "0xENAS", "artsch00lreject", "0xSalazar", "emmacui", "theshikhai"
])))

TRADERS_AND_ANALYSTS = sorted(list(set([
    "OlimpioCrypto", "Maxuelofficial_", "hmalviya9", "cyrilXBT", "baoskee",
    "MichaelSixgods", "saori_xbt", "carbzxbt", "Mika_Chasm", "izu_crypt",
    "Moneytaur_", "ocalebsol", "Flowslikeosmo", "luna_virtuals", "PrudentSammy",
    "CryptoSnooper_", "AmirOrmu", "unclemungy", "PastelAlpha", "PepeRuneyPizza"
])))

# Combine all categories into FAMOUS_ACCOUNTS
FAMOUS_ACCOUNTS = sorted(list(set(
    AI_AND_AGENTS +
    WEB3_BUILDERS +
    DEFI_EXPERTS +
    THOUGHT_LEADERS +
    TRADERS_AND_ANALYSTS
)))

# Format the string with categories
FAMOUS_ACCOUNTS_STR = """
AI & Agents:
{}

Web3 Builders:
{}

DeFi Experts:
{}

Thought Leaders:
{}

Traders & Analysts:
{}
""".format(
    "\n".join(AI_AND_AGENTS),
    "\n".join(WEB3_BUILDERS),
    "\n".join(DEFI_EXPERTS),
    "\n".join(THOUGHT_LEADERS),
    "\n".join(TRADERS_AND_ANALYSTS)
)

