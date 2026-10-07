import sys
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from mcp.server import MCPServer
from mcp.server.elicitation import ElicitationResult
from mcp.server.mcpserver import Elicit, Resolve

mcp = MCPServer("product server")

def log(msg: str) -> None:
    """Narrate to STDERR (stdout is reserved for the MCP protocol)."""
    print(f"[SERVER] {msg}", file=sys.stderr, flush=True)

# The form the user will see. MCPServer turns this Pydantic model into the
# requestedSchema of the elicitation/create request (flat, primitive fields only).

class LaunchConfirmation(BaseModel):
    confirmLaunch: bool = Field(description="Confirm you want to launch this product")
    price: float = Field(default=29.99, ge=0, description="Retail price (USD)")
    initialStock: int = Field(default=100, ge=0, description="Initial stock quantity")
    shippingSpeed: Literal["standard", "priority", "overnight"] = Field(default="standard", description="Shipping speed to offer at launch")

# A resolver: says WHAT to ask. It can read tool arguments by name.
def ask_launch_details(product_name: str) -> Elicit[LaunchConfirmation]:
    log(f"asking the user to confirm launch details for '{product_name}'")
    return Elicit(f"Please confirm launch details for '{product_name}':", LaunchConfirmation)

@mcp.tool()
async def launch_product(
    product_name: str,
    answer: Annotated[ElicitationResult[LaunchConfirmation], Resolve(ask_launch_details)],
) -> str:
    """Launch a product, confirming pricing and inventory with the user first."""
    # By the time the body runs, the SDK has already asked the user
    # (input_required -> client retry) and injected the outcome here.
    if answer.action == "accept":
        data = answer.data
        if not data.confirmLaunch:
            return "Launch not confirmed by user."
        log("user accepted, finalizing launch")
        return (
            f"Launched {product_name}! Price: ${data.price:.2f}, "
            f"Initial stock: {data.initialStock}, Shipping: {data.shippingSpeed}."
        )
    if answer.action == "decline":
        return "User declined to provide launch details."
    return "User cancelled the launch flow."

if __name__ == "__main__":
    log("product-server starting on stdio...")
    mcp.run()  # stdio transport by default
