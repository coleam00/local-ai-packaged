import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className = '', title, onClick }) => {
  return (
    <div className={`card ${className}`} onClick={onClick}>
      {title && <h3 className="text-lg font-semibold mb-3">{title}</h3>}
      {children}
    </div>
  );
};
