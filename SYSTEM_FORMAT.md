# system Format

## How to describe a system
we will use a **graph**  

Core idea (given by chatGPT)  
Node = a thing (service, datastore, topic/queue, external system, job, API, user)  
Edge = a relationship/flow (produces, consumes, calls, writes_to, reads_from, scheduled_by)  
Everything else is metadata (protocol, SLA, scale, auth, schema, failure behavior, etc.)  

Every entity is going to have mandatory fields and optional fields  