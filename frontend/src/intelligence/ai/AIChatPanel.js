import React, { useRef, useState } from 'react';
import { aiChat } from '../services/intelApi';

export default function AIChatPanel({ open, onClose, context, aiConfig }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I can help you configure your comparison rules. Describe what you want to compare and I\'ll guide you.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const data = await aiChat(input, context, aiConfig);
      const reply = data.error
        ? `Error: ${data.error}`
        : (data.response || 'No response received.');
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Failed to reach AI. Check your API key in settings.' }]);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-white shadow-2xl border-l border-gray-200 flex flex-col z-50">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-blue-600 text-white">
        <div className="flex items-center gap-2">
          <span className="text-lg">✨</span>
          <p className="font-semibold text-sm">AI Assistant</p>
        </div>
        <button onClick={onClose} className="text-white/80 hover:text-white transition-colors">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {/* Render markdown-like ```json blocks */}
              {msg.content.split('```').map((part, pi) => {
                if (pi % 2 === 1) {
                  const code = part.replace(/^json\n/, '');
                  return (
                    <pre key={pi} className="bg-gray-800 text-green-300 text-xs rounded p-2 my-1 overflow-x-auto whitespace-pre-wrap">
                      {code}
                    </pre>
                  );
                }
                return <span key={pi} style={{ whiteSpace: 'pre-wrap' }}>{part}</span>;
              })}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-xl px-3 py-2 text-sm text-gray-500">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-200 p-3">
        <div className="flex gap-2">
          <input
            className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Ask about comparison rules..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
