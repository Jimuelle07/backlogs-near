// Site-wide settings. Edit here, not in components.

// Working brand from the branding artifact. The final project name is the team lead's call
// at submission (AGENTS.md §4); change it here when it is set.
export const PROJECT_NAME = "Attested";

// Shown under the hero. Keep it true: update as checks land (sprints.md).
export const STATUS_NOTE =
  "Hackathon build on NEAR testnet. The checks are landing this week; until Jev fusion is wired in, the checker allows every payment.";

// Live receipts (lane E). guardian-v2 is the current testnet Guardian (sprints.md A1 log).
export const NEAR_RPC_URL = "https://rpc.testnet.near.org";
export const GUARDIAN_ID = "guardian-v2.jimuelle-firewall.testnet";
export const EXPLORER_URL = "https://testnet.nearblocks.io";

// Hard caps in contract code (contract/guardian/src/lib.rs), in whole tUSDC.
export const PER_PAYMENT_CAP = 200;
export const DAILY_CAP = 500;

// Public repository URL: set by the human once the repo is public (AGENTS.md §4). Empty hides the link.
export const REPO_URL = "";
