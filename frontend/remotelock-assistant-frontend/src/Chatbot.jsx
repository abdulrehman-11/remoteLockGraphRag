import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.css'; // Link to our chatbot specific styles

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false); // Controls chat window visibility
  const [messages, setMessages] = useState([]); // Stores chat messages
  const [inputValue, setInputValue] = useState(''); // Stores current input field value
  const [isLoading, setIsLoading] = useState(false); // Shows typing indicator
  const messagesEndRef = useRef(null); // Ref for auto-scrolling to the latest message

  // Effect to scroll to the bottom of the messages display whenever new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]); // Also re-scroll when loading state changes

  // Toggles the chat window open/closed
  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  // Handles sending a user message and triggering a bot response
  const handleSendMessage = async (e) => {
    e.preventDefault(); // Prevent default form submission behavior
    if (inputValue.trim() === '') return; // Don't send empty messages

    const newUserMessage = { text: inputValue, sender: 'user' };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]); // Add user message
    const messageToSend = inputValue;
    setInputValue(''); // Clear input field

    // Send message to backend chat endpoint
    setIsLoading(true);
    try {
      const API_BASE = (import.meta && import.meta.env && import.meta.env.VITE_API_URL) ? import.meta.env.VITE_API_URL : 'http://localhost:8000';
      console.log({api: import.meta.env.VITE_API_URL, base: API_BASE});
      const resp = await fetch(`${API_BASE.replace(/\/$/, '')}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageToSend }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      console.log('Backend response data:', data); // Add this line
      const rawReply = data.response || "Sorry, no reply.";
      const botReply = sanitizeReply(rawReply);
      setMessages((prevMessages) => [...prevMessages, { text: botReply, sender: 'bot' }]);
    } catch (err) {
      console.error('Chat request failed', err);
      setMessages((prevMessages) => [...prevMessages, { text: "Sorry, I'm having trouble connecting right now.", sender: 'bot' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Simple keyword-based bot response logic - KEPT AS IS
  const generateBotResponse = (userMessage) => {
    const lowerCaseMessage = userMessage.toLowerCase();

    if (lowerCaseMessage.includes('hello') || lowerCaseMessage.includes('hi')) {
      return "Hello! Welcome to RemoteLock Support. How can I assist you today?";
    } else if (lowerCaseMessage.includes('account')) {
      return "For account-related issues, please visit our 'My Account' section or contact our support team directly.";
    } else if (lowerCaseMessage.includes('lock') || lowerCaseMessage.includes('device')) {
      return "Are you having trouble with a specific lock or device? Please provide more details.";
    } else if (lowerCaseMessage.includes('troubleshooting')) {
        return "Our troubleshooting guides can be found on our support page under 'Troubleshooting & FAQs'.";
    } else if (lowerCaseMessage.includes('contact')) {
        return "You can reach our support team via phone at [Your Phone Number] or by submitting a ticket on our 'Contact Us' page.";
    } else if (lowerCaseMessage.includes('thanks') || lowerCaseMessage.includes('thank you')) {
        return "You're welcome! Is there anything else I can help you with?";
    } else {
      return "I'm sorry, I don't understand that. Can you please rephrase or ask about common topics like 'account', 'lock', 'troubleshooting', or 'contact'?";
    }
  };

  // Sanitize and format replies from the LLM/backend
  const sanitizeReply = (text) => {
    if (!text) return '';
    // Remove common control chars and excessive asterisks/markdown artifacts
    let s = text.replace(/\r/g, '')
                .replace(/\*{2,}/g, '')        // remove repeated asterisks
                .replace(/[_~`]{1,}/g, '')      // remove simple markdown markers
                .trim();

    // Remove zero-width and odd invisible characters, collapse multiple whitespace
    s = s.replace(/[\u200B\u200C\u200D\uFEFF]/g, '');
    s = s.replace(/\s{2,}/g, ' ');

    // Collapse weird inter-letter spacing like "R e m o t e" -> "Remote"
    // and collapse newline-separated single letters like:
    // R\n e\n m\n o\n t\n e  -> Remote
    // We'll replace runs of single-letter tokens separated by spaces/newlines with joined words.
    s = s.replace(/(?:\b(?:[A-Za-z](?:[ \t\n\r]+|$)){3,})/g, (match) => {
      // remove whitespace between letters
      const lettersOnly = match.replace(/[^A-Za-z\n\r ]+/g, '').replace(/[\n\r\s]+/g, '');
      return lettersOnly;
    });

    // Split into lines and trim each line
    let lines = s.split('\n').map(l => l.trim()).filter(Boolean);

    // Normalize list markers: convert leading '* ', '- ', '+ ', '• ', or '1.' to a single bullet marker '• '
    const normalized = lines.map((line) => {
      // Match common list prefixes
      const m = line.match(/^\s*([*+\-•]|\d+\.)\s+(.*)$/);
      if (m) return `• ${m[2].trim()}`;
      // If a line itself is a sequence of single letters separated by spaces or newlines, join them
      if (/^(?:[A-Za-z](?:[ \t\n\r]+|$)){2,}$/.test(line)) {
        return line.replace(/[\s\n\r]+/g, '');
      }
      // Also remove stray leading asterisks or bullets
      return line.replace(/^\s*[\*•]\s?/, '').trim();
    }).filter(l => l && !/^\s*[-*]{2,}$/.test(l));

    // If many lines are bullets (start with '• '), keep them as a bullet list separated by newlines
    const bulletCount = normalized.filter(l => l.startsWith('• ')).length;
    if (bulletCount >= 2) {
      return normalized.join('\n');
    }

    // Otherwise collapse multiple blank lines into single paragraph breaks
    const paragraphs = normalized.join('\n').split(/\n{2,}/).map(p => p.trim()).filter(Boolean);
    // Fix pathological cases where characters are spaced out like 'R e m o t e'
    const fixed = paragraphs.map((p) => {
      // If a paragraph has many single-character tokens in a row, join contiguous runs
      const tokens = p.split(/(\s+)/); // keep whitespace tokens
      let out = '';
      let run = [];
      const flushRun = () => {
        if (run.length === 0) return;
        // decide if we should join run tokens
        const runTokens = run.join('').trim().split(/\s+/).filter(Boolean);
        const singleCount = runTokens.filter(t => t.length === 1).length;
        if (runTokens.length > 3 && singleCount / runTokens.length > 0.5) {
          out += runTokens.join('');
        } else {
          out += run.join('');
        }
        run = [];
      };
      for (let tok of tokens) {
        if (/^\s+$/.test(tok)) {
          run.push(tok);
        } else if (tok.length === 1 && /[A-Za-z0-9]/.test(tok)) {
          run.push(tok + ' ');
        } else {
          flushRun();
          out += tok;
        }
      }
      flushRun();
      return out.trim();
    });
    return fixed.join('\n\n');
  };

  // Render text into paragraphs and bullet lists, also detect and format links
  const renderMessageText = (text) => {
    if (!text) return null;

    // Regex to find URLs (http/https, optional www, followed by valid URL characters)
    const urlRegex = /(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/[a-zA-Z0-9]+\.[^\s]{2,}|[a-zA-Z0-9]+\.[^\s]{2,})([\w\/\?#&=.-]*)/gi;

    const formatTextWithLinks = (line) => {
      const parts = [];
      let lastIndex = 0;

      if (typeof line !== 'string') {
        console.error('formatTextWithLinks received non-string line:', line);
        return parts; // Skip processing if line is not a string
      }
      line.replace(urlRegex, (match, urlBase, urlPath, offset) => {
        // Add preceding text as a simple text node
        if (offset > lastIndex) {
          parts.push(line.substring(lastIndex, offset));
        }

        // Construct the full URL and the display text
        const fullUrl = urlBase.startsWith('http') ? urlBase + urlPath : `https://${urlBase}${urlPath}`;
        const displayText = urlBase + urlPath;

        // Add the link
        parts.push(
          <a key={offset} href={fullUrl} target="_blank" rel="noopener noreferrer">
            {displayText}
          </a>
        );
        lastIndex = offset + match.length;
        return match;
      });

      // Add any remaining text
      if (lastIndex < line.length) {
        parts.push(line.substring(lastIndex));
      }
      return parts;
    };


    const paragraphs = text
      .replace(/\r/g, '')
      .split(/\n{2,}/) // Split by double newlines for paragraphs
      .map(p => p.trim())
      .filter(Boolean);

    return paragraphs.map((para, idx) => {
      const lines = para.split(/\n/).map(l => l.trim()).filter(Boolean);
      const listItems = [];
      let currentList = [];

      lines.forEach((line, lineIdx) => {
        if (line.startsWith('• ')) {
          currentList.push(<li key={lineIdx}>{formatTextWithLinks(line.substring(2))}</li>);
        } else {
          if (currentList.length > 0) {
            listItems.push(<ul key={`ul-${idx}-${lineIdx}`}>{currentList}</ul>);
            currentList = [];
          }
          listItems.push(<p key={`p-${idx}-${lineIdx}`}>{formatTextWithLinks(line)}</p>);
        }
      });

      if (currentList.length > 0) {
        listItems.push(<ul key={`ul-final-${idx}`}>{currentList}</ul>);
      }

      return <div key={idx}>{listItems}</div>;
    });
  };

  return (
    <>
      {/* Chatbot Toggle Button (the floating icon) */}
      <button className="chatbot-toggle-button" onClick={toggleChat} aria-label={isOpen ? "Close Chat" : "Open Chat"}>
        {isOpen ? (
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
            <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          // Simple logo mark for RemoteLock (stylized lock)
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
            <rect x="3" y="10" width="18" height="11" rx="2" stroke="white" strokeWidth="1.5" fill="#0f4c5c" />
            <path d="M7 10V7a5 5 0 0110 0v3" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
      </button>

      {/* Chat Window - conditionally rendered based on 'isOpen' state */}
      {/* The 'is-open' class is added for smooth CSS transitions */}
      {/* This ensures the visibility and transform animations work as defined in Chatbot.css */}
      {isOpen && (
        <div className={`chatbot-window ${isOpen ? 'is-open' : ''}`}>
          {/* Chat Window Header */}
          <div className="chatbot-header">
            RemoteLock Support
            <button className="chatbot-close-button" onClick={toggleChat} aria-label="Minimize Chat">
              <i className="fas fa-minus"></i> {/* Minus icon to minimize */}
            </button>
          </div>

          {/* Chat Messages Display Area */}
          <div className="chatbot-messages">
            {messages.length === 0 && (
              <div className="chatbot-welcome-message">
                Hi there! I'm your RemoteLock Support Assistant. How can I help you today?
              </div>
            )}
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                {renderMessageText(msg.text)}
              </div>
            ))}
            {/* Loading indicator moved to the bottom */}
            {isLoading && (
              <div className="typing-indicator">
                <div className="typing-dots"><span></span><span></span><span></span></div>
              </div>
            )}
            <div ref={messagesEndRef} /> {/* Invisible element to scroll to */}
          </div>

          {/* User Input Area */}
          <form className="chatbot-input-area" onSubmit={handleSendMessage}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your message..."
              aria-label="Type your message"
              disabled={isLoading}
            />
            <button type="submit" aria-label="Send Message" className="send-button" disabled={isLoading || inputValue.trim() === ''}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
                <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M22 2L15 22l-4-9-9-4 20-7z" stroke="white" strokeWidth="0" fill="white" opacity="0.0001" />
                <path d="M11 13l-4 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </>
  );
};

export default Chatbot;




































// import React, { useState, useRef, useEffect } from 'react';
// import './Chatbot.css'; // Link to our chatbot specific styles

// const Chatbot = () => {
//   const [isOpen, setIsOpen] = useState(false); // Controls chat window visibility
//   const [messages, setMessages] = useState([]); // Stores chat messages
//   const [inputValue, setInputValue] = useState(''); // Stores current input field value
//   const [isLoading, setIsLoading] = useState(false); // Shows typing indicator
//   const messagesEndRef = useRef(null); // Ref for auto-scrolling to the latest message

//   // Effect to scroll to the bottom of the messages display whenever new messages are added
//   useEffect(() => {
//     messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
//   }, [messages]);

//   // Toggles the chat window open/closed
//   const toggleChat = () => {
//     setIsOpen(!isOpen);
//   };

//   // Handles sending a user message and triggering a bot response
//   const handleSendMessage = async (e) => {
//     e.preventDefault(); // Prevent default form submission behavior
//     if (inputValue.trim() === '') return; // Don't send empty messages

//     const newUserMessage = { text: inputValue, sender: 'user' };
//     setMessages((prevMessages) => [...prevMessages, newUserMessage]); // Add user message
//     const messageToSend = inputValue;
//     setInputValue(''); // Clear input field

//     // Send message to backend chat endpoint
//     setIsLoading(true);
//     try {
//       const API_BASE = (import.meta && import.meta.env && import.meta.env.VITE_API_URL) ? import.meta.env.VITE_API_URL : 'http://localhost:8000';
//       const resp = await fetch(`${API_BASE.replace(/\/$/, '')}/chat/`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ message: messageToSend }),
//       });

//       if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
//       const data = await resp.json();
//       const rawReply = data.response || "Sorry, no reply.";
//       const botReply = sanitizeReply(rawReply);
//       setMessages((prevMessages) => [...prevMessages, { text: botReply, sender: 'bot' }]);
//     } catch (err) {
//       console.error('Chat request failed', err);
//       setMessages((prevMessages) => [...prevMessages, { text: "Sorry, I'm having trouble connecting right now.", sender: 'bot' }]);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   // Simple keyword-based bot response logic
//   const generateBotResponse = (userMessage) => {
//     const lowerCaseMessage = userMessage.toLowerCase();

//     if (lowerCaseMessage.includes('hello') || lowerCaseMessage.includes('hi')) {
//       return "Hello! Welcome to RemoteLock Support. How can I assist you today?";
//     } else if (lowerCaseMessage.includes('account')) {
//       return "For account-related issues, please visit our 'My Account' section or contact our support team directly.";
//     } else if (lowerCaseMessage.includes('lock') || lowerCaseMessage.includes('device')) {
//       return "Are you having trouble with a specific lock or device? Please provide more details.";
//     } else if (lowerCaseMessage.includes('troubleshooting')) {
//         return "Our troubleshooting guides can be found on our support page under 'Troubleshooting & FAQs'.";
//     } else if (lowerCaseMessage.includes('contact')) {
//         return "You can reach our support team via phone at [Your Phone Number] or by submitting a ticket on our 'Contact Us' page.";
//     } else if (lowerCaseMessage.includes('thanks') || lowerCaseMessage.includes('thank you')) {
//         return "You're welcome! Is there anything else I can help you with?";
//     } else {
//       return "I'm sorry, I don't understand that. Can you please rephrase or ask about common topics like 'account', 'lock', 'troubleshooting', or 'contact'?";
//     }
//   };

//   // Sanitize and format replies from the LLM/backend
//   const sanitizeReply = (text) => {
//     if (!text) return '';
//     // Remove common control chars and excessive asterisks/markdown artifacts
//     let s = text.replace(/\r/g, '')
//                 .replace(/\*{2,}/g, '')        // remove repeated asterisks
//                 .replace(/[_~`]{1,}/g, '')      // remove simple markdown markers
//                 .trim();

//   // Remove zero-width and odd invisible characters, collapse multiple whitespace
//   s = s.replace(/[\u200B\u200C\u200D\uFEFF]/g, '');
//   s = s.replace(/\s{2,}/g, ' ');

//   // Collapse weird inter-letter spacing like "R e m o t e" -> "Remote"
//   // and collapse newline-separated single letters like:
//   // R\n e\n m\n o\n t\n e  -> Remote
//   // We'll replace runs of single-letter tokens separated by spaces/newlines with joined words.
//   s = s.replace(/(?:\b(?:[A-Za-z](?:[ \t\n\r]+|$)){3,})/g, (match) => {
//     // remove whitespace between letters
//     const lettersOnly = match.replace(/[^A-Za-z\n\r ]+/g, '').replace(/[\n\r\s]+/g, '');
//     return lettersOnly;
//   });

//   // Split into lines and trim each line
//   let lines = s.split('\n').map(l => l.trim()).filter(Boolean);

//     // Normalize list markers: convert leading '* ', '- ', '+ ', '• ', or '1.' to a single bullet marker '• '
//     const normalized = lines.map((line) => {
//       // Match common list prefixes
//       const m = line.match(/^\s*([*+\-•]|\d+\.)\s+(.*)$/);
//       if (m) return `• ${m[2].trim()}`;
//       // If a line itself is a sequence of single letters separated by spaces or newlines, join them
//       if (/^(?:[A-Za-z](?:[ \t\n\r]+|$)){2,}$/.test(line)) {
//         return line.replace(/[\s\n\r]+/g, '');
//       }
//       // Also remove stray leading asterisks or bullets
//       return line.replace(/^\s*[\*•]\s?/, '').trim();
//     }).filter(l => l && !/^\s*[-*]{2,}$/.test(l));

//     // If many lines are bullets (start with '• '), keep them as a bullet list separated by newlines
//     const bulletCount = normalized.filter(l => l.startsWith('• ')).length;
//     if (bulletCount >= 2) {
//       return normalized.join('\n');
//     }

//     // Otherwise collapse multiple blank lines into single paragraph breaks
//     const paragraphs = normalized.join('\n').split(/\n{2,}/).map(p => p.trim()).filter(Boolean);
//     // Fix pathological cases where characters are spaced out like 'R e m o t e'
//     const fixed = paragraphs.map((p) => {
//       // If a paragraph has many single-character tokens in a row, join contiguous runs
//       const tokens = p.split(/(\s+)/); // keep whitespace tokens
//       let out = '';
//       let run = [];
//       const flushRun = () => {
//         if (run.length === 0) return;
//         // decide if we should join run tokens
//         const runTokens = run.join('').trim().split(/\s+/).filter(Boolean);
//         const singleCount = runTokens.filter(t => t.length === 1).length;
//         if (runTokens.length > 3 && singleCount / runTokens.length > 0.5) {
//           out += runTokens.join('');
//         } else {
//           out += run.join('');
//         }
//         run = [];
//       };
//       for (let tok of tokens) {
//         if (/^\s+$/.test(tok)) {
//           run.push(tok);
//         } else if (tok.length === 1 && /[A-Za-z0-9]/.test(tok)) {
//           run.push(tok + ' ');
//         } else {
//           flushRun();
//           out += tok;
//         }
//       }
//       flushRun();
//       return out.trim();
//     });
//     return fixed.join('\n\n');
//   };

//   // Render text into paragraphs and bullet lists for professional layout
//   const renderMessageText = (text) => {
//     if (!text) return null;
//     const paragraphs = text
//       .replace(/\r/g, '')
//       .split(/\n{2,}/) // paragraph breaks
//       .map(p => p.trim())
//       .filter(Boolean);

//     return paragraphs.map((para, idx) => {
//       const lines = para.split(/\n/).map(l => l.trim()).filter(Boolean);
//       const bulletLines = lines.filter(l => /^•\s+/.test(l));
//       const isMostlyBullets = bulletLines.length >= Math.max(2, Math.ceil(lines.length * 0.6));

//       if (isMostlyBullets) {
//         return (
//           <ul key={idx}>
//             {lines
//               .filter(l => /^•\s+/.test(l))
//               .map((l, i) => <li key={i}>{l.replace(/^•\s*/, '')}</li>)}
//           </ul>
//         );
//       }
//       return <p key={idx}>{para.replace(/^•\s*/g, '')}</p>;
//     });
//   };

//   return (
//     <>
//       {/* Chatbot Toggle Button (the floating icon) */}
//       <button className="chatbot-toggle-button" onClick={toggleChat} aria-label={isOpen ? "Close Chat" : "Open Chat"}>
//         {isOpen ? (
//           <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
//             <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
//           </svg>
//         ) : (
//           // Simple logo mark for RemoteLock (stylized lock)
//           <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
//             <rect x="3" y="10" width="18" height="11" rx="2" stroke="white" strokeWidth="1.5" fill="#0f4c5c" />
//             <path d="M7 10V7a5 5 0 0110 0v3" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
//           </svg>
//         )}
//       </button>

//       {/* Chat Window - conditionally rendered based on 'isOpen' state */}
//       {/* The 'is-open' class is added for smooth CSS transitions */}
//       {/* This ensures the visibility and transform animations work as defined in Chatbot.css */}
//       {isOpen && (
//         <div className={`chatbot-window ${isOpen ? 'is-open' : ''}`}>
//           {/* Chat Window Header */}
//           <div className="chatbot-header">
//             RemoteLock Support
//             <button className="chatbot-close-button" onClick={toggleChat} aria-label="Minimize Chat">
//               <i className="fas fa-minus"></i> {/* Minus icon to minimize */}
//             </button>
//           </div>

//           {/* Chat Messages Display Area */}
//           <div className="chatbot-messages">
//             {messages.length === 0 && (
//               <div className="chatbot-welcome-message">
//                 Hi there! I'm your RemoteLock Support Assistant. How can I help you today?
//               </div>
//             )}
//             {isLoading && (
//               <div className="typing-indicator">
//                 <div className="typing-dots"><span></span><span></span><span></span></div>
//               </div>
//             )}
//             {messages.map((msg, index) => (
//               <div key={index} className={`message ${msg.sender}`}>
//                 {renderMessageText(msg.text)}
//               </div>
//             ))}
//             <div ref={messagesEndRef} /> {/* Invisible element to scroll to */}
//           </div>

//           {/* User Input Area */}
//           <form className="chatbot-input-area" onSubmit={handleSendMessage}>
//             <input
//               type="text"
//               value={inputValue}
//               onChange={(e) => setInputValue(e.target.value)}
//               placeholder="Type your message..."
//               aria-label="Type your message"
//               disabled={isLoading}
//             />
//             <button type="submit" aria-label="Send Message" className="send-button" disabled={isLoading || inputValue.trim() === ''}>
//               <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
//                 <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
//                 <path d="M22 2L15 22l-4-9-9-4 20-7z" stroke="white" strokeWidth="0" fill="white" opacity="0.0001" />
//                 <path d="M11 13l-4 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
//               </svg>
//             </button>
//           </form>
//         </div>
//       )}
//     </>
//   );
// };

// export default Chatbot;

