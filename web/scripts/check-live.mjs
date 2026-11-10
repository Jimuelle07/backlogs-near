// Public view calls only: no keys, signatures, transactions, or token spending.
import { createReader } from '../src/near.js';

const reader = createReader({ guardian: process.env.VITE_GUARDIAN_ID, rpc: process.env.VITE_NEAR_RPC_URL });
const snapshot = await reader.snapshot();
console.log(JSON.stringify({
  guardian: reader.guardian, block: snapshot.blockHeight,
  token: snapshot.config.token_id, decimals: snapshot.config.token_decimals,
  receipts: snapshot.receipts.map(({ request_id, amount, status, outcome, reasons }) => ({ request_id, amount, status, outcome, reasons })),
}, null, 2));
