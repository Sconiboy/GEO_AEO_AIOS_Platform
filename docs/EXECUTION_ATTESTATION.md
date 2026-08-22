# Trusted Execution Attestation

> A **human-supported comparative assessment** is allowed only when the corresponding collection execution was issued by the platform’s configured trusted issuer. A caller cannot supply a replacement issuer or registry at promotion time.

The collector and comparator independently resolve the same runtime configuration. The collector persists issuer-attested execution records, and the comparator resolves those records at human-promotion time. Snapshot evidence, raw artifacts, and canonical execution context are still separately verified; issuer attestation is an additional origin control, not a substitute for those checks.

| Runtime variable | Requirement | Purpose |
| --- | --- | --- |
| `GEO_AEO_TRUSTED_ISSUER_ID` | Non-empty stable identifier | Identifies the only issuer trusted for promotion. |
| `GEO_AEO_TRUSTED_ISSUER_KEY_HEX` | At least 32 random bytes, hex encoded | Protected HMAC key used to attest the issuer-bound execution digest. Never commit or include it in audit artifacts. |
| `GEO_AEO_EXECUTION_REGISTRY_DIR` | Protected writable directory | Durable append-only storage for issued execution records. It must be available to both collection and comparative promotion. |

When none of these variables are configured, bounded source collection and non-promoting comparative analysis remain available. Any human promotion fails closed because no trusted issuer is available. Partially configured or malformed values are rejected at startup.

The collector uses an ephemeral registry only for non-promoting controlled runs when no trusted issuer configuration exists. That ephemeral registry is deliberately insufficient for a promotable result: a later comparator cannot resolve it as the platform issuer.
