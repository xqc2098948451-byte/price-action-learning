# Verification

Run only project-authorized verification mechanisms selected by the Work Unit/CONTROL. Normalize results into Evidence and Result Envelope. This Skill does not decide project-specific thresholds; Fitness extensions do.

## Evidence transport

Verification execution establishes evidence; transport only carries retained facts. When supplied by an authentic completed execution, retain `command`, tested SHA, exit code, test count, failures, errors, and a concise relevant summary. Transport must reuse the existing Evidence/Result Envelope for those facts. Use `UNKNOWN` for a fact not established by authoritative evidence. Transport does not establish verification success and must not overwrite, discard, or re-derive retained verification facts.

Verification may be rerun only after a source/test change, material environment change, incomplete execution, or unauthentic evidence. It must NOT be rerun because console capture was lost or only report formatting/delivery information is missing. For a transport-only gap, reuse the retained evidence and report the transport fact separately as `UNKNOWN` when necessary.

No result platform is created by transport, and there is no telemetry authority. Transport success is not result success; verification authority remains with the existing Evidence/Result Envelope and authorized verification mechanism.
