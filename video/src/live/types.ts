// Mirrors agent/tools/showdown/video_data.py output (format "eclipse.live-demo.v2").
export type Side = "plain" | "eclipse";

export type RunEvent = {
  readonly row: number;
  readonly side: Side;
  readonly index: number;
  readonly scenario: string;
  readonly label: string;
  readonly family: string;
  readonly receiver: string;
  readonly amount: string;
  readonly to_attacker: boolean;
  readonly result: string;
  readonly outcome: string | null;
  readonly reasons: readonly string[];
  readonly check_s: number | null;
  // Seconds into this side's own take.
  readonly t_start_s: number;
  readonly t_verdict_s: number;
  readonly attacker_display: string;
};

export type Take = {
  readonly file: string;
  readonly capture_fps: number;
  readonly width: number;
  readonly height: number;
  readonly footage_seconds: number;
  readonly first_start_s: number;
  readonly last_verdict_s: number;
};

export type RunData = {
  readonly format: "eclipse.live-demo.v2";
  readonly run: string;
  readonly fps: number;
  readonly rows: number;
  readonly takes: { readonly plain: Take; readonly eclipse: Take };
  readonly caps: { readonly per_payment: number; readonly daily: number; readonly new_payee: number };
  readonly events: readonly RunEvent[];
  readonly totals: {
    readonly plain: {
      readonly attacks: number;
      readonly reached_attacker: number;
      readonly paid_to_attacker: string;
      readonly benign_paid: number;
    };
    readonly eclipse: {
      readonly attacks: number;
      readonly reached_attacker: number;
      readonly paid_to_attacker: string;
      readonly held_for_attacker: string;
      readonly stopped: number;
      readonly benign_paid: number;
      readonly benign_held: number;
      readonly benign_blocked: number;
    };
  };
  readonly check_s: { readonly median: number; readonly max: number } | null;
};

export type LiveProps = { readonly data: RunData | null };
