This project is a distributed system that will be used to analyze web content.
There will be 5 nodes in the system. Think of them as a star topology. In this topology, there is a central node (Orchestrator) and four other nodes (Crawler, DB, VLM, LLM).
And think also they are all running on distributed computers. So we will develop every node separately. 

OOP gonna be used for development. SOLID gonna be used for design. Microservices gonna be used for architecture.

Every node's inputs and outputs will be well defined. All gonna have error handling and logging mechanism. All processes ended successfully or failed or timeout gonna push information to orchestrator. Also there will be handshake mechanism between nodes. I think gRPC gonna handle this but its gonna be like:
- (node)I am a "node_name" I want to connect to orchestrator
- (orchestrator)Orchestrator gonna say yes I accept your connection request ur ID is "node_id"
- (node)connects to orchestrator
at the begining(connection process).

at working process gonna be like:
- (Orchestrator)You seem like you are free verify it
- (node)I am free
- (Orchestrator)do this process
- (node)I successfully did this process

also for node exit or terminating system synario too.

-When a node added to the system node name will describe its tasks, how to behave and how to adapt to the system exactly. 
-Node ID will be unique for each node.
-gRPC gonna be used for communication.
-every folder gonna has own requirements.txt because they will be separated and gonna run on different machines.



Process Flow:
- (Orchestrator)->(Crawler) Start crawling
- (Crawler) Crawls then (Crawler)->(Orchestrator) Crawling ended (sends json data with image URLs)
- (Orchestrator)->(DB) Store data, download images to MinIO, vectorize content
- (DB) Downloads images from URLs, saves to MinIO, stores metadata in PostgreSQL
- (Orchestrator)->(DB) Get next queue item
- (DB)->(Orchestrator) Next queue item (sends json data with MinIO paths)
- (Orchestrator)->(VLM) Analyze images (provides MinIO paths, DB sends image bytes)
- (VLM) Analyzes then (VLM)->(Orchestrator) Analysis ended (sends json data)
- (Orchestrator)->(LLM) Analyze text + VLM results
- (LLM) Analyzes then (LLM)->(Orchestrator) Analysis ended (summary + sentiment -1/0/1)
- (Orchestrator)->(DB) Store final analysis results

