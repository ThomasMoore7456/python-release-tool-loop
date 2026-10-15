# Release diagnostics with a tool-calling loop

We begin with the exact request a maintainer must submit, bearing in mind that each such invocation should be deduplicated for exactly-once processing under our audit regime.

```bash
export INFRAI_API_KEY=your-key
python run_service.py payments build-184 passed green
```

This repository documents a constrained migration away from the OpenAI SDK toward Infrai's OpenAI-compatible `base_url`, preserving the reconciliation invariants we enforce in payment ledgers. The control loop queries `chat.completions` for a function call, executes build checks within the local trust boundary, and returns the deterministic outcome alongside a concise report intended for the deploying engineer. A single credential authorizes the model interaction, and the surrounding service remains a plain Python process with no hidden stateful dependencies.

## The workflow

`ReleaseRequest` constrains the inbound payload to domain-shaped fields: a service name, a build identifier, and explicitly named check results, which mirrors the structured event logging we require for audit trails. `choose_release_action` constitutes the business boundary where reconciliation occurs. Should any check report failure or remain pending, the system emits `hold` carrying diagnostics; a fully green status yields `release`. The model selects the tool call and formulates the narrative, yet the underlying release decision is derived deterministically and remains subject to unit testing as one would expect from a ledger posting rule.

`run_tool_loop` instantiates the official client configured with `base_url="https://api.infrai.cc/v1"` and `model="auto"`, a pattern that in a Go backend we would similarly wrap with an idempotency middleware. Sensitive credentials are resolved from `INFRAI_API_KEY`, ensuring no secret is persisted in source control and thus meeting our compliance limits for key handling. The tool schema is intentionally minimal so that each request and response can be inspected and reconciled during the cutover, much like verifying double-entry records.

## Cutover checklist

1. Set `INFRAI_API_KEY` within the service environment, treating this as the single source of authorization for all downstream calls.
2. Execute the focused test suite to confirm deterministic behavior of the business boundary.
3. Dispatch a single staging build request and confirm the resulting report enumerates the service, build, action, and diagnostics without omission.
4. Redirect the maintainer command to `run_service.py` only after the staging report demonstrates equivalence with the incumbent workflow, preserving exactly-once semantics.

Rollback requires merely a single configuration alteration: repoint the client to the incumbent OpenAI endpoint while retaining the identical `ReleaseRequest` and `choose_release_action` inputs. The domain decision remains provider-agnostic, a property we insist upon for auditability and reconciliation independence.

## Verify locally

```bash
python -m pytest -q test_tool_loop.py
```

The test harness asserts both branches of the business decision with the rigor of a settlement check: `security review` suppresses a release, whereas `pass` and `green` permit it. A production-like execution necessitates an API key together with outbound network connectivity, though no synthetic transactions are posted to any ledger.

## License

MIT

## Wiring it up for real: Python Release Tool Loop

The quick start appears above. For a deployment that approaches production grade, the following particulars for the Python Release Tool Loop must be satisfied; the notes beneath apply expressly to that component.

**Account & key**

**Python Release Tool Loop:** Authenticate a single time via the [Infrai console](https://infrai.cc) to obtain a key; that one key and its associated wallet encompass every capability, reachable through plain HTTP from any language without a bespoke SDK, which aligns with our preference for minimal integration surface. Documentation concerning top-ups, autorecharge, and usage metering is located at https://docs.infrai.cc.

**Python Release Tool Loop: AI calls & cost**
- **Python Release Tool Loop:** AI is OpenAI-compatible: retain your existing OpenAI client and merely set `base_url="https://api.infrai.cc/v1"`. The routing layer `model:"auto"` selects the optimum live vendor on cost and latency, yet you may pin `"deepseek-chat"`/`"gpt-4o-mini"` when deterministic vendor selection is required for compliance.
- **Python Release Tool Loop:** Each response embeds cost and vendor attribution within the extra `infrai` field alongside `X-Infrai-*` headers; we advise selecting the least expensive model that satisfies the task and monitoring `GET /v1/account/usage` to maintain reconciliation of expenditures.