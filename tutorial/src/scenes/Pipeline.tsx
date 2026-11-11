import React from 'react';
import {useCurrentFrame} from 'remotion';
import {C, prog, rise} from '../theme';
import {Eyebrow, Headline, Scene} from '../ui';

const S = 4; // icon stroke width

const PhoneIcon = () => (
  <svg width={110} height={110} viewBox="0 0 110 110">
    <rect x={32} y={8} width={46} height={94} rx={12} fill="none" stroke={C.accent} strokeWidth={S} />
    <path d="M 40 66 L 48 54 L 55 62 L 62 44 L 70 66" fill="none" stroke={C.accent} strokeWidth={S} strokeLinejoin="round" strokeLinecap="round" />
    <line x1={48} x2={62} y1={90} y2={90} stroke={C.accent} strokeWidth={S} strokeLinecap="round" />
  </svg>
);

const StackIcon = () => (
  <svg width={110} height={110} viewBox="0 0 110 110">
    {[0, 1, 2].map((i) => (
      <rect key={i} x={18 + i * 8} y={58 - i * 18} width={66} height={40} rx={10} fill={C.surface} stroke={C.accent} strokeWidth={S} />
    ))}
    <path d="M 40 72 Q 55 46 70 72" fill="none" stroke={C.accent} strokeWidth={S} strokeLinecap="round" transform="translate(16,-36)" />
  </svg>
);

const RejectIcon = () => (
  <svg width={110} height={110} viewBox="0 0 110 110">
    <path d="M 14 18 L 96 18 L 64 58 L 64 92 L 46 84 L 46 58 Z" fill="none" stroke={C.accent} strokeWidth={S} strokeLinejoin="round" />
    <circle cx={88} cy={84} r={14} fill={C.warmSoft} stroke={C.warm} strokeWidth={S} />
    <path d="M 82 78 L 94 90 M 94 78 L 82 90" stroke={C.warm} strokeWidth={S} strokeLinecap="round" />
  </svg>
);

const ResultIcon = () => (
  <svg width={110} height={110} viewBox="0 0 110 110">
    <path d="M 14 78 A 41 41 0 0 1 96 78" fill="none" stroke={C.faint} strokeWidth={12} strokeLinecap="round" />
    <path d="M 40 41 A 41 41 0 0 1 82 46" fill="none" stroke={C.accentSoft} strokeWidth={12} strokeLinecap="round" />
    <path d="M 40 41 A 41 41 0 0 1 82 46" fill="none" stroke={C.accent} strokeWidth={4} strokeLinecap="round" opacity={0.5} />
    <line x1={55} y1={78} x2={64} y2={42} stroke={C.accent} strokeWidth={S + 1} strokeLinecap="round" />
    <circle cx={55} cy={78} r={7} fill={C.accent} />
  </svg>
);

const steps: {icon: React.ReactNode; title: string; lines: string[]}[] = [
  {icon: <PhoneIcon />, title: 'On the phone', lines: ['Spectra only', 'Nothing above 25 Hz', 'No raw recording leaves the phone']},
  {icon: <StackIcon />, title: 'Per building', lines: ['Stack many nights', 'and many phones']},
  {icon: <RejectIcon />, title: 'Reject what is not the building', lines: ['Machinery', 'Elevators', 'The phone itself']},
  {icon: <ResultIcon />, title: 'Result', lines: ['Frequency', 'Damping', 'Score with an uncertainty band']},
];

export const Pipeline: React.FC = () => {
  const f = useCurrentFrame();
  const cardW = 370;
  const gap = 56;
  const left = (1920 - (cardW * 4 + gap * 3)) / 2;
  return (
    <Scene>
      <div style={{position: 'absolute', left, top: 110}}>
        <Eyebrow style={rise(f, 6)}>The pipeline</Eyebrow>
        <Headline style={{marginTop: 14, ...rise(f, 12)}}>From a phone on a table to a score.</Headline>
      </div>
      {steps.map((s, i) => {
        const start = 30 + i * 55;
        const x = left + i * (cardW + gap);
        return (
          <React.Fragment key={s.title}>
            <div
              style={{
                position: 'absolute',
                left: x,
                top: 320,
                width: cardW,
                height: 520,
                borderRadius: 28,
                background: C.surface,
                padding: '36px 32px',
                boxSizing: 'border-box',
                boxShadow: '0 2px 10px rgba(0,0,0,0.04)',
                ...rise(f, start, 24, 30),
              }}
            >
              <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                {s.icon}
                <div
                  style={{
                    width: 54,
                    height: 54,
                    borderRadius: 27,
                    background: C.accentSoft,
                    color: C.accent,
                    fontSize: 30,
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {i + 1}
                </div>
              </div>
              <div style={{marginTop: 26, fontSize: 38, fontWeight: 700, lineHeight: 1.15, letterSpacing: -0.4}}>{s.title}</div>
              <div style={{marginTop: 20, display: 'flex', flexDirection: 'column', gap: 12}}>
                {s.lines.map((l) => (
                  <div key={l} style={{fontSize: 30, lineHeight: 1.25, color: C.ink2}}>
                    {l}
                  </div>
                ))}
              </div>
            </div>
            {i < 3 ? (
              <svg
                width={gap}
                height={40}
                style={{position: 'absolute', left: x + cardW, top: 560, opacity: prog(f, start + 30, 20)}}
              >
                <path d={`M 12 20 L ${gap - 14} 20 M ${gap - 24} 10 L ${gap - 14} 20 L ${gap - 24} 30`} fill="none" stroke={C.ink3} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : null}
          </React.Fragment>
        );
      })}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 920,
          textAlign: 'center',
          fontSize: 40,
          color: C.ink2,
          ...rise(f, 260, 24),
        }}
      >
        A statistical screening layer, not an engineering assessment.
      </div>
    </Scene>
  );
};
