// API configuration
export const getApiBase = () => {
  const apiUrl = import.meta?.env?.VITE_API_URL;
  console.log('VITE_API_URL:', apiUrl); // Added for debugging
  return apiUrl || 'http://localhost:8000';
};

// Sanitize and format replies from the LLM/backend
export const sanitizeReply = (text) => {
  if (!text) return '';
  // Remove common control chars and excessive asterisks/markdown artifacts
  let s = text
    .replace(/\r/g, '')
    .replace(/\*{2,}/g, '') // remove repeated asterisks
    .replace(/[_~`]{1,}/g, '') // remove simple markdown markers
    .trim();

  // Remove zero-width and odd invisible characters, collapse multiple whitespace
  s = s.replace(/[\u200B\u200C\u200D\uFEFF]/g, '');
  s = s.replace(/\s{2,}/g, ' ');

  // Collapse weird inter-letter spacing like "R e m o t e" -> "Remote"
  s = s.replace(/(?:\b(?:[A-Za-z](?:[ \t\n\r]+|$)){3,})/g, (match) => {
    const lettersOnly = match
      .replace(/[^A-Za-z\n\r ]+/g, '')
      .replace(/[\n\r\s]+/g, '');
    return lettersOnly;
  });

  // Split into lines and trim each line
  let lines = s
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);

  // Normalize list markers
  const normalized = lines
    .map((line) => {
      const m = line.match(/^\s*([*+\-•]|\d+\.)\s+(.*)$/);
      if (m) return `• ${m[2].trim()}`;
      if (/^(?:[A-Za-z](?:[ \t\n\r]+|$)){2,}$/.test(line)) {
        return line.replace(/[\s\n\r]+/g, '');
      }
      return line.replace(/^\s*[\*•]\s?/, '').trim();
    })
    .filter((l) => l && !/^\s*[-*]{2,}$/.test(l));

  // If many lines are bullets, keep them as a bullet list
  // Preserve all newlines and let the rendering component handle paragraph breaks
  return normalized.join('\n');
};

// Local storage helpers for conversation history
export const saveConversationHistory = (messages) => {
  try {
    localStorage.setItem('remotelock_chat_history', JSON.stringify(messages));
    localStorage.setItem(
      'remotelock_chat_timestamp',
      new Date().toISOString()
    );
  } catch (error) {
    console.error('Failed to save conversation history:', error);
  }
};

export const loadConversationHistory = () => {
  try {
    const history = localStorage.getItem('remotelock_chat_history');
    const timestamp = localStorage.getItem('remotelock_chat_timestamp');

    if (!history || !timestamp) return [];

    // Clear history if older than 24 hours
    const lastSaved = new Date(timestamp);
    const now = new Date();
    const hoursSinceLastSave = (now - lastSaved) / (1000 * 60 * 60);

    if (hoursSinceLastSave > 24) {
      clearConversationHistory();
      return [];
    }

    return JSON.parse(history);
  } catch (error) {
    console.error('Failed to load conversation history:', error);
    return [];
  }
};

export const clearConversationHistory = () => {
  try {
    localStorage.removeItem('remotelock_chat_history');
    localStorage.removeItem('remotelock_chat_timestamp');
  } catch (error) {
    console.error('Failed to clear conversation history:', error);
  }
};
