"""
Soft1 ERP MCP Server + REST Proxy
- MCP tools: used by Claude
- REST proxy: used by browser artifacts directly
"""

import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler
from typing import Optional
import asyncio
import traceback

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


# ============================================================================
# MCP Tools (used by Claude)
# ============================================================================

@mcp.tool()
async def soft1_login(username: str, password: str) -> dict:
    """Login to Soft1 ERP and get session token"""
    return await soft1.login(username, password)


@mcp.tool()
async def soft1_search_customers(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    """Search for customers by name, code, VAT, city, or phone"""
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
    """Get complete customer profile with all details"""
    locate_info = "CUSTOMER:CODE,NAME,AFM,ADDRESS,CITY,ZIP,PHONE01,PHONE02,FAX,EMAIL,WEBPAGE,DISCOUNT,REMARKS"
    return await soft1.get_data(client_id, "CUSTOMER", customer_key, locate_info)


@mcp.tool()
async def soft1_customer_balance(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    """Get customer balance and turnover information"""
    filter_map = {
        "name": "CUSTOMER.NAME={0}*",
        "code": "CUSTOMER.CODE={0}*",
        "vat": "CUSTOMER.AFM={0}"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "CUSTOMER", "Customer Balance - Turnover", filter_str, limit)


@mcp.tool()
async def soft1_search_items(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    """Search for items/products by name, code, or category"""
    filter_map = {
        "name": "ITEM.NAME={0}*",
        "code": "ITEM.CODE={0}*",
        "category": "ITEM.CATEGORY={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "ITEM", "Items", filter_str, limit)


@mcp.tool()
async def soft1_item_stock_balance(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    """Check stock levels and availability"""
    filter_map = {
        "name": "ITEM.NAME={0}*",
        "code": "ITEM.CODE={0}*",
        "category": "ITEM.CATEGORY={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    return await soft1.get_browser_info(client_id, "ITEM", "Item balance", filter_str, limit)


@mcp.tool()
async def soft1_search_sales_documents(client_id: str, filter_type: str, filter_value: str, limit: int = 20) -> dict:
    """Search sales documents (invoices, orders, offers, credit notes)"""
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
    """Get outstanding/uninvoiced sales orders"""
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
    """Generate a report (aged_balance or customer_address_book)"""
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
    """Fetch a specific page of a generated report (returns HTML)"""
    return await soft1.get_report_data(client_id, req_id, page_num)


# ============================================================================
# Vercel HTTP Handler — REST proxy for browser artifacts
# ============================================================================

class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler"""
    
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
        
        response = json.dumps({
            "status": "Soft1 MCP Proxy is running",
            "method": "GET",
            "endpoints": ["POST / - Proxy Soft1 API calls"],
            "soft1_url": SOFT1_URL
        })
        self.wfile.write(response.encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Log for debugging (Vercel will capture this)
            print(f"Received POST data length: {content_length}")
            print(f"Raw data preview: {post_data[:200]}")
            
            if not post_data:
                raise ValueError("Empty request body")
            
            payload = json.loads(post_data.decode('utf-8'))
            print(f"Parsed payload service: {payload.get('service', 'unknown')}")
            
            # Forward to Soft1 API with better error handling
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                SOFT1_URL,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/plain, */*"
                },
                method="POST"
            )
            
            print(f"Sending request to Soft1: {SOFT1_URL}")
            
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    print(f"Soft1 response status: {resp.status}")
                    print(f"Soft1 response length: {len(raw)}")
                    
                    if not raw:
                        raise ValueError("Empty response from Soft1 API")
                    
                    # Try to decode response
                    raw_str = raw.decode('utf-8', errors='replace')
                    print(f"Response preview: {raw_str[:200]}")
                    
                    # Try to parse JSON
                    try:
                        result = json.loads(raw_str)
                    except json.JSONDecodeError as je:
                        # Try Latin-1
                        try:
                            result = json.loads(raw.decode('latin-1'))
                        except:
                            # If still fails, return as text
                            result = {
                                "success": False,
                                "error": "Non-JSON response from Soft1",
                                "raw_response": raw_str[:500],
                                "content_type": resp.headers.get('Content-Type', 'unknown')
                            }
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode('utf-8'))
                    
            except urllib.error.HTTPError as e:
                error_body = e.read()
                print(f"HTTP Error {e.code}: {error_body[:200]}")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                error_response = json.dumps({
                    "error": f"Soft1 API returned HTTP {e.code}",
                    "details": error_body.decode('utf-8', errors='replace')[:500]
                })
                self.wfile.write(error_response.encode('utf-8'))
                
            except urllib.error.URLError as e:
                print(f"URL Error: {e.reason}")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                error_response = json.dumps({
                    "error": f"Failed to connect to Soft1 API",
                    "details": str(e.reason)
                })
                self.wfile.write(error_response.encode('utf-8'))
            
        except json.JSONDecodeError as e:
            error_response = json.dumps({
                "error": "Invalid JSON in request body",
                "details": str(e),
                "received": post_data.decode('utf-8', errors='replace')[:200]
            })
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
            
        except Exception as e:
            print(f"Unexpected error: {traceback.format_exc()}")
            error_response = json.dumps({
                "error": str(e),
                "type": type(e).__name__,
                "details": traceback.format_exc()
            })
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))


# ============================================================================
# MCP entrypoint (when run directly, not via Vercel)
# ============================================================================

if __name__ == "__main__":
    mcp.run()
