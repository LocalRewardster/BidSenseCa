import React from 'react';
import { motion } from 'framer-motion';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glass' | 'gradient';
  gradient?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  hover?: boolean;
  padding?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

const Card: React.FC<CardProps> = ({
  children,
  className = '',
  variant = 'default',
  gradient,
  hover = false,
  padding = 'md',
  onClick,
  ...props
}) => {
  const baseClasses = 'rounded-2xl shadow-lg transition-all duration-300';
  
  const variantClasses = {
    default: 'bg-white border border-gray-200',
    glass: 'glass-card',
    gradient: gradient ? `gradient-card-${gradient}` : 'gradient-card-primary'
  };

  const paddingClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };

  const hoverClasses = hover ? 'card-hover cursor-pointer' : '';

  const classes = `${baseClasses} ${variantClasses[variant]} ${paddingClasses[padding]} ${hoverClasses} ${className}`;

  const MotionComponent = onClick ? motion.div : motion.div;

  return (
    <MotionComponent
      className={classes}
      whileHover={hover ? { y: -5 } : undefined}
      onClick={onClick}
      {...props}
    >
      {children}
    </MotionComponent>
  );
};

// Card Header Component
interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className = '' }) => (
  <div className={`mb-4 ${className}`}>
    {children}
  </div>
);

// Card Title Component
interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const CardTitle: React.FC<CardTitleProps> = ({ 
  children, 
  className = '', 
  size = 'md' 
}) => {
  const sizeClasses = {
    sm: 'text-lg font-semibold',
    md: 'text-xl font-bold',
    lg: 'text-2xl font-bold'
  };

  return (
    <h3 className={`text-gray-900 ${sizeClasses[size]} ${className}`}>
      {children}
    </h3>
  );
};

// Card Content Component
interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({ children, className = '' }) => (
  <div className={`${className}`}>
    {children}
  </div>
);

// Card Footer Component
interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({ children, className = '' }) => (
  <div className={`mt-4 pt-4 border-t border-gray-200 ${className}`}>
    {children}
  </div>
);

export default Card; 