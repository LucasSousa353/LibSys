interface AvatarProps {
  name: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map(word => word.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function getColorFromName(name: string): string {
  const colors = [
    'bg-blue-500/20 text-blue-600 dark:text-blue-400',
    'bg-purple-500/20 text-purple-600 dark:text-purple-400',
    'bg-green-500/20 text-green-600 dark:text-green-400',
    'bg-orange-500/20 text-orange-600 dark:text-orange-400',
    'bg-pink-500/20 text-pink-600 dark:text-pink-400',
    'bg-teal-500/20 text-teal-600 dark:text-teal-400',
    'bg-indigo-500/20 text-indigo-600 dark:text-indigo-400',
  ];

  const index = name.charCodeAt(0) % colors.length;
  return colors[index];
}

export function Avatar({ name, src, size = 'md', className = '' }: AvatarProps) {
  const sizes = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-9 h-9 text-sm',
    lg: 'w-10 h-10 text-sm',
    xl: 'w-32 h-32 text-3xl',
  };

  if (src) {
    return (
      <div
        className={`${sizes[size]} rounded-full bg-cover bg-center ${className}`}
        style={{ backgroundImage: `url(${src})` }}
      />
    );
  }

  return (
    <div
      className={`
        ${sizes[size]} 
        ${getColorFromName(name)}
        rounded-full flex items-center justify-center font-bold
        ${className}
      `}
    >
      {getInitials(name)}
    </div>
  );
}

export default Avatar;
