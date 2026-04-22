# Privacy Policy

_Last updated: 2026-01-15_

## Data we collect

When you interact with our service we collect the minimum data required
to operate and improve it. This includes request metadata (IP address,
user agent), account identifiers (hashed user ID, session reference),
and product-event telemetry (page views, feature toggles).

## Retention

Personal identifiers (IP address, direct identifiers) are retained for
a **maximum of 30 days**, after which they are either deleted or
replaced with a salted hash that cannot be reversed to the source
identifier.

Event telemetry disassociated from personal identifiers is retained for
up to 24 months for product analytics.

## Lawful basis

We rely on **explicit opt-in consent** (GDPR Article 6(1)(a)) for
analytics and marketing processing. You may withdraw consent at any
time via your account settings; withdrawal takes effect immediately and
suppresses all subsequent analytics events from the affected session.

## Data subject rights

You may exercise your rights under Articles 15–22 of the GDPR
(including the Right to Access, the Right to Erasure, and the Right to
Restrict Processing) by filing a Data Subject Access Request (DSAR) to
`privacy@example.com`. We will respond within 30 days.

## Implementation

The analytics pipeline is implemented in `src/analytics.js`. See that
file for the source of truth on which fields are captured and how
consent is applied.
