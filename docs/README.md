# Documentation map

Meteoscape separates product intent, release requirements, architecture, delivery state, and history
so that each fact has one owner.

| Question | Source of truth |
|---|---|
| Why does the product exist, and where is it going? | [Product roadmap](./product-roadmap.md) |
| What must v1 demonstrate? | [v1 requirements](./v1-requirements.md) |
| What are the durable system boundaries and decisions? | [Architecture](./architecture.md), [ADRs](./adr), and [glossary](./glossary.md) |
| What is implemented, ready, or next? | [v1 delivery status](./tickets/README.md) |
| What does an individual work item require? | [Active tickets](./tickets) |
| How is a Provider implemented and independently verified? | [Provider authoring guide](./provider-authoring.md) |
| How is a work item's implementation planned, and why that shape? | [Implementation RFCs](./rfc) |
| What remains deliberately unresolved? | [Open concerns](./concerns.md) and [ideas](./ideas.md) |
| Why was a past choice made? | [Development sessions](./sessions), [completed tickets](./tickets/done), and [resolved RFCs](./rfc/done) |

Current delivery terms such as **Done**, **In progress**, **Ready**, **Partial**, **Planned**,
**Blocked**, and **Next**
belong in the delivery status and active ticket headers. Product and contract documents describe
targets and requirements; dated session, completed-ticket, and resolved-RFC records remain historical.

An RFC plans one ticket's implementation and records the decisions taken to get there; once its ticket
is closed it moves to [`rfc/done`](./rfc/done) and is kept as written. Durable contracts it settled
belong in the [architecture](./architecture.md) / [ADRs](./adr), not in the RFC.
