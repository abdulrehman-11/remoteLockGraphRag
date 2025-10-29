import { FileText, ExternalLink } from 'lucide-react';
import Card from './Card';

const ArticleCard = ({ title, url, summary }) => {
  return (
    <Card
      padding="md"
      hover
      className="group transition-all duration-200 bg-white border border-gray-200 shadow-sm"
      data-testid="article-card"
    >
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
      >
        <div className="flex items-start space-x-3">
          {/* Icon */}
          <div className="flex-shrink-0 w-10 h-10 bg-remotelock-50 rounded-lg flex items-center justify-center group-hover:bg-remotelock-100 transition-colors">
            <FileText size={20} className="text-remotelock-500" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-remotelock-500 transition-colors flex items-center gap-2">
              {title}
              <ExternalLink size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </h3>
            {summary && (
              <p className="text-sm text-gray-600 line-clamp-2">
                {summary}
              </p>
            )}
          </div>
        </div>

        {/* URL Preview (on hover) */}
        <div className="mt-3 pt-3 border-t border-gray-100 opacity-0 group-hover:opacity-100 transition-opacity">
          <p className="text-xs text-remotelock-500 truncate">
            {url}
          </p>
        </div>
      </a>
    </Card>
  );
};

export default ArticleCard;
