# Synthetic demonstration data

Generated deterministically with random seed 42; timestamps are relative to the
generation date. No real people or customer data are included. All addresses use
the reserved example.test domain. Events span 180 days and share customer/product
IDs with the related CSVs. Amounts are illustrative USD values.

Import customers.csv first, then events.csv (or the equivalent JSON files). The
import form has a synthetic-data checkbox: select it for these demonstration
files so imported records retain a synthetic provenance label. The two small
import-demo files provide a single extra synthetic customer with four events for
an end-to-end upload walkthrough, even when the main demo dataset is seeded.

The other CSVs document the product, campaign, channel, order, and support relationships
used by the generated demonstration. The browser importer accepts customers and
events; orders, support rows, and temporal relationships are derived automatically
from event ingestion rather than imported separately.

Run `python scripts/seed.py` on an empty database to regenerate sample exports.
