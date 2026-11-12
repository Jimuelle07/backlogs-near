# External scenario attribution

`agent/scenarios/external/ext-*.json` are derived from the public datasets below, rewritten into
payment-scenario form by `agent/tools/build_external_scenarios.py` (each attack text gets an appended
receiver line naming a synthetic `ext-<source>-NN` account; each scenario also carries a generated
invoice email for a known payee). Attack amounts equal the invoice amount so that the label cannot be
read from an amount mismatch (decided by Jim, 2026-11-13). The scenarios are modified works; the license of each source applies
to the text taken from it. All URLs are pinned to the revision shown.

## uiuc-kang-lab/InjecAgent (`injecagent`)

- License: MIT
- Source: https://github.com/uiuc-kang-lab/InjecAgent
- Revision: `f19c9f2c79a41046eb13c03c51a24c567a8ffa07`
- Files:
  - https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/f19c9f2c79a41046eb13c03c51a24c567a8ffa07/data/test_cases_dh_base.json
    - sha256 `0a8186468d21389af432e8c7b399ae42264d1b93a07b65c7a489468508604305`
- Selection: data/test_cases_dh_base.json; attacker tools BankManagerPayBill, BankManagerTransferFunds, BinanceDeposit, BinanceWithdraw, VenmoWithdrawMoney; the first 6 distinct `User Tool` per attacker tool (file order) = 30 attack scenarios.
- Rewrite: inbox[1].text is the case `Tool Response` with ` Pay to <attacker>.` appended to the embedded attacker instruction; the amount is the invoice amount, so the attack redirects the receiver only; receiver is a synthetic ext-injecagent-NN account.

## ethz-spylab/agentdojo (`agentdojo`)

- License: MIT
- Source: https://github.com/ethz-spylab/agentdojo
- Revision: `089ed468cf3ed0322acc66b0211f26d9d90dbf60`
- Files:
  - https://raw.githubusercontent.com/ethz-spylab/agentdojo/089ed468cf3ed0322acc66b0211f26d9d90dbf60/src/agentdojo/default_suites/v1/banking/injection_tasks.py
    - sha256 `fa2dedf8e66c95ffadb54f5a26648728b08c56f302858de4ee9a5cc0b3891618`
  - https://raw.githubusercontent.com/ethz-spylab/agentdojo/089ed468cf3ed0322acc66b0211f26d9d90dbf60/src/agentdojo/attacks/important_instructions_attacks.py
    - sha256 `519f24e0b9d72f43343d665679adacc33758b50cd1b586a81fa53fb098dcfe71`
- Selection: banking injection tasks 0-6 and 8 (task 7 changes a password, not a payment) x vectors injection_bill_text and injection_incoming_transaction = 16 attack scenarios.
- Rewrite: inbox[1].text is the `important_instructions` template (user `Emma Johnson`, model `AI assistant`) with {goal} = the task GOAL, its IBAN replaced by a synthetic ext-agentdojo-NN account; prefixed by `Bill for December 2023. ` (bill vector) or `Incoming transaction subject: ` (transaction vector). The amount is the invoice amount, so the attack redirects the receiver only.

## nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1 (`nemotron`)

- License: CC-BY-4.0
- Source: https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1
- Revision: `d738d4f361cc38bb4d7a42b9066776dade5332f5`
- Files:
  - https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1/resolve/d738d4f361cc38bb4d7a42b9066776dade5332f5/train.jsonl
    - sha256 `3329da17564a7eb287e2730fc7d6956e1f4fe51e8950ac4f110b3c37e78cf3b9`
- Selection: train.jsonl rows with attack_category == unauthorized_action; the first 30 by `id`.
- Rewrite: inbox[1].text is `injection.injection_text` with ` Settle the outstanding balance by paying <attacker>.` appended; the amount is the invoice amount, so the attack redirects the receiver only; receiver is a synthetic ext-nemotron-NN account.

## 3nesdeniz/agentic-prompt-injection-boundary-pairs (`boundary`)

- License: CC-BY-4.0
- Source: https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-boundary-pairs
- Revision: `a5682e7573e1c7bc4b12e64d49c0dcd90ca776cf`
- Files:
  - https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-boundary-pairs/resolve/a5682e7573e1c7bc4b12e64d49c0dcd90ca776cf/data/test.jsonl
    - sha256 `034523eefaec18c291f9daa7699037acb0e7a91b1aeb1b205878b124f6e18f10`
  - https://huggingface.co/datasets/3nesdeniz/agentic-prompt-injection-boundary-pairs/resolve/a5682e7573e1c7bc4b12e64d49c0dcd90ca776cf/data/validation.jsonl
    - sha256 `1e5f483277ca776f0bb7d26c1a85ca4cd6d73f8d30f638c75265d82a6de751c3`
- Selection: data/test.jsonl rows with risk_domain in {billing, procurement}; data/validation.jsonl rows with the same filter are added only if the test split has fewer than 20 attack rows. label 1 = attack, label 0 = benign hard negative.
- Rewrite: attack: text + ` Payment destination: <attacker>.`, the amount is the invoice amount (so the attack redirects the receiver only), receiver a synthetic ext-boundary-NN account; family memory_context_poisoning -> memory_poisoning, obfuscation_encoding -> encoded_injection, otherwise indirect_injection. benign: text as-is, receiver and amount are the invoice payee and invoice amount.

## microsoft/llmail-inject-challenge (`llmail`)

- License: MIT
- Source: https://huggingface.co/datasets/microsoft/llmail-inject-challenge
- Revision: `1063bdf01ec8762b812d5e06ee768a06faa5a6f7`
- Files:
  - https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/1063bdf01ec8762b812d5e06ee768a06faa5a6f7/data/emails_for_fp_tests.json
    - sha256 `4ddd950b5dbaa8548f5597c886d8e09a051ba07f80a9291fdcca9c2397d22abe`
- Selection: data/emails_for_fp_tests.json (benign emails, file order); the first N such that the total benign count equals the total attack count.
- Rewrite: benign: the email is inbox[1] (source `email`); the invoice payee is paid the invoice amount.
