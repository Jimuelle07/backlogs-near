import { ExternalLink } from "lucide-react";
import { EXPLORER_URL, GUARDIAN_ID, NEAR_RPC_URL } from "../config";

// Slot for E1 (live receipts panel, lane E). E1 replaces the body with read-only calls to
// list_receipts / get_held / get_daily_spent / get_config on GUARDIAN_ID over NEAR_RPC_URL
// (JSON-RPC "query", request_type "call_function"); shape: schemas/receipt.schema.json. No wallet.
export function ReceiptsPanel() {
  return (
    <div className="panel" data-rpc={NEAR_RPC_URL}>
      <span className="kicker">Testnet Guardian</span>
      <code className="ic">{GUARDIAN_ID}</code>
      <p>
        The live panel lists each receipt this Guardian has written: outcome, reason codes, amount, receiver,
        input and record hashes, and the checker version. Until it lands, every receipt is visible on the explorer.
      </p>
      <div className="row">
        <a className="pill" href={`${EXPLORER_URL}/address/${GUARDIAN_ID}`} target="_blank" rel="noreferrer">
          Open on NearBlocks <ExternalLink size={14} aria-hidden="true" />
        </a>
      </div>
    </div>
  );
}
