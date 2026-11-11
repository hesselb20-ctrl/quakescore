import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, FONT, ease, prog} from './theme';

/** Scene shell: neutral background, fade in and out at the scene edges. */
export const Scene: React.FC<{children: React.ReactNode; fadeOut?: boolean}> = ({
  children,
  fadeOut = true,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const fin = prog(frame, 0, 16, ease);
  const fout = fadeOut ? 1 - prog(frame, durationInFrames - 16, 16, ease) : 1;
  return (
    <AbsoluteFill style={{fontFamily: FONT, color: C.ink, opacity: Math.min(fin, fout)}}>
      {children}
    </AbsoluteFill>
  );
};

export const Eyebrow: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({
  children,
  style,
}) => (
  <div
    style={{
      fontSize: 30,
      fontWeight: 600,
      letterSpacing: 0.4,
      color: C.accent,
      textTransform: 'uppercase',
      ...style,
    }}
  >
    {children}
  </div>
);

export const Headline: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({
  children,
  style,
}) => (
  <div
    style={{
      fontSize: 60,
      fontWeight: 650,
      lineHeight: 1.15,
      letterSpacing: -0.8,
      color: C.ink,
      ...style,
    }}
  >
    {children}
  </div>
);

/** The visible tag on every chart or map that shows simulated data. */
export const SimTag: React.FC<{style?: React.CSSProperties}> = ({style}) => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 12,
      padding: '10px 22px',
      borderRadius: 999,
      background: C.warmSoft,
      border: `2px solid ${C.warm}`,
      color: C.warmText,
      fontSize: 28,
      fontWeight: 700,
      ...style,
    }}
  >
    <span style={{width: 14, height: 14, borderRadius: 7, background: C.warm}} />
    Simulated
  </div>
);

type BuildingProps = {
  width: number;
  height: number;
  floors: number;
  cols: number;
  /** Horizontal offset of the roof in px; floors shear linearly towards the ground. */
  sway: number;
  color?: string;
  window?: string;
  children?: (floorY: (i: number) => number, floorH: number, shift: (i: number) => number) => React.ReactNode;
};

/** A simple shear-frame building drawn floor by floor, so sway bends it instead of tilting it. */
export const Building: React.FC<BuildingProps> = ({
  width,
  height,
  floors,
  cols,
  sway,
  color = '#c9ccd3',
  window = '#eef0f4',
  children,
}) => {
  const floorH = height / floors;
  const shift = (level: number) => sway * Math.sin((Math.PI / 2) * (level / floors));
  const floorY = (i: number) => height - (i + 1) * floorH; // i = 0 is ground floor
  const pad = 22;
  const winW = (width - pad * 2 - (cols - 1) * 14) / cols;
  return (
    <svg width={width + Math.abs(sway) * 2 + 20} height={height + 4} style={{overflow: 'visible'}}>
      <g transform={`translate(${Math.abs(sway) + 10},0)`}>
        {Array.from({length: floors}).map((_, i) => {
          const y = floorY(i);
          const x0 = shift(i);
          const x1 = shift(i + 1);
          const top = i === floors - 1;
          const r = top ? 18 : 0;
          return (
            <g key={i}>
              <path
                d={`M ${x0} ${y + floorH} L ${x0 + width} ${y + floorH} L ${x1 + width} ${y + r} Q ${x1 + width} ${y} ${x1 + width - r} ${y} L ${x1 + r} ${y} Q ${x1} ${y} ${x1} ${y + r} Z`}
                fill={color}
              />
              {Array.from({length: cols}).map((__, j) => {
                const wx = (x0 + x1) / 2 + pad + j * (winW + 14);
                return (
                  <rect
                    key={j}
                    x={wx}
                    y={y + floorH * 0.24}
                    width={winW}
                    height={floorH * 0.46}
                    rx={6}
                    fill={window}
                  />
                );
              })}
            </g>
          );
        })}
        {children ? children(floorY, floorH, shift) : null}
      </g>
    </svg>
  );
};

export const Ground: React.FC<{width: number; style?: React.CSSProperties}> = ({width, style}) => (
  <div style={{width, height: 6, borderRadius: 3, background: C.line, ...style}} />
);
