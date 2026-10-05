import React from 'react';
import { Camera, ShieldCheck, X } from 'lucide-react';

interface ConsentNoticeProps {
  onAccept: () => void;
  onCancel: () => void;
}

export const ConsentNotice: React.FC<ConsentNoticeProps> = ({ onAccept, onCancel }) => {
  return (
    <div className="p-space-6 space-y-space-6 max-w-md mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-space-3">
          <div className="w-10 h-10 rounded-radius-full bg-bg-info text-accent-primary flex items-center justify-center">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-text-primary">
              Live Camera Detection
            </h3>
            <p className="text-xs text-text-muted">
              Privacy & Consent Notice
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="text-text-muted hover:text-text-primary transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-space-4 bg-bg-info border border-accent-primary/20 rounded-radius-lg space-y-space-2 text-xs text-text-body">
        <div className="flex items-start space-x-space-2">
          <ShieldCheck className="w-4 h-4 text-accent-primary flex-shrink-0 mt-0.5" />
          <p className="font-semibold text-text-primary">
            Strict Privacy Guarantees (D4, D5):
          </p>
        </div>
        <ul className="list-disc pl-space-6 space-y-space-1 text-xs text-text-secondary">
          <li>Video is analysed in real-time in memory and <strong>never recorded or stored</strong>.</li>
          <li>No biometric facial recognition is performed. Identities remain anonymous.</li>
          <li>Generated indicators support teacher observation; they are not diagnostic or disciplinary records.</li>
          <li>Closing this window immediately terminates camera access and hardware light.</li>
        </ul>
      </div>

      <div className="flex justify-end space-x-space-3 pt-space-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-space-4 py-space-2 text-xs font-semibold text-text-secondary border border-border-subtle rounded-radius-lg hover:border-border-strong hover:text-text-primary transition-colors focus:ring-2 focus:ring-accent-primary"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onAccept}
          className="px-space-4 py-space-2 text-xs font-semibold text-bg-surface bg-accent-primary rounded-radius-lg hover:opacity-90 transition-opacity shadow-sm focus:ring-2 focus:ring-accent-primary"
        >
          Start Camera
        </button>
      </div>
    </div>
  );
};
