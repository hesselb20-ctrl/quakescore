# QuakeScore tutorial video

Source of `docs/media/quakescore_tutorial.mp4` (99 s, 1920x1080, 30 frames a second, no sound), its
poster and the teaser clip on the repository front page. Written in React with Remotion; every frame
is drawn in code, so a render is repeatable.

Everything on screen is simulated and labelled as such. Numbers come from `README.md`,
`docs/REPORT.md` and `results/demo_city_summary.md`. In the dashboard scene the place names next to
scored footprints are blurred, so no simulated score appears beside a real building's name.

## Render

Needs Node 20 or newer and ffmpeg. From Git Bash:

```bash
cd tutorial && npm install && bash render.sh
```

This writes the video, `tutorial_poster.png` and `tutorial_teaser.gif` to `docs/media/`. A full
render takes a few minutes; `out/` and `node_modules/` are not kept in the repository.

Scene lengths are in `src/Root.tsx`, colours and type in `src/theme.ts`, one file per scene in
`src/scenes/`.
