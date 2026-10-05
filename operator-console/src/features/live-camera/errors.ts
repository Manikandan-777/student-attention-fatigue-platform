export type LiveCameraErrorCode =
  | 'INSECURE_CONTEXT'
  | 'UNSUPPORTED'
  | 'PERMISSION_DENIED'
  | 'NOT_FOUND'
  | 'BUSY'
  | 'OVERCONSTRAINED'
  | 'DISABLED'
  | 'SERVER_BUSY'
  | 'TIMEOUT'
  | 'FRAME_TOO_LARGE'
  | 'CONNECTION_LOST'
  | 'UNKNOWN';

export class LiveCameraError extends Error {
  code: LiveCameraErrorCode;

  constructor(code: LiveCameraErrorCode, message?: string) {
    super(message || code);
    this.code = code;
    this.name = 'LiveCameraError';
  }
}

export function getErrorMessage(code: LiveCameraErrorCode | string): string {
  switch (code) {
    case 'INSECURE_CONTEXT':
      return 'The camera needs a secure (HTTPS) connection. Ask your administrator.';
    case 'PERMISSION_DENIED':
      return 'Camera permission was blocked. Allow it in the browser address bar and try again.';
    case 'NOT_FOUND':
      return 'No camera found.';
    case 'BUSY':
      return 'The camera is in use by another app or window. Close it and try again.';
    case 'UNSUPPORTED':
      return 'This browser does not support camera access. Use a current Chrome, Edge, Firefox or Safari.';
    case 'DISABLED':
    case '4403':
      return 'Live camera detection is not enabled on this server.';
    case 'SERVER_BUSY':
    case '4429':
    case '4503':
      return 'Live detection is busy. Try again in a moment.';
    case 'TIMEOUT':
    case '4408':
      return 'The live view stopped after a period of inactivity.';
    case 'FRAME_TOO_LARGE':
    case '4413':
      return 'The camera resolution was too high for network transmission.';
    case 'CONNECTION_LOST':
      return 'Connection lost. Reconnect to resume live detection.';
    default:
      return 'An unexpected camera error occurred. Please try again.';
  }
}
