import { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';
import { clsx } from 'clsx';

const ChatMessage = ({ message, sender, sources = [], timestamp }) => {
  const [copied, setCopied] = useState(false);
  const isUser = sender === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render text with links
  const renderMessageText = (text) => {
    if (!text) return null;

    const markdownLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g; // Matches [text](url)
    const rawUrlRegex = /<(https?:\/\/[^\s>]+)>|(https?:\/\/[^\s)]+)/g; // Matches <url> or raw URLs, excluding trailing ')' or '>'

    const formatTextWithLinks = (line) => {
      const parts = [];
      let lastIndex = 0;

      // Find all markdown links and raw URLs
      const matches = [];
      let match;

      // Find markdown links
      while ((match = markdownLinkRegex.exec(line)) !== null) {
        matches.push({ type: 'markdown', match: match, index: match.index });
      }

      // Find raw URLs, ensuring they don't overlap with markdown links
      while ((match = rawUrlRegex.exec(line)) !== null) {
        const isOverlap = matches.some(m =>
          (match.index >= m.index && match.index < m.index + m.match[0].length) ||
          (m.index >= match.index && m.index < match.index + match[0].length)
        );
        if (!isOverlap) {
          matches.push({ type: 'raw', match: match, index: match.index });
        }
      }

      // Sort matches by their index in the string
      matches.sort((a, b) => a.index - b.index);

      matches.forEach(({ type, match }) => {
        const [fullMatch, textOrUrl, url] = match;
        const startIndex = match.index;
        const endIndex = startIndex + fullMatch.length;

        // Add preceding text
        if (startIndex > lastIndex) {
          parts.push(line.substring(lastIndex, startIndex));
        }

        let displayUrl = '';
        let displayText = '';

        if (type === 'markdown') {
          displayText = textOrUrl; // The text inside the brackets
          displayUrl = url; // The URL inside the parentheses
        } else { // type === 'raw'
          // For raw URLs, either match[1] (angle bracket) or match[2] (plain URL) will be defined
          displayUrl = textOrUrl || url; // Use whichever capturing group matched
          displayText = displayUrl; // The raw URL itself
        }

        // Remove trailing punctuation from raw URLs if it's not part of the URL
        if (type === 'raw' && displayUrl) {
          displayUrl = displayUrl.replace(/\)+$/, '');
          if (displayUrl.endsWith('.') || displayUrl.endsWith(',') || displayUrl.endsWith(';')) {
            displayUrl = displayUrl.substring(0, displayUrl.length - 1);
          }
          displayText = displayUrl; // Update display text if URL was cleaned
        }

        // Only create link if we have a valid URL
        if (displayUrl) {
          const fullLink = displayUrl.startsWith('http') ? displayUrl : `https://${displayUrl}`;

          parts.push(
            <a
              key={startIndex}
              href={fullLink}
              target="_blank"
              rel="noopener noreferrer"
              className="text-remotelock-500 hover:text-remotelock-600 underline"
            >
              {displayText}
            </a>
          );
          // Add a line break after each link for better formatting if there are multiple links
          // This is a stylistic choice, can be removed if not desired.
          // For now, let's keep it to ensure links are on separate lines as requested.
          parts.push(<br key={`br-${startIndex}`} />);
        }

        lastIndex = endIndex;
      });

      // Add any remaining text
      if (lastIndex < line.length) {
        parts.push(line.substring(lastIndex));
      }
      return parts;
    };

    const paragraphs = (text || '')
      .replace(/\r/g, '')
      .split(/\n{2,}/) // Split by double newlines for paragraphs
      .map((p) => p.trim())
      .filter(Boolean);

    return paragraphs.map((para, idx) => {
      const lines = para.split(/\n/); // Split by single newline for lines within a paragraph
      const listItems = [];
      let currentList = [];
      let listType = null; // 'ul' or 'ol'

      lines.forEach((line, lineIdx) => {
        const trimmedLine = line.trim();
        const isUnorderedListItem = /^[*-•]\s+/.test(trimmedLine);
        const isOrderedListItem = /^\d+\.\s+/.test(trimmedLine);

        if (isUnorderedListItem || isOrderedListItem) {
          const newItemType = isOrderedListItem ? 'ol' : 'ul';
          if (currentList.length > 0 && listType !== newItemType) {
            // Close previous list if type changes
            listItems.push(
              listType === 'ol' ? (
                <ol key={`ol-${idx}-${lineIdx}`} className="list-decimal list-inside space-y-1 my-2">
                  {currentList}
                </ol>
              ) : (
                <ul key={`ul-${idx}-${lineIdx}`} className="list-disc list-inside space-y-1 my-2">
                  {currentList}
                </ul>
              )
            );
            currentList = [];
          }
          listType = newItemType;

          const content = trimmedLine.replace(/^([*-•]|\d+\.)\s*/, '').trim();
          currentList.push(
            <li key={lineIdx} className="text-gray-700">
              {formatTextWithLinks(content)}
            </li>
          );
        } else {
          if (currentList.length > 0) {
            // Close any open list
            listItems.push(
              listType === 'ol' ? (
                <ol key={`ol-${idx}-${lineIdx}`} className="list-decimal list-inside space-y-1 my-2">
                  {currentList}
                </ol>
              ) : (
                <ul key={`ul-${idx}-${lineIdx}`} className="list-disc list-inside space-y-1 my-2">
                  {currentList}
                </ul>
              )
            );
            currentList = [];
            listType = null;
          }
          // Render as paragraph, preserving single newlines as <br />
          if (trimmedLine) {
            listItems.push(
              <p key={`p-${idx}-${lineIdx}`} className="mb-2 last:mb-0">
                {formatTextWithLinks(trimmedLine)}
              </p>
            );
          } else {
            // Preserve empty lines as <br /> for spacing within paragraphs if needed
            listItems.push(<br key={`br-${idx}-${lineIdx}`} />);
          }
        }
      });

      // Add any remaining open list
      if (currentList.length > 0) {
        listItems.push(
          listType === 'ol' ? (
            <ol key={`ol-final-${idx}`} className="list-decimal list-inside space-y-1 my-2">
              {currentList}
            </ol>
          ) : (
            <ul key={`ul-final-${idx}`} className="list-disc list-inside space-y-1 my-2">
              {currentList}
            </ul>
          )
        );
      }

      return <div key={idx}>{listItems}</div>;
    });
  };

  return (
    <div
      className={clsx(
        'flex items-end space-x-2 mb-4 group',
        isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'
      )}
    >
      {/* Message Bubble */}
      <div
        className={clsx(
          'max-w-[75%] rounded-2xl px-4 py-3 shadow-sm relative break-words overflow-wrap-anywhere',
          isUser
            ? 'bg-remotelock-500 text-white rounded-br-sm'
            : 'bg-white border border-gray-200 rounded-bl-sm'
        )}
      >
        {/* Message Content */}
        <div className={clsx('text-sm leading-relaxed', isUser ? 'text-white' : 'text-gray-800')}>
          {renderMessageText(message)}
        </div>

        {/* Sources (if available, for bot messages) */}
        {!isUser && sources && sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500 font-semibold mb-2">
              Sources:
            </p>
            <div className="space-y-1">
              {sources.map((source, idx) => (
                <a
                  key={idx}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-xs text-remotelock-500 hover:text-remotelock-600 hover:underline"
                >
                  <ExternalLink size={12} className="mr-1" />
                  {source.title || source.url}
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Copy Button (shown on hover for bot messages) */}
        {!isUser && (
          <button
            onClick={handleCopy}
            className="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white border border-gray-200 rounded-full p-1.5 shadow-sm hover:bg-gray-50"
            aria-label="Copy message"
          >
            {copied ? (
              <Check size={14} className="text-green-500" />
            ) : (
              <Copy size={14} className="text-gray-600" />
            )}
          </button>
        )}

        {/* Timestamp */}
        {timestamp && (
          <div
            className={clsx(
              'text-xs mt-1',
              isUser ? 'text-white/70' : 'text-gray-400'
            )}
          >
            {timestamp}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
