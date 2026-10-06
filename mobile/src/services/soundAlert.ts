import { Platform } from 'react-native';
import * as Speech from 'expo-speech';
import { Audio } from 'expo-av';
import { Alert } from '../types';

let webAudioCtx: any = null;

function getWebAudioContext(): any {
  if (typeof window === 'undefined') return null;
  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
  if (!AudioContextClass) return null;
  if (!webAudioCtx) {
    webAudioCtx = new AudioContextClass();
  }
  if (webAudioCtx.state === 'suspended') {
    webAudioCtx.resume().catch(() => {});
  }
  return webAudioCtx;
}

class SoundAlertService {
  private isMuted: boolean = false;
  private lastAlertTime: number = 0;
  private activeUtterance: any = null;

  constructor() {
    this.isMuted = false;
    this.initAudioUnlock();
  }

  /**
   * Unlock browser audio context and speech synthesis on user gestures.
   */
  private initAudioUnlock() {
    if (typeof window !== 'undefined') {
      const unlock = () => {
        this.unlockAudio();
      };
      ['click', 'touchstart', 'touchend', 'pointerdown', 'keydown'].forEach((evt) => {
        if (typeof window.addEventListener === 'function') {
          window.addEventListener(evt, unlock, { passive: true });
        }
        if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
          document.addEventListener(evt, unlock, { passive: true });
        }
      });
    }
  }

  /**
   * Explicitly unlock audio context and speech synthesis.
   */
  unlockAudio(): void {
    if (typeof window !== 'undefined') {
      try {
        const ctx = getWebAudioContext();
        if (ctx && ctx.state === 'suspended') {
          ctx.resume().catch(() => {});
        }
        if ('speechSynthesis' in window) {
          if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
          }
        }
      } catch {
        // Ignore
      }
    }
  }

  setMuted(muted: boolean): void {
    this.isMuted = muted;
    if (muted) {
      this.stop();
    }
  }

  toggleMute(): boolean {
    this.setMuted(!this.isMuted);
    return this.isMuted;
  }

  getIsMuted(): boolean {
    return this.isMuted;
  }

  stop(): void {
    if (Platform.OS === 'web' && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignore
      }
    }
    try {
      Speech.stop();
    } catch {
      // Ignore
    }
  }

  /**
   * Plays a loud, attention-grabbing dual-tone alert chime (alarm tone).
   */
  async playAlertSound(): Promise<void> {
    if (this.isMuted) return;

    // 1. Synthesize loud alert chime using Web Audio API (works 100% reliably in Web/browsers)
    if (typeof window !== 'undefined') {
      try {
        const ctx = getWebAudioContext();
        if (ctx) {
          const now = ctx.currentTime;
          
          // Dual-frequency beep burst 1 (High tone 880Hz)
          const osc1 = ctx.createOscillator();
          const gain1 = ctx.createGain();
          osc1.type = 'triangle';
          osc1.frequency.setValueAtTime(880, now);
          gain1.gain.setValueAtTime(0.5, now);
          gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.18);
          osc1.connect(gain1);
          gain1.connect(ctx.destination);
          osc1.start(now);
          osc1.stop(now + 0.2);

          // Second tone (660Hz)
          const osc2 = ctx.createOscillator();
          const gain2 = ctx.createGain();
          osc2.type = 'triangle';
          osc2.frequency.setValueAtTime(660, now + 0.12);
          gain2.gain.setValueAtTime(0.5, now + 0.12);
          gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.32);
          osc2.connect(gain2);
          gain2.connect(ctx.destination);
          osc2.start(now + 0.12);
          osc2.stop(now + 0.35);

          // Burst 2 (repeat chime 200ms later for urgency)
          const osc3 = ctx.createOscillator();
          const gain3 = ctx.createGain();
          osc3.type = 'triangle';
          osc3.frequency.setValueAtTime(980, now + 0.28);
          gain3.gain.setValueAtTime(0.6, now + 0.28);
          gain3.gain.exponentialRampToValueAtTime(0.01, now + 0.48);
          osc3.connect(gain3);
          gain3.connect(ctx.destination);
          osc3.start(now + 0.28);
          osc3.stop(now + 0.5);
        }
      } catch (e) {
        console.warn('Web Audio chime playback failed:', e);
      }
    }

    // 2. Also attempt bundled audio playback via expo-av
    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../assets/sounds/alert_high.wav'),
        { shouldPlay: true, volume: 1.0 }
      );
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          sound.unloadAsync().catch(() => {});
        }
      });
    } catch {
      // Bundled asset playback fallback to synth
    }
  }

  /**
   * Plays an urgent high-priority alarm siren (higher pitch, rapid rising bursts).
   */
  async playUrgentAlarmSound(): Promise<void> {
    if (this.isMuted) return;

    if (typeof window !== 'undefined') {
      try {
        const ctx = getWebAudioContext();
        if (ctx) {
          const now = ctx.currentTime;

          // Urgent Pulse 1: 960Hz -> 1220Hz
          const osc1 = ctx.createOscillator();
          const gain1 = ctx.createGain();
          osc1.type = 'sawtooth';
          osc1.frequency.setValueAtTime(960, now);
          osc1.frequency.exponentialRampToValueAtTime(1220, now + 0.15);
          gain1.gain.setValueAtTime(0.7, now);
          gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.18);
          osc1.connect(gain1);
          gain1.connect(ctx.destination);
          osc1.start(now);
          osc1.stop(now + 0.19);

          // Urgent Pulse 2: 1220Hz -> 1500Hz
          const osc2 = ctx.createOscillator();
          const gain2 = ctx.createGain();
          osc2.type = 'sawtooth';
          osc2.frequency.setValueAtTime(1220, now + 0.16);
          osc2.frequency.exponentialRampToValueAtTime(1500, now + 0.31);
          gain2.gain.setValueAtTime(0.75, now + 0.16);
          gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.33);
          osc2.connect(gain2);
          gain2.connect(ctx.destination);
          osc2.start(now + 0.16);
          osc2.stop(now + 0.34);

          // Urgent Pulse 3: 1500Hz -> 1850Hz (Loudest climax)
          const osc3 = ctx.createOscillator();
          const gain3 = ctx.createGain();
          osc3.type = 'sawtooth';
          osc3.frequency.setValueAtTime(1500, now + 0.32);
          osc3.frequency.exponentialRampToValueAtTime(1850, now + 0.5);
          gain3.gain.setValueAtTime(0.8, now + 0.32);
          gain3.gain.exponentialRampToValueAtTime(0.01, now + 0.53);
          osc3.connect(gain3);
          gain3.connect(ctx.destination);
          osc3.start(now + 0.32);
          osc3.stop(now + 0.54);
        }
      } catch (e) {
        console.warn('Web Audio urgent alarm failed:', e);
      }
    }

    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../assets/sounds/alert_high.wav'),
        { shouldPlay: true, volume: 1.0 }
      );
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          sound.unloadAsync().catch(() => {});
        }
      });
    } catch {
      // Audio asset fallback
    }
  }

  /**
   * Speak out text using Web Speech API or expo-speech.
   */
  speakText(text: string): void {
    if (this.isMuted) return;

    if (Platform.OS === 'web' && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
        if (window.speechSynthesis.speaking || window.speechSynthesis.pending) {
          window.speechSynthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 1.05;
        utterance.pitch = 1.1;
        utterance.volume = 1.0;

        // Retain reference on class and window to prevent V8 Garbage Collection bug in Chrome/Chromium
        this.activeUtterance = utterance;
        (window as any).__voiceUtterance = utterance;

        utterance.onend = () => {
          if (this.activeUtterance === utterance) this.activeUtterance = null;
        };
        utterance.onerror = (e) => {
          console.warn('SpeechSynthesis error:', e);
          if (this.activeUtterance === utterance) this.activeUtterance = null;
        };

        // Small 30ms timeout after cancel() prevents Chromium from swallowing the utterance
        setTimeout(() => {
          try {
            if (window.speechSynthesis.paused) {
              window.speechSynthesis.resume();
            }
            window.speechSynthesis.speak(utterance);
          } catch (speakErr) {
            console.warn('Speak error:', speakErr);
          }
        }, 30);

        return;
      } catch (err) {
        console.warn('Web Speech API error:', err);
      }
    }

    // Native mobile fallback (Expo Speech)
    try {
      Speech.speak(text, {
        language: 'en-US',
        pitch: 1.05,
        rate: 1.0,
        volume: 1.0,
      });
    } catch {
      // Ignore
    }
  }

  /**
   * Alias for speakText.
   */
  speak(text: string): void {
    this.speakText(text);
  }

  /**
   * Speak alert directly.
   */
  speakAlert(alert: Alert): void {
    this.triggerAlert(alert);
  }

  /**
   * Trigger both loud sound chime AND voice speech for a student behavior alert.
   */
  triggerAlert(alert: Alert): void {
    if (this.isMuted) return;

    const now = Date.now();
    if (now - this.lastAlertTime < 3500) {
      return; // Cooldown
    }
    this.lastAlertTime = now;

    // 1. Play loud chime immediately
    this.playAlertSound();

    // 2. Speak voice alert
    const studentLabel = alert.label
      ? alert.label.startsWith('S')
        ? `Student ${alert.label}`
        : alert.label
      : `Student #${alert.track_id ?? ''}`;

    let messageText = '';
    if (alert.type === 'fatigue') {
      messageText = `Alert! ${studentLabel} shows fatigue. ${alert.message}.`;
    } else if (alert.type === 'distraction') {
      messageText = `Alert! ${studentLabel} is inattentive and looking away from class.`;
    } else {
      messageText = `Class alert: ${alert.message}.`;
    }

    setTimeout(() => {
      this.speakText(messageText);
    }, 450);
  }

  /**
   * Immediate Shout when high amount of student fatigue is detected.
   * Plays loud emergency siren alarm and speaks urgent alert prompt.
   */
  shoutImmediateHighFatigue(details: {
    fatiguePct: number;
    count: number;
    studentLabel?: string;
    advisoryText?: string;
  }): void {
    if (this.isMuted) return;

    this.lastAlertTime = Date.now();

    // 1. Play urgent emergency siren alarm
    this.playUrgentAlarmSound();

    // 2. Immediate urgent voice shout
    const pct = Math.round(details.fatiguePct || 0);
    const count = details.count || 0;

    let speech = '';
    if (details.studentLabel) {
      speech = `Emergency Alert! High fatigue detected for ${details.studentLabel}. ${details.advisoryText || 'Immediate teacher action needed.'}`;
    } else {
      speech = `Emergency Alert! High student fatigue detected! ${count} students are fatigued, class fatigue at ${pct} percent! ${details.advisoryText ? details.advisoryText + '.' : ''} Immediate teacher intervention required!`;
    }

    setTimeout(() => {
      this.speakText(speech);
    }, 480);
  }

  /**
   * Automatic 30-Second Periodic Shout for active session fatigue & attention status.
   */
  shoutPeriodic30s(summary: {
    fatiguePct: number;
    count: number;
    distractedCount: number;
    advisoryText?: string;
    activeAlertLabel?: string;
  }): void {
    if (this.isMuted) return;

    this.lastAlertTime = Date.now();

    // 1. Play alert chime
    this.playAlertSound();

    // 2. Spoken 30s status summary
    const pct = Math.round(summary.fatiguePct || 0);
    const count = summary.count || 0;
    const distracted = summary.distractedCount || 0;

    let speech = `Attention! 30-second fatigue check: ${count} students fatigued, ${distracted} distracted. Class fatigue is at ${pct} percent.`;
    if (summary.activeAlertLabel) {
      speech += ` Attention required for ${summary.activeAlertLabel}.`;
    } else if (summary.advisoryText) {
      speech += ` Advisory: ${summary.advisoryText}.`;
    }

    setTimeout(() => {
      this.speakText(speech);
    }, 450);
  }

  /**
   * Trigger sound & voice test.
   */
  testAlert(): void {
    this.playAlertSound();
    setTimeout(() => {
      this.speakText('Alert! Student S001 shows fatigue indicators. Frequent yawning detected.');
    }, 450);
  }

  /**
   * Test immediate high fatigue emergency shout.
   */
  testHighFatigueAlert(): void {
    this.shoutImmediateHighFatigue({
      fatiguePct: 48,
      count: 6,
      advisoryText: 'Make the session more interactive',
    });
  }

  /**
   * Test 30-second periodic shout.
   */
  testPeriodic30sAlert(): void {
    this.shoutPeriodic30s({
      fatiguePct: 38,
      count: 6,
      distractedCount: 8,
      advisoryText: 'Provide active student interaction',
    });
  }
}

export const soundAlertService = new SoundAlertService();
export const speechService = soundAlertService; // Alias for compatibility
