import { LiveCameraError } from './errors';

export async function openCamera(): Promise<MediaStream> {
  // Allow localhost or secure HTTPS context
  const isLocalhost =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  if (typeof window !== 'undefined' && !window.isSecureContext && !isLocalhost) {
    throw new LiveCameraError('INSECURE_CONTEXT');
  }

  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    throw new LiveCameraError('UNSUPPORTED');
  }

  try {
    return await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user',
      },
      audio: false, // Strict privacy guarantee: never request audio
    });
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'name' in err) {
      const errorName = (err as { name: string }).name;
      if (errorName === 'NotAllowedError' || errorName === 'PermissionDeniedError') {
        throw new LiveCameraError('PERMISSION_DENIED');
      }
      if (errorName === 'NotFoundError' || errorName === 'DevicesNotFoundError') {
        throw new LiveCameraError('NOT_FOUND');
      }
      if (errorName === 'NotReadableError' || errorName === 'TrackStartError') {
        throw new LiveCameraError('BUSY');
      }
      if (errorName === 'OverconstrainedError') {
        // Fallback retry with generic video constraints
        try {
          return await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
          });
        } catch {
          throw new LiveCameraError('OVERCONSTRAINED');
        }
      }
    }
    throw new LiveCameraError('UNKNOWN', String(err));
  }
}

export function stopCamera(stream: MediaStream | null): void {
  if (!stream) return;
  stream.getTracks().forEach((track) => {
    track.stop();
  });
}
