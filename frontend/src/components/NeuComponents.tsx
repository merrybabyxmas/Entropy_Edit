import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface NeuPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  inset?: boolean;
}

export const NeuPanel: React.FC<NeuPanelProps> = ({
  children,
  className,
  inset = false,
  ...props
}) => {
  return (
    <div
      className={cn(
        "bg-background rounded-xl p-4 transition-all duration-200",
        inset ? "shadow-neu-in" : "shadow-neu-out",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const NeuButton: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }> = ({
  children,
  className,
  active = false,
  ...props
}) => {
  return (
    <button
      className={cn(
        "px-4 py-2 rounded-lg font-medium transition-all duration-200 active:shadow-neu-in outline-none select-none",
        active ? "shadow-neu-in text-primary" : "shadow-neu-out text-text hover:-translate-y-0.5",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};

export const NeuSlider: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = ({ className, ...props }) => {
  return (
    <div className="relative w-full h-6 flex items-center">
      <input
        type="range"
        className={cn(
          "w-full h-2 bg-transparent appearance-none cursor-pointer z-10",
          "focus:outline-none",
          className
        )}
        {...props}
      />
      <div className="absolute inset-0 h-2 my-auto bg-background rounded-full shadow-neu-in pointer-events-none" />
      {/* Custom thumb styles usually need standard CSS due to browser prefixes */}
      <style>{`
        input[type=range]::-webkit-slider-thumb {
          -webkit-appearance: none;
          height: 16px;
          width: 16px;
          border-radius: 50%;
          background: #e0e5ec;
          box-shadow: 5px 5px 10px #a3b1c6, -5px -5px 10px #ffffff;
          margin-top: -4px; /* Adjust as needed */
        }
      `}</style>
    </div>
  );
};
