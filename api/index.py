"""
Soft1 ERP MCP Server - REAL MCP Implementation
Uses FastMCP for proper MCP protocol support
"""

import httpx
import json
from fastmcp import FastMCP
from typing import Optional

# ============================================================================
# Initialize MCP Server (FastMCP handles the protocol)
# ============================================================================

mcp = FastMCP("Soft1 ERP Server")


# ============================================================================
# Soft1 API Client
# ============================================================================

class Soft1Client:
    """Client for Soft1 ERP API"""

    BASE_URL = "https://pm.oncloud.gr/s1services/"

    def __init__(self):
        self.client_id: Optional[str] = None

    async def login(self, username: str, password: str) -> dict:
        """Login to Soft1"""
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
            response = await client.post(self.BASE_URL, json=payload)

            # Handle different encodings (Soft1 may return Latin-1 instead of UTF-8)
            try:
                data = response.json()
            except UnicodeDecodeError:
                # Try Latin-1 encoding
                text = response.content.decode('latin-1')
                data = json.loads(text)

            if data.get("success"):
                self.client_id = data.get("clientID")
            return data

    async def get_browser_info(
        self,
        client_id: str,
        obj: str,
        list_name: str,
        filters: str = "",
        limit: int = 20
    ) -> dict:
        """Get list of records"""
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
            response = await client.post(self.BASE_URL, json=payload)

            try:
                return response.json()
            except UnicodeDecodeError:
                text = response.content.decode('latin-1')
                return json.loads(text)

    async def get_data(
        self,
        client_id: str,
        obj: str,
        key: int,
        locate_info: str = ""
    ) -> dict:
        """Get detailed record"""
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
            response = await client.post(self.BASE_URL, json=payload)

            try:
                return response.json()
            except UnicodeDecodeError:
                text = response.content.decode('latin-1')
                return json.loads(text)

    async def get_report_info(
        self,
        client_id: str,
        obj: str,
        filters: str = ""
    ) -> dict:
        """Generate report"""
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "getReportInfo",
                "clientID": client_id,
                "appId": "1001",
                "OBJECT": obj,
                "LIST": "",
                "FILTERS": filters
            }
            response = await client.post(self.BASE_URL, json=payload)

            try:
                return response.json()
            except UnicodeDecodeError:
                text = response.content.decode('latin-1')
                return json.loads(text)

    async def get_report_data(
        self,
        client_id: str,
        req_id: str,
        page_num: int
    ) -> dict:
        """Fetch report page"""
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "service": "getReportData",
                "clientID": client_id,
                "appId": "1001",
                "reqID": req_id,
                "PAGENUM": page_num
            }
            response = await client.post(self.BASE_URL, json=payload)

            try:
                return response.json()
            except UnicodeDecodeError:
                text = response.content.decode('latin-1')
                return json.loads(text)


soft1 = Soft1Client()


# ============================================================================
# MCP Tools (FastMCP handles protocol automatically)
# ============================================================================

@mcp.tool()
async def soft1_login(username: str, password: str) -> dict:
    """Login to Soft1 ERP and get session token"""
    result = await soft1.login(username, password)
    return result


@mcp.tool()
async def soft1_search_customers(
    client_id: str,
    filter_type: str,
    filter_value: str,
    limit: int = 20
) -> dict:
    """
    Search for customers by name, code, VAT, city, or phone

    Args:
        client_id: Session clientID from login
        filter_type: 'name', 'code', 'vat', 'city', or 'phone'
        filter_value: Value to search (supports * for partial)
        limit: Max results (default 20)
    """
    filter_map = {
        "name": "CUSTOMER.NAME={0}*",
        "code": "CUSTOMER.CODE={0}*",
        "vat": "CUSTOMER.AFM={0}",
        "city": "CUSTOMER.CITY={0}",
        "phone": "CUSTOMER.PHONE01={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    result = await soft1.get_browser_info(
        client_id, "CUSTOMER", "Customers", filter_str, limit
    )
    return result


@mcp.tool()
async def soft1_get_customer_profile(
    client_id: str,
    customer_key: int
) -> dict:
    """Get complete customer profile with all details"""
    locate_info = "CUSTOMER:CODE,NAME,AFM,ADDRESS,CITY,ZIP,PHONE01,PHONE02,FAX,EMAIL,WEBPAGE,DISCOUNT,REMARKS"
    result = await soft1.get_data(
        client_id, "CUSTOMER", customer_key, locate_info
    )
    return result


@mcp.tool()
async def soft1_customer_balance(
    client_id: str,
    filter_type: str,
    filter_value: str,
    limit: int = 20
) -> dict:
    """Get customer balance and turnover information"""
    filter_map = {
        "name": "CUSTOMER.NAME={0}*",
        "code": "CUSTOMER.CODE={0}*",
        "vat": "CUSTOMER.AFM={0}"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    result = await soft1.get_browser_info(
        client_id, "CUSTOMER", "Customer Balance - Turnover",
        filter_str, limit
    )
    return result


@mcp.tool()
async def soft1_search_items(
    client_id: str,
    filter_type: str,
    filter_value: str,
    limit: int = 20
) -> dict:
    """Search for items/products by name, code, or category"""
    filter_map = {
        "name": "ITEM.NAME={0}*",
        "code": "ITEM.CODE={0}*",
        "category": "ITEM.CATEGORY={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    result = await soft1.get_browser_info(
        client_id, "ITEM", "Items", filter_str, limit
    )
    return result


@mcp.tool()
async def soft1_item_stock_balance(
    client_id: str,
    filter_type: str,
    filter_value: str,
    limit: int = 20
) -> dict:
    """Check stock levels and availability"""
    filter_map = {
        "name": "ITEM.NAME={0}*",
        "code": "ITEM.CODE={0}*",
        "category": "ITEM.CATEGORY={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    result = await soft1.get_browser_info(
        client_id, "ITEM", "Item balance", filter_str, limit
    )
    return result


@mcp.tool()
async def soft1_search_sales_documents(
    client_id: str,
    filter_type: str,
    filter_value: str,
    limit: int = 20
) -> dict:
    """Search sales documents (invoices, orders, offers, credit notes)"""
    filter_map = {
        "customer_name": "SALDOC.TRDRNAME={0}*",
        "customer_code": "SALDOC.CCCCODE={0}*",
        "date": "SALDOC.FINDATE={0}*",
        "type": "SALDOC.SERIES={0}*"
    }
    filter_str = filter_map[filter_type].format(filter_value)
    result = await soft1.get_browser_info(
        client_id, "SALDOC", "Sales List", filter_str, limit
    )
    return result


@mcp.tool()
async def soft1_outstanding_orders(
    client_id: str,
    filter_type: str = "all",
    filter_value: str = ""
) -> dict:
    """Get outstanding/uninvoiced sales orders"""
    filter_str = ""
    if filter_type != "all":
        filter_map = {
            "customer_name": "SALDOC.TRDRNAME={0}*",
            "customer_code": "SALDOC.CCCCODE={0}*"
        }
        filter_str = filter_map[filter_type].format(filter_value)
    result = await soft1.get_browser_info(
        client_id, "SALDOC", "Outstanding documents - Sales", filter_str
    )
    return result


@mcp.tool()
async def soft1_generate_report(
    client_id: str,
    report_type: str,
    filter_type: str = "all",
    filter_value: str = ""
) -> dict:
    """
    Generate a report (aged_balance or customer_address_book)
    Returns reqID and number of pages
    """
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
    result = await soft1.get_report_info(client_id, report_obj, filter_str)
    return result


@mcp.tool()
async def soft1_fetch_report_page(
    client_id: str,
    req_id: str,
    page_num: int
) -> dict:
    """Fetch a specific page of a generated report (returns HTML)"""
    result = await soft1.get_report_data(client_id, req_id, page_num)
    return result


# ============================================================================
# Run the MCP Server
# ============================================================================
app = mcp.http_app(stateless_http=True, path="/")

if __name__ == "__main__":
    mcp.run()
