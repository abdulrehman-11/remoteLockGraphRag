import { useState } from 'react';
import { Send } from 'lucide-react';
import { clsx } from 'clsx';

const ChatInput = ({ onSend, disabled = false, placeholder = 'Type your message...' }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4 bg-white">
      <div className="flex items-end space-x-2">
        <div className="flex-1">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={clsx(
              'w-full px-4 py-2.5 border border-gray-300 rounded-lg',
              'focus:outline-none focus:ring-2 focus:ring-remotelock-500 focus:border-transparent',
              'resize-none transition-all duration-200',
              'disabled:bg-gray-100 disabled:cursor-not-allowed',
              'text-sm'
            )}
            style={{
              minHeight: '42px',
              maxHeight: '120px',
            }}
          />
          <p className="text-xs text-gray-400 mt-1">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className={clsx(
            'bg-remotelock-500 text-white rounded-lg px-4 py-2.5',
            'hover:bg-remotelock-600 transition-colors duration-200',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'flex items-center justify-center',
            'shadow-elevation-sm hover:shadow-elevation-md'
          )}
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </div>
    </form>
  );
};

export default ChatInput;
