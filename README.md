# Serial scale
API & comms for serial scale operations
---

## Outline
- run scale api server:
  - serial-port
  - serial-baud-rate
  - server-host
  - server-port
- api endpoints
  - info -> get host info, scale id (`weighingstation372`)
  - weight -> get weight
  - tare -> tare scale
  - zero -> set relative zero (!= tare)
- integration with `LabWatch`:
  - check scales that are online via `LabWatch` API adapter
    - >> what about machines inside of subnets ?
  - send queries via `LabWatch` API adapter, from UI/core, get weight / tare
  -
