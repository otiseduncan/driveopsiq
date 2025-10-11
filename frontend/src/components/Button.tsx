/**
 * Button Component with TypeScript support and accessibility features
 */

import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { ButtonProps } from '../types';

interface ExtendedButtonProps extends ButtonProps, Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick' | 'type'> {
  loading?: boolean;
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ExtendedButtonProps>(
  (
    {
      children,
      className = '',
      variant = 'primary',
      size = 'medium',
      disabled = false,
      loading = false,
      fullWidth = false,
      icon,
      onClick,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      'btn',
      `btn--${variant}`,
      `btn--${size}`,
      fullWidth && 'btn--full-width',
      loading && 'btn--loading',
      disabled && 'btn--disabled',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      if (disabled || loading) {
        event.preventDefault();
        return;
      }
      onClick?.();
    };

    return (
      <button
        ref={ref}
        type={type}
        className={baseClasses}
        disabled={disabled || loading}
        onClick={handleClick}
        aria-disabled={disabled || loading}
        aria-label={loading ? 'Loading...' : undefined}
        {...props}
      >
        {loading && (
          <span className="btn__spinner" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle
                cx="8"
                cy="8"
                r="6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeDasharray="37.7"
                strokeDashoffset="37.7"
                className="btn__spinner-circle"
              />
            </svg>
          </span>
        )}
        {icon && <span className="btn__icon">{icon}</span>}
        <span className="btn__text">{children}</span>
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;