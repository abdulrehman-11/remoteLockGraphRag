import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/layout/Header';
import HeroSection from './components/home/HeroSection';
import CategoryGrid from './components/home/CategoryGrid';
import ChatWidget from './components/chat/ChatWidget';
import SearchResultsPage from './pages/SearchResultsPage';
import ArticlesListPage from './pages/ArticlesListPage';

function HomePage({ onChatWithTopic, onChatOpen }) {
  return (
    <>
      <HeroSection onChatOpen={onChatOpen} />
      <CategoryGrid onChatWithTopic={onChatWithTopic} />

      {/* Additional Support Options */}
      <section className="py-16 bg-white">
          <div className="w-full mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                Still Need Help?
              </h2>
              <p className="text-gray-600 text-lg">
                Our support team is here for you
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Email Support */}
              <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-remotelock-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-6 h-6 text-remotelock-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Email Support
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Get help via email
                </p>
                <a
                  href="mailto:support@remotelock.com"
                  className="text-remotelock-500 hover:text-remotelock-600 font-medium text-sm"
                >
                  support@remotelock.com
                </a>
              </div>

              {/* Phone Support */}
              <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-remotelock-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-6 h-6 text-remotelock-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Call Us
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Speak with our team
                </p>
                <a
                  href="tel:+18005551234"
                  className="text-remotelock-500 hover:text-remotelock-600 font-medium text-sm"
                >
                  1-800-555-1234
                </a>
              </div>

              {/* Submit Ticket */}
              <div className="bg-gray-50 rounded-lg p-6 text-center hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-remotelock-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-6 h-6 text-remotelock-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Submit Ticket
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Track your request
                </p>
                <button
                  onClick={() => handleChatOpen('I need to submit a support ticket')}
                  className="text-remotelock-500 hover:text-remotelock-600 font-medium text-sm"
                >
                  Create Ticket
                </button>
              </div>
            </div>
          </div>
        </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-8">
        <div className="w-full px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-gray-400 text-sm">
            © 2025 RemoteLock. All rights reserved.
          </p>
        </div>
      </footer>
    </>
  );
}

function AppNew() {
  const [chatMessage, setChatMessage] = useState(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messageKey, setMessageKey] = useState(0); // Force re-render

  const handleChatWithTopic = (topic) => {
    console.log('[AppNew] Chat with topic triggered:', topic);
    const message = `I need help with ${topic}`;
    setChatMessage(message);
    setMessageKey(prev => prev + 1);
    setIsChatOpen(true);
    console.log('[AppNew] State updated - chatOpen:', true, 'message:', message);
  };

  const handleChatOpen = (message = null) => {
    console.log('[AppNew] Chat open triggered, message:', message);
    if (message) {
      setChatMessage(message);
      setMessageKey(prev => prev + 1);
    }
    setIsChatOpen(true);
    console.log('[AppNew] State updated - chatOpen:', true);
  };

  return (
    <BrowserRouter>
      <div className="w-full min-h-screen bg-white">
        <Header />

        <main>
          <Routes>
            <Route
              path="/"
              element={<HomePage onChatWithTopic={handleChatWithTopic} onChatOpen={handleChatOpen} />}
            />
            <Route path="/search" element={<SearchResultsPage />} />
            <Route path="/articles" element={<ArticlesListPage />} />
          </Routes>
        </main>

        {/* Floating Chat Widget - Available on all pages */}
        <ChatWidget
          initialMessage={chatMessage}
          isOpen={isChatOpen}
          onOpenChange={setIsChatOpen}
        />
      </div>
    </BrowserRouter>
  );
}

export default AppNew;
