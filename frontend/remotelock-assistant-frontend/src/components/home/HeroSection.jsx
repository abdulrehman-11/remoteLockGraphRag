import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import SearchBar from '../common/SearchBar';
import Button from '../common/Button';

const HeroSection = ({ onChatOpen }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = () => {
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  const suggestionTopics = [
    'Troubleshooting a Lock',
    'Guest Access Codes',
    'Installation Guides',
    'Billing Questions',
  ];

  return (
    <section className="bg-gradient-to-br from-remotelock-50 via-white to-blue-50 py-16 md:py-24">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        {/* Hero Content */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center mb-4">
            <Sparkles className="text-remotelock-500 mr-2" size={32} />
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900">
              How can we help you?
            </h1>
          </div>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Search our knowledge base or chat with our AI assistant for instant support
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-2xl mx-auto mb-8">
          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            onSubmit={handleSearch}
            placeholder="Search for help articles, guides, or ask a question..."
            size="lg"
          />
        </div>

        {/* Quick Actions */}
        <div className="flex flex-col items-center space-y-4">
          <p className="text-sm text-gray-500">Popular topics:</p>
          <div className="flex flex-wrap justify-center gap-3">
            {suggestionTopics.map((topic) => (
              <Button
                key={topic}
                variant="outline"
                size="sm"
                onClick={() => onChatOpen && onChatOpen(topic)}
                className="hover:border-remotelock-500 hover:text-remotelock-500"
                data-testid="popular-topic"
              >
                {topic}
              </Button>
            ))}
          </div>
        </div>

        {/* AI Assistant CTA */}
        <div className="text-center mt-10">
          <p className="text-gray-600 mb-3">
            Not finding what you need? Try our AI assistant
          </p>
          <Button
            variant="primary"
            size="lg"
            onClick={() => onChatOpen && onChatOpen()}
            data-testid="chat-assistant-button"
          >
            <Sparkles size={20} className="mr-2" />
            Chat with AI Assistant
          </Button>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
