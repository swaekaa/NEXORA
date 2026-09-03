import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.orchestrator import run_negotiation_loop
from app.models.negotiation import NegotiationState
from app.models.negotiation_message import SenderType, MessageType
from app.agents.buyer.schemas import BuyerIntent

# Note: For full integration, we patch the agent runners to simulate deterministic responses
# since we are testing the orchestrator loop, not the LLM behavior here.

@pytest.mark.asyncio
async def test_negotiation_loop_progresses_buyer():
    """
    Simulate:
    Message 1: Buyer Offer 13500
    Message 2: Merchant Counter 14500
    
    Assert that the orchestrator invokes the buyer agent successfully and 
    continues the loop.
    """
    negotiation_id = uuid.uuid4()
    intent = BuyerIntent(
        buyer_id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        negotiation_id=negotiation_id,
        product_query="Monitor",
        quantity=10,
        maximum_budget=Decimal("450000")
    )
    
    # We mock the DB and agent calls to simulate the progress 
    # without depending on real LLM calls and DB setup for this narrow test.
    with patch("app.services.orchestrator.get_negotiation") as mock_get_neg, \
         patch("app.services.orchestrator.get_negotiation_messages") as mock_get_msgs, \
         patch("app.services.orchestrator.run_buyer_agent") as mock_run_buyer, \
         patch("app.services.orchestrator.run_merchant_agent") as mock_run_merchant:
        
        # Setup mock DB state
        mock_neg = AsyncMock()
        mock_neg.state = NegotiationState.COUNTER_OFFER.value
        mock_neg.round_count = 1
        mock_get_neg.return_value = mock_neg
        
        # Setup mock messages
        msg1 = AsyncMock()
        msg1.id = 1
        msg1.sender_type = SenderType.BUYER_AGENT.value
        
        msg2 = AsyncMock()
        msg2.id = 2
        msg2.sender_type = SenderType.MERCHANT_AGENT.value
        
        mock_get_msgs.side_effect = [
            [msg1, msg2], # Turn 1 check (Last sender is merchant)
            [msg1, msg2, AsyncMock(id=3)], # After Buyer runs (New message persisted)
            [msg1, msg2, AsyncMock(id=3)]  # Next loop iteration
        ]
        
        mock_run_buyer.return_value = {"status": "completed"}
        
        # To prevent infinite loop in test, we'll raise an Exception on the second iteration
        mock_run_merchant.side_effect = Exception("Stop Loop")
        
        try:
            await run_negotiation_loop(negotiation_id, intent)
        except Exception as e:
            assert str(e) == "Stop Loop"
            
        # Assert the Buyer Agent was called because the last message was from the Merchant
        mock_run_buyer.assert_called_once()
