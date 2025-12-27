import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Button } from './Button';

interface ConfirmDeleteDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmWord?: string;
  confirmButtonText?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDeleteDialog: React.FC<ConfirmDeleteDialogProps> = ({
  isOpen,
  title,
  message,
  confirmWord = 'delete',
  confirmButtonText,
  onConfirm,
  onCancel,
}) => {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const isConfirmEnabled = inputValue.toLowerCase() === confirmWord.toLowerCase();

  useEffect(() => {
    if (isOpen) {
      setInputValue('');
      // Focus input after a short delay to allow dialog to render
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isConfirmEnabled) {
      onConfirm();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="relative bg-[#1e293b] border border-[#374151] rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
        {/* Close button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="p-3 bg-red-500/20 rounded-full">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
        </div>

        {/* Title */}
        <h3 className="text-xl font-semibold text-white text-center mb-2">
          {title}
        </h3>

        {/* Message */}
        <p className="text-gray-400 text-center mb-6">
          {message}
        </p>

        {/* Confirmation input */}
        <div className="mb-6">
          <label className="block text-sm text-gray-400 mb-2">
            Type <span className="font-mono text-red-400 font-semibold">{confirmWord}</span> to confirm:
          </label>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={confirmWord}
            className="w-full px-4 py-3 bg-[#0f172a] border border-[#374151] rounded-lg
                       text-white placeholder-gray-600 text-center font-mono
                       focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="ghost"
            className="flex-1"
            onClick={onCancel}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            className="flex-1"
            onClick={onConfirm}
            disabled={!isConfirmEnabled}
          >
            {confirmButtonText || (confirmWord === 'delete' ? 'Confirm Delete' : 'Confirm')}
          </Button>
        </div>
      </div>
    </div>
  );
};
