import { useState, useRef, useEffect } from 'react';
import { X, Trash2, Minimize2 } from 'lucide-react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import TypingIndicator from './TypingIndicator';
import Button from '../common/Button';
import {
  getApiBase,
  sanitizeReply,
  saveConversationHistory,
  loadConversationHistory,
  clearConversationHistory,
} from '../../utils/chatHelpers';

const ChatWindow = ({ isOpen, onClose, onMinimize, initialMessage = null }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Load conversation history on mount
  useEffect(() => {
    const history = loadConversationHistory();
    if (history.length > 0) {
      setMessages(history);
    }
  }, []);

  // Save conversation history whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      saveConversationHistory(messages);
    }
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Handle initial message (from category click or hero search)
  useEffect(() => {
    if (initialMessage && messages.length === 0) {
      handleSendMessage(initialMessage);
    }
  }, [initialMessage]);

  const handleSendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    const userMessage = {
      text: messageText,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const apiBase = getApiBase();
      const response = await fetch(`${apiBase.replace(/\/$/, '')}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const rawReply = data.response || 'Sorry, no reply.';
      const botReply = sanitizeReply(rawReply);

      const botMessage = {
        text: botReply,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        sources: data.sources || [], // Future: backend will provide sources
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error('Chat request failed:', error);
      setMessages((prev) => [
        ...prev,
        {
          text: "Sorry, I'm having trouble connecting right now. Please try again later.",
          sender: 'bot',
          timestamp: new Date().toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([]);
    clearConversationHistory();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-4 right-4 w-[400px] h-[600px] bg-white rounded-lg shadow-2xl flex flex-col z-50 animate-slide-up" data-testid="chat-window">
      {/* Header */}
      <div className="bg-remotelock-500 text-white px-4 py-3 rounded-t-lg flex items-center justify-between" data-testid="chat-header">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect
                x="3"
                y="10"
                width="18"
                height="11"
                rx="2"
                stroke="white"
                strokeWidth="1.5"
                fill="none"
              />
              <path
                d="M7 10V7a5 5 0 0110 0v3"
                stroke="white"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-sm">RemoteLock Support</h3>
            <p className="text-xs text-white/70">AI Assistant</p>
          </div>
        </div>
        <div className="flex items-center space-x-1">
          {messages.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="p-1.5 hover:bg-white/10 rounded transition-colors"
              aria-label="Clear chat history"
            >
              <Trash2 size={16} />
            </button>
          )}
          {onMinimize && (
            <button
              onClick={onMinimize}
              className="p-1.5 hover:bg-white/10 rounded transition-colors"
              aria-label="Minimize chat"
            >
              <Minimize2 size={16} />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/10 rounded transition-colors"
            aria-label="Close chat"
            data-testid="chat-close-button"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50" data-testid="chat-messages-area">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4" data-testid="chat-welcome-message">
            <div className="w-16 h-16 bg-remotelock-50 rounded-full flex items-center justify-center mb-4">
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect
                  x="3"
                  y="10"
                  width="18"
                  height="11"
                  rx="2"
                  stroke="#0176d3"
                  strokeWidth="1.5"
                  fill="none"
                />
                <path
                  d="M7 10V7a5 5 0 0110 0v3"
                  stroke="#0176d3"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">
              Hi there! I'm your RemoteLock Support Assistant.
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              How can I help you today?
            </p>
            <div className="grid grid-cols-1 gap-2 w-full">
              {[
                'How do I reset my lock?',
                'Setup guest access codes',
                'Troubleshooting connection issues',
              ].map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  onClick={() => handleSendMessage(suggestion)}
                  className="text-left justify-start"
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, index) => (
          <ChatMessage
            key={index}
            message={msg.text}
            sender={msg.sender}
            sources={msg.sources}
            timestamp={msg.timestamp}
          />
        ))}

        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <ChatInput
        onSend={handleSendMessage}
        disabled={isLoading}
        placeholder="Ask me anything about RemoteLock..."
      />
    </div>
  );
};

export default ChatWindow;
