"""
gRPC Server for Crawler Node
Handles incoming commands from Orchestrator (e.g. ExecuteCrawl).
"""
import grpc
import json
import asyncio
from concurrent import futures

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crawler.generated import orchestrator_pb2 as pb2
from crawler.generated import orchestrator_pb2_grpc as pb2_grpc
from crawler.config import ORCHESTRATOR_PORT  # Note: Server needs its OWN port, not Orchestrator's

# Default Crawler Port (can be overridden)
CRAWLER_GRPC_PORT = 50052

class CrawlerService(pb2_grpc.CrawlerServiceServicer):
    """
    Implementation of the CrawlerService defined in orchestrator.proto.
    """
    
    def __init__(self, crawler_instance):
        self.crawler = crawler_instance
        
    async def ExecuteCrawl(self, request, context):
        """
        Handle ExecuteCrawl request from Orchestrator.
        Triggers the crawling process.
        """
        print(f"[gRPC Server] Received ExecuteCrawl task: {request.task_id}")
        
        # Trigger the crawl logic
        # Note: We run this as a background task or await it depending on requirement
        # Since 'run()' is long-running and we want to reply 'Started', we might just await it 
        # or return 'Started' and let it report back later.
        # But looking at proto: returns (CrawlTaskResponse)
        # This implies it might wait for result? 
        # "rpc ReportCrawlResult" exists too. 
        # Usually ExecuteCrawl starts it, and ReportCrawlResult sends back individual items.
        # But the return type is CrawlTaskResponse which contains 'json_data'.
        # This implies Synchronous/Blocking RPC if we follow signature strictly?
        # NO, usually meant for "Batch Result" or just "Acknowledgement".
        
        # Strategy: Run crawl, collect results, return them in batch?
        # OR: Run crawl, return empty/ack immediately, and stream results via ReportCrawlResult?
        # Given 'ReportCrawlResult' exists in OrchestratorService, the latter is better for streaming.
        # BUT current proto signature for ExecuteCrawl returns CrawlTaskResponse.
        # Let's assume we return a summary or "Job Started" status here.
        
        try:
             # Run the crawl logic (assuming crawler.run() is modified to be called here)
             # If we await here, the Orchestrator blocks until crawl finishes.
             # Given it's a crawler, this might be okay for batch jobs.
             
             # Let's adapt crawler to be callable
             print(f"[gRPC Server] Starting crawl for task {request.task_id}...")
             
             # Execute crawl (awaiting means blocking response until done)
             # This matches the signature 'returns CrawlTaskResponse' with data.
             await self.crawler.execute_crawl_task(request.urls)
             
             return pb2.CrawlTaskResponse(
                 task_id=request.task_id,
                 status=pb2.SUCCESS,
                 json_data=json.dumps({"status": "completed", "count": len(self.crawler.results)}),
                 error_message=""
             )
        except Exception as e:
            print(f"[gRPC Server] Crawl failed: {e}")
            return pb2.CrawlTaskResponse(
                task_id=request.task_id,
                status=pb2.FAILED,
                json_data="",
                error_message=str(e)
            )

class GRPCServer:
    """
    Manages the gRPC Server for the Crawler node.
    """
    
    def __init__(self, crawler_instance, port=CRAWLER_GRPC_PORT):
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        self.port = port
        self.crawler_service = CrawlerService(crawler_instance)
        
        pb2_grpc.add_CrawlerServiceServicer_to_server(
            self.crawler_service, self.server
        )
        self.server.add_insecure_port(f'[::]:{self.port}')
        
    async def start(self):
        print(f"[gRPC Server] Starting Crawler Server on port {self.port}...")
        await self.server.start()
        
    async def stop(self):
        print("[gRPC Server] Stopping...")
        await self.server.stop(0)
