import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {C, ease, easeInOut, prog, rise, window_} from '../theme';
import {Eyebrow, Headline, Scene, SimTag} from '../ui';

// Map labels in the screenshot that name individual buildings are softened, so no real
// building name sits next to a (simulated) score. Rectangles are in screenshot pixels (1280 x 820).
const SOFTEN: [number, number, number, number][] = [
  [796, 148, 92, 26],
  [814, 178, 96, 26],
  [1092, 170, 172, 86],
  [866, 298, 64, 36],
  [986, 424, 70, 26],
  [536, 708, 74, 28],
];

export const Dashboard: React.FC = () => {
  const f = useCurrentFrame();
  const imgW = 1180;
  const k = imgW / 1280;
  const imgH = 820 * k;
  const zoom = interpolate(f, [0, 300], [1, 1.045], {easing: easeInOut});
  return (
    <Scene>
      <div style={{position: 'absolute', left: 100, top: 70}}>
        <Eyebrow style={rise(f, 6)}>What comes out</Eyebrow>
        <Headline style={{marginTop: 10, fontSize: 54, ...rise(f, 12)}}>Each scored building gets a score with an uncertainty band.</Headline>
      </div>
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 230,
          width: imgW,
          height: imgH,
          borderRadius: 24,
          overflow: 'hidden',
          boxShadow: '0 16px 44px rgba(0,0,0,0.12)',
          ...rise(f, 14, 26, 20),
        }}
      >
        <div style={{position: 'absolute', inset: 0, transform: `scale(${zoom})`, transformOrigin: '40% 20%'}}>
          <Img src={staticFile('dashboard.png')} style={{width: imgW, height: imgH, display: 'block'}} />
          {SOFTEN.map(([x, y, w, h], i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: x * k,
                top: y * k,
                width: w * k,
                height: h * k,
                borderRadius: 8,
                backdropFilter: 'blur(4px)',
                background: 'rgba(236,234,230,0.18)',
              }}
            />
          ))}
        </div>
        <SimTag style={{position: 'absolute', right: 22, bottom: 22, boxShadow: '0 4px 14px rgba(0,0,0,0.12)'}} />
      </div>
      <div style={{position: 'absolute', left: 1340, top: 250, width: 500}}>
        <div style={{fontSize: 36, fontWeight: 700, ...rise(f, 40)}}>Demo district</div>
        <div style={{marginTop: 10, fontSize: 28, lineHeight: 1.35, color: C.ink2, ...rise(f, 50)}}>
          Real map footprints. Structures, phones and scores are simulated.
        </div>
        <div style={{marginTop: 44, ...rise(f, 80)}}>
          <div style={{fontSize: 96, fontWeight: 700, letterSpacing: -3, color: C.accent, lineHeight: 1}}>222</div>
          <div style={{fontSize: 32, color: C.ink, marginTop: 8}}>of 687 buildings scored</div>
        </div>
        <div style={{marginTop: 44, fontSize: 32, fontWeight: 650, ...rise(f, 120)}}>Coverage follows height</div>
        <div style={{marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10, fontSize: 28, color: C.ink2, ...rise(f, 132)}}>
          <div>30+ storeys: 55 of 56</div>
          <div>15-29 storeys: 76 of 86</div>
          <div>1-3 storeys: 7 of 231</div>
        </div>
      </div>
    </Scene>
  );
};

const Mark: React.FC<{kind: 'check' | 'open' | 'next'}> = ({kind}) => {
  const col = kind === 'next' ? C.accent : kind === 'open' ? C.warm : C.ink2;
  return (
    <svg width={64} height={64} viewBox="0 0 64 64">
      <circle cx={32} cy={32} r={28} fill="none" stroke={col} strokeWidth={4} strokeDasharray={kind === 'open' ? '8 7' : undefined} />
      {kind === 'check' ? <path d="M 20 33 L 28 41 L 44 24" fill="none" stroke={col} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" /> : null}
      {kind === 'next' ? <path d="M 20 32 L 42 32 M 34 23 L 43 32 L 34 41" fill="none" stroke={col} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" /> : null}
    </svg>
  );
};

export const Status: React.FC = () => {
  const f = useCurrentFrame();
  const rows: [React.ComponentProps<typeof Mark>['kind'], string][] = [
    ['check', 'Validated in simulation only'],
    ['open', 'No real building measured yet'],
    ['next', 'Next step: the first real night'],
  ];
  const listOp = 1 - prog(f, 200, 20, ease);
  const endOp = prog(f, 214, 26, ease);
  return (
    <Scene fadeOut={false}>
      <div style={{position: 'absolute', left: 260, top: 290, opacity: listOp}}>
        <Eyebrow style={rise(f, 6)}>Where it stands</Eyebrow>
        <div style={{marginTop: 40, display: 'flex', flexDirection: 'column', gap: 44}}>
          {rows.map(([kind, text], i) => (
            <div key={text} style={{display: 'flex', alignItems: 'center', gap: 34, ...rise(f, 20 + i * 34, 24)}}>
              <Mark kind={kind} />
              <div style={{fontSize: 64, fontWeight: 650, letterSpacing: -1, color: kind === 'next' ? C.accent : C.ink}}>{text}</div>
            </div>
          ))}
        </div>
      </div>
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          opacity: endOp,
          transform: `translateY(${(1 - endOp) * 20}px)`,
        }}
      >
        <div style={{fontSize: 150, fontWeight: 700, letterSpacing: -4}}>QuakeScore</div>
        <div style={{marginTop: 26, fontSize: 44, color: C.ink2}}>
          A statistical screening layer, not an engineering assessment.
        </div>
        <div style={{marginTop: 44, fontSize: 32, color: C.accent, opacity: window_(f, 230, 400)}}>
          hesselb20-ctrl.github.io/quakescore-collector
        </div>
      </AbsoluteFill>
    </Scene>
  );
};
