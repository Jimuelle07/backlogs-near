// Site-wide settings. Edit here, not in components.

// Project name, set by Jim on 2026-11-13.
export const PROJECT_NAME = "Eclipse";
export const PROJECT_TAGLINE = "Steps in front of the bad payment, stays in the background otherwise.";

// Shown under the hero. Keep it true: update as checks land (sprints.md).
export const STATUS_NOTE =
  "Hackathon build on NEAR testnet. The checker decides with Jev fusion; the first testnet receipts predate it and show stub_allow. The masked re-run is not built.";

// Live receipts (lane E). guardian-v2 is the current testnet Guardian (sprints.md A1 log).
export const NEAR_RPC_URL = "https://test.rpc.fastnear.com";
export const GUARDIAN_ID = "guardian-v2.jimuelle-firewall.testnet";
export const EXPLORER_URL = "https://testnet.nearblocks.io";

// Hard caps in contract code (contract/guardian/src/lib.rs), in whole tUSDC.
export const PER_PAYMENT_CAP = 200;
export const DAILY_CAP = 500;

// Public repository URL: set by the human once the repo is public (AGENTS.md §4). Empty hides the link.
export const REPO_URL = "";
