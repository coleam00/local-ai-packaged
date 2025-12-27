import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  onClick?: () => void;
  variant?: 'default' | 'blue' | 'green' | 'purple';
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  onClick,
  variant = 'default',
}) => {
  const variantBorder = {
    default: 'border-[#374151] hover:border-[#4b5563]',
    blue: 'border-blue-500/30 hover:border-blue-500/50',
    green: 'border-emerald-500/30 hover:border-emerald-500/50',
    purple: 'border-purple-500/30 hover:border-purple-500/50',
  }[variant];

  return (
    <div
      className={`bg-[#1e293b] rounded-[12px] border p-4 transition-colors ${variantBorder} ${
        onClick ? 'cursor-pointer' : ''
      } ${className}`}
      style={{ boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)' }}
      onClick={onClick}
    >
      {title && (
        <h3 className="text-lg font-semibold text-white mb-3">{title}</h3>
      )}
      {children}
    </div>
  );
};
