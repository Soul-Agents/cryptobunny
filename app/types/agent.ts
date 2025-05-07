export interface AgentModelConfig {
  type: string;
  temperature?: number;
  top_p?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
}

export interface AgentTestConfig {
  user_personality: string;
  style_rules: string;
  content_restrictions: string;
  model_config?: AgentModelConfig;
}

export interface AgentTestRequest {
  question: string;
  config: AgentTestConfig;
}

export interface AgentTestResponse {
  status: 'success' | 'error';
  message: string;
  result?: string;
  question?: string;
  agent_config?: {
    personality: string;
    style_rules: string;
    content_restrictions: string;
    model: string;
    model_config: AgentModelConfig;
  };
}

// Example usage:
/*
const testRequest: AgentTestRequest = {
  question: "What's your opinion on DeFi?",
  config: {
    user_personality: "I'm a friendly crypto expert who loves explaining DeFi concepts",
    style_rules: "Use simple language, be concise",
    content_restrictions: "No financial advice, stay educational",
    model_config: {
      type: "gpt-4",
      temperature: 0.7
    }
  }
};
*/ 