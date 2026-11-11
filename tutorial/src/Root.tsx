import React from 'react';
import {AbsoluteFill, Composition, Sequence} from 'remotion';
import {C, FPS, H, W} from './theme';
import {Idea, Problem, Title} from './scenes/Intro';
import {Stacking} from './scenes/Stacking';
import {Pipeline} from './scenes/Pipeline';
import {Record} from './scenes/Record';
import {Dashboard, Status} from './scenes/Outro';

// Scene list with lengths in frames (30 fps). Starts are derived, so a change in one
// length moves everything after it.
export const SCENES: {name: string; frames: number; C: React.FC}[] = [
  {name: 'Title', frames: 180, C: Title},
  {name: 'Problem', frames: 300, C: Problem},
  {name: 'Idea', frames: 330, C: Idea},
  {name: 'Stacking', frames: 480, C: Stacking},
  {name: 'Pipeline', frames: 420, C: Pipeline},
  {name: 'Record', frames: 630, C: Record},
  {name: 'Dashboard', frames: 300, C: Dashboard},
  {name: 'Status', frames: 330, C: Status},
];
const TOTAL = SCENES.reduce((a, s) => a + s.frames, 0);

const Tutorial: React.FC = () => {
  let start = 0;
  return (
    <AbsoluteFill style={{background: C.bg}}>
      {SCENES.map((s) => {
        const from = start;
        start += s.frames;
        return (
          <Sequence key={s.name} name={s.name} from={from} durationInFrames={s.frames}>
            <s.C />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <Composition id="Tutorial" component={Tutorial} durationInFrames={TOTAL} fps={FPS} width={W} height={H} />
);
