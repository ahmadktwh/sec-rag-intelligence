import React from 'react';
import { BarChart3, Settings as SettingsIcon } from 'lucide-react';

interface SidebarProps {
  allTickers: string[];
  selectedTickers: string[];
  onToggleTicker: (t: string) => void;
  onOpenSettings: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  allTickers, 
  selectedTickers, 
  onToggleTicker, 
  onOpenSettings 
}) => {
  return (
    <div className="p-8 pb-4 w-64 h-full flex flex-col">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-8 h-8 rounded bg-finance-accent flex items-center justify-center">
          <BarChart3 className="text-black w-5 h-5" />
        </div>
        <h1 className="font-serif text-lg font-medium tracking-tight">SEC Insight</h1>
      </div>

      <div className="space-y-6 flex-1 overflow-hidden flex flex-col">
        <div>
          <p className="text-[10px] font-bold text-finance-muted uppercase tracking-[0.2em] mb-4">Coverage</p>
          <div className="space-y-1 h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
            {allTickers.map((t) => (
              <button 
                key={t}
                onClick={() => onToggleTicker(t)}
                className={`w-full flex items-center justify-between px-3 py-1.5 rounded transition-all text-[12px] ${selectedTickers.includes(t) ? 'bg-white/5 text-finance-accent border border-white/10' : 'text-finance-muted hover:text-finance-accent hover:bg-white/5 border border-transparent'}`}
              >
                <span className="font-mono">{t}</span>
                {selectedTickers.includes(t) && <div className="w-1.5 h-1.5 rounded-full bg-finance-profit shadow-[0_0_8px_#a7c080]" />}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-finance-border bg-black/20">
        <button 
          onClick={onOpenSettings}
          className="flex items-center gap-3 w-full p-2 rounded hover:bg-white/5 transition-colors group"
        >
          <div className="w-8 h-8 rounded-full border border-white/10 flex items-center justify-center text-[10px] text-finance-muted group-hover:text-finance-accent">
            <SettingsIcon className="w-4 h-4" />
          </div>
          <div className="text-left whitespace-nowrap">
            <p className="text-[11px] font-bold">Engine Settings</p>
            <p className="text-[9px] text-finance-muted">BYOK Mode Active</p>
          </div>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
