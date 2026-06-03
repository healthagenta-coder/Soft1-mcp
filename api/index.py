"""
Soft1 ERP MCP Server + REST Proxy
- MCP tools: used by Claude
- REST proxy: used by browser artifacts directly
"""

import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Optional

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
# Vercel detects this class automatically and uses it for all HTTP requestss
# ============================================================================

def handler(request, context):
    """Vercel serverless function entry point"""
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
            "body": ""
        }
    
    # Handle GET request
    if request.method == "GET":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"status": "Soft1 MCP Proxy is running", "method": "GET"})
        }
    
    # Handle POST request
    if request.method == "POST":
        try:
            # Parse request body
            body = json.loads(request.body or "{}")
            
            # Forward to Soft1 API
            req = urllib.request.Request(
                SOFT1_URL,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                try:
                    result = json.loads(raw.decode("utf-8"))
                except:
                    result = json.loads(raw.decode("latin-1"))
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(result)
            }
            
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": str(e), "details": "Failed to proxy request"})
            }
    
    return {
        "statusCode": 405,
        "body": json.dumps({"error": "Method not allowed"})
    }


# ============================================================================
# MCP entrypoint (when run directly, not via Vercel)
# ============================================================================

if __name__ == "__main__":
    mcp.run()
