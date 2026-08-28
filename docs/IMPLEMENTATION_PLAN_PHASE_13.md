# Phase 13: Frontend Implementation Plan

## 1. Overview
This phase builds the React + TypeScript + Vite + TailwindCSS frontend for NEXORA. It is NOT a generic CRUD dashboard; it is an "agreement layer for AI commerce" where the core principle is:
> **LLMs PROPOSE. DETERMINISTIC SYSTEMS DECIDE.**

## 2. Frontend Architecture
- **Tech Stack**: React, TypeScript, Vite, TailwindCSS (for utility-first, premium dark-mode styling).
- **State Management**: React Hooks (e.g., `useState`, `useEffect`) and lightweight Context for global settings. We will avoid complex global state libraries (like Redux) to maintain simplicity.
- **Component Architecture**: Reusable, modular components separated into logical features (`agent`, `negotiation`, `policy`, `agreement`, `approval`, `audit`, `payment`).

## 3. Pages
1. **Buyer Console (`BuyerPage.tsx`)**: Natural-language procurement input, rendering an Agent Activity Panel and a real-time Negotiation Timeline.
2. **Negotiation Detail (`NegotiationDetail.tsx`)**: Deep dive into the AI-to-AI timeline. Specifically highlights the `DecisionBoundary` (the deterministic policy checks against the LLM's proposals).
3. **Merchant Dashboard (`MerchantDashboard.tsx`)**: Command center displaying metrics, active negotiations, and a dedicated queue for Pending Approvals.
4. **Agreement Detail (`AgreementDetail.tsx`)**: An immutable digital contract view. Displays deterministic totals, inventory reservations, and handles Razorpay checkout.
5. **Audit Trail (`AuditPage.tsx`)**: An append-only, filterable event timeline proving that nothing happens invisibly.

## 4. Components
- **`DecisionBoundary.tsx`**: A critical visual component demonstrating the LLM proposing vs. the Policy Engine evaluating (ALLOW / REVIEW / DENY).
- **`NegotiationTimeline.tsx`**: Chronological display of agent messages, distinguishing between Buyer and Merchant.
- **`ApprovalCard.tsx`**: High-visibility card for human escalation (e.g., when transactions exceed the autonomous limit).
- **`AppShell.tsx` & `Sidebar.tsx`**: Core layout elements.

## 5. API Mapping & Typed Client
We will create a centralized typed API client (`frontend/src/api/client.ts`) using `fetch` or `axios`.
- **Buyers**: `api.buyers.runAgent(intent)`
- **Merchants**: `api.merchants.runAgent(negotiationId)`
- **Approvals**: `api.approvals.list()`, `api.approvals.approve(id)`, `api.approvals.reject(id)`
- **Payments**: `api.payments.initiate(agreementId)`
- **Audit**: `api.audit.list(filters)`

*Critical Rule*: Frontend money values are strictly for presentation (e.g., formatting `"1150000.00"` as `₹11,50,000.00`). No authoritative math will happen in JS.

## 6. Polling Strategy
Since WebSocket support isn't mandated by the backend yet, we will use robust polling hooks (e.g., `useNegotiationPolling.ts`).
- **Interval**: 2 seconds.
- **Lifecycle**: Stops polling when the resource reaches a terminal state (e.g., `ACCEPTED`, `REJECTED`, `EXPIRED`).
- **Cleanup**: Clears intervals on unmount to prevent memory leaks.

## 7. Error Handling & Loading States
- **Errors**: Meaningful, graceful error states (e.g., "Payment could not be initiated" instead of raw stack traces). API errors will map directly to UI alerts.
- **Loading**: Skeletons for full-page loads; inline spinners for agent processing ("Connecting to Buyer Agent...", "Validating agreement...").
- **Empty States**: Clear instructions when no data is present (e.g., "No active negotiations").

## 8. Design System
- **Theme**: Premium Dark Mode. Near-black backgrounds (e.g., `bg-slate-950`), subtle glassmorphism (`backdrop-blur-md bg-white/5`), thin borders (`border-slate-800`), and electric blue accents (`text-blue-500`).
- **Typography**: Clean, readable fonts (e.g., Inter) with monospace for financial data.
- **Visuals**: Professional and developer-focused. No generic SaaS aesthetics or cartoonish AI imagery.

## 9. Security
- The backend remains the sole authority.
- The frontend will **never** expose `RAZORPAY_KEY_SECRET` or bypass the `PolicyEngine`.
- Razorpay payments will securely pass the `order_id` to the frontend checkout script; success is confirmed via the backend webhook, not the frontend callback.

## 10. Testing & Build Strategy
- **Framework**: Vitest + React Testing Library.
- **Coverage**: Rendering the Buyer page, API error display, negotiation timeline, policy status, approval flow, and payment initiation.
- **Validation**: Ensure `npm run build`, `npm run lint`, and `npm test` pass flawlessly without breaking the existing backend `pytest` suite.
