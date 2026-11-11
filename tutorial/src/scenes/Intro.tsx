import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C, ease, easeInOut, prog, rise} from '../theme';
import {Building, Eyebrow, Ground, Headline, Scene} from '../ui';

// Scene 1: title.
export const Title: React.FC = () => {
  const f = useCurrentFrame();
  const draw = prog(f, 10, 70, easeInOut);
  // A calm trace that draws in under the title.
  const pts: string[] = [];
  const n = 240;
  for (let i = 0; i <= n * draw; i++) {
    const x = (i / n) * 900;
    const env = Math.sin((Math.PI * i) / n);
    const y = 40 - env * 26 * Math.sin(i * 0.21 + f * 0.05);
    pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  return (
    <Scene>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
        <div style={{fontSize: 150, fontWeight: 700, letterSpacing: -4, ...rise(f, 8, 28, 30)}}>
          QuakeScore
        </div>
        <svg width={900} height={80} style={{marginTop: 18, opacity: prog(f, 10, 20)}}>
          <polyline points={pts.join(' ')} fill="none" stroke={C.accent} strokeWidth={4} strokeLinecap="round" />
        </svg>
        <div
          style={{
            marginTop: 30,
            fontSize: 50,
            fontWeight: 450,
            color: C.ink2,
            textAlign: 'center',
            lineHeight: 1.3,
            ...rise(f, 34, 26),
          }}
        >
          Measuring how buildings move,
          <br />
          with the phones already inside them.
        </div>
      </AbsoluteFill>
    </Scene>
  );
};

const Chip: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <div
    style={{
      padding: '10px 22px',
      borderRadius: 999,
      background: C.surface,
      border: `2px solid ${C.line}`,
      fontSize: 30,
      fontWeight: 550,
      color: C.ink2,
      ...style,
    }}
  >
    {children}
  </div>
);

// Scene 2: the problem.
export const Problem: React.FC = () => {
  const f = useCurrentFrame();
  const shake = prog(f, 120, 40, ease);
  // Same labels, different stiffness: one sways slowly and further, one quickly and less.
  const swayA = shake * 10 * Math.sin(f * 0.16);
  const swayB = shake * 22 * Math.sin(f * 0.11);
  const labels = ['Same age', 'Same height', 'Same construction class'];
  const bld = (sway: number, start: number, tag: string, tagOn: number) => (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', ...rise(f, start, 24)}}>
      <Building width={300} height={420} floors={7} cols={3} sway={sway} />
      <Ground width={420} />
      <div
        style={{
          marginTop: 22,
          fontSize: 34,
          fontWeight: 650,
          color: C.accent,
          opacity: prog(f, tagOn, 20),
        }}
      >
        {tag}
      </div>
    </div>
  );
  return (
    <Scene>
      <div style={{position: 'absolute', left: 140, top: 110, width: 1700}}>
        <Eyebrow style={rise(f, 6)}>The problem</Eyebrow>
        <Headline style={{marginTop: 14, fontSize: 52, ...rise(f, 12)}}>
          Catastrophe models guess a building's vulnerability from labels.
        </Headline>
      </div>
      <div
        style={{
          position: 'absolute',
          top: 330,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-end',
          gap: 90,
        }}
      >
        {bld(swayA, 30, 'Stiffer', 150)}
        <div style={{display: 'flex', flexDirection: 'column', gap: 18, alignItems: 'center', marginBottom: 120}}>
          {labels.map((l, i) => (
            <Chip key={l} style={rise(f, 50 + i * 14)}>
              {l}
            </Chip>
          ))}
        </div>
        {bld(swayB, 38, 'Softer', 150)}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 140,
          right: 140,
          top: 930,
          textAlign: 'center',
          fontSize: 44,
          fontWeight: 500,
          color: C.ink,
          ...rise(f, 150, 24),
        }}
      >
        Two buildings with the same labels can differ a lot, and the model cannot see it.
      </div>
    </Scene>
  );
};

// Scene 3: the idea.
export const Idea: React.FC = () => {
  const f = useCurrentFrame();
  const amp = prog(f, 20, 40, ease) * 16;
  const sway = amp * Math.sin(f * 0.13);
  const floors = 8;
  const phoneFloor = 4;
  return (
    <Scene>
      <div style={{position: 'absolute', left: 140, top: 200, width: 900}}>
        <Eyebrow style={rise(f, 6)}>The idea</Eyebrow>
        <Headline style={{marginTop: 14, ...rise(f, 12)}}>
          Every building sways by a few millionths of g under wind and traffic.
        </Headline>
        <div style={{marginTop: 46, fontSize: 46, lineHeight: 1.3, color: C.ink2, ...rise(f, 90, 24)}}>
          A phone lying still on a table inside it senses that sway.
        </div>
        <div style={{marginTop: 46, fontSize: 30, color: C.ink3, ...rise(f, 150, 24)}}>
          Motion in this drawing is exaggerated.
        </div>
      </div>
      {/* wind */}
      <svg width={360} height={300} style={{position: 'absolute', left: 1080, top: 300}}>
        {[0, 1, 2].map((i) => {
          const t = (f * 2.2 + i * 70) % 260;
          const op = Math.sin((Math.PI * t) / 260) * prog(f, 20, 30);
          return (
            <path
              key={i}
              d={`M ${t - 60} ${70 + i * 70} q 40 -18 80 0 t 80 0`}
              fill="none"
              stroke={C.line}
              strokeWidth={5}
              strokeLinecap="round"
              opacity={op}
            />
          );
        })}
      </svg>
      <div style={{position: 'absolute', left: 1330, top: 170, ...rise(f, 10, 26)}}>
        <Building width={400} height={760} floors={floors} cols={3} sway={sway}>
          {(floorY, floorH, shift) => {
            const y = floorY(phoneFloor) + floorH;
            const x = (shift(phoneFloor) + shift(phoneFloor + 1)) / 2;
            const pulse = 0.5 + 0.5 * Math.sin(f * 0.25);
            return (
              <g transform={`translate(${x},0)`} opacity={prog(f, 70, 20)}>
                {/* interior of this floor */}
                <rect x={14} y={y - floorH + 8} width={372} height={floorH - 16} rx={10} fill="#ffffff" />
                {/* table */}
                <rect x={100} y={y - 42} width={230} height={12} rx={6} fill="#8e8e93" />
                <rect x={120} y={y - 30} width={10} height={22} fill="#8e8e93" />
                <rect x={300} y={y - 30} width={10} height={22} fill="#8e8e93" />
                {/* phone lying flat */}
                <rect x={170} y={y - 56} width={90} height={14} rx={7} fill={C.ink} />
                <circle cx={215} cy={y - 72} r={9 + pulse * 7} fill="none" stroke={C.accent} strokeWidth={3.5} opacity={1 - pulse * 0.6} />
              </g>
            );
          }}
        </Building>
        <Ground width={480} style={{marginLeft: -30}} />
      </div>
    </Scene>
  );
};
