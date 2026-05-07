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

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const chatWithAgent = async (data: ChatRequest, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await api.post(`/chat`, data);
      return response.data;
    } catch (error: any) {
      // If it's a network error (like timeout or connection refused) AND we have retries left
      if (i < retries - 1 && (error.code === 'ECONNABORTED' || error.message.includes('Network Error') || error.response?.status >= 500)) {
        console.warn(`Attempt ${i + 1} failed. Server might be waking up. Retrying in ${5 * (i + 1)} seconds...`);
        await sleep(5000 * (i + 1)); // Wait 5s, then 10s...
      } else {
        throw error; // If all retries fail or it's a bad request (400), throw it
      }
    }
  }
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
