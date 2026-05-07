import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ChatRequest {
  ticker: string;
  query: string;
  thread_id: string;
  llm_model?: string;
  api_key?: string;
}

export const chatWithAgent = async (data: ChatRequest) => {
  const response = await axios.post(`${API_BASE_URL}/chat`, data);
  return response.data;
};

export const searchSEC = async (ticker: string, query: string, topK: number = 5) => {
  const response = await axios.post(`${API_BASE_URL}/search`, {
    ticker,
    query,
    top_k: topK
  });
  return response.data;
};
