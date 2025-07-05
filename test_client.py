#!/usr/bin/env python3
import httpx
import sys
import asyncio
from pathlib import Path


class MapMapTestClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_service_info(self):
        print("\n=== Testing Service Info ===")
        response = await self.client.get(f"{self.base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    
    async def test_health_check(self):
        print("\n=== Testing Health Check ===")
        response = await self.client.get(f"{self.base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    
    async def test_coordinate_systems(self):
        print("\n=== Testing Coordinate Systems ===")
        response = await self.client.get(f"{self.base_url}/coordinate-systems")
        print(f"Status: {response.status_code}")
        print(f"Available systems: {list(response.json().keys())}")
        return response.status_code == 200
    
    async def test_endpoints(self):
        print("\n=== Testing Endpoints ===")
        response = await self.client.get(f"{self.base_url}/endpoints")
        print(f"Status: {response.status_code}")
        print(f"Available endpoints: {list(response.json().keys())}")
        return response.status_code == 200
    
    async def test_tile_request(self, z=10, x=580, y=316, endpoint=None):
        print(f"\n=== Testing Tile Request z={z}, x={x}, y={y} ===")
        url = f"{self.base_url}/tiles/{z}/{x}/{y}"
        if endpoint:
            url += f"?endpoint={endpoint}"
        
        response = await self.client.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {len(response.content)} bytes")
            
            # Save tile to file for inspection
            filename = f"test_tile_{z}_{x}_{y}.png"
            Path(filename).write_bytes(response.content)
            print(f"Tile saved to: {filename}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    
    async def test_invalid_tile(self):
        print("\n=== Testing Invalid Tile Request ===")
        response = await self.client.get(f"{self.base_url}/tiles/10/0/0")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 400
    
    async def test_cache(self):
        print("\n=== Testing Cache ===")
        
        # First request
        print("First request...")
        await self.client.get(f"{self.base_url}/tiles/10/580/316")
        
        # Check cache size
        response = await self.client.get(f"{self.base_url}/health")
        cache_size_1 = response.json()["cache_size"]
        print(f"Cache size after first request: {cache_size_1}")
        
        # Second request (should be cached)
        print("Second request (should be cached)...")
        await self.client.get(f"{self.base_url}/tiles/10/580/316")
        
        # Check cache size again
        response = await self.client.get(f"{self.base_url}/health")
        cache_size_2 = response.json()["cache_size"]
        print(f"Cache size after second request: {cache_size_2}")
        
        return True
    
    async def run_all_tests(self):
        print("Starting MapMap Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_service_info(),
            self.test_health_check(),
            self.test_coordinate_systems(),
            self.test_endpoints(),
            self.test_tile_request(),
            self.test_tile_request(z=12, x=2321, y=1264),
            self.test_invalid_tile(),
            self.test_cache(),
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        passed = sum(1 for r in results if r is True)
        failed = len(results) - passed
        
        print("\n" + "=" * 50)
        print(f"Tests completed: {passed} passed, {failed} failed")
        
        await self.client.aclose()
        return failed == 0


async def main():
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    print(f"Testing MapMap at: {base_url}")
    
    client = MapMapTestClient(base_url)
    success = await client.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())