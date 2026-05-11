# TODO

- [ ] Re-enable CUA research mode after the surface agent path is stable end-to-end with orchestrator, RabbitMQ acknowledgements, result handling, and node busy/idle status.
- [ ] Deep research: feed search result URLs back into the research planner or auto-visit promising results so research mode actually uses discovered pages.
- [ ] Production hardening: change orchestrator result consumption so RabbitMQ result messages are acknowledged only after downstream handling succeeds, especially after DB publish succeeds. Current `RabbitMQManager.get_message()` auto-acks immediately, so an agent/VLM/LLM result can be lost if later processing fails.
