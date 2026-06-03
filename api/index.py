"""
Soft1 ERP MCP Server + REST Proxy
"""

import json
import urllib.request
import urllib.error
import gzip
import zlib
from http.server import BaseHTTPRequestHandler
from typing import Optional
import traceback
import io

import httpx
from fastmcp import FastMCP

SOFT1_URL = "https://pm.oncloud.gr/s1services/"

# ============================================================================
# Initialize MCP Server
# ============================================================================

mcp = FastMCP("Soft1 ERP Server")

# ============================================================================
# Soft1 API Client (used by MCP tools)
# ============================================================================

class Soft1Client:
    def __init__(self):
        self.client_id: Optional[str] = None

    async def login(self, username: str, password: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "login",
                "username": username,
                "password": password,
                "appId": "1001",
                "COMPANY": "1000",
                "BRANCH": "1000",
                "MODULE": "0",
                "REFID": "1"
            }
            response = await client.post(SOFT1_URL, json=payload)
            try:
                data = response.json()
            except UnicodeDecodeError:
                data = json.loads(response.content.decode('latin-1'))
            if data.get("success"):
                self.client_id = data.get("clientID")
            return data

    async def get_browser_info(self, client_id, obj, list_name, filters="", limit=20):
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "getBrowserInfo",
                "clientID": client_id,
                "appId": "1001",
                "OBJECT": obj,
                "LIST": list_name,
                "VERSION": 2,
                "LIMIT": limit,
                "FILTERS": filters
            }
            response = await client.post(SOFT1_URL, json=payload)
            try:
                return response.json()
            except UnicodeDecodeError:
                return json.loads(response.content.decode('latin-1'))

    async def get_data(self, client_id, obj, key, locate_info=""):
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "getData",
                "clientID": client_id,
                "appId": "1001",
                "OBJECT": obj,
                "FORM": "",
                "KEY": key,
                "LOCATEINFO": locate_info
            }
            response = await client.post(SOFT1_URL, json=payload)
            try:
                return response.json()
            except UnicodeDecodeError:
                return json.loads(response.content.decode('latin-1'))

    async def get_report_info(self, client_id, obj, filters=""):
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "getReportInfo",
                "clientID": client_id,
                "appId": "1001",
                "OBJECT": obj,
                "LIST": "",
                "FILTERS": filters
            }
            response = await client.post(SOFT1_URL, json=payload)
            try:
                return response.json()
            except UnicodeDecodeError:
                return json.loads(response.content.decode('latin-1'))

    async def get_report_data(self, client_id, req_id, page_num):
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "getReportData",
                "clientID": client_id,
                "appId": "1001",
                "reqID": req_id,
                "PAGENUM": page_num
            }
            response = await client.post(SOFT1_URL, json=payload)
            try:
                return response.json()
            except UnicodeDecodeError:
                return json.loads(response.content.decode('latin-1'))


soft1 = Soft1Client()


def decompress_response(data: bytes) -> str:
    """Decompress gzip or deflate compressed response"""
    try:
        if len(data) >= 2 and data[0] == 0x1f and data[1] == 0x8b:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                decompressed = gz.read()
                return decompressed.decode('utf-8', errors='replace')
        else:
            try:
                decompressed = zlib.decompress(data, -zlib.MAX_WBITS)
                return decompressed.decode('utf-8', errors='replace')
            except:
                try:
                    decompressed = zlib.decompress(data)
                    return decompressed.decode('utf-8', errors='replace')
                except:
                    return data.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Decompression error: {e}")
        return data.decode('utf-8', errors='replace')


def parse_soft1_response(raw_data: bytes, content_type: str) -> dict:
    """Parse Soft1 response handling compression and encoding"""
    decompressed_str = decompress_response(raw_data)
    print(f"Decompressed response preview: {decompressed_str[:200]}")
    
    try:
        return json.loads(decompressed_str)
    except json.JSONDecodeError:
        pass
    
    try:
        if len(raw_data) >= 2 and raw_data[0] == 0x1f and raw_data[1] == 0x8b:
            with gzip.GzipFile(fileobj=io.BytesIO(raw_data)) as gz:
                decompressed = gz.read()
                decoded = decompressed.decode('windows-1253')
                return json.loads(decoded)
    except:
        pass
    
    return {
        "success": True,
        "raw_response": decompressed_str[:1000],
        "content_type": content_type,
        "note": "Response received but not valid JSON"
    }


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def soft1_login(username: str, password: str) -> dict:
    return await soft1.login(username, password)

@mcp.tool()
async def soft1_search_customers(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    filter_map = {
        "name": "CUSTOMER.NAME={0}*",
        "code": "CUSTOMER.CODE={0}*",
        "vat": "CUSTOMER.AFM={0}",
        "city": "CUSTOMER.CITY={0}",
        "phone": "CUSTOMER.PHONE01={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "CUSTOMER", "Customers", filter_str, limit)

@mcp.tool()
async def soft1_get_customer_profile(client_id: str, customer_key: int) -> dict:
    locate_info = "CUSTOMER:CODE,NAME,AFM,ADDRESS,CITY,ZIP,PHONE01,PHONE02,FAX,EMAIL,WEBPAGE,DISCOUNT,REMARKS"
    return await soft1.get_data(client_id, "CUSTOMER", customer_key, locate_info)

@mcp.tool()
async def soft1_customer_balance(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    filter_map = {
        "name": "CUSTOMER.NAME={0}*",
        "code": "CUSTOMER.CODE={0}*",
        "vat": "CUSTOMER.AFM={0}"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "CUSTOMER", "Customer Balance - Turnover", filter_str, limit)

@mcp.tool()
async def soft1_search_items(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    filter_map = {
        "name": "ITEM.NAME={0}*",
        "code": "ITEM.CODE={0}*",
        "category": "ITEM.CATEGORY={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "ITEM", "Items", filter_str, limit)

@mcp.tool()
async def soft1_item_stock_balance(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    filter_map = {
        "name": "ITEM.NAME={0}*",
        "code": "ITEM.CODE={0}*",
        "category": "ITEM.CATEGORY={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "ITEM", "Item balance", filter_str, limit)

@mcp.tool()
async def soft1_search_sales_documents(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    filter_map = {
        "customer_name": "SALDOC.TRDRNAME={0}*",
        "customer_code": "SALDOC.CCCCODE={0}*",
        "date": "SALDOC.FINDATE={0}*",
        "type": "SALDOC.SERIES={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "SALDOC", "Sales List", filter_str, limit)

@mcp.tool()
async def soft1_outstanding_orders(client_id: str, filter_type: str = "all", filter_value: str = "") -> dict:
    filter_str = ""
    if filter_type != "all":
        filter_map = {
            "customer_name": "SALDOC.TRDRNAME={0}*",
            "customer_code": "SALDOC.CCCCODE={0}*"
        }
        filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "SALDOC", "Outstanding documents - Sales", filter_str)

@mcp.tool()
async def soft1_generate_report(client_id: str, report_type: str, filter_type: str = "all", filter_value: str = "") -> dict:
    report_map = {
        "aged_balance": "Cust_OPITEM",
        "customer_address_book": "CUST_ADDR_BOOK"
    }
    report_obj = report_map[report_type]
    filter_str = ""
    if filter_type != "all":
        filter_map = {
            "customer_code": "CUSTOMER.CODE={0}*",
            "customer_vat": "CUSTOMER.AFM={0}"
        }
        filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_report_info(client_id, report_obj, filter_str)

@mcp.tool()
async def soft1_fetch_report_page(client_id: str, req_id: str, page_num: int) -> dict:
    return await soft1.get_report_data(client_id, req_id, page_num)


# ============================================================================
# Vercel HTTP Handler
# ============================================================================

class handler(BaseHTTPRequestHandler):
    
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        response = json.dumps({"status": "Soft1 MCP Proxy running", "soft1_url": SOFT1_URL})
        self.wfile.write(response.encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            if not post_data:
                raise ValueError("Empty request body")
            
            payload = json.loads(post_data.decode('utf-8'))
            
            # 🔥 CRITICAL FIX: Add appId if missing (except for login)
            if payload.get('service') != 'login' and 'appId' not in payload:
                payload['appId'] = '1001'
                print(f"Added appId=1001 to {payload.get('service')} request")
            
            print(f"Forwarding: service={payload.get('service')}, appId={payload.get('appId')}")
            
            # Forward to Soft1 API
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                SOFT1_URL,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_data = resp.read()
                content_type = resp.headers.get('Content-Type', '')
                result = parse_soft1_response(raw_data, content_type)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except json.JSONDecodeError as e:
            error_response = json.dumps({"error": "Invalid JSON", "details": str(e)})
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error: {traceback.format_exc()}")
            error_response = json.dumps({"error": str(e), "type": type(e).__name__})
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))


if __name__ == "__main__":
    mcp.run()
