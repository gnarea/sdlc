# Invoice-reading prototype plan

The accounts-payable team types about 2,000 supplier invoices a month into the ledger. We're considering a provider's OCR API to extract each invoice's supplier, date, total, and VAT, so that clerks only check the amounts instead of typing them. The provider's contract would run for two years.

## Questions

### Does the OCR API read our suppliers' invoices accurately enough?

- **Risk**: If the API misreads more than one invoice in 20, clerks would spend longer correcting its mistakes than they spend typing today, and we wouldn't sign the contract.
- **Approach**: Hypothesis: the API extracts the correct total and VAT from at least 95% of our suppliers' invoices. Test: send 300 invoices from last quarter, chosen at random from both the scanned paper invoices and the PDFs, to the provider's API, under the data-processing agreement that the provider signed for the trial. Compare what it extracts with the amounts booked in the ledger. Refuted if it extracts the wrong total or VAT from more than 15 of them. Pulling the invoices from the archive and matching them to the ledger takes about three days.

### Would clerks trust the extracted amounts?

- **Risk**: If clerks retype the amounts anyway, the project saves nothing.
- **Approach**: Show five clerks a clickable mock-up of the screen where they'd check each invoice, with the amounts that the API extracted from ten of last quarter's invoices, and ask them to approve or correct each one. Count how many amounts they retype.

## Non-goals

- Paying invoices: the ledger's payment run stays as it is.
