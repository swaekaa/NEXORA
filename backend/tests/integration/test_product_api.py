"""
Phase 3 Integration Tests — Product API

Tests the full HTTP → Service → PostgreSQL stack for the product catalog.

KEY DESIGN:
  The `db` fixture in Phase 2 tests worked because tests operated on the
  session DIRECTLY (no HTTP layer). For API tests, the HTTP client uses a
  SEPARATE session managed by FastAPI's get_db dependency. Uncommitted data
  from the test fixture's session is NOT visible to the app session.

  Solution: _create_merchant_in_db commits the merchant immediately.
  A module-level cleanup fixture deletes all created merchants after each test.

Coverage:
  - CRUD lifecycle (create, list, get, update, delete)
  - Input validation (price, inventory, currency, status, SKU)
  - Merchant ownership isolation (cross-merchant access blocked)
  - Duplicate SKU handling (409 conflict + session recovery)
  - Decimal precision preservation through the full stack
  - Soft-delete behaviour (status → inactive)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

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
    Products/policies cascade-delete with the merchant.
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
    can see it. Tracks the merchant ID for post-test cleanup.
    """
    async with AsyncSessionLocal() as session:
        m = Merchant(
            name=f"Test Merchant {suffix}",
            email=f"merchant_{uuid.uuid4().hex[:8]}@prod.test.nexora.ai",
            status=MerchantStatus.ACTIVE,
        )
        session.add(m)
        await session.commit()
        await session.refresh(m)
        _cleanup_merchant_ids.append(m.id)
        return m


def _product_payload(
    sku: str = "SKU-001",
    price: str = "1000.00",
    inventory: int = 10,
    currency: str = "INR",
) -> dict:
    return {
        "name": "Test Product",
        "description": "Integration test product",
        "sku": sku,
        "price": price,
        "currency": currency,
        "inventory": inventory,
        "status": "active",
    }


# ── CREATE ────────────────────────────────────────────────────────────────────

class TestCreateProduct:
    async def test_create_product_success(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("create_success")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "SKU-001"
        assert data["price"] == "1000.00"
        assert data["currency"] == "INR"
        assert data["inventory"] == 10
        assert data["status"] == "active"
        assert data["merchant_id"] == str(merchant.id)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_product_returns_201(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("status_201")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SKU-201"),
        )
        assert response.status_code == 201

    async def test_create_product_for_nonexistent_merchant(self, client: AsyncClient):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/merchants/{fake_id}/products",
            json=_product_payload(),
        )
        assert response.status_code == 404
        assert "NOT_FOUND" in response.json()["error"]

    async def test_create_product_invalid_price_zero(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("zero_price")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(price="0.00"),
        )
        assert response.status_code == 422

    async def test_create_product_negative_price(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("neg_price")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(price="-100.00"),
        )
        assert response.status_code == 422

    async def test_create_product_negative_inventory(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("neg_inv")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(inventory=-1),
        )
        assert response.status_code == 422

    async def test_create_product_invalid_currency_length(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("bad_curr")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(currency="US"),
        )
        assert response.status_code == 422

    async def test_create_product_invalid_currency_non_alpha(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("num_curr")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(currency="1N2"),
        )
        assert response.status_code == 422

    async def test_create_product_currency_lowercased_accepted(self, client: AsyncClient):
        """Currency 'inr' should be normalised to 'INR'."""
        merchant = await _create_merchant_in_db("lower_curr")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SKU-CURR", currency="inr"),
        )
        assert response.status_code == 201
        assert response.json()["currency"] == "INR"

    async def test_create_product_invalid_status(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("bad_status")
        payload = _product_payload()
        payload["status"] = "invalid_status"
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=payload,
        )
        assert response.status_code == 422

    async def test_create_product_decimal_preserved(self, client: AsyncClient):
        """Verify Decimal precision is preserved through the full stack."""
        merchant = await _create_merchant_in_db("decimal")
        response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SKU-DEC", price="10800.10"),
        )
        assert response.status_code == 201
        assert response.json()["price"] == "10800.10"


# ── DUPLICATE SKU ─────────────────────────────────────────────────────────────

class TestDuplicateSKU:
    async def test_duplicate_sku_same_merchant_rejected(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("dup_sku")
        r1 = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="DUP-SKU-001"),
        )
        assert r1.status_code == 201

        r2 = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="DUP-SKU-001"),
        )
        assert r2.status_code == 409
        assert "DUPLICATE" in r2.json()["error"]

    async def test_same_sku_different_merchant_allowed(self, client: AsyncClient):
        """SKU uniqueness is per-merchant, not global."""
        merchant_a = await _create_merchant_in_db("sku_a")
        merchant_b = await _create_merchant_in_db("sku_b")

        r1 = await client.post(
            f"/api/v1/merchants/{merchant_a.id}/products",
            json=_product_payload(sku="SHARED-SKU"),
        )
        r2 = await client.post(
            f"/api/v1/merchants/{merchant_b.id}/products",
            json=_product_payload(sku="SHARED-SKU"),
        )
        assert r1.status_code == 201
        assert r2.status_code == 201

    async def test_session_usable_after_conflict(self, client: AsyncClient):
        """
        A failed 409 must not leave the DB session in a broken state.
        A subsequent valid request must succeed.
        """
        merchant = await _create_merchant_in_db("session_recovery")
        await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SESSION-SKU-001"),
        )
        r_conflict = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SESSION-SKU-001"),
        )
        assert r_conflict.status_code == 409

        # Subsequent valid request must succeed
        r_ok = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SESSION-SKU-002"),
        )
        assert r_ok.status_code == 201


# ── LIST ──────────────────────────────────────────────────────────────────────

class TestListProducts:
    async def test_list_products_empty(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("empty_list")
        response = await client.get(f"/api/v1/merchants/{merchant.id}/products")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_products_returns_own_products(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("list_own")
        await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="LIST-001"),
        )
        await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="LIST-002"),
        )
        response = await client.get(f"/api/v1/merchants/{merchant.id}/products")
        assert response.status_code == 200
        assert response.json()["total"] == 2

    async def test_list_products_isolation(self, client: AsyncClient):
        """Products from merchant B must NOT appear in merchant A's list."""
        merchant_a = await _create_merchant_in_db("iso_a")
        merchant_b = await _create_merchant_in_db("iso_b")

        await client.post(
            f"/api/v1/merchants/{merchant_a.id}/products",
            json=_product_payload(sku="A-PROD"),
        )
        await client.post(
            f"/api/v1/merchants/{merchant_b.id}/products",
            json=_product_payload(sku="B-PROD"),
        )

        response = await client.get(f"/api/v1/merchants/{merchant_a.id}/products")
        assert response.status_code == 200
        skus = [p["sku"] for p in response.json()["items"]]
        assert "A-PROD" in skus
        assert "B-PROD" not in skus

    async def test_list_products_nonexistent_merchant(self, client: AsyncClient):
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/merchants/{fake_id}/products")
        assert response.status_code == 404


# ── GET ───────────────────────────────────────────────────────────────────────

class TestGetProduct:
    async def test_get_product_success(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("get_success")
        create_response = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="GET-001"),
        )
        product_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/merchants/{merchant.id}/products/{product_id}")
        assert response.status_code == 200
        assert response.json()["id"] == product_id

    async def test_get_nonexistent_product(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("get_404")
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/merchants/{merchant.id}/products/{fake_id}")
        assert response.status_code == 404

    async def test_get_product_cross_merchant_blocked(self, client: AsyncClient):
        """
        CRITICAL: Merchant A must not access Merchant B's product by UUID.
        Must return 404 (not 403) to avoid leaking resource existence.
        """
        merchant_a = await _create_merchant_in_db("cross_a")
        merchant_b = await _create_merchant_in_db("cross_b")

        create_r = await client.post(
            f"/api/v1/merchants/{merchant_b.id}/products",
            json=_product_payload(sku="B-SECRET"),
        )
        product_b_id = create_r.json()["id"]

        response = await client.get(
            f"/api/v1/merchants/{merchant_a.id}/products/{product_b_id}"
        )
        assert response.status_code == 404


# ── UPDATE ────────────────────────────────────────────────────────────────────

class TestUpdateProduct:
    async def test_update_product_price(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("update_price")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="UPD-001"),
        )
        product_id = create_r.json()["id"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}",
            json={"price": "1500.50"},
        )
        assert response.status_code == 200
        assert response.json()["price"] == "1500.50"

    async def test_partial_update_only_changes_provided_fields(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("partial_upd")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="PART-001", inventory=20),
        )
        product_id = create_r.json()["id"]
        original_sku = create_r.json()["sku"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}",
            json={"inventory": 99},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["inventory"] == 99
        assert data["sku"] == original_sku  # unchanged

    async def test_update_sku_success(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("sku_change")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="OLD-SKU"),
        )
        product_id = create_r.json()["id"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}",
            json={"sku": "NEW-SKU"},
        )
        assert response.status_code == 200
        assert response.json()["sku"] == "NEW-SKU"

    async def test_update_sku_to_duplicate_rejected(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("sku_dup_upd")
        await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="EXISTING-SKU"),
        )
        create_r2 = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="OTHER-SKU"),
        )
        product2_id = create_r2.json()["id"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{product2_id}",
            json={"sku": "EXISTING-SKU"},
        )
        assert response.status_code == 409

    async def test_update_invalid_price(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("bad_price_upd")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="PRICE-UPD-001"),
        )
        product_id = create_r.json()["id"]

        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}",
            json={"price": "-500.00"},
        )
        assert response.status_code == 422

    async def test_update_nonexistent_product(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("upd_404")
        fake_id = uuid.uuid4()
        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{fake_id}",
            json={"price": "999.00"},
        )
        assert response.status_code == 404

    async def test_update_decimal_precision(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("dec_upd")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="DEC-UPD-001"),
        )
        product_id = create_r.json()["id"]
        response = await client.patch(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}",
            json={"price": "0.10"},
        )
        assert response.status_code == 200
        assert response.json()["price"] == "0.10"


# ── DELETE (SOFT) ─────────────────────────────────────────────────────────────

class TestDeleteProduct:
    async def test_delete_product_returns_204(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("del_204")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="DEL-001"),
        )
        product_id = create_r.json()["id"]

        response = await client.delete(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}"
        )
        assert response.status_code == 204

    async def test_deleted_product_is_inactive(self, client: AsyncClient):
        """After DELETE, product status becomes 'inactive' (soft delete)."""
        merchant = await _create_merchant_in_db("del_inactive")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant.id}/products",
            json=_product_payload(sku="SOFT-DEL-001"),
        )
        product_id = create_r.json()["id"]

        await client.delete(f"/api/v1/merchants/{merchant.id}/products/{product_id}")

        # Product still retrievable but inactive
        get_r = await client.get(
            f"/api/v1/merchants/{merchant.id}/products/{product_id}"
        )
        assert get_r.status_code == 200
        assert get_r.json()["status"] == "inactive"

    async def test_delete_nonexistent_product(self, client: AsyncClient):
        merchant = await _create_merchant_in_db("del_404")
        fake_id = uuid.uuid4()
        response = await client.delete(
            f"/api/v1/merchants/{merchant.id}/products/{fake_id}"
        )
        assert response.status_code == 404

    async def test_delete_cross_merchant_blocked(self, client: AsyncClient):
        """Cannot delete another merchant's product."""
        merchant_a = await _create_merchant_in_db("del_cross_a")
        merchant_b = await _create_merchant_in_db("del_cross_b")
        create_r = await client.post(
            f"/api/v1/merchants/{merchant_b.id}/products",
            json=_product_payload(sku="DEL-CROSS"),
        )
        product_b_id = create_r.json()["id"]

        response = await client.delete(
            f"/api/v1/merchants/{merchant_a.id}/products/{product_b_id}"
        )
        assert response.status_code == 404


# ── CROSS-MERCHANT ISOLATION ──────────────────────────────────────────────────

class TestCrossMerchantIsolation:
    async def test_full_isolation_scenario(self, client: AsyncClient):
        """
        Critical isolation test:
        - Create Merchant A and Merchant B
        - Create products for both
        - Verify GET list for A only shows A's products
        - Verify GET/PATCH/DELETE via A's URL for B's product → 404
        """
        merchant_a = await _create_merchant_in_db("full_iso_a")
        merchant_b = await _create_merchant_in_db("full_iso_b")

        await client.post(f"/api/v1/merchants/{merchant_a.id}/products", json=_product_payload(sku="A-1"))
        await client.post(f"/api/v1/merchants/{merchant_a.id}/products", json=_product_payload(sku="A-2"))
        r_b = await client.post(f"/api/v1/merchants/{merchant_b.id}/products", json=_product_payload(sku="B-1"))
        product_b_id = r_b.json()["id"]

        # A's list has 2 items, B's product not in it
        list_a = await client.get(f"/api/v1/merchants/{merchant_a.id}/products")
        assert list_a.json()["total"] == 2
        assert "B-1" not in [p["sku"] for p in list_a.json()["items"]]

        # GET B's product via A → 404
        assert (await client.get(f"/api/v1/merchants/{merchant_a.id}/products/{product_b_id}")).status_code == 404
        # PATCH B's product via A → 404
        assert (await client.patch(f"/api/v1/merchants/{merchant_a.id}/products/{product_b_id}", json={"price": "1.00"})).status_code == 404
        # DELETE B's product via A → 404
        assert (await client.delete(f"/api/v1/merchants/{merchant_a.id}/products/{product_b_id}")).status_code == 404
