# The Model Knows

**Category:** misc/AI | **Flag:** `spooky{spooky_vault_bones_and_bytes_2026}`

## Approach
A fine-tuned model was the artifact. Prompting it to complete the code literal `flag = "spooky{...}"` produced the flag at high confidence. The model also emitted a defensive decoy `spooky{flag_bones_and_bytes_2026}`, matching the "it won't reveal it" framing — the real value includes `spooky_vault_`.

## Reproduction
Prompt the model with the organizer/flag-completion context; the top-probability completion is:
`spooky{spooky_vault_bones_and_bytes_2026}`
(Confirmed accepted by the platform.)
