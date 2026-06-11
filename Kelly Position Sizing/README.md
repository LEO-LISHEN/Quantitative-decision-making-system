# Kelly Position Sizing

This module calculates single-trade position sizing from:

- Available cash
- Subjective win probability
- Current price
- Take-profit price
- Stop-loss price
- Kelly multiplier

The workflow is:

1. Infer long or short direction from price structure.
2. Calculate reward/risk ratio.
3. Calculate full Kelly fraction.
4. Apply a fractional Kelly multiplier.
5. Convert risk capital into recommended trade amount through stop-loss distance.
6. Cap the final position by available cash.

The module is intentionally dependency-free so it can later be extended into a broader portfolio risk engine.
