#!/usr/bin/env python3
"""Quick API helper for item operations"""
import requests
import sys
import logging
import os

BASE_URL = "http://localhost:8000/api/v1"
REQUEST_TIMEOUT = 10  # seconds

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_token():
    """Login and get token using credentials from environment variables.
    
    Environment variables:
        API_USERNAME: Username for API authentication (required)
        API_PASSWORD: Password for API authentication (required)
    
    Returns:
        str: Access token
        
    Raises:
        ValueError: If credentials are missing or invalid
        requests.RequestException: On network/HTTP errors
    """
    # Get credentials from environment - NO DEFAULTS for security
    username = os.getenv("API_USERNAME")
    password = os.getenv("API_PASSWORD")
    
    if not username or not password:
        raise ValueError(
            "API credentials not configured. You must set API_USERNAME and API_PASSWORD environment variables.\n"
            "Example: export API_USERNAME=admin && export API_PASSWORD=your_secure_password\n"
            "Or create a .env file with these variables (see scripts/README.md for details)."
        )
    
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        
        # Safely parse JSON response
        try:
            data = resp.json()
        except ValueError as e:
            logging.error(f"Invalid JSON response from login endpoint: {e}")
            raise ValueError(f"Login endpoint returned invalid JSON: {e}")
        
        # Validate token presence
        token = data.get("access_token")
        if not token:
            logging.error("Login response missing 'access_token' field")
            raise ValueError(
                "Login successful but no access_token in response. "
                "This may indicate an API authentication issue."
            )
        
        return token
        
    except requests.HTTPError as e:
        logging.error(f"HTTP error during login: {e}")
        # Check if response exists before accessing attributes
        response = getattr(e, 'response', None)
        if response is not None:
            if response.status_code == 401:
                raise ValueError(
                    "Login failed: Invalid credentials. "
                    "Check API_USERNAME and API_PASSWORD environment variables."
                )
            elif response.status_code == 404:
                raise ValueError(
                    f"Login endpoint not found at {BASE_URL}/auth/login. "
                    "Check BASE_URL configuration."
                )
            else:
                raise ValueError(f"Login failed with HTTP {response.status_code}: {e}")
        else:
            raise ValueError(f"Login failed: {e}")
    except requests.Timeout as e:
        logging.error(f"Timeout during login: {e}")
        raise ValueError(
            f"Login request timed out after {REQUEST_TIMEOUT} seconds. "
            "Check network connectivity and API server status."
        )
    except requests.ConnectionError as e:
        logging.error(f"Connection error during login: {e}")
        raise ValueError(
            f"Cannot connect to API server at {BASE_URL}. "
            "Check that the server is running and the BASE_URL is correct."
        )
    except requests.RequestException as e:
        logging.error(f"Unexpected error during login: {e}")
        raise ValueError(f"Login failed due to network error: {e}")

def patch_item(item_id, data, token=None):
    """Update item
    
    Args:
        item_id: ID of the item to update
        data: Dictionary of fields to update
        token: Optional auth token (will get new one if not provided)
    
    Returns:
        Response JSON on success
    
    Raises:
        requests.RequestException: On network/HTTP errors
        ValueError: On invalid response data
    """
    if token is None:
        token = get_token()
    
    try:
        resp = requests.patch(
            f"{BASE_URL}/items/{item_id}",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        logging.error(f"HTTP error patching item {item_id}: {e}")
        # Check if response exists before accessing attributes
        response = getattr(e, 'response', None)
        if response is not None and response.text:
            logging.error(f"Response body: {response.text}")
        raise
    except requests.RequestException as e:
        logging.error(f"Request error patching item {item_id}: {e}")
        raise
    except ValueError as e:
        logging.error(f"Invalid JSON response for item {item_id}: {e}")
        raise

def create_item(data, token=None):
    """Create item
    
    Args:
        data: Dictionary of item fields
        token: Optional auth token (will get new one if not provided)
    
    Returns:
        Response JSON on success
    
    Raises:
        requests.RequestException: On network/HTTP errors
        ValueError: On invalid response data
    """
    if token is None:
        token = get_token()
    
    try:
        resp = requests.post(
            f"{BASE_URL}/items",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        logging.error(f"HTTP error creating item: {e}")
        # Check if response exists before accessing attributes
        response = getattr(e, 'response', None)
        if response is not None and response.text:
            logging.error(f"Response body: {response.text}")
        raise
    except requests.RequestException as e:
        logging.error(f"Request error creating item: {e}")
        raise
    except ValueError as e:
        logging.error(f"Invalid JSON response: {e}")
        raise

def get_item_by_sku(sku, token=None):
    """Look up an item by SKU
    
    Args:
        sku: SKU to search for
        token: Optional auth token (will get new one if not provided)
    
    Returns:
        Item dict on success, None if not found
    
    Raises:
        requests.RequestException: On network/HTTP errors
        ValueError: On invalid response data
    """
    if token is None:
        token = get_token()
    
    try:
        resp = requests.get(
            f"{BASE_URL}/items",
            params={"sku": sku},
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        
        try:
            data = resp.json()
        except ValueError as e:
            logging.error(f"Invalid JSON response when looking up SKU {sku}: {e}")
            raise
        
        items = data.get("items", [])
        if not items:
            return None
        
        # Return first exact match
        for item in items:
            if item.get("sku") == sku:
                return item
        
        return None
        
    except requests.HTTPError as e:
        logging.error(f"HTTP error looking up SKU {sku}: {e}")
        response = getattr(e, 'response', None)
        if response is not None and response.text:
            logging.error(f"Response body: {response.text[:200]}")
        raise
    except requests.RequestException as e:
        logging.error(f"Network error looking up SKU {sku}: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python api_helper.py [fix_skus|create_pivot|list_items]")
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        # Get token once and reuse it
        token = get_token()
        logging.info("Successfully authenticated")

        if cmd == "fix_skus":
            # Fix SKUs with trailing tabs - look up items by SKU first
            skus_to_fix = [
                ("GEAR-SPUR-48", "GEAR-SPUR-48"),  # (current_sku, corrected_sku)
                ("BRACKET-MOTOR-V2", "BRACKET-MOTOR-V2"),
            ]
            
            for current_sku, corrected_sku in skus_to_fix:
                print(f"Looking up item with SKU '{current_sku}'...")
                item = get_item_by_sku(current_sku, token=token)
                
                if not item:
                    logging.warning(f"Item with SKU '{current_sku}' not found, skipping")
                    continue
                
                item_id = item.get("id")
                if not item_id:
                    logging.error(f"Item found but missing ID: {item}")
                    continue
                
                print(f"  Found item ID {item_id}, updating SKU to '{corrected_sku}'...")
                r = patch_item(item_id, {"sku": corrected_sku}, token=token)
                print(f"  Result: {r.get('sku', r)}")

        elif cmd == "create_pivot":
            # Get category_id from environment variable with default fallback
            category_id_str = os.getenv("CATEGORY_ID", "3")
            try:
                category_id = int(category_id_str)
            except (ValueError, TypeError):
                logging.error(f"Invalid CATEGORY_ID '{category_id_str}', must be an integer. Using default: 3")
                category_id = 3
            
            print(f"Creating Pivot Hardware Kit (category_id: {category_id})...")
            r = create_item({
                "sku": "HW-PIVOT-KIT",
                "name": "Pivot Hardware Kit",
                "description": "Pivot pins and springs for gripper assemblies",
                "item_type": "component",
                "procurement_type": "buy",
                "category_id": category_id,
                "unit": "EA",
                "standard_cost": 2.50
            }, token=token)
            print(f"  Result: {r.get('id', r)} - {r.get('sku', r)}")

        elif cmd == "list_items":
            try:
                resp = requests.get(
                    f"{BASE_URL}/items?item_type=finished_good",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=REQUEST_TIMEOUT
                )
                resp.raise_for_status()
                
                # Parse JSON response
                try:
                    data = resp.json()
                except ValueError as e:
                    logging.error(f"Invalid JSON response when listing items: {e}")
                    if resp.text:
                        logging.error(f"Response body: {resp.text[:200]}")
                    raise
                
                items = data.get("items", [])
                if not items:
                    print("No finished goods found")
                else:
                    for i in items[:10]:
                        item_id = i.get('id', 0)
                        item_sku = i.get('sku', '')
                        item_name = i.get('name', '')
                        print(f"{item_id:3} | {item_sku:<25} | {item_name}")
                        
            except requests.HTTPError as e:
                logging.error(f"HTTP error listing items: {e}")
                # Check if response exists before accessing attributes
                response = getattr(e, 'response', None)
                if response is not None and response.text:
                    logging.error(f"Response body: {response.text[:200]}")
                raise
            except requests.RequestException as e:
                logging.error(f"Network error listing items: {e}")
                raise

        else:
            logging.error(f"Unknown command: {cmd}")
            print("Usage: python api_helper.py [fix_skus|create_pivot|list_items]")
            sys.exit(1)

    except Exception as e:
        logging.error(f"Command failed: {e}")
        sys.exit(1)
