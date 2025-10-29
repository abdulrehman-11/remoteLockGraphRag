import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HelpCircle, Rocket, Settings, Wrench, Lock, FileText, MessageCircle, BookOpen, Cpu, Link2 } from 'lucide-react';
import Card from '../common/Card';
import Button from '../common/Button';
import { fetchSitemap, formatSitemapForCategories } from '../../utils/api';

const CategoryGrid = ({ onChatWithTopic }) => {
  const navigate = useNavigate();
  const [hoveredCard, setHoveredCard] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Icon mapping
  const iconMap = {
    HelpCircle, Rocket, Settings, Wrench, Lock, BookOpen, FileText, Cpu, Link2
  };

  // Fetch categories from backend
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const sitemap = await fetchSitemap();
        const formattedCategories = formatSitemapForCategories(sitemap);
        setCategories(formattedCategories);
      } catch (error) {
        console.error('Failed to load categories:', error);
      } finally {
        setLoading(false);
      }
    };

    loadCategories();
  }, []);

  const handleCardHover = (index) => {
    setHoveredCard(index);
  };

  const handleCardLeave = () => {
    setHoveredCard(null);
  };

  return (
    <section className="py-16 bg-gray-50">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
            Browse by Category
          </h2>
          <p className="text-gray-600 text-lg">
            Find the help you need, organized by topic
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-remotelock-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {categories.map((category, index) => {
              const IconComponent = iconMap[category.icon] || FileText;
              const isHovered = hoveredCard === index;

              return (
                <Card
                key={category.name}
                padding="md"
                hover
                onMouseEnter={() => handleCardHover(index)}
                onMouseLeave={handleCardLeave}
                className="relative group"
              >
                {/* Card Content */}
                <div className="flex items-start space-x-4">
                  <div className={`p-3 bg-gray-50 rounded-lg ${category.color}`}>
                    <IconComponent size={28} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 mb-1">
                      {category.name}
                    </h3>
                    <p className="text-gray-600 text-sm mb-2">
                      {category.description}
                    </p>
                    <p className="text-xs text-gray-500">
                      {category.count} articles
                    </p>
                  </div>
                </div>

                {/* Action Buttons (shown on hover) */}
                {isHovered && (
                  <div className="mt-4 pt-4 border-t border-gray-100 flex space-x-2 animate-fade-in">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => onChatWithTopic && onChatWithTopic(category.name)}
                    >
                      <MessageCircle size={16} className="mr-1" />
                      Ask AI
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="flex-1"
                      onClick={() => navigate(`/articles?category=${encodeURIComponent(category.name)}`)}
                    >
                      <FileText size={16} className="mr-1" />
                      Browse
                    </Button>
                  </div>
                )}
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};

export default CategoryGrid;
