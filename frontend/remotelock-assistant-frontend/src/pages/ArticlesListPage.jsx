import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { FileText, ArrowLeft, MessageCircle } from 'lucide-react';
import ArticleCard from '../components/common/ArticleCard';
import Button from '../components/common/Button';
import { getApiBase } from '../utils/api';

const ArticlesListPage = () => {
  const [searchParams] = useSearchParams();
  const category = searchParams.get('category') || '';

  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchArticles = async () => {
      if (!category) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const apiBase = getApiBase();
        const response = await fetch(`${apiBase}/articles/?category=${encodeURIComponent(category)}`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setArticles(data.articles || []);
      } catch (err) {
        console.error('Articles fetch error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchArticles();
  }, [category]);

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
            <FileText size={24} className="text-remotelock-500" />
            <h1 className="text-2xl font-bold text-gray-900">
              {category}
            </h1>
          </div>

          <p className="text-gray-600">
            Browse articles and guides in this category
          </p>
        </div>
      </header>

      {/* Articles List */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="articles-list">
        {loading && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-remotelock-500"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 mb-4">
              Failed to load articles: {error}
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </div>
        )}

        {!loading && !error && articles.length === 0 && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <FileText size={48} className="mx-auto text-gray-300 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              No articles found
            </h2>
            <p className="text-gray-600 mb-6">
              We couldn't find any articles in the "{category}" category.
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

        {!loading && !error && articles.length > 0 && (
          <>
            <div className="mb-6">
              <p className="text-gray-600">
                Found <span className="font-semibold text-gray-900">{articles.length}</span> {articles.length === 1 ? 'article' : 'articles'}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {articles.map((article, index) => (
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

export default ArticlesListPage;
