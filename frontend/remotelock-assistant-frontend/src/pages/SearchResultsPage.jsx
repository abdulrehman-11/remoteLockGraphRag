import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search, ArrowLeft, MessageCircle } from 'lucide-react';
import ArticleCard from '../components/common/ArticleCard';
import Button from '../components/common/Button';
import { getApiBase } from '../utils/api';

const SearchResultsPage = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      if (!query) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const apiBase = getApiBase();
        const response = await fetch(`${apiBase}/search/suggestions/?q=${encodeURIComponent(query)}`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setResults(data.articles || []);
      } catch (err) {
        console.error('Search error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [query]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link to="/" className="inline-flex items-center text-remotelock-500 hover:text-remotelock-600 mb-4">
            <ArrowLeft size={20} className="mr-2" />
            Back to Home
          </Link>

          <div className="flex items-center space-x-3 mb-4">
            <Search size={24} className="text-gray-400" />
            <h1 className="text-2xl font-bold text-gray-900">
              Search Results
            </h1>
          </div>

          <p className="text-gray-600">
            Showing results for: <span className="font-semibold text-gray-900">"{query}"</span>
          </p>
        </div>
      </header>

      {/* Results */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="search-results">
        {loading && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-remotelock-500"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 mb-4">
              Failed to load search results: {error}
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </div>
        )}

        {!loading && !error && results.length === 0 && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <Search size={48} className="mx-auto text-gray-300 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              No results found
            </h2>
            <p className="text-gray-600 mb-6">
              We couldn't find any articles matching "{query}".
              Try our Chat Assistant for general questions.
            </p>
            <div className="flex justify-center gap-4">
              <Link to="/">
                <Button variant="outline">
                  <ArrowLeft size={16} className="mr-2" />
                  Back to Home
                </Button>
              </Link>
              <Link to="/">
                <Button>
                  <MessageCircle size={16} className="mr-2" />
                  Ask Chat Assistant
                </Button>
              </Link>
            </div>
          </div>
        )}

        {!loading && !error && results.length > 0 && (
          <>
            <div className="mb-6">
              <p className="text-gray-600">
                Found <span className="font-semibold text-gray-900">{results.length}</span> {results.length === 1 ? 'article' : 'articles'}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {results.map((article, index) => (
                <ArticleCard
                  key={index}
                  title={article.title}
                  url={article.url}
                  summary={article.summary}
                />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default SearchResultsPage;
