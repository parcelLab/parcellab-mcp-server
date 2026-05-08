# parcelLab MCP Server - Public Beta

> Public beta of the parcelLab MCP Server for order tracking and returns.

The parcelLab MCP (Model Context Protocol) Server exposes parcelLab logistics APIs to MCP-compatible clients for order tracking and return registration. This public beta focuses on core customer-facing capabilities used in common e-commerce workflows.

## What is parcelLab MCP Server?

The parcelLab MCP Server integrates parcelLab logistics APIs with MCP-compatible agent frameworks (LangChain, CrewAI, AutoGen) and custom applications. Built on the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP), it provides tools to:

- **Track Orders**: Real-time order status and shipping information
- **Process Returns**: Complete return registration workflow from lookup to submission
- **Customer Support**: Instant access to logistics data for customer inquiries

### Key Benefits for Developers

- **MCP-standard**: Works with agent frameworks and custom clients
- **Live data**: Access to parcelLab logistics APIs
- **Robust Authentication**: Token-based with scoped access
- **Agent workflows**: Tools designed for agent use
- **Infrastructure**: Embedded in parcelLab platform infrastructure

---

## Public Beta Tools

This beta includes seven tools for order information and return registration:

### Order Information

#### `public_order_info`

Retrieve order status information for customer-facing use cases.

**Capabilities:**

- Order status and tracking updates
- Delivery predictions and milestones
- Shipping carrier information
- Customer notification history

### Return Registration Workflow

Return management workflow with six tools:

#### `public_lookup_order`

Create a return registration from an order reference and customer identifier.

#### `public_registration_get_article_selection`

Retrieve the current article selection state for a return registration.

#### `public_registration_update_article_selection`

Update and validate which articles are being returned.

#### `public_registration_get_options`

Get available courier and drop-off options for the return.

#### `public_registration_select_option`

Select a specific courier or drop-off option to finalize logistics.

#### `public_submit_registration`

Submit the completed return registration for processing.

---

## Getting Started

### 1. Choose Your Integration Approach

The parcelLab MCP Server works with multiple integration patterns:

- Agent frameworks: CrewAI, AutoGen, LangChain, Swarm
- Python MCP client: Direct programmatic access
- Development tools: Claude Code, Cursor, VS Code for testing
- Custom clients: Any MCP-compatible implementation

### 2. Installation & Setup

#### Python MCP Client (Recommended)

```bash
# Install the official Python MCP client
pip install mcp

# Or with async support
pip install mcp[asyncio]
```

#### Agent Framework Integration

```bash
# For CrewAI
pip install crewai mcp

# For LangChain
pip install langchain mcp

# For AutoGen
pip install pyautogen mcp
```

### 3. Connect to parcelLab MCP Server

#### Simple Customer Test With Service Account Credentials

If you received a parcelLab service account with:

- `PARCELLAB_CLIENT`
- `PARCELLAB_SECRET`

you can test your MCP access in four simple steps.

1. Create a local environment file:

```bash
cp .env.example .env
```

2. Add your credentials to `.env`:

```bash
PARCELLAB_CLIENT=your-client-id
PARCELLAB_SECRET=your-client-secret
```

3. Install the example dependencies with `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install mcp httpx
```

4. Run the service-account example:

```bash
python examples/service_account_list_tools.py
```

What this example does:

1. Reads `PARCELLAB_CLIENT` and `PARCELLAB_SECRET` from `.env`
2. Requests an OAuth access token using the `client_credentials` flow
3. Connects to `https://agents.parcellab.com/mcp/`
4. Calls `list_tools()` and prints the tools available to your service account

If the credentials are valid, you should see the MCP tools printed in the terminal.
If you receive `401 Unauthorized`, double-check the client ID, client secret, and that the service account has the required scopes.

#### Python MCP Client (OAuth2 + HTTP)

```python
import asyncio
from urllib.parse import parse_qs, urlparse

from pydantic import AnyUrl

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken


class InMemoryTokenStorage(TokenStorage):
    """Minimal token storage for demos. Replace in production."""
    def __init__(self):
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None: return self.tokens
    async def set_tokens(self, tokens: OAuthToken) -> None: self.tokens = tokens
    async def get_client_info(self) -> OAuthClientInformationFull | None: return self.client_info
    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None: self.client_info = client_info


async def handle_redirect(auth_url: str) -> None:
    print(f"Open this URL in a browser and complete login: {auth_url}")


async def handle_callback() -> tuple[str, str | None]:
    callback_url = input("Paste the final redirected URL here: ")
    params = parse_qs(urlparse(callback_url).query)
    return params["code"][0], params.get("state", [None])[0]


async def connect_to_parcellab():
    # Configure OAuth2 dynamic client registration per MCP spec
    oauth_auth = OAuthClientProvider(
        server_url="https://agents.parcellab.com",  # RS origin (issuer for metadata)
        client_metadata=OAuthClientMetadata(
            client_name="parcelLab MCP Client",
            redirect_uris=[AnyUrl("http://localhost:8765/callback")],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="mcp:full returns:registration track:orderinfo",
        ),
        storage=InMemoryTokenStorage(),
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )

    # Connect over Streamable HTTP; SDK attaches Authorization: Bearer <token>
    async with streamablehttp_client("https://agents.parcellab.com/mcp/", auth=oauth_auth) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])
            return session
```

#### CrewAI Integration

```python
from crewai import Agent, Task, Crew, Process
from crewai_tools import MCPServerAdapter
import asyncio
from mcp_server.docs.snippets.oauth_client import acquire_access_token

# Acquire OAuth access token via dynamic client registration
access_token = asyncio.run(
    acquire_access_token(
        server_url="https://agents.parcellab.com/mcp/",
        issuer_url="https://agents.parcellab.com",
        scope="mcp:full returns:registration track:orderinfo",
    )
)
server_params = {
    "url": "https://agents.parcellab.com/mcp/",
    "transport": "streamable-http",
    "headers": {"Authorization": f"Bearer {access_token}"},
}

with MCPServerAdapter(server_params, connect_timeout=60) as pl_tools:
    print("Tools:", [t.name for t in pl_tools])

    logistics_agent = Agent(
        role="Logistics Specialist",
        goal="Help customers track orders and process returns efficiently",
        backstory="Expert in e-commerce logistics and customer service",
        tools=pl_tools,
        verbose=True,
    )

    track_order_task = Task(
        description="Track order PL-2024-001234 and provide status update",
        expected_output="Detailed order status with tracking information",
        agent=logistics_agent,
    )

    crew = Crew(agents=[logistics_agent], tasks=[track_order_task], process=Process.sequential, verbose=2)
    result = crew.kickoff()
    print(result)
```

#### LangChain / LangGraph Integration

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools

# (Reuse the OAuth snippet from above or implement a TokenStorage)
class InMemoryTokenStorage(TokenStorage):
    def __init__(self):
        self.tokens = None
        self.client_info = None
    async def get_tokens(self): return self.tokens
    async def set_tokens(self, tokens): self.tokens = tokens
    async def get_client_info(self): return self.client_info
    async def set_client_info(self, info): self.client_info = info

oauth_auth = OAuthClientProvider(
    server_url="https://agents.parcellab.com",
    client_metadata=OAuthClientMetadata(
        client_name="LangChain Client",
        redirect_uris=["http://localhost:8765/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="mcp:full returns:registration track:orderinfo",
    ),
    storage=InMemoryTokenStorage(),
    redirect_handler=lambda url: print("Open:", url),
    callback_handler=lambda: (input("Paste callback URL and press Enter:\n") or "?code=...", None),
)

async def main():
    # Connect with OAuth; SDK attaches Authorization: Bearer automatically
    async with streamablehttp_client("https://agents.parcellab.com/mcp/", auth=oauth_auth) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)  # -> List[langchain.tools.BaseTool]

            agent = create_react_agent("openai:gpt-4.1", tools)
            res = await agent.ainvoke({"messages": "Track order PL-2024-001234 for customer@example.com (account 12345)"})
            print(res)

asyncio.run(main())
```

### 4. Development & Testing Tools

#### Claude Code (For Development)

```bash
# Add the public beta endpoint for development/testing
claude mcp add parcellab_beta --transport http https://agents.parcellab.com/mcp/
```

#### Cursor IDE

Create `.cursorrules` in your workspace root:

```json
{
  "mcpServers": {
    "parcellab_beta": {
      "url": "https://agents.parcellab.com/mcp/"
    }
  }
}
```

#### VS Code

Create `.vscode/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "parcellab_beta": {
      "transport": {
        "type": "http",
        "url": "https://agents.parcellab.com/mcp/"
      }
    }
  }
}
```

### 5. Authentication

The parcelLab MCP server requires an HTTP Authorization header on every request:

- Header: `Authorization: Bearer <access_token>`
- Tokens are obtained via OAuth 2.1 with dynamic client registration as defined by the MCP specification.
- The server publishes RFC 9728 Protected Resource Metadata that clients use to discover the Authorization Server and perform OAuth flows.

Recommended client flow (per MCP Python SDK):

```python
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

oauth_auth = OAuthClientProvider(
    server_url="https://agents.parcellab.com",   # RS origin for metadata
    client_metadata=...,                          # name, redirect_uris, scopes, etc.
    storage=...,                                  # persist tokens
    redirect_handler=..., callback_handler=...    # user login + code capture
)

async with streamablehttp_client("https://agents.parcellab.com/mcp/", auth=oauth_auth) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        ...
```

If you already have a token (service-to-service), pass it as a Bearer header via your transport’s header configuration.

Required scopes commonly used in public beta:

- `mcp:preview` – List/inspect tools (read-only)
- `track:orderinfo` – Order information tools
- `returns:registration` – Return registration workflow tools

---

## Developer How-To Guides

### Track an Order with Python MCP Client

**Use Case**: Build an order tracking service for your e-commerce platform

```python
import asyncio

async def track_order_for_customer(lookup_params: dict, client):
    """Track order status using parcelLab MCP server with flexible lookup methods.
    Pass an MCP client that already attaches Authorization headers (see Authentication).
    """

    try:
        # Call the order info tool with provided lookup parameters
        result = await client.call_tool("public_order_info", lookup_params)

        # Process the response
        order_data = result.content[0].text  # Extract tool result

        return {
            "success": True,
            "order_info": order_data
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Example lookup methods
async def track_by_order_number(client):
    return await track_order_for_customer({
        "order_number": "PL-2024-001234",
        "account": 12345
    }, client)

async def track_by_tracking_number(client):
    return await track_order_for_customer({
        "tracking_number": "1Z999AA1234567890",
        "courier": "ups"
    }, client)

async def track_by_customer_email(client):
    return await track_order_for_customer({
        "recipient_email": "customer@example.com",
        "account": 12345,
        "postal_code": "10001"  # Optional verification
    }, client)

# Usage example
async def main(client):
    # Track by order number
    order_info = await track_by_order_number(client)
    print(f"Order status: {order_info}")

    # Track by tracking number (when customer only has tracking info)
    tracking_info = await track_by_tracking_number(client)
    print(f"Tracking status: {tracking_info}")

# Example response structure
"""
{
    "order_number": "PL-2024-001234",
    "status": "in_transit",
    "tracking_number": "1Z999AA1234567890",
    "carrier": "UPS",
    "estimated_delivery": "2024-01-15T18:00:00Z",
    "checkpoints": [
        {
            "status": "shipped",
            "timestamp": "2024-01-12T10:30:00Z",
            "location": "Distribution Center"
        }
    ]
}
"""
```

### Build a Complete Return Processing System

**Use Case**: Create a return management system for your customer service team

```python
import asyncio
from typing import Dict, Any, List

class ReturnProcessor:
    """Complete return processing system using parcelLab MCP."""

    def __init__(self, client):
        """Pass an MCP client that already attaches Authorization headers."""
        self.client = client

    async def initiate_return(self, order_ref: str, customer_email: str,
                            account_id: int, portal_code: str) -> Dict[str, Any]:
        """Step 1: Look up the order and create return registration."""

        try:
            result = await self.client.call_tool("public_lookup_order", {
                "account": account_id,
                "code": portal_code,
                "reference": order_ref,
                "identifier": customer_email
            })

            registration_data = result.content[0].text
            registration_id = registration_data["external_id"]

            return {
                "success": True,
                "registration_id": registration_id,
                "message": "Return registration created successfully"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_returnable_items(self, registration_id: str, account_id: int,
                                 portal_code: str) -> Dict[str, Any]:
        """Step 2: Get available articles for return."""

        try:
            result = await self.client.call_tool("public_registration_get_article_selection", {
                "account": account_id,
                "code": portal_code,
                "external_id": registration_id
            })

            articles_data = result.content[0].text
            return {
                "success": True,
                "articles": articles_data["articles"]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def select_return_items(self, registration_id: str, account_id: int,
                                portal_code: str, selected_articles: List[Dict]) -> Dict[str, Any]:
        """Step 3: Select and validate items for return."""

        try:
            result = await self.client.call_tool("public_registration_update_article_selection", {
                "account": account_id,
                "code": portal_code,
                "external_id": registration_id,
                "articles": selected_articles
            })

            return {"success": True, "message": "Articles selected for return"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_return_options(self, registration_id: str, account_id: int,
                               portal_code: str) -> Dict[str, Any]:
        """Step 4: Get available courier and drop-off options."""

        try:
            result = await self.client.call_tool("public_registration_get_options", {
                "account": account_id,
                "code": portal_code,
                "external_id": registration_id
            })

            options_data = result.content[0].text
            return {
                "success": True,
                "courier_options": options_data.get("courier_options", []),
                "dropoff_options": options_data.get("dropoff_options", [])
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def select_return_method(self, registration_id: str, account_id: int,
                                 portal_code: str, selected_option: Dict) -> Dict[str, Any]:
        """Step 5: Select return method (courier pickup or drop-off)."""

        try:
            result = await self.client.call_tool("public_registration_select_option", {
                "account": account_id,
                "code": portal_code,
                "external_id": registration_id,
                "selected_option": selected_option
            })

            return {"success": True, "message": "Return method selected"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def submit_return(self, registration_id: str, account_id: int,
                          portal_code: str, commit: bool = True) -> Dict[str, Any]:
        """Step 6: Submit the completed return registration."""

        try:
            result = await self.client.call_tool("public_submit_registration", {
                "account": account_id,
                "code": portal_code,
                "external_id": registration_id,
                "commit": commit
            })

            submission_data = result.content[0].text
            return {
                "success": True,
                "return_reference": submission_data.get("return_reference"),
                "tracking_info": submission_data
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

# Complete workflow example
async def process_customer_return():
    """Example: Complete return processing workflow."""

    processor = ReturnProcessor()

    # Customer return request
    order_ref = "PL-2024-001234"
    customer_email = "customer@example.com"
    account_id = 12345
    portal_code = "main_return_portal"

    # Step 1: Initiate return
    init_result = await processor.initiate_return(
        order_ref, customer_email, account_id, portal_code
    )

    if not init_result["success"]:
        print(f"Failed to initiate return: {init_result['error']}")
        return

    registration_id = init_result["registration_id"]
    print(f"Return registration created: {registration_id}")

    # Step 2: Get returnable items
    items_result = await processor.get_returnable_items(
        registration_id, account_id, portal_code
    )

    if items_result["success"]:
        print(f"Available items for return: {len(items_result['articles'])}")

    # Step 3: Select items to return
    selected_articles = [
        {
            "id": "article_123",
            "selected_quantity": 1,
            "reason": "Size too small"
        }
    ]

    select_result = await processor.select_return_items(
        registration_id, account_id, portal_code, selected_articles
    )

    if select_result["success"]:
        print("Items selected for return")

    # Step 4: Get return options
    options_result = await processor.get_return_options(
        registration_id, account_id, portal_code
    )

    if options_result["success"]:
        print(f"Return options: {len(options_result['courier_options'])} courier, "
              f"{len(options_result['dropoff_options'])} drop-off")

    # Step 5: Select return method (auto-select free option)
    if options_result["success"] and options_result["courier_options"]:
        free_option = next(
            (opt for opt in options_result["courier_options"] if opt.get("cost") == "€0.00"),
            options_result["courier_options"][0]
        )

        method_result = await processor.select_return_method(
            registration_id, account_id, portal_code,
            {"type": "courier", "id": free_option["id"]}
        )

        if method_result["success"]:
            print(f"Selected return method: {free_option['name']}")

    # Step 6: Submit return
    submit_result = await processor.submit_return(
        registration_id, account_id, portal_code
    )

    if submit_result["success"]:
        print(f"Return submitted successfully! Reference: {submit_result['return_reference']}")
        return submit_result
    else:
        print(f"Failed to submit return: {submit_result['error']}")

# Run the example
if __name__ == "__main__":
    asyncio.run(process_customer_return())
```

---

## Technical Reference

### Tool Specifications

#### Order Information Tools

##### `public_order_info`

- **Endpoint**: `GET /v4/track/orders/info/`
- **Required Scope**: `mcp:preview` OR `track:orderinfo`
- **Primary Lookup Methods** (choose one):
  1. **Order Number**: `order_number` (string) + `account` (int) + optional `client` (string)
  2. **External Order ID**: `external_order_id` (string) + `account` (int)
  3. **External Reference**: `external_reference` (string) + `account` (int)
  4. **Tracking Number**: `tracking_number` (string) + `courier` (string) + optional `account` (int)
  5. **Customer Number**: `customer_number` (string) + `account` (int)
  6. **Recipient Email**: `recipient_email` (string) + `account` (int)
- **Optional Parameters** (for all lookup methods):
  - `postal_code` (string): Recipient's postal code for verification
  - `recipient_email` (string): Recipient's email for secondary verification
- **Returns**: Order status object with tracking information

#### Return Registration Tools

##### `public_lookup_order`

- **Endpoint**: `POST /v4/returns/return-registrations/lookup-order/`
- **Required Scope**: `mcp:full` AND `returns:registration`
- **Parameters**:
  - `account` (int): Account ID
  - `code` (string): Return portal configuration code
  - `reference` (string): Order reference number
  - `identifier` (string): Customer email or identifier
- **Returns**: Registration object with `external_id`

##### `public_registration_get_article_selection`

- **Endpoint**: `GET /v4/returns/return-registrations/{external_id}/article-info/`
- **Required Scope**: `mcp:full` AND `returns:registration`
- **Parameters**:
  - `account` (int): Account ID
  - `code` (string): Return portal configuration code
  - `external_id` (string): Registration ID from lookup
- **Returns**: Available articles and current selection

##### `public_registration_update_article_selection`

- **Endpoint**: `PATCH /v4/returns/return-registrations/{external_id}/article-info/`
- **Required Scope**: `mcp:full` AND `returns:registration`
- **Parameters**:
  - `account` (int): Account ID
  - `code` (string): Return portal configuration code
  - `external_id` (string): Registration ID
  - `articles` (array): Selected articles with quantities and reasons
- **Returns**: Updated article selection

##### `public_registration_get_options`

- **Endpoint**: `GET /v4/returns/return-registrations/{external_id}/return-options/`
- **Required Scope**: `mcp:full` AND `returns:registration`
- **Parameters**:
  - `account` (int): Account ID
  - `code` (string): Return portal configuration code
  - `external_id` (string): Registration ID
- **Returns**: Available courier and drop-off options

##### `public_registration_select_option`

- **Endpoint**: `POST /v4/returns/return-registrations/{external_id}/return-options/`
- **Required Scope**: `mcp:full` AND `returns:registration`
- **Parameters**:
  - `account` (int): Account ID
  - `code` (string): Return portal configuration code
  - `external_id` (string): Registration ID
  - `selected_option` (object): Chosen return method
- **Returns**: Confirmation of selected option

##### `public_submit_registration`

- **Endpoint**: `POST /v4/returns/return-registrations/{external_id}/submit/`
- **Required Scope**: `mcp:full` AND `returns:registration`
- **Parameters**:
  - `account` (int): Account ID
  - `code` (string): Return portal configuration code
  - `external_id` (string): Registration ID
  - `commit` (boolean, optional): Whether to finalize submission (default: true)
- **Returns**: Final registration status and tracking information

### Error Handling

Standard HTTP status codes are returned:

- **200 OK**: Successful operation
- **400 Bad Request**: Invalid parameters or request format
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions for requested scope
- **404 Not Found**: Resource not found (order, registration, etc.)
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server-side error

### Rate Limits

The public beta has the following rate limits:

- **Order Info**: 100 requests per minute per account
- **Return Registration**: 50 operations per minute per account

---

## Developer Integration Patterns

### Multi-Agent E-commerce System with CrewAI

```python
from crewai import Agent, Task, Crew, Process
from crewai_tools import MCPServerAdapter
import asyncio
from mcp_server.docs.snippets.oauth_client import acquire_access_token

# Acquire OAuth access token via dynamic client registration
access_token = asyncio.run(
    acquire_access_token(
        server_url="https://agents.parcellab.com/mcp/",
        issuer_url="https://agents.parcellab.com",
        scope="mcp:full returns:registration track:orderinfo",
    )
)
server_params = {
    "url": "https://agents.parcellab.com/mcp/",
    "transport": "streamable-http",
    "headers": {"Authorization": f"Bearer {access_token}"},
}

pl_tools_adapter = MCPServerAdapter(server_params)
pl_tools = list(pl_tools_adapter)  # enumerate immediately if you need names

# Create specialized agents
logistics_agent = Agent(
    role='Logistics Specialist',
    goal='Track orders and handle shipping inquiries efficiently',
    backstory='Expert in package tracking and delivery logistics',
    tools=pl_tools
)

returns_agent = Agent(
    role='Returns Specialist',
    goal='Process return requests and guide customers through return workflow',
    backstory='Specialist in return processing and customer satisfaction',
    tools=pl_tools
)

customer_service_agent = Agent(
    role='Customer Service Manager',
    goal='Coordinate logistics and returns teams to resolve customer issues',
    backstory='Experienced manager who orchestrates complex customer service workflows'
)

# Define workflow tasks
def create_customer_service_workflow(customer_inquiry: str):
    """Create a multi-agent workflow for customer service."""

    track_task = Task(
        description=f'Track the order mentioned in: {customer_inquiry}',
        agent=logistics_agent,
        expected_output='Order status with tracking details'
    )

    returns_task = Task(
        description=f'If customer wants to return items, process: {customer_inquiry}',
        agent=returns_agent,
        expected_output='Return registration details or guidance',
        context=[track_task]  # Use tracking info as context
    )

    coordination_task = Task(
        description='Coordinate response and provide comprehensive customer service',
        agent=customer_service_agent,
        expected_output='Complete customer service response',
        context=[track_task, returns_task]
    )

    crew = Crew(
        agents=[logistics_agent, returns_agent, customer_service_agent],
        tasks=[track_task, returns_task, coordination_task],
        verbose=2
    )

    return crew.kickoff()

# Usage
async def handle_customer_inquiry():
    inquiry = "I need to track order PL-2024-001234 and possibly return one item"
    response = create_customer_service_workflow(inquiry)
    print(f"Customer Service Response: {response}")
```

## Beta Program & Support

### Contact & Feedback

**Beta Support**: [engineering@parcellab.com](mailto:engineering@parcellab.com)

We welcome feedback on:

- Tool functionality and ease of use
- Documentation clarity and completeness
- Integration challenges
- Feature requests for production release

### Request Additional Capabilities

The public beta focuses on essential customer-facing tools. Additional capabilities are available on request:

- **Internal Analytics**: Data warehouse access and reporting
- **Advanced Configuration**: Journey management and campaign tools
- **System Integration**: Carrier APIs and webhook management
- **Support Tools**: Ticket management and knowledge base access

**To request preview access**: Email [engineering@parcellab.com](mailto:engineering@parcellab.com) with your use case.

### Production Migration

We can help migrate beta integrations to production:

- Access to production endpoints
- Guidance for adapting existing integrations
- Support during rollout

### Additional Resources

- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **parcelLab Platform**: [parcellab.com](https://parcellab.com/)
- **API Documentation**: Available with beta access credentials
- **Developer Community**: Join our beta Slack channel

---

## What's Next?

The public beta focuses on order tracking and return registration. Additional tools and endpoints may be added over time.

For access credentials or questions, contact [engineering@parcellab.com](mailto:engineering@parcellab.com).

---
