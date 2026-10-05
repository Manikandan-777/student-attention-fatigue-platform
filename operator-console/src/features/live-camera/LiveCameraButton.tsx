import React, { useState } from 'react';
import { Camera } from 'lucide-react';
import { LiveCameraDialog } from './LiveCameraDialog';

export const LiveCameraButton: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-text-primary bg-bg-surface border border-border-strong rounded-radius-lg hover:border-accent-primary hover:text-accent-primary transition-colors focus:outline-none focus:ring-2 focus:ring-accent-primary shadow-sm"
        aria-label="Open live camera detection dialog"
      >
        <Camera className="w-3.5 h-3.5 mr-space-2 text-accent-primary" aria-hidden="true" />
        Live camera detection
      </button>

      {isOpen && (
        <LiveCameraDialog
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
        />
      )}
    </>
  );
};

export default LiveCameraButton;
