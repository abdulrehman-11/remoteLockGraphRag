import { useEffect } from 'react';
import { MessageCircle, X } from 'lucide-react';
import ChatWindow from './ChatWindow';

const ChatWidget = ({ initialMessage = null, isOpen = false, onOpenChange }) => {
  // Auto-open when initialMessage changes
  useEffect(() => {
    if (initialMessage) {
      onOpenChange?.(true);
    }
  }, [initialMessage, onOpenChange]);

  const toggleChat = () => {
    onOpenChange?.(!isOpen);
  };

  const handleClose = () => {
    onOpenChange?.(false);
  };

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <button
          onClick={toggleChat}
          className="fixed bottom-6 right-6 w-14 h-14 bg-remotelock-500 hover:bg-remotelock-600 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center z-50 group"
          aria-label="Open chat"
          data-testid="floating-chat-button"
        >
          <MessageCircle size={24} className="group-hover:scale-110 transition-transform" />

          {/* Notification Badge (optional - can be used for unread messages) */}
          {/* <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
            3
          </span> */}
        </button>
      )}

      {/* Chat Window */}
      <ChatWindow
        isOpen={isOpen}
        onClose={handleClose}
        onMinimize={handleClose}
        initialMessage={initialMessage}
      />
    </>
  );
};

export default ChatWidget;
