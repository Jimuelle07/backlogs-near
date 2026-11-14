import { Composition } from "remotion";
import { EclipseInProduction } from "./EclipseInProduction";
import { calcLiveDemo, EclipseLiveDemo } from "./live/EclipseLiveDemo";
import { ReadmeDemo } from "./readme/ReadmeDemo";

// EclipseInProduction: 64 s of scenes at 30 fps (1920 frames) minus 8 fades of 15 frames = 1800.
// EclipseLiveDemo: length and data come from public/live-demo/run.json (calcLiveDemo).
// ReadmeDemo: 15 s at 25 fps (GIF frame delay 4 cs, exact); encoded to site/public/demo/eclipse-demo.gif.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="EclipseInProduction"
        component={EclipseInProduction}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="EclipseLiveDemo"
        component={EclipseLiveDemo}
        fps={30}
        width={1920}
        height={1080}
        durationInFrames={300}
        defaultProps={{ data: null }}
        calculateMetadata={calcLiveDemo}
      />
      <Composition
        id="ReadmeDemo"
        component={ReadmeDemo}
        durationInFrames={375}
        fps={25}
        width={1920}
        height={1080}
      />
    </>
  );
};
