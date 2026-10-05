import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Camera, X, AlertTriangle, RefreshCw, StopCircle } from 'lucide-react';
import { ConsentNotice } from './ConsentNotice';
import { OverlayCanvas } from './OverlayCanvas';
import { ResultsPanel } from './ResultsPanel';
import { openCamera, stopCamera } from './useCamera';
import { grabFrame } from './frameCapture';
import { useLiveSocket } from './useLiveSocket';
import { getErrorMessage, LiveCameraError } from './errors';

interface LiveCameraDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LiveCameraDialog: React.FC<LiveCameraDialogProps> = ({ isOpen, onClose }) => {
  const [hasConsented, setHasConsented] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [videoDims, setVideoDims] = useState<{ width: number; height: number }>({ width: 640, height: 480 });

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const frameLoopRef = useRef<number | null>(null);
  const hiddenTimeoutRef = useRef<number | null>(null);

  const {
    isConnected,
    isSlowConnection,
    errorMessage: socketError,
    latestTracks,
    lastLatencyMs,
    sendFrame,
  } = useLiveSocket({
    enabled: isOpen && hasConsented && stream !== null,
  });

  const handleStop = useCallback(() => {
    if (frameLoopRef.current) {
      clearInterval(frameLoopRef.current);
      frameLoopRef.current = null;
    }
    stopCamera(stream);
    setStream(null);
    setHasConsented(false);
    setCameraError(null);
    onClose();
  }, [stream, onClose]);

  // Escape key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleStop();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleStop]);

  // Tab visibility change: stop if hidden > 30s
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        hiddenTimeoutRef.current = window.setTimeout(() => {
          handleStop();
        }, 30000);
      } else {
        if (hiddenTimeoutRef.current) {
          clearTimeout(hiddenTimeoutRef.current);
          hiddenTimeoutRef.current = null;
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (hiddenTimeoutRef.current) clearTimeout(hiddenTimeoutRef.current);
    };
  }, [handleStop]);

  // Start camera when consent is given
  const startCameraStream = async () => {
    setIsInitializing(true);
    setCameraError(null);
    try {
      const mediaStream = await openCamera();
      setStream(mediaStream);
      setHasConsented(true);
    } catch (err: unknown) {
      if (err instanceof LiveCameraError) {
        setCameraError(getErrorMessage(err.code));
      } else {
        setCameraError(getErrorMessage('UNKNOWN'));
      }
    } finally {
      setIsInitializing(false);
    }
  };

  // Wire stream to video element
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.onloadedmetadata = () => {
        if (videoRef.current) {
          const vw = videoRef.current.videoWidth || 640;
          const vh = videoRef.current.videoHeight || 480;
          setVideoDims({ width: vw, height: vh });
          videoRef.current.play().catch(() => {});
        }
      };
    }
  }, [stream]);

  // Frame capture loop (10 FPS)
  useEffect(() => {
    if (!isOpen || !hasConsented || !stream || !isConnected) {
      if (frameLoopRef.current) {
        clearInterval(frameLoopRef.current);
        frameLoopRef.current = null;
      }
      return;
    }

    const interval = 1000 / 10; // ~10 FPS target
    frameLoopRef.current = window.setInterval(() => {
      if (videoRef.current) {
        const frameB64 = grabFrame(videoRef.current, 640, 0.7);
        if (frameB64) {
          sendFrame(frameB64);
        }
      }
    }, interval);

    return () => {
      if (frameLoopRef.current) {
        clearInterval(frameLoopRef.current);
        frameLoopRef.current = null;
      }
    };
  }, [isOpen, hasConsented, stream, isConnected, sendFrame]);

  // Clean cleanup on dialog unmount
  useEffect(() => {
    return () => {
      stopCamera(stream);
    };
  }, [stream]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-space-4"
      role="dialog"
      aria-modal="true"
      aria-label="Live Camera Detection Dialog"
    >
      <div className="bg-bg-surface border border-border-subtle rounded-radius-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {!hasConsented ? (
          <ConsentNotice
            onAccept={startCameraStream}
            onCancel={handleStop}
          />
        ) : (
          <>
            {/* Header toolbar */}
            <div className="flex items-center justify-between px-space-6 py-space-4 border-b border-border-subtle bg-bg-surface">
              <div className="flex items-center space-x-space-3">
                <Camera className="w-5 h-5 text-accent-primary" />
                <h3 className="text-base font-bold text-text-primary">
                  Live Camera Analytics
                </h3>
                {/* Persistent Camera On badge */}
                <span className="inline-flex items-center px-space-2 py-0.5 rounded-radius-pill text-xs font-semibold text-accent-success bg-bg-success border border-accent-success">
                  <span className="w-2 h-2 rounded-full bg-accent-success animate-pulse mr-space-1" />
                  Camera on
                </span>
                {isSlowConnection && (
                  <span className="text-xs text-accent-primary font-medium">
                    Connection slow
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-space-3">
                <button
                  type="button"
                  onClick={handleStop}
                  className="inline-flex items-center px-space-3 py-space-2 text-xs font-semibold text-accent-danger bg-bg-surface border border-accent-danger rounded-radius-lg hover:bg-accent-danger hover:text-bg-surface transition-colors focus:ring-2 focus:ring-accent-danger"
                  aria-label="Stop camera stream"
                >
                  <StopCircle className="w-4 h-4 mr-space-1" />
                  Stop Camera
                </button>
                <button
                  type="button"
                  onClick={handleStop}
                  className="text-text-muted hover:text-text-primary transition-colors p-1"
                  aria-label="Close dialog"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content area: Preview & Results */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-space-4 p-space-6 flex-1 overflow-hidden">
              {/* Camera Preview with Overlay */}
              <div className="md:col-span-2 relative bg-black rounded-radius-lg overflow-hidden flex items-center justify-center min-h-[360px]">
                {isInitializing && (
                  <div className="text-center text-text-muted space-y-space-2">
                    <RefreshCw className="w-8 h-8 mx-auto animate-spin text-accent-primary" />
                    <p className="text-xs font-medium text-bg-surface">Connecting to camera...</p>
                  </div>
                )}

                {cameraError || socketError ? (
                  <div className="p-space-6 text-center space-y-space-3 max-w-sm">
                    <AlertTriangle className="w-8 h-8 text-accent-danger mx-auto" />
                    <p className="text-xs font-semibold text-bg-surface">
                      {cameraError || socketError}
                    </p>
                    <button
                      type="button"
                      onClick={startCameraStream}
                      className="px-space-4 py-space-2 text-xs font-semibold bg-accent-primary text-bg-surface rounded-radius-lg hover:opacity-90"
                    >
                      Try Again
                    </button>
                  </div>
                ) : (
                  <>
                    <video
                      ref={videoRef}
                      className="w-full h-full object-contain"
                      style={{ transform: 'scaleX(-1)' }} // Preview mirrored for user comfort
                      muted
                      playsInline
                      autoPlay
                    />
                    <OverlayCanvas
                      tracks={latestTracks}
                      width={videoDims.width}
                      height={videoDims.height}
                      mirrored={true}
                    />
                  </>
                )}
              </div>

              {/* Real-time Status Results Panel */}
              <div className="bg-bg-surface border border-border-subtle rounded-radius-lg p-space-4 flex flex-col h-[360px] md:h-full">
                <ResultsPanel tracks={latestTracks} latencyMs={lastLatencyMs} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
