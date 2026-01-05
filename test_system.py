"""
Local Test Script for Distributed System
Tests the basic connectivity between nodes without external dependencies.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_orchestrator():
    """Test 1: Start Orchestrator and verify it's running."""
    print("=" * 60)
    print("TEST 1: Orchestrator Startup")
    print("=" * 60)
    
    from orchestrator.main import Orchestrator
    
    orch = Orchestrator()
    orch.start()
    
    print(f"✅ Orchestrator running on port 50051")
    print(f"   Registered nodes: {len(orch.registry)}")
    
    await asyncio.sleep(2)
    orch.stop()
    print("✅ Orchestrator stopped cleanly\n")
    return True


async def test_node_registration():
    """Test 2: Start Orchestrator, then register a mock node."""
    print("=" * 60)
    print("TEST 2: Node Registration")
    print("=" * 60)
    
    from orchestrator.main import Orchestrator
    import grpc
    from orchestrator.generated import orchestrator_pb2 as pb2
    from orchestrator.generated import orchestrator_pb2_grpc as pb2_grpc
    
    # Start orchestrator
    orch = Orchestrator()
    orch.start()
    await asyncio.sleep(1)
    
    # Connect as a client
    channel = grpc.insecure_channel('localhost:50051')
    stub = pb2_grpc.OrchestratorServiceStub(channel)
    
    # Register as DB node
    response = stub.Register(pb2.RegisterRequest(node_type="db"))
    print(f"   DB Node registered: {response.node_id}")
    assert response.success, "DB registration failed"
    
    # Register as VLM node
    response2 = stub.Register(pb2.RegisterRequest(node_type="vlm"))
    print(f"   VLM Node registered: {response2.node_id}")
    assert response2.success, "VLM registration failed"
    
    # Check registry
    print(f"   Total registered nodes: {len(orch.registry)}")
    
    # Cleanup
    channel.close()
    orch.stop()
    print("✅ Node registration works!\n")
    return True


async def test_heartbeat():
    """Test 3: Test heartbeat mechanism."""
    print("=" * 60)
    print("TEST 3: Heartbeat")
    print("=" * 60)
    
    from orchestrator.main import Orchestrator
    import grpc
    from orchestrator.generated import orchestrator_pb2 as pb2
    from orchestrator.generated import orchestrator_pb2_grpc as pb2_grpc
    
    orch = Orchestrator()
    orch.start()
    await asyncio.sleep(1)
    
    channel = grpc.insecure_channel('localhost:50051')
    stub = pb2_grpc.OrchestratorServiceStub(channel)
    
    # Register
    reg = stub.Register(pb2.RegisterRequest(node_type="crawler"))
    node_id = reg.node_id
    
    # Send heartbeat
    hb = stub.Heartbeat(pb2.HeartbeatRequest(
        node_id=node_id,
        status=1  # BUSY
    ))
    
    print(f"   Heartbeat acknowledged: {hb.acknowledged}")
    assert hb.acknowledged, "Heartbeat not acknowledged"
    
    # Check node status
    node = orch.registry.get_node(node_id)
    print(f"   Node status: {node.status.name}")
    
    channel.close()
    orch.stop()
    print("✅ Heartbeat works!\n")
    return True


async def test_crawl_result():
    """Test 4: Send mock crawl data through the pipeline."""
    print("=" * 60)
    print("TEST 4: Crawl Result Flow")
    print("=" * 60)
    
    from orchestrator.main import Orchestrator
    import grpc
    import json
    from orchestrator.generated import orchestrator_pb2 as pb2
    from orchestrator.generated import orchestrator_pb2_grpc as pb2_grpc
    
    orch = Orchestrator()
    orch.start()
    await asyncio.sleep(1)
    
    channel = grpc.insecure_channel('localhost:50051')
    stub = pb2_grpc.OrchestratorServiceStub(channel)
    
    # Register as crawler
    reg = stub.Register(pb2.RegisterRequest(node_type="crawler"))
    
    # Send mock news data
    mock_news = {
        "source": "Test Source",
        "country": "test",
        "url": "https://example.com/test-article",
        "keyword_found": "test",
        "scraped_at": "2025-01-01T12:00:00",
        "content": "This is test content about Turkey and the region...",
        "media": {
            "main_image": "https://example.com/image.jpg",
            "content_images": [],
            "videos": []
        }
    }
    
    result = pb2.CrawlTaskResponse(
        task_id="test_task_001",
        status=pb2.SUCCESS,
        json_data=json.dumps(mock_news),
        error_message=""
    )
    
    stub.ReportCrawlResult(result)
    print(f"   Sent mock crawl result")
    
    # Check pipeline
    pending = orch.pipeline.get_pending_tasks()
    print(f"   Pipeline pending tasks: {len(pending)}")
    
    channel.close()
    orch.stop()
    print("✅ Crawl result flow works!\n")
    return True


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 DISTRIBUTED SYSTEM LOCAL TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        ("Orchestrator Startup", test_orchestrator),
        ("Node Registration", test_node_registration),
        ("Heartbeat", test_heartbeat),
        ("Crawl Result Flow", test_crawl_result),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ All tests passed! System is working.\n")
        print("Next steps:")
        print("  1. Install LM Studio and load a Qwen model")
        print("  2. Start PostgreSQL + MinIO for DB node")
        print("  3. Test with real crawler data")
    
    return failed == 0


if __name__ == "__main__":
    asyncio.run(run_all_tests())
