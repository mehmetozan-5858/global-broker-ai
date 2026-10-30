// Exact-total sandbox receipts require a non-trial, non-overridden price.
export function matchesSandboxPrice(price, expected) {
  return Boolean(price && price.id === expected.price_id && price.product_id === expected.product_id
    && price.status === 'active'
    && price.unit_price?.amount === String(expected.amount_minor)
    && price.unit_price?.currency_code === 'USD'
    && price.billing_cycle?.interval === 'month' && price.billing_cycle?.frequency === 1
    && price.trial_period === null
    && Array.isArray(price.unit_price_overrides) && price.unit_price_overrides.length === 0
    && price.tax_mode === 'internal'
    && Number.isInteger(price.quantity?.minimum) && price.quantity.minimum <= 1
    && price.quantity.minimum >= 1
    && Number.isInteger(price.quantity?.maximum) && price.quantity.maximum >= 1);
}
