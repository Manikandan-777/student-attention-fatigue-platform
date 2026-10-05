let captureCanvas: HTMLCanvasElement | null = null;

export function grabFrame(
  video: HTMLVideoElement,
  maxW: number = 640,
  quality: number = 0.7,
): string | null {
  const vw = video.videoWidth;
  const vh = video.videoHeight;

  if (!vw || !vh) {
    return null; // Camera feed not yet populated with pixels
  }

  if (!captureCanvas) {
    captureCanvas = document.createElement('canvas');
  }

  const scale = Math.min(1.0, maxW / vw);
  const targetW = Math.round(vw * scale);
  const targetH = Math.round(vh * scale);

  captureCanvas.width = targetW;
  captureCanvas.height = targetH;

  const ctx = captureCanvas.getContext('2d');
  if (!ctx) {
    return null;
  }

  // Draw unmirrored frame to canvas (server expects canonical coordinate system)
  ctx.drawImage(video, 0, 0, targetW, targetH);

  // Return base64 JPEG data without data-URL scheme prefix
  const dataUrl = captureCanvas.toDataURL('image/jpeg', quality);
  const commaIdx = dataUrl.indexOf(',');
  return commaIdx !== -1 ? dataUrl.slice(commaIdx + 1) : null;
}
