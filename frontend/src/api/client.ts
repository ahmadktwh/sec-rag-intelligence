import axios from 'axios';

// Change this to your deployed Render/AWS URL for the Public Demo
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://sec-rag-intelligence.onrender.com'; 

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds for Render wake-up + AI processing
});

export interface ChatRequest {
  ticker: string;
  query: string;
  thread_id: string;
  llm_model?: string;
  api_key?: string;
}

export const chatWithAgent = async (data: ChatRequest) => {
  const response = await api.post(`/chat`, data);
  return response.data;
};

export const searchSEC = async (ticker: string, query: string, topK: number = 5) => {
  const response = await api.post(`/search`, {
    ticker,
    query,
    top_k: topK
  });
  return response.data;
};

export const pingBackend = async () => {
  try {
    const response = await api.get('/');
    return response.data;
  } catch (e) {
    console.log("Wakeup ping sent...");
  }
};
