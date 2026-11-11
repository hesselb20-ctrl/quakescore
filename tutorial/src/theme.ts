import {Easing, interpolate} from 'remotion';

export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const C = {
  bg: '#f5f5f7',
  surface: '#ffffff',
  ink: '#1d1d1f',
  ink2: '#424245',
  ink3: '#6e6e73',
  line: '#d2d2d7',
  faint: '#e8e8ed',
  accent: '#0071e3',
  accentSoft: '#e6f0fc',
  warm: '#e0782b',
  warmText: '#b4561a',
  warmSoft: '#fcefe4',
};

export const FONT =
  'system-ui, -apple-system, "Segoe UI Variable Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif';
export const MONO = 'ui-monospace, "Cascadia Mono", Consolas, "SF Mono", Menlo, monospace';

export const ease = Easing.bezier(0.25, 0.1, 0.25, 1);
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.45, 0, 0.55, 1);

/** 0 -> 1 between start and start + dur, eased, clamped. */
export const prog = (frame: number, start: number, dur = 20, e = easeOut) =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: e,
  });

/** Fade-and-rise style for an element that appears at `start`. */
export const rise = (frame: number, start: number, dur = 22, dist = 24): React.CSSProperties => {
  const p = prog(frame, start, dur);
  return {opacity: p, transform: `translateY(${(1 - p) * dist}px)`};
};

/** Visible between `start` and `end`, with soft fades on both sides. */
export const window_ = (frame: number, start: number, end: number, fade = 14) =>
  Math.min(prog(frame, start, fade, ease), 1 - prog(frame, end - fade, fade, ease));

// Small deterministic PRNG so every render is identical.
export const mulberry32 = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

export const gaussian = (rnd: () => number) => {
  const u = Math.max(rnd(), 1e-9);
  const v = rnd();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
};
