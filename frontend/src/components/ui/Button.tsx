import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyle = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 disabled:opacity-40 disabled:pointer-events-none cursor-pointer';
  
  const variantStyles = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary-hover shadow-md hover:shadow-primary/10',
    secondary: 'bg-muted text-foreground border border-border hover:bg-muted/80',
    danger: 'bg-critical/10 text-critical border border-critical/20 hover:bg-critical/20',
    ghost: 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
  };

  const sizeStyles = {
    sm: 'px-2.5 py-1 text-[11px] gap-1.5',
    md: 'px-4 py-2 text-xs gap-2',
    lg: 'px-5 py-2.5 text-sm gap-2.5'
  };

  return (
    <button
      disabled={disabled || isLoading}
      aria-disabled={disabled || isLoading}
      className={`${baseStyle} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" aria-hidden="true"></span>
      ) : null}
      {children}
    </button>
  );
};
