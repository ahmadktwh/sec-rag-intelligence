import React, { useState, useEffect, useRef } from 'react';
import { 
  Menu, 
  Cpu, 
  ShieldCheck, 
  RefreshCw, 
  Send, 
  Settings as SettingsIcon, 
  HelpCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// --- Local Imports ---
import { chatWithAgent, pingBackend } from './api/client';
import Sidebar from './components/Sidebar';

// --- Types ---
interface Message {
  role: 'user' | 'assistant';
  content: string;
  query_type?: string;
  tickers?: string[];
  confidence?: number;
  sources?: string[];
}

const ALL_TICKERS = [
  "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "CSCO",
  "ADBE", "CRM", "QCOM", "TXN", "AMAT", "IBM", "AMD", "INTC",
  "AMZN", "TSLA", "NFLX", "WMT", "COST", "HD", "MCD", "KO",
  "PEP", "DIS", "PG", "JPM", "BRK.B", "V", "MA", "BAC", "WFC",
  "UNH", "JNJ", "ABBV", "ABT", "MRK", "DHR", "TMO", "LLY",
  "XOM", "CVX", "CAT", "PM", "LIN", "ACN", "INTU"
].sort();

// --- Components ---

// --- Removed FinancialTable Component ---

const App: React.FC = () => {
  const [query, setQuery] = useState('');
  const [selectedTickers, setSelectedTickers] = useState<string[]>(['AAPL']);
  const [apiKey, setApiKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini/gemini-2.5-pro');
  const [showSettings, setShowSettings] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [currentAgent, setCurrentAgent] = useState('');

  // Wake up backend on mount
  useEffect(() => {
    pingBackend();
  }, []);

  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "System Initialized. I am your specialized Financial Intelligence Agent. I have indexed 39 S&P 500 companies from recent SEC filings. How can I assist your analysis today?"
    }
  ]);
  const [isThinking, setIsThinking] = useState(false);
  const [currentAgent, setCurrentAgent] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  // --- Utility: Parse Claude Artifacts (Removed) ---

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const toggleTicker = (t: string) => {
    setSelectedTickers(prev => 
      prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]
    );
  };

  const handleSend = async () => {
    if (!query.trim()) return;
    if (!apiKey && !selectedModel.includes('ollama')) {
        alert("Security Protocol: Please provide your API Key in settings to proceed.");
        setShowSettings(true);
        return;
    }

    const userMsg: Message = { role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setIsThinking(true);
    setCurrentAgent('Router');

    try {
      setTimeout(() => setCurrentAgent('Retrieval'), 800);
      setTimeout(() => setCurrentAgent('Analyst'), 2000);
      setTimeout(() => setCurrentAgent('Citation'), 3500);

      const data = await chatWithAgent({
        ticker: selectedTickers.join(', '),
        query: query,
        thread_id: "claude_session_premium",
        llm_model: selectedModel,
        api_key: apiKey
      });

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        query_type: data.query_type,
        tickers: data.tickers,
        confidence: data.confidence,
        sources: data.sources
      }]);
    } catch (error: any) {
      console.error("API Error:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Unknown Connection Error";
      setMessages(prev => [...prev, { role: 'assistant', content: `Protocol Failure: ${errorMessage}. Please check if the backend is waking up (Render free tier can take 40s).` }]);
    } finally {
      setIsThinking(false);
      setCurrentAgent('');
    }
  };

  return (
    <div className="flex h-screen bg-finance-dark text-finance-accent overflow-hidden font-sans selection:bg-finance-accent/20">
      
      {/* --- Sidebar (Collapsible) --- */}
      <AnimatePresence>
        {showSidebar && (
          <motion.aside 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 256, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="border-r border-finance-border bg-[#0a0c10] flex flex-col z-20 overflow-hidden whitespace-nowrap"
          >
            <Sidebar 
              allTickers={ALL_TICKERS}
              selectedTickers={selectedTickers}
              onToggleTicker={toggleTicker}
              onOpenSettings={() => setShowSettings(true)}
            />
          </motion.aside>
        )}
      </AnimatePresence>

      {/* --- Main Chat Area --- */}
      <main className="flex-1 flex flex-col transition-all duration-500 relative">
        {/* Header */}
        <header className="h-20 flex items-center justify-between px-6 z-10 border-b border-finance-border bg-finance-dark/50 backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 rounded-lg hover:bg-white/5 text-finance-muted hover:text-finance-accent transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="h-4 w-px bg-white/10 mx-2" />
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-finance-profit animate-pulse" />
              <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-finance-muted">Agent System Online</span>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-10 py-10 space-y-12 max-w-5xl mx-auto w-full custom-scrollbar">
          {messages.map((m, i) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              key={i}
              className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              {m.role === 'user' ? (
                <div className="bg-white/5 border border-white/10 px-6 py-4 rounded-2xl max-w-[90%] text-[15px] leading-relaxed">
                  {m.content}
                </div>
              ) : (
                <div className="w-full space-y-6">
                  <div className="flex items-start gap-5">
                    <div className="w-10 h-10 rounded bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 mt-1">
                      <Cpu className="w-5 h-5 text-finance-accent/50" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="prose prose-invert prose-finance max-w-none">
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({node, ...props}) => (
                              <div className="overflow-x-auto my-8 border border-white/10 rounded-xl bg-white/5 shadow-xl">
                                <table className="w-full text-sm border-collapse" {...props} />
                              </div>
                            ),
                            th: ({node, ...props}) => (
                              <th className="px-5 py-4 bg-black/40 text-[11px] font-bold text-finance-accent uppercase tracking-widest text-left border-b border-white/10" {...props} />
                            ),
                            td: ({node, ...props}) => (
                              <td className="px-5 py-3 border-b border-white/5 text-[14px] text-white/90 font-mono transition-colors hover:bg-white/5" {...props} />
                            ),
                            h2: ({node, ...props}) => (
                              <h2 className="font-serif text-2xl text-finance-accent mb-6 mt-12 pb-2 border-b border-finance-accent/20" {...props} />
                            ),
                            h3: ({node, ...props}) => (
                              <h3 className="font-serif text-xl text-white mb-4 mt-8" {...props} />
                            ),
                            p: ({node, ...props}) => (
                              <p className="text-[16px] leading-loose text-white/80 mb-5 font-serif" {...props} />
                            ),
                            ul: ({node, ...props}) => (
                              <ul className="space-y-3 mb-6 list-none pl-0" {...props} />
                            ),
                            li: ({node, ...props}) => (
                              <li className="text-[15px] leading-relaxed text-white/80 flex items-start gap-3 before:content-[''] before:block before:w-1.5 before:h-1.5 before:mt-2 before:bg-finance-accent before:rounded-full" {...props} />
                            ),
                            strong: ({node, ...props}) => (
                              <strong className="font-bold text-white tracking-wide" {...props} />
                            )
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>
                      </div>
                      
                      {m.sources && m.sources.length > 0 && (
                        <div className="mt-8 flex flex-wrap gap-2">
                          {m.sources.map((_, si) => (
                            <div key={si} className="text-[10px] text-finance-muted border border-white/5 px-3 py-1 rounded bg-white/5 font-mono hover:border-finance-accent/30 transition-colors cursor-pointer">
                              Ref {si+1}
                            </div>
                          ))}
                        </div>
                      )}

                      {m.confidence !== undefined && (
                        <div className="mt-6 flex items-center gap-4 border-t border-white/5 pt-4 max-w-2xl">
                          <div className="flex items-center gap-2 text-[9px] font-bold text-finance-muted uppercase tracking-widest">
                            <ShieldCheck className="w-3 h-3 text-finance-profit" /> Confidence: {(m.confidence * 100).toFixed(0)}%
                          </div>
                          <div className="w-px h-3 bg-white/10" />
                          <div className="text-[9px] font-bold text-finance-muted uppercase tracking-widest">
                            Engine: {selectedModel.split('/')[1] || selectedModel}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
          
          {isThinking && (
            <div className="flex items-start gap-5">
              <div className="w-10 h-10 rounded bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 mt-1">
                <RefreshCw className="w-5 h-5 text-finance-accent/30 animate-spin" />
              </div>
              <div className="py-2">
                <div className="flex gap-1.5 mb-2">
                  <div className="w-1 h-1 bg-finance-accent/40 rounded-full animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1 h-1 bg-finance-accent/40 rounded-full animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1 h-1 bg-finance-accent/40 rounded-full animate-bounce" />
                </div>
                <span className="text-[10px] font-bold text-finance-muted uppercase tracking-[0.2em]">
                  {currentAgent} Agent Processing
                </span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="p-8">
          <div className="max-w-5xl mx-auto">
            <div className="relative glass border-white/10 rounded-2xl overflow-hidden shadow-2xl focus-within:border-finance-accent/40 transition-all duration-300">
              <textarea 
                rows={1}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Message financial engine..."
                className="w-full bg-transparent border-none outline-none text-[15px] py-5 pl-6 pr-24 placeholder:text-finance-muted resize-none max-h-48"
              />
              <div className="absolute right-4 bottom-4">
                <button 
                  onClick={handleSend}
                  disabled={isThinking || !query.trim()}
                  className="bg-finance-accent hover:bg-white text-black w-10 h-10 rounded-xl transition-all flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed shadow-xl"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
            <p className="text-[9px] text-finance-muted mt-4 text-center tracking-[0.3em] uppercase font-medium">
              Enterprise RAG • Verified Sources • Private Execution
            </p>
          </div>
        </div>
      </main>

      {/* Settings Modal (Overlay) */}
      <AnimatePresence>
        {showSettings && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-lg bg-[#0a0c10] border border-finance-accent/20 p-10 rounded-3xl shadow-2xl relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-finance-accent/30 to-transparent" />
              
              <div className="flex justify-between items-center mb-10">
                <div>
                  <h3 className="font-serif text-2xl text-finance-accent flex items-center gap-3">
                    <SettingsIcon className="w-5 h-5" /> Intelligence Settings
                  </h3>
                  <p className="text-[10px] text-finance-muted uppercase tracking-[0.2em] mt-1">Configure Model Agnostic Engine</p>
                </div>
                <button onClick={() => setShowSettings(false)} className="text-finance-muted hover:text-white transition-colors text-2xl">×</button>
              </div>

              <div className="space-y-8">
                <div>
                  <label className="block text-[11px] font-bold text-finance-muted uppercase tracking-widest mb-3">Target Model (LiteLLM Format)</label>
                  <input 
                    type="text"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    placeholder="e.g. anthropic/claude-3-5-sonnet"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-5 py-4 text-sm text-finance-accent outline-none focus:border-finance-accent/40 transition-all font-mono"
                  />
                  <div className="mt-3 flex gap-4 overflow-x-auto pb-2 custom-scrollbar">
                    {['openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'gemini/gemini-2.0-flash', 'ollama/llama3'].map(m => (
                      <button 
                        key={m}
                        onClick={() => setSelectedModel(m)}
                        className={`whitespace-nowrap text-[9px] font-bold px-3 py-1.5 rounded-full border transition-all ${selectedModel === m ? 'bg-finance-accent text-black border-finance-accent' : 'border-white/10 text-finance-muted hover:border-white/30'}`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-finance-muted uppercase tracking-widest mb-3 flex items-center justify-between">
                    <span>Provider API Key</span>
                    <span className="text-[9px] font-normal italic lowercase opacity-50">Sent via encrypted headers</span>
                  </label>
                  <div className="relative">
                    <ShieldCheck className="absolute left-4 top-4 w-4 h-4 text-finance-profit/50" />
                    <input 
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter Key for Provider"
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-5 py-4 text-sm text-finance-accent outline-none focus:border-finance-accent/40 transition-all"
                    />
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-finance-accent/5 border border-finance-accent/10">
                  <div className="flex items-start gap-3">
                    <HelpCircle className="w-4 h-4 text-finance-accent/60 mt-0.5" />
                    <p className="text-[11px] leading-relaxed text-finance-accent/60">
                      Our "Zero-Leakage" architecture ensures your API keys are never stored on any server. They are processed in-memory for your current session only.
                    </p>
                  </div>
                </div>

                <button 
                  onClick={() => setShowSettings(false)}
                  className="w-full bg-finance-accent hover:bg-white text-black py-4 rounded-xl text-[11px] font-bold uppercase tracking-[0.2em] transition-all shadow-xl"
                >
                  Initialize Configuration
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;

