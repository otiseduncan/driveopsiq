/**
 * Input Component with TypeScript support and validation
 */

import React, { InputHTMLAttributes, forwardRef, useState } from 'react';
// Import removed - using inline interface definition

interface ExtendedInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type' | 'value' | 'onBlur'> {
  // Custom props from InputProps
  type?: string;
  value?: string;
  placeholder?: string;
  onChange?: (value: string) => void;
  onBlur?: () => void;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  className?: string;
  children?: React.ReactNode;
  
  // Extended props
  label?: string;
  helperText?: string;
  showError?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onClear?: () => void;
  clearable?: boolean;
}

const Input = forwardRef<HTMLInputElement, ExtendedInputProps>(
  (
    {
      className = '',
      type = 'text',
      value = '',
      placeholder,
      label,
      helperText,
      error,
      showError = true,
      disabled = false,
      required = false,
      leftIcon,
      rightIcon,
      clearable = false,
      onChange,
      onBlur,
      onClear,
      ...props
    },
    ref
  ) => {
    const [focused, setFocused] = useState(false);
    const hasError = Boolean(error);
    const hasValue = Boolean(value);

    const containerClasses = [
      'input-container',
      focused && 'input-container--focused',
      hasError && 'input-container--error',
      disabled && 'input-container--disabled',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    const inputClasses = [
      'input',
      leftIcon && 'input--with-left-icon',
      (rightIcon || (clearable && hasValue)) && 'input--with-right-icon',
    ]
      .filter(Boolean)
      .join(' ');

    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(event.target.value);
    };

    const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
      setFocused(true);
      props.onFocus?.(event);
    };

    const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
      setFocused(false);
      onBlur?.();
      // Call native onBlur if it exists
      if ('onBlur' in props && typeof props.onBlur === 'function') {
        (props.onBlur as (event: React.FocusEvent<HTMLInputElement>) => void)(event);
      }
    };

    const handleClear = () => {
      onChange?.('');
      onClear?.();
    };

    return (
      <div className={containerClasses}>
        {label && (
          <label className="input-label" htmlFor={props.id}>
            {label}
            {required && <span className="input-label__required" aria-label="required">*</span>}
          </label>
        )}
        
        <div className="input-wrapper">
          {leftIcon && (
            <div className="input-icon input-icon--left" aria-hidden="true">
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            type={type}
            value={value}
            placeholder={placeholder}
            className={inputClasses}
            disabled={disabled}
            required={required}
            onChange={handleChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            aria-invalid={hasError}
            aria-describedby={
              [
                error && `${props.id}-error`,
                helperText && `${props.id}-helper`,
              ]
                .filter(Boolean)
                .join(' ') || undefined
            }
            {...props}
          />
          
          {clearable && hasValue && !disabled && (
            <button
              type="button"
              className="input-clear"
              onClick={handleClear}
              aria-label="Clear input"
              tabIndex={-1}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M12 4L4 12M4 4L12 12"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          )}
          
          {rightIcon && (
            <div className="input-icon input-icon--right" aria-hidden="true">
              {rightIcon}
            </div>
          )}
        </div>
        
        {showError && error && (
          <div className="input-error" id={`${props.id}-error`} role="alert">
            {error}
          </div>
        )}
        
        {helperText && !error && (
          <div className="input-helper" id={`${props.id}-helper`}>
            {helperText}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;