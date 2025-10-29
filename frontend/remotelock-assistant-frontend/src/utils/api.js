import { getApiBase } from './chatHelpers';

// Re-export getApiBase for convenience
export { getApiBase };

// Fetch sitemap structure from backend
export const fetchSitemap = async () => {
  try {
    const apiBase = getApiBase();
    const response = await fetch(`${apiBase.replace(/\/$/, '')}/sitemap/`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to fetch sitemap:', error);
    // Return fallback data if backend is unavailable
    return getFallbackSitemap();
  }
};

// Fallback sitemap data (matches backend structure)
const getFallbackSitemap = () => {
  return {
    "FAQs": {
      "url": "https://support.remotelock.com/s/topic/0TO3l000000E1SUGA0/faqs",
      "subcategories": {}
    },
    "Getting Started": {
      "url": "https://support.remotelock.com/s/topic/0TO3l000000E1SVGA0/getting-started",
      "subcategories": {}
    },
    "Device Setup": {
      "url": "https://support.remotelock.com/s/topic/0TO3l000000E1SWGA0/device-setup",
      "subcategories": {}
    },
    "Troubleshooting": {
      "url": "https://support.remotelock.com/s/topic/0TO3l000000E1SXGA0/troubleshooting",
      "subcategories": {}
    },
    "Access Management": {
      "url": "https://support.remotelock.com/s/topic/0TO3l000000E1SYGA0/access-management",
      "subcategories": {}
    },
    "RemoteLock Portal": {
      "url": "https://support.remotelock.com/s/topic/0TO3l000000E1SZGA0/remotelock-portal",
      "subcategories": {}
    }
  };
};

// Format sitemap for CategoryGrid
export const formatSitemapForCategories = (sitemap) => {
  const categoryIcons = {
    'FAQs': 'HelpCircle',
    'Getting Started': 'Rocket',
    'Device Setup': 'Settings',
    'Troubleshooting': 'Wrench',
    'Access Management': 'Lock',
    'RemoteLock Portal': 'BookOpen',
    'Hardware Information': 'Cpu',
    'Integration': 'Link2'
  };

  const categoryColors = {
    'FAQs': 'text-blue-500',
    'Getting Started': 'text-green-500',
    'Device Setup': 'text-purple-500',
    'Troubleshooting': 'text-orange-500',
    'Access Management': 'text-red-500',
    'RemoteLock Portal': 'text-indigo-500',
    'Hardware Information': 'text-cyan-500',
    'Integration': 'text-pink-500'
  };

  return Object.keys(sitemap).map(name => {
    const category = sitemap[name];
    const subcategoryCount = Object.keys(category.subcategories || {}).length;
    const pageCount = category.pages ? category.pages.length : 0;
    const totalCount = subcategoryCount + pageCount || 15; // fallback count

    return {
      name,
      icon: categoryIcons[name] || 'FileText',
      description: `Learn about ${name.toLowerCase()}`,
      count: totalCount,
      color: categoryColors[name] || 'text-gray-500',
      url: category.url
    };
  });
};
