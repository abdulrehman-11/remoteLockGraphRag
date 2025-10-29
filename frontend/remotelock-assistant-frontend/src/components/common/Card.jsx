import { clsx } from 'clsx';

const Card = ({
  children,
  className = '',
  padding = 'md',
  hover = false,
  onClick,
  ...props
}) => {
  const baseStyles = 'bg-white rounded-remotelock shadow-elevation-sm transition-all duration-200';

  const paddingStyles = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const hoverStyles = hover ? 'cursor-pointer hover:shadow-elevation-md hover:scale-[1.02]' : '';

  return (
    <div
      className={clsx(baseStyles, paddingStyles[padding], hoverStyles, className)}
      onClick={onClick}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;
