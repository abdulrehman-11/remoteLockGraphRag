import { Search } from 'lucide-react';
import { clsx } from 'clsx';

const SearchBar = ({
  placeholder = 'Search...',
  value,
  onChange,
  onSubmit,
  className = '',
  size = 'md',
}) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit) {
      onSubmit(value);
    }
  };

  const sizes = {
    sm: 'py-2 pl-10 pr-4 text-sm',
    md: 'py-3 pl-12 pr-4 text-base',
    lg: 'py-4 pl-14 pr-4 text-lg',
  };

  const iconSizes = {
    sm: 18,
    md: 20,
    lg: 24,
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <Search
        className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
        size={iconSizes[size]}
      />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={clsx(
          'w-full rounded-lg border-2 border-gray-200',
          'focus:border-remotelock-500 focus:ring-4 focus:ring-remotelock-50',
          'transition-all duration-200 outline-none',
          sizes[size],
          className
        )}
      />
    </form>
  );
};

export default SearchBar;
