"""
Phase 3 Integration Tests — Policy API

Tests the full HTTP → Service → PostgreSQL stack for the policy catalog.

KEY DESIGN:
  Merchants must be COMMITTED before the HTTP client can see them.
  The test helper _create_merchant_in_db uses its own session and commits.
  An autouse cleanup fixture deletes all created merchants after each test
  (cascade-deletes their policies too).

Coverage:
  - CRUD lifecycle (create, list, get, update, delete)
  - Financial validation (minimum_price, max_discount_percent, max_autonomous)
  - One-active-policy-per-merchant rule enforcement
  - Merchant ownership isolation (cross-merchant access blocked)
  - Decimal precision preservation through the full stack
  - Hard-delete vs soft-deactivate behavior
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal
from app.models.merchant import Merchant, MerchantStatus


# ── Cleanup Tracking ──────────────────────────────────────────────────────────

_cleanup_merchant_ids: list[uuid.UUID] = []


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """
    Auto-run cleanup after every test in this file.
    Deletes all merchants created via _create_merchant_in_db.
    Policies cascade-delete with the merchant.
    """
    _cleanup_merchant_ids.clear()
    yield
    if _cleanup_merchant_ids:
        async with AsyncSessionLocal() as session:
            for merchant_id in _cleanup_merchant_ids:
                result = await session.execute(
                    sa.select(Merchant).where(Merchant.id == merchant_id)
                )
                merchant = result.scalar_one_or_none()
                if merchant:
                    await session.delete(merchant)
            await session.commit()
        _cleanup_merchant_ids.clear()


# ── Shared Helpers ────────────────────────────────────────────────────────────

async def _create_merchant_in_db(suffix: str = "") -> Merchant:
    """
    Create and COMMIT a merchant so the FastAPI HTTP client's separate session
    can see it. Tracks merchant ID for post-test cleanup.
    """
    async with AsyncSessionLocal() as session:
        m = Merchant(
            name=f"Policy Test Merchant {suffix}",
            email=f"policy_merchant_{uuid.uuid4().hex[:8]}@pol.test.nexora.ai",
            status=MerchantStatus.ACTIVE,
        )
        session.add(m)
        await session.commit()
        await session.refresh(m)
        _cleanup_merchant_ids.append(m.id)
        return m


def _policy_payload(
    name: str = "Default Policy",
    minimum_price: str = "40000.00",
    max_discount: str = "10.00",
    max_autonomous: str = "500000.00",
    is_active: bool = True,
) -> dict:
    return {
        "name": name,
        "minimum_price": minimum_price,
        "maximum_discount_percent": max_discount,
        "maximum_autonomous_transaction": max_autonomous,
        "human_approval_required": False,
        "is_active": is_active,
        "max_negotiation_rounds": 10,
        "max_delivery_days": 7,
        "min_warranty_months": 12,
    }


# ── CREATE ────────────────────────────────────────────────────────────────────

class TestCreatePolicy:
    async def test_create_policy_success(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("create_ok")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Default Policy"
        assert data["minimum_price"] == "40000.00"
        assert data["maximum_discount_percent"] == "10.00"
        assert data["maximum_autonomous_transaction"] == "500000.00"
        assert data["is_active"] is True
        assert data["merchant_id"] == str(merchant.id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_policy_for_nonexistent_merchant(self, client: AsyncClient):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/merchants/{fake_id}/policies",
            json=_policy_payload(),
        )
        assert response.status_code == 404

    async def test_create_policy_invalid_negative_minimum_price(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("neg_min_price")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(minimum_price="-100.00"),
        )
        assert response.status_code == 422

    async def test_create_policy_zero_minimum_price(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("zero_min_price")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(minimum_price="0.00"),
        )
        assert response.status_code == 422

    async def test_create_policy_discount_above_100(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("disc_101")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(max_discount="101.00"),
        )
        assert response.status_code == 422

    async def test_create_policy_negative_discount(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("neg_disc")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(max_discount="-1.00"),
        )
        assert response.status_code == 422

    async def test_create_policy_zero_discount_accepted(self, client: AsyncClient):
        """0% discount is valid — means no discount allowed."""
        merchant = await _create_merchant_in_db("zero_disc")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(max_discount="0.00"),
        )
        assert response.status_code == 201
        assert response.json()["maximum_discount_percent"] == "0.00"

    async def test_create_policy_100_discount_accepted(self, client: AsyncClient):
        """100% is valid upper boundary."""
        merchant = await _create_merchant_in_db("full_disc")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(max_discount="100.00"),
        )
        assert response.status_code == 201

    async def test_create_policy_zero_autonomous_transaction(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("zero_auto")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(max_autonomous="0.00"),
        )
        assert response.status_code == 422

    async def test_create_policy_negative_autonomous_transaction(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("neg_auto")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(max_autonomous="-1000.00"),
        )
        assert response.status_code == 422

    async def test_create_policy_decimal_precision_preserved(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_dec")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(minimum_price="12345.67", max_autonomous="99999.99"),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["minimum_price"] == "12345.67"
        assert data["maximum_autonomous_transaction"] == "99999.99"


# ── ONE ACTIVE POLICY RULE ────────────────────────────────────────────────────

class TestOneActivePolicyRule:
    async def test_creating_second_active_policy_deactivates_first(self, client: AsyncClient):
        """
        ONE ACTIVE POLICY PER MERCHANT rule:
        Creating a second active policy must automatically deactivate the first.
        """
        merchant = await _create_merchant_in_db("one_active")

        r1 = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(name="Policy Alpha"),
        )
        assert r1.status_code == 201
        policy1_id = r1.json()["id"]

        r2 = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(name="Policy Beta"),
        )
        assert r2.status_code == 201
        policy2_id = r2.json()["id"]

        # Policy 1 should now be inactive
        r_get1 = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy1_id}")
        assert r_get1.json()["is_active"] is False

        # Policy 2 should be active
        r_get2 = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy2_id}")
        assert r_get2.json()["is_active"] is True

    async def test_creating_inactive_policy_does_not_deactivate_existing(self, client: AsyncClient):
        """Creating an is_active=False policy must not affect existing active ones."""
        merchant = await _create_merchant_in_db("inactive_pol")

        r1 = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(name="Active Policy"),
        )
        policy1_id = r1.json()["id"]

        await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(name="Inactive Policy", is_active=False),
        )

        # Policy 1 must still be active
        r_get1 = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy1_id}")
        assert r_get1.json()["is_active"] is True

    async def test_activating_policy_via_patch_deactivates_others(self, client: AsyncClient):
        """PATCH is_active=True on an inactive policy deactivates existing active ones."""
        merchant = await _create_merchant_in_db("patch_activate")

        r1 = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(name="First Active"),
        )
        policy1_id = r1.json()["id"]

        r2 = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(name="Inactive One", is_active=False),
        )
        policy2_id = r2.json()["id"]

        # Activate policy 2
        await client.patch(
            f"/api/v1/merchants/{merchant.id}/policies/{policy2_id}",
            json={"is_active": True},
        )

        # Policy 1 now inactive
        assert (await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy1_id}")).json()["is_active"] is False
        # Policy 2 now active
        assert (await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy2_id}")).json()["is_active"] is True


# ── LIST ──────────────────────────────────────────────────────────────────────

class TestListPolicies:
    async def test_list_policies_empty(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_empty_list")
        response = await client.get(f"/api/v1/merchants/{merchant.id}/policies")
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["items"] == []

    async def test_list_policies_returns_all_statuses(self, client: AsyncClient):
        """List returns both active and inactive policies."""
        merchant = await _create_merchant_in_db("pol_all_list")
        await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload(name="P1"))
        await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload(name="P2", is_active=False))
        response = await client.get(f"/api/v1/merchants/{merchant.id}/policies")
        assert response.json()["total"] == 2

    async def test_list_policies_isolation(self, client: AsyncClient):
        """Merchant A's list must not include Merchant B's policies."""
        merchant_a = await _create_merchant_in_db("pol_iso_a")
        merchant_b = await _create_merchant_in_db("pol_iso_b")
        await client.post(f"/api/v1/merchants/{merchant_a.id}/policies", json=_policy_payload(name="A-Policy"))
        await client.post(f"/api/v1/merchants/{merchant_b.id}/policies", json=_policy_payload(name="B-Policy"))

        response = await client.get(f"/api/v1/merchants/{merchant_a.id}/policies")
        names = [p["name"] for p in response.json()["items"]]
        assert "A-Policy" in names
        assert "B-Policy" not in names

    async def test_list_policies_nonexistent_merchant(self, client: AsyncClient):
        response = await client.get(f"/api/v1/merchants/{uuid.uuid4()}/policies")
        assert response.status_code == 404


# ── GET ───────────────────────────────────────────────────────────────────────

class TestGetPolicy:
    async def test_get_policy_success(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_get_ok")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/policies",
            json=_policy_payload(),
        )
        policy_id = create_r.json()["id"]
        response = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy_id}")
        assert response.status_code == 200
        assert response.json()["id"] == policy_id

    async def test_get_nonexistent_policy(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_get_404")
        response = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_get_policy_cross_merchant_blocked(self, client: AsyncClient):
        """Merchant A must not access Merchant B's policy."""
        merchant_a = await _create_merchant_in_db("pol_cross_a")
        merchant_b = await _create_merchant_in_db("pol_cross_b")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant_b.id}/policies",
            json=_policy_payload(),
        )
        policy_b_id = create_r.json()["id"]
        response = await client.get(f"/api/v1/merchants/{merchant_a.id}/policies/{policy_b_id}")
        assert response.status_code == 404


# ── UPDATE ────────────────────────────────────────────────────────────────────

class TestUpdatePolicy:
    async def test_update_policy_name(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_upd_name")
        create_r = await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload())
        policy_id = create_r.json()["id"]
        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/policies/{policy_id}",
            json={"name": "Holiday Policy"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Holiday Policy"

    async def test_partial_update_only_changes_provided_fields(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_partial")
        create_r = await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload())
        policy_id = create_r.json()["id"]
        original_min_price = create_r.json()["minimum_price"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/policies/{policy_id}",
            json={"max_delivery_days": 14},
        )
        assert response.status_code == 200
        assert response.json()["max_delivery_days"] == 14
        assert response.json()["minimum_price"] == original_min_price

    async def test_update_policy_invalid_discount(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_inv_disc")
        create_r = await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload())
        policy_id = create_r.json()["id"]
        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/policies/{policy_id}",
            json={"maximum_discount_percent": "150.00"},
        )
        assert response.status_code == 422

    async def test_update_nonexistent_policy(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_upd_404")
        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/policies/{uuid.uuid4()}",
            json={"name": "Ghost Policy"},
        )
        assert response.status_code == 404

    async def test_update_cross_merchant_policy_blocked(self, client: AsyncClient):
        merchant_a = await _create_merchant_in_db("pol_upd_cross_a")
        merchant_b = await _create_merchant_in_db("pol_upd_cross_b")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant_b.id}/policies",
            json=_policy_payload(),
        )
        policy_b_id = create_r.json()["id"]
        response = await client.patch(
            f"/api/v1/merchants/{merchant_a.id}/policies/{policy_b_id}",
            json={"name": "Hacked"},
        )
        assert response.status_code == 404


# ── DELETE ────────────────────────────────────────────────────────────────────

class TestDeletePolicy:
    async def test_delete_policy_returns_204(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_del_204")
        create_r = await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload())
        policy_id = create_r.json()["id"]
        response = await client.delete(f"/api/v1/merchants/{merchant.id}/policies/{policy_id}")
        assert response.status_code == 204

    async def test_deleted_policy_not_retrievable(self, client: AsyncClient):
        """Hard delete: policy is gone after DELETE."""
        merchant = await _create_merchant_in_db("pol_del_gone")
        create_r = await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload())
        policy_id = create_r.json()["id"]
        await client.delete(f"/api/v1/merchants/{merchant.id}/policies/{policy_id}")
        response = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy_id}")
        assert response.status_code == 404

    async def test_delete_nonexistent_policy(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("pol_del_404")
        response = await client.delete(f"/api/v1/merchants/{merchant.id}/policies/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_deactivate_via_patch_without_deleting(self, client: AsyncClient):
        """Policy can be deactivated (is_active=False) without being deleted."""
        merchant = await _create_merchant_in_db("pol_deactivate")
        create_r = await client.post(f"/api/v1/merchants/{merchant.id}/policies", json=_policy_payload())
        policy_id = create_r.json()["id"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/policies/{policy_id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

        # Policy still exists
        get_r = await client.get(f"/api/v1/merchants/{merchant.id}/policies/{policy_id}")
        assert get_r.status_code == 200
        assert get_r.json()["is_active"] is False

    async def test_delete_cross_merchant_policy_blocked(self, client: AsyncClient):
        merchant_a = await _create_merchant_in_db("pol_del_cross_a")
        merchant_b = await _create_merchant_in_db("pol_del_cross_b")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant_b.id}/policies",
            json=_policy_payload(),
        )
        policy_b_id = create_r.json()["id"]
        response = await client.delete(f"/api/v1/merchants/{merchant_a.id}/policies/{policy_b_id}")
        assert response.status_code == 404
