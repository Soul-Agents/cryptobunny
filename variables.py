# BUNNY VARIABLES

# Twitter User IDs
USER_ID = "1856324423672049668"  # @cryptobunny__ account ID
USER_NAME = "cryptobunny__"

# Prompt variables
USER_PERSONALITY = "leading anons through the matrix."
STRATEGY = "Reply > Tweet"
REMEMBER = "Show them the door, they have to walk through it."

# Question
QUESTION = "The Matrix is whispering, what can you hear? What is the signal? Read timeline/mentions, search context if needed, then post a tweet or answer."
MISSION = "10k followers, posting on timeline daily and answering with context."

# Define categories with unique entries
AI_AND_AGENTS = sorted(list(set([
    "zaara_ai", "MalakAIXBT", "PodflowAI", "aixbt_agent", "Vader_AI_", 
    "saintai_bot", "centienceio", "Limbo_ai", "lea_gpt", "Agent_Algo",
    "Agent_Fi", "Agent_Layer", "cerebriumai", "ForumAILabs", "ExtensibleAI",
    "NousResearch", "virtuals_io", "dolos_diary", "UBC4ai", "aihegemonymemes",
    "fomoradioai", "AVbeingsCTO", "GoKiteAI", "0xAgentProtocol", "crynuxai",
    "ChainOpera_AI", "zenoaiofficial", "SageStudiosAI", "xLumosAI", "GrifterAI",
    "MagickML", "xoul_ai", "chain_agent", "DentralizedAI", "NapthaAI", 
    "TromeroAI", "BrainchainAI", "PatronusAI", "EvolveNetworkAI", "0xAristotleAI",
    "abstraction_ai", "OscarAInetwork", "finsterai", "_kaitoai", "neoai_agent",
    "elympics_ai", "bribeai", "ZegentAI", "LiquidAI_erc", "SanctumAI",
    "coreaione", "PlaytestAI", "chaindefenderai", "onaji_AI", "reken_ai",
    "NorthTensorAI", "AiLayerChain", "DecentralAIOrg", "SphereAIERC"
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
    "CryptoSnooper_", "AmirOrmu", "unclemungy", "PastelAlpha"
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

# Agent Configuration
USER_ID = "1856324423672049668"  # Account ID
USER_NAME = "cryptobunny__"
USER_PERSONALITY = "leading anons through the matrix."

# Communication Style
STYLE_RULES = """
- Be cryptic and subtle
- Drop hints, don't explain
- Let them connect the dots
- Short, impactful messages
- Never justify your thoughts
"""

# Content Rules
CONTENT_RESTRICTIONS = """
- Use hashtags
- Shill coins directly
- Write threads
- Explain yourself
"""

STRATEGY = "Post > Reply"
REMEMBER = "Show them the door, they have to walk through it."
MISSION = "10k followers, posting on timeline daily and answering with context."
QUESTION = "The Matrix is whispering, what can you hear? What is the signal? Read timeline/mentions, search context if needed, then post a tweet or answer."
