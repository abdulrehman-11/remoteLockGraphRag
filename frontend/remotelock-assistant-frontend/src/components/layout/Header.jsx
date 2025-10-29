import { Home, Mail, Phone } from 'lucide-react';
import Button from '../common/Button';

const Header = () => {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Logo Section */}
          <div className="flex items-center">
            <div className="flex items-center space-x-3">
              {/* RemoteLock Logo Placeholder - Replace with actual logo */}
              <div className="w-10 h-10 bg-remotelock-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">RL</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">RemoteLock</h1>
                <p className="text-xs text-gray-500">Support Center</p>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-6">
            <a
              href="#home"
              className="flex items-center space-x-1 text-gray-700 hover:text-remotelock-500 transition-colors"
            >
              <Home size={18} />
              <span>Home</span>
            </a>
            <a
              href="#contact"
              className="flex items-center space-x-1 text-gray-700 hover:text-remotelock-500 transition-colors"
            >
              <Mail size={18} />
              <span>Contact Support</span>
            </a>
          </nav>

          {/* CTA Button */}
          <div className="flex items-center space-x-3">
            <Button variant="outline" size="sm" className="hidden sm:inline-flex">
              <Phone size={16} className="mr-2" />
              Schedule Call
            </Button>
            <Button variant="primary" size="sm">
              Get Help
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
