import React from 'react';
import {interpolate, interpolateColors, useCurrentFrame} from 'remotion';
import {C, easeInOut, gaussian, mulberry32, prog, rise, window_} from '../theme';
import {Eyebrow, Scene, SimTag} from '../ui';

// Illustrative spectrum in the style of docs/pitch/figures/fig1_principle.png.
// Two modes at 1.68 Hz and 1.99 Hz on a sloping phone-noise floor; the per-night
// noise is scaled so a single night hides the peaks. No axis values are claimed.
const F0 = 1.1;
const F1 = 2.7;
const NPTS = 321;
const NIGHTS = 20;
const freqs = Array.from({length: NPTS}, (_, i) => F0 + ((F1 - F0) * i) / (NPTS - 1));
const floorAt = (f: number) => 16.2 - 1.9 * ((f - F0) / (F1 - F0)) - 0.25 * Math.sin(((f - F0) / (F1 - F0)) * Math.PI);
const mode = (f: number, f0: number, z: number, a: number) => a / (1 + ((f - f0) / (z * f0)) ** 2);
const truth = freqs.map((f) => floorAt(f) + mode(f, 1.68, 0.03, 6.2) + mode(f, 1.99, 0.029, 6.6));
const nights: number[][] = (() => {
  const rnd = mulberry32(20261111);
  return Array.from({length: NIGHTS}, () => {
    const raw = freqs.map(() => gaussian(rnd));
    // short smoothing kernel (neighbouring spectral bins are not independent), rescaled to unit variance
    const ker = [0.05, 0.12, 0.2, 0.26, 0.2, 0.12, 0.05];
    const norm = Math.sqrt(ker.reduce((a, b) => a + b * b, 0));
    return raw.map((_, i) => ker.reduce((a, w, j) => a + w * (raw[Math.min(NPTS - 1, Math.max(0, i + j - 3))]), 0) / norm);
  });
})();
// cumulative sums so the average over k nights is cheap
const cum: number[][] = [];
nights.forEach((n, k) => cum.push(n.map((v, i) => v + (k ? cum[k - 1][i] : 0))));
const REL = 0.33; // one night: noise standard deviation as a share of the expected level

const stackedAt = (k: number) => {
  const lo = Math.max(1, Math.floor(k));
  const hi = Math.min(NIGHTS, lo + 1);
  const t = k - lo;
  return truth.map((tv, i) => {
    const a = tv * (1 + (REL * cum[lo - 1][i]) / lo);
    const b = tv * (1 + (REL * cum[hi - 1][i]) / hi);
    return Math.max(0.6, a + (b - a) * t);
  });
};

// chart geometry
const CX = 150;
const CY = 250;
const CW = 1240;
const CH = 640;

export const Stacking: React.FC = () => {
  const f = useCurrentFrame();
  // nights stacked over time: 1 -> 5 -> 10 -> 20
  const k = interpolate(f, [150, 200, 230, 280, 310, 370], [1, 5, 5, 10, 10, 20], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeInOut,
  });
  const zoom = interpolate(k, [1, 20], [0, 1]);
  const yMin = interpolate(zoom, [0, 1], [0, 9.5]);
  const yMax = interpolate(zoom, [0, 1], [36, 27.5]);
  const sx = (fr: number) => CX + ((fr - F0) / (F1 - F0)) * CW;
  const sy = (v: number) => CY + CH - ((Math.min(Math.max(v, yMin), yMax) - yMin) / (yMax - yMin)) * CH;

  const reveal = prog(f, 30, 50, easeInOut);
  const vals = stackedAt(k);
  const nShow = Math.max(2, Math.round(NPTS * reveal));
  const line = vals
    .slice(0, nShow)
    .map((v, i) => `${sx(freqs[i]).toFixed(1)},${sy(v).toFixed(1)}`)
    .join(' ');
  const floorLine = freqs.map((fr) => `${sx(fr).toFixed(1)},${sy(floorAt(fr)).toFixed(1)}`).join(' ');
  const color = interpolateColors(k, [1, 8, 20], [C.warm, '#9a7a8a', C.accent]);
  const peaks = prog(f, 385, 24);
  const nightsLabel = Math.round(k);

  const captions: [number, number, string][] = [
    [20, 160, "One night, one phone: the building is buried in the phone's own noise."],
    [160, 380, 'Stack more nights, and the noise averages away.'],
    [380, 500, 'Two narrow peaks rise above the noise floor: the building.'],
  ];

  const ticks = [1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6];
  return (
    <Scene>
      <div style={{position: 'absolute', left: CX, top: 70, width: 1620}}>
        <Eyebrow style={rise(f, 6)}>Why stacking</Eyebrow>
        <div style={{position: 'relative', height: 80, marginTop: 12}}>
          {captions.map(([a, b, t]) => (
            <div
              key={t}
              style={{
                position: 'absolute',
                fontSize: 50,
                fontWeight: 650,
                letterSpacing: -0.6,
                opacity: window_(f, a, b, 16),
              }}
            >
              {t}
            </div>
          ))}
        </div>
      </div>
      <SimTag style={{position: 'absolute', left: 1450, top: CY, ...rise(f, 10)}} />

      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        <g opacity={prog(f, 14, 24)}>
          <rect x={CX} y={CY} width={CW} height={CH} rx={20} fill={C.surface} />
          {ticks.map((t) => (
            <g key={t}>
              <line x1={sx(t)} x2={sx(t)} y1={CY + 16} y2={CY + CH - 16} stroke={C.faint} strokeWidth={2} />
              <text x={sx(t)} y={CY + CH + 44} textAnchor="middle" fontSize={28} fill={C.ink3}>
                {t.toFixed(1)}
              </text>
            </g>
          ))}
          <text x={CX + CW / 2} y={CY + CH + 92} textAnchor="middle" fontSize={30} fill={C.ink2} fontWeight={550}>
            Frequency (Hz)
          </text>
          <text
            x={CX - 36}
            y={CY + CH / 2}
            textAnchor="middle"
            fontSize={30}
            fill={C.ink2}
            fontWeight={550}
            transform={`rotate(-90 ${CX - 36} ${CY + CH / 2})`}
          >
            Sway power
          </text>
        </g>
        <polyline
          points={floorLine}
          fill="none"
          stroke={C.ink3}
          strokeWidth={3}
          strokeDasharray="14 10"
          opacity={prog(f, 60, 24) * 0.9}
        />
        <polyline points={line} fill="none" stroke={color} strokeWidth={3.5} strokeLinejoin="round" />
        {[
          [1.68, '1.68 Hz'],
          [1.99, '1.99 Hz'],
        ].map(([fr, lab], i) => {
          const x = sx(fr as number);
          const c = Math.round((((fr as number) - F0) / (F1 - F0)) * (NPTS - 1));
          const y = Math.min(...vals.slice(c - 6, c + 7).map(sy)) - 34;
          const p = prog(f, 385 + i * 10, 24);
          return (
            <g key={lab as string} opacity={p} transform={`translate(0 ${(1 - p) * 12})`}>
              <line x1={x} x2={x} y1={y - 8} y2={y + 26} stroke={C.ink} strokeWidth={2.5} />
              <rect x={x - 82} y={y - 66} width={164} height={52} rx={26} fill={C.accent} />
              <text x={x} y={y - 30} textAnchor="middle" fontSize={30} fontWeight={700} fill="#ffffff">
                {lab}
              </text>
            </g>
          );
        })}
      </svg>

      {/* right panel: nights counter and legend */}
      <div style={{position: 'absolute', left: 1450, top: CY + 110, width: 400, ...rise(f, 20)}}>
        <div style={{fontSize: 30, color: C.ink2, fontWeight: 550}}>Nights stacked</div>
        <div
          style={{
            fontSize: 150,
            fontWeight: 700,
            letterSpacing: -4,
            color,
            fontVariantNumeric: 'tabular-nums',
            lineHeight: 1.05,
          }}
        >
          {nightsLabel}
        </div>
        <div style={{marginTop: 40, display: 'flex', flexDirection: 'column', gap: 22, fontSize: 28, color: C.ink2}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
            <svg width={56} height={10}>
              <line x1={2} x2={54} y1={5} y2={5} stroke={C.ink3} strokeWidth={4} strokeDasharray="12 8" />
            </svg>
            Phone noise floor
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
            <svg width={56} height={10}>
              <line x1={2} x2={54} y1={5} y2={5} stroke={color} strokeWidth={5} strokeLinecap="round" />
            </svg>
            Average of all nights
          </div>
        </div>
        <div style={{marginTop: 46, fontSize: 28, lineHeight: 1.35, color: C.ink3, opacity: peaks}}>
          Example values from the simulation.
        </div>
      </div>
    </Scene>
  );
};
