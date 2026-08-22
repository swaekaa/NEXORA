"""
NEXORA — Pydantic Schemas
All LLM tool inputs/outputs validated against these schemas.
All monetary fields use Decimal — never float.
"""
# TODO (Phase 2+): Implement schemas
# Schemas to implement:
#   - MerchantSchema, MerchantPolicySchema, BulkDiscountTier
#   - BuyerSchema, BuyerPolicySchema
#   - ProductSchema
#   - NegotiationSchema, NegotiationMessageSchema
#   - CommercialAgreement, AgreementStatus
#   - PolicyResult, PolicyCheck, PolicyDecision
#   - Buyer tools: DiscoverProductsTool, SubmitBuyRequestTool, SubmitCounterOfferTool, AcceptOfferTool, RejectOfferTool
#   - Merchant tools: EvaluateBuyRequestTool, GenerateOfferTool, RequestHumanApprovalTool, RejectBuyRequestTool
#   - PaymentSchema, PaymentAuthorizationResult
#   - AuditEvent, AuditAction, AgentType
#   - ApprovalRequestSchema
