import React from 'react';
import {useCurrentFrame} from 'remotion';
import {C, MONO, prog, rise, window_} from '../theme';
import {Eyebrow, Headline, Scene} from '../ui';

const STARTS = [40, 125, 210, 295, 380, 465];
const COLLECTOR = 'hesselb20-ctrl.github.io/quakescore-collector';

const steps: {main: string; sub?: React.ReactNode}[] = [
  {
    main: 'Open the collector page on your phone',
    sub: (
      <>
        <span style={{fontFamily: MONO, color: C.accent}}>{COLLECTOR}</span>
        <br />
        or install the Android app
      </>
    ),
  },
  {main: 'Type a building name and the floor'},
  {main: 'Lay the phone flat on a hard surface, on its charger, and press Start'},
  {main: 'Dim the screen and leave it overnight'},
  {main: 'In the morning, save the session file'},
  {
    main: 'On the computer, run:',
    sub: <span style={{fontFamily: MONO, color: C.ink}}>python experiments/inspect_sessions.py &lt;folder&gt;</span>,
  },
];

const Field: React.FC<{label: string; value: string; active: boolean}> = ({label, value, active}) => (
  <div style={{marginBottom: 18}}>
    <div style={{fontSize: 22, color: C.ink2, marginBottom: 8}}>{label}</div>
    <div
      style={{
        height: 54,
        borderRadius: 14,
        border: `2px solid ${active ? C.accent : C.line}`,
        background: C.surface,
        fontSize: 26,
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
      }}
    >
      {value}
    </div>
  </div>
);

const Button: React.FC<{label: string; on: boolean; secondary?: boolean}> = ({label, on, secondary}) => (
  <div
    style={{
      height: 64,
      borderRadius: 16,
      background: secondary ? C.faint : C.accent,
      color: secondary ? C.ink : '#ffffff',
      fontSize: 25,
      fontWeight: 650,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: on ? `0 0 0 6px ${C.accentSoft}` : 'none',
      marginTop: 14,
    }}
  >
    {label}
  </div>
);

/** Phone screen for the current step. */
const Screen: React.FC<{f: number}> = ({f}) => {
  const typed = (txt: string, start: number) => txt.slice(0, Math.floor(Math.max(0, f - start) / 3));
  const at = (i: number) => window_(f, STARTS[i], STARTS[i + 1] ?? 999, 12);
  return (
    <div style={{position: 'absolute', inset: 0, padding: '64px 26px 26px', boxSizing: 'border-box'}}>
      {/* browser bar */}
      <div
        style={{
          height: 46,
          borderRadius: 23,
          background: C.faint,
          fontSize: 19,
          color: C.ink2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 22,
        }}
      >
        quakescore-collector
      </div>
      <div style={{fontSize: 32, fontWeight: 700, letterSpacing: -0.4, marginBottom: 22}}>QuakeScore collector</div>
      <div style={{position: 'relative'}}>
        {/* step 1 and 2: set up form */}
        <div style={{position: 'absolute', inset: 0, opacity: Math.max(at(0), at(1))}}>
          <div style={{fontSize: 26, fontWeight: 650, marginBottom: 16}}>Set up</div>
          <Field label="Building name" value={typed('home', STARTS[1] + 10)} active={at(1) > 0.5} />
          <Field label="Floor (0 is ground level)" value={f > STARTS[1] + 30 ? '0' : ''} active={false} />
          <div style={{fontSize: 22, color: C.ink2, display: 'flex', gap: 10, alignItems: 'center'}}>
            <span style={{width: 24, height: 24, borderRadius: 6, background: C.accent, display: 'inline-block'}} />
            The phone is on its charger
          </div>
          <Button label="Start measuring" on={false} />
        </div>
        {/* step 3: start */}
        <div style={{position: 'absolute', inset: 0, opacity: at(2)}}>
          <div style={{fontSize: 26, fontWeight: 650, marginBottom: 16}}>Set up</div>
          <Field label="Building name" value="home" active={false} />
          <Field label="Floor (0 is ground level)" value="0" active={false} />
          <div style={{fontSize: 22, color: C.ink2, display: 'flex', gap: 10, alignItems: 'center'}}>
            <span style={{width: 24, height: 24, borderRadius: 6, background: C.accent, display: 'inline-block'}} />
            The phone is on its charger
          </div>
          <Button label="Start measuring" on={f > STARTS[2] + 30} />
        </div>
        {/* step 5: save */}
        <div style={{position: 'absolute', inset: 0, opacity: Math.max(at(4), at(5))}}>
          <div style={{fontSize: 26, fontWeight: 650, marginBottom: 16}}>Session finished</div>
          <div style={{fontSize: 22, color: C.ink2, lineHeight: 1.4, marginBottom: 10}}>
            Keep the file. It holds spectra only, no raw recording.
          </div>
          <Button label="Save the session file" on={f > STARTS[4] + 24} />
          <Button label="Start a new session" on={false} secondary />
        </div>
      </div>
      {/* step 4: dimmed screen */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: '#0b0b0d',
          opacity: at(3) * 0.94,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 18,
          color: '#8e8e93',
          fontSize: 26,
        }}
      >
        <svg width={60} height={60} viewBox="0 0 60 60">
          <path d="M 40 8 A 24 24 0 1 0 52 40 A 19 19 0 0 1 40 8 Z" fill="#5b5b60" />
        </svg>
        Measuring
      </div>
    </div>
  );
};

export const Record: React.FC = () => {
  const f = useCurrentFrame();
  const current = STARTS.reduce((acc, s, i) => (f >= s ? i : acc), -1);
  const termOn = prog(f, STARTS[5], 22);
  const flat = prog(f, STARTS[2] + 4, 26);
  return (
    <Scene>
      <div style={{position: 'absolute', left: 130, top: 80}}>
        <Eyebrow style={rise(f, 6)}>Tutorial</Eyebrow>
        <Headline style={{marginTop: 10, ...rise(f, 12)}}>Record a night</Headline>
      </div>
      <div style={{position: 'absolute', left: 130, top: 250, width: 1060, display: 'flex', flexDirection: 'column', gap: 24}}>
        {steps.map((s, i) => {
          const isCur = i === current;
          return (
            <div key={s.main} style={{display: 'flex', gap: 24, ...rise(f, STARTS[i], 20, 18)}}>
              <div
                style={{
                  flex: '0 0 auto',
                  width: 52,
                  height: 52,
                  borderRadius: 26,
                  background: isCur ? C.accent : C.faint,
                  color: isCur ? '#ffffff' : C.ink2,
                  fontSize: 28,
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {i + 1}
              </div>
              <div style={{paddingTop: 4}}>
                <div style={{fontSize: 36, fontWeight: isCur ? 650 : 500, color: isCur ? C.ink : C.ink2, lineHeight: 1.22}}>
                  {s.main}
                </div>
                {s.sub ? (
                  <div style={{marginTop: 8, fontSize: 29, color: C.ink2, lineHeight: 1.35}}>{s.sub}</div>
                ) : null}
              </div>
            </div>
          );
        })}
        <div
          style={{
            marginTop: 8,
            padding: '18px 26px',
            borderRadius: 18,
            background: C.warmSoft,
            color: C.ink,
            fontSize: 30,
            lineHeight: 1.3,
            ...rise(f, 530, 24, 18),
          }}
        >
          The first thing a night gives you is the phone's own noise level.
        </div>
      </div>

      {/* phone illustration */}
      <div style={{position: 'absolute', left: 1330, top: 160, opacity: 1 - termOn, ...{}}}>
        <div style={{...rise(f, 30, 26, 30)}}>
          <div
            style={{
              position: 'relative',
              width: 400,
              height: 780,
              borderRadius: 60,
              background: '#1d1d1f',
              padding: 14,
              boxSizing: 'border-box',
              boxShadow: '0 20px 50px rgba(0,0,0,0.12)',
            }}
          >
            <div style={{position: 'relative', width: '100%', height: '100%', borderRadius: 47, background: C.bg, overflow: 'hidden'}}>
              <Screen f={f} />
              <div style={{position: 'absolute', top: 14, left: '50%', marginLeft: -50, width: 100, height: 28, borderRadius: 14, background: '#1d1d1f'}} />
            </div>
          </div>
          {/* table and charger, from step 3 */}
          <div style={{opacity: flat, marginTop: 6}}>
            <svg width={560} height={90} style={{marginLeft: -80}}>
              <path d="M 280 0 C 280 40, 420 30, 470 52" fill="none" stroke="#8e8e93" strokeWidth={6} strokeLinecap="round" />
              <rect x={460} y={44} width={44} height={26} rx={6} fill="#8e8e93" />
              <rect x={0} y={74} width={560} height={14} rx={7} fill="#b9b9be" />
            </svg>
          </div>
        </div>
      </div>

      {/* terminal for step 6 */}
      <div
        style={{
          position: 'absolute',
          left: 1240,
          top: 300,
          width: 600,
          borderRadius: 24,
          background: '#1d1d1f',
          padding: '26px 30px 34px',
          boxSizing: 'border-box',
          opacity: termOn,
          transform: `translateY(${(1 - termOn) * 24}px)`,
          boxShadow: '0 20px 50px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{display: 'flex', gap: 10, marginBottom: 26}}>
          {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
            <span key={c} style={{width: 16, height: 16, borderRadius: 8, background: c}} />
          ))}
        </div>
        <div style={{fontFamily: MONO, fontSize: 27, lineHeight: 1.5, color: '#f5f5f7'}}>
          <span style={{color: '#8e8e93'}}>$ </span>python experiments/
          <br />
          &nbsp;&nbsp;inspect_sessions.py &lt;folder&gt;
        </div>
        <div style={{marginTop: 26, fontSize: 25, lineHeight: 1.45, color: '#c7c7cc'}}>
          Prints each session, the phone's noise floor and every candidate peak.
        </div>
      </div>
    </Scene>
  );
};
