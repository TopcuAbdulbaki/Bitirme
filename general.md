This project is a distributed system that will be used to analyze web content.
There will be 5 nodes in the system. Think of them as a star topology. In this topology, there is a central node (Orchestrator) and four other nodes (Crawler, DB, VLM, LLM).
And think also they are all running on distributed computers. So we will develop every node separately. 

OOP gonna be used for development. SOLID gonna be used for design. Microservices gonna be used for architecture.

Every node's inputs and outputs will be well defined. All gonna have error handling and logging mechanism. All processes ended successfully or failed or timeout gonna push information to orchestrator. Also there will be handshake mechanism between nodes. I think gRPC gonna handle this but its gonna be like:
- (node)I want to connect to orchestrator
- (orchestrator)Orchestrator gonna say yes
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
- (Crawler) Crawls then (Crawler)->(Orchestrator) Crawling ended(sended json data)
- (Orchestrator)->(DB) Store data also vectorize data and add to vector database (sended json data)
- (Orchestrator)->(DB) Send next queue
- (DB)->(Orchestrator) Next queue (sended json data)
- (Orchestrator)->(VLM) Analyze images (sended json data)
- (VLM)Analyzes then (VLM)->(Orchestrator) Analyzing ended(sended json data)
- (Orchestrator)->(LLM) Analyze text (sended json data added images analysis results)
- (LLM)Analyzes then (LLM)->(Orchestrator) Analyzing ended(sended json data)
- (Orchestrator)->(DB) Store data also vectorize data and add to vector database(sended json data added images analysis results and text analysis results)

