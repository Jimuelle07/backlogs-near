import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import type React from "react";
import { type CalculateMetadataFunction, staticFile } from "remotion";
import { C } from "../theme";
import { Footage, takeTiming } from "./Footage";
import { Intro } from "./Intro";
import { JudgeNotes } from "./JudgeNotes";
import { Scoreboard } from "./Scoreboard";
import type { LiveProps, RunData } from "./types";

const FPS = 30;
const FADE = 15;
const INTRO = 12 * FPS;
const SCORE = 14 * FPS;
const NOTES = 16 * FPS;
// Intro, WITHOUT take, WITH take, scoreboard, notes: 4 fades.
const FADES = 4;

export const calcLiveDemo: CalculateMetadataFunction<LiveProps> = async () => {
  const res = await fetch(staticFile("live-demo/run.json")).catch(() => null);
  if (!res || !res.ok) {
    throw new Error("video/public/live-demo/run.json missing: run agent/tools/showdown/video_data.py");
  }
  const data = (await res.json()) as RunData;
  const takes = takeTiming(data, "plain").frames + takeTiming(data, "eclipse").frames;
  return { durationInFrames: INTRO + takes + SCORE + NOTES - FADES * FADE, props: { data } };
};

export const EclipseLiveDemo: React.FC<LiveProps> = ({ data }) => {
  if (!data) return null;
  const transition = <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: FADE })} />;
  return (
    <TransitionSeries name="Scenes" style={{ backgroundColor: C.ground }}>
      <TransitionSeries.Sequence name="Intro" durationInFrames={INTRO}>
        <Intro data={data} />
      </TransitionSeries.Sequence>
      {transition}
      <TransitionSeries.Sequence name="Without Eclipse" durationInFrames={takeTiming(data, "plain").frames}>
        <Footage data={data} side="plain" />
      </TransitionSeries.Sequence>
      {transition}
      <TransitionSeries.Sequence name="With Eclipse" durationInFrames={takeTiming(data, "eclipse").frames}>
        <Footage data={data} side="eclipse" />
      </TransitionSeries.Sequence>
      {transition}
      <TransitionSeries.Sequence name="Scoreboard" durationInFrames={SCORE}>
        <Scoreboard data={data} />
      </TransitionSeries.Sequence>
      {transition}
      <TransitionSeries.Sequence name="What to check" durationInFrames={NOTES}>
        <JudgeNotes data={data} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
