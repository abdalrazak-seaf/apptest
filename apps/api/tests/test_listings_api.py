"""Posting, editing, photos and the listing lifecycle."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.enums import ListingStatus, StatusReasonCode, UserRole
from api.models.geo import City
from api.models.listing import Listing
from api.models.taxonomy import Make, Trim, VehicleModel
from api.models.user import User
from api.testing import AuthHeaders, ListingFactory, UserFactory, png_bytes

FLOOR_PRICE = 82_000


def listing_payload(
    make: Make, model: VehicleModel, city: City, **overrides: object
) -> dict[str, object]:
    payload: dict[str, object] = {
        "make_id": str(make.id),
        "model_id": str(model.id),
        "city_id": str(city.id),
        "year": 2019,
        "mileage_km": 85_000,
        "asking_price_sar": 90_000,
        "description_ar": "سيارة نظيفة، فحص كامل",
    }
    payload.update(overrides)
    return payload


class TestCreate:
    async def test_creates_a_draft_that_is_not_yet_public(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make: Make,
        vehicle_model: VehicleModel,
        city: City,
    ) -> None:
        seller: User = await make_user(role=UserRole.SELLER)
        response = await client.post(
            "/listings",
            headers=auth_headers(seller),
            json=listing_payload(make, vehicle_model, city),
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == ListingStatus.DRAFT
        assert body["seller_type"] == "private"
        # The model's body type is inherited when the seller does not pick one.
        assert body["body_type"] == "suv"
        assert body["photos"] == []

        # A draft is invisible to everyone else.
        assert (await client.get(f"/listings/{body['id']}")).status_code == 404

    async def test_requires_sign_in(
        self, client: AsyncClient, make: Make, vehicle_model: VehicleModel, city: City
    ) -> None:
        response = await client.post("/listings", json=listing_payload(make, vehicle_model, city))
        assert response.status_code == 401

    async def test_accepts_arabic_indic_digits(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make: Make,
        vehicle_model: VehicleModel,
        city: City,
    ) -> None:
        seller: User = await make_user()
        response = await client.post(
            "/listings",
            headers=auth_headers(seller),
            json=listing_payload(
                make,
                vehicle_model,
                city,
                year="٢٠١٩",
                mileage_km="٨٥٬٠٠٠",
                asking_price_sar="٩٠٬٠٠٠",
            ),
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert (body["year"], body["mileage_km"], body["asking_price_sar"]) == (
            2019,
            85_000,
            90_000,
        )

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("year", 1800),
            ("year", 2200),
            ("mileage_km", -1),
            ("asking_price_sar", 0),
            ("asking_price_sar", "abc"),
        ],
    )
    async def test_rejects_impossible_values(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make: Make,
        vehicle_model: VehicleModel,
        city: City,
        field: str,
        value: object,
    ) -> None:
        seller: User = await make_user()
        response = await client.post(
            "/listings",
            headers=auth_headers(seller),
            json=listing_payload(make, vehicle_model, city, **{field: value}),
        )
        assert response.status_code == 422

    async def test_rejects_a_model_from_another_make(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make: Make,
        vehicle_model: VehicleModel,
        city: City,
        session: AsyncSession,
    ) -> None:
        other_make = Make(slug=f"kia-{uuid.uuid4().hex[:6]}", name_ar="كيا", name_en="Kia")
        session.add(other_make)
        await session.commit()

        seller: User = await make_user()
        response = await client.post(
            "/listings",
            headers=auth_headers(seller),
            json=listing_payload(make, vehicle_model, city, make_id=str(other_make.id)),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "model_not_found"

    async def test_rejects_an_unknown_city(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make: Make,
        vehicle_model: VehicleModel,
        city: City,
    ) -> None:
        seller: User = await make_user()
        response = await client.post(
            "/listings",
            headers=auth_headers(seller),
            json=listing_payload(make, vehicle_model, city, city_id=str(uuid.uuid4())),
        )
        assert response.status_code == 404
        assert response.json()["code"] == "city_not_found"

    async def test_cannot_post_for_a_showroom_you_do_not_belong_to(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make: Make,
        vehicle_model: VehicleModel,
        city: City,
    ) -> None:
        seller: User = await make_user()
        response = await client.post(
            "/listings",
            headers=auth_headers(seller),
            json=listing_payload(make, vehicle_model, city, showroom_id=str(uuid.uuid4())),
        )
        assert response.status_code == 403
        assert response.json()["code"] == "not_showroom_staff"


class TestFloorPriceStaysPrivate:
    """The seller's walk-away price must never reach a buyer (CLAUDE.md rule)."""

    async def test_absent_from_the_public_detail_page(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, floor_price_sar=FLOOR_PRICE)

        response = await client.get(f"/listings/{listing.id}")
        assert response.status_code == 200
        assert "floor_price_sar" not in response.json()
        assert str(FLOOR_PRICE) not in response.text

    async def test_absent_when_another_signed_in_user_looks(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        buyer: User = await make_user()
        listing = await make_listing(seller=seller, floor_price_sar=FLOOR_PRICE)

        response = await client.get(f"/listings/{listing.id}", headers=auth_headers(buyer))
        assert "floor_price_sar" not in response.json()
        assert str(FLOOR_PRICE) not in response.text

    async def test_absent_from_search_results(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        await make_listing(seller=seller, floor_price_sar=FLOOR_PRICE)

        response = await client.get("/listings")
        assert str(FLOOR_PRICE) not in response.text

    async def test_visible_to_the_seller(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, floor_price_sar=FLOOR_PRICE)

        # The buyer-facing page never carries it, even for the seller...
        public = await client.get(f"/listings/{listing.id}", headers=auth_headers(seller))
        assert "floor_price_sar" not in public.json()

        # ...it is on the seller's own management view.
        response = await client.get(f"/listings/{listing.id}/manage", headers=auth_headers(seller))
        assert response.json()["floor_price_sar"] == FLOOR_PRICE

    async def test_the_manage_view_is_closed_to_others(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        stranger: User = await make_user()
        listing = await make_listing(seller=seller, floor_price_sar=FLOOR_PRICE)

        assert (await client.get(f"/listings/{listing.id}/manage")).status_code == 401
        blocked = await client.get(f"/listings/{listing.id}/manage", headers=auth_headers(stranger))
        assert blocked.status_code == 403
        assert str(FLOOR_PRICE) not in blocked.text


class TestUpdate:
    async def test_the_seller_can_edit(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT)

        response = await client.patch(
            f"/listings/{listing.id}",
            headers=auth_headers(seller),
            json={"asking_price_sar": "٨٥٬٠٠٠", "negotiable": False},
        )
        assert response.status_code == 200
        assert response.json()["asking_price_sar"] == 85_000
        assert response.json()["negotiable"] is False

    async def test_a_stranger_cannot_edit(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        stranger: User = await make_user()
        listing = await make_listing(seller=seller)

        response = await client.patch(
            f"/listings/{listing.id}",
            headers=auth_headers(stranger),
            json={"asking_price_sar": 1000},
        )
        assert response.status_code == 403

    async def test_a_sold_listing_is_frozen(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.SOLD)

        response = await client.patch(
            f"/listings/{listing.id}",
            headers=auth_headers(seller),
            json={"asking_price_sar": 1000},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "listing_not_editable"

    async def test_trim_must_belong_to_the_model(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
        trim: Trim,
        session: AsyncSession,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT)

        ok = await client.patch(
            f"/listings/{listing.id}",
            headers=auth_headers(seller),
            json={"trim_id": str(trim.id)},
        )
        assert ok.status_code == 200

        bad = await client.patch(
            f"/listings/{listing.id}",
            headers=auth_headers(seller),
            json={"trim_id": str(uuid.uuid4())},
        )
        assert bad.status_code == 404
        assert bad.json()["code"] == "trim_not_found"


class TestPhotos:
    async def test_upload_and_delete(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT, photos=0)

        upload = await client.post(
            f"/listings/{listing.id}/photos",
            headers=auth_headers(seller),
            files={"file": ("car.png", png_bytes(), "image/png")},
        )
        assert upload.status_code == 201, upload.text
        photo = upload.json()
        assert photo["position"] == 0
        assert photo["url"]

        removed = await client.delete(
            f"/listings/{listing.id}/photos/{photo['id']}", headers=auth_headers(seller)
        )
        assert removed.status_code == 200

    async def test_rejects_a_file_that_is_not_an_image(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT, photos=0)

        # A script that merely claims to be a PNG.
        response = await client.post(
            f"/listings/{listing.id}/photos",
            headers=auth_headers(seller),
            files={"file": ("evil.png", b"<?php system($_GET[0]); ?>", "image/png")},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "photo_unsupported_type"

    async def test_rejects_an_oversized_file(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT, photos=0)

        oversized = png_bytes() + b"\x00" * (8 * 1024 * 1024)
        response = await client.post(
            f"/listings/{listing.id}/photos",
            headers=auth_headers(seller),
            files={"file": ("big.png", oversized, "image/png")},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "photo_too_large"

    async def test_a_stranger_cannot_upload(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        stranger: User = await make_user()
        listing = await make_listing(seller=seller, photos=0)

        response = await client.post(
            f"/listings/{listing.id}/photos",
            headers=auth_headers(stranger),
            files={"file": ("car.png", png_bytes(), "image/png")},
        )
        assert response.status_code == 403


class TestLifecycle:
    async def test_publishing_requires_enough_photos(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT, photos=2)

        response = await client.post(
            f"/listings/{listing.id}/publish", headers=auth_headers(seller)
        )
        assert response.status_code == 409
        assert response.json()["code"] == "not_enough_photos"

    async def test_publish_puts_it_in_review_with_a_reason(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT, photos=4)

        response = await client.post(
            f"/listings/{listing.id}/publish", headers=auth_headers(seller)
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == ListingStatus.PENDING_REVIEW
        assert body["status_reason_code"] == StatusReasonCode.AWAITING_REVIEW

    async def test_admin_approves_and_the_listing_becomes_public(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        admin: User = await make_user(role=UserRole.ADMIN)
        listing = await make_listing(seller=seller, status=ListingStatus.PENDING_REVIEW)

        response = await client.post(
            f"/listings/{listing.id}/moderate",
            headers=auth_headers(admin),
            json={"approve": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == ListingStatus.ACTIVE
        # An active listing needs no explanation.
        assert body["status_reason_code"] is None
        assert body["published_at"] is not None

        assert (await client.get(f"/listings/{listing.id}")).status_code == 200

    async def test_rejection_must_carry_a_reason_the_seller_can_read(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        admin: User = await make_user(role=UserRole.ADMIN)
        listing = await make_listing(seller=seller, status=ListingStatus.PENDING_REVIEW)

        missing_reason = await client.post(
            f"/listings/{listing.id}/moderate",
            headers=auth_headers(admin),
            json={"approve": False},
        )
        assert missing_reason.status_code == 409
        assert missing_reason.json()["code"] == "reason_code_required"

        rejected = await client.post(
            f"/listings/{listing.id}/moderate",
            headers=auth_headers(admin),
            json={
                "approve": False,
                "reason_code": StatusReasonCode.CONTACT_IN_DESCRIPTION,
                "note": "رقم الجوال مذكور في الوصف",
            },
        )
        assert rejected.status_code == 200
        body = rejected.json()
        assert body["status"] == ListingStatus.REJECTED
        assert body["status_reason_code"] == StatusReasonCode.CONTACT_IN_DESCRIPTION
        assert body["status_reason_note"] == "رقم الجوال مذكور في الوصف"

    async def test_only_admins_moderate(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.PENDING_REVIEW)

        response = await client.post(
            f"/listings/{listing.id}/moderate",
            headers=auth_headers(seller),
            json={"approve": True},
        )
        assert response.status_code == 403

    async def test_seller_hides_and_republishes(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.ACTIVE)

        hidden = await client.put(
            f"/listings/{listing.id}/status",
            headers=auth_headers(seller),
            json={"status": ListingStatus.HIDDEN},
        )
        assert hidden.status_code == 200
        assert hidden.json()["status_reason_code"] == StatusReasonCode.SELLER_HID
        assert (await client.get(f"/listings/{listing.id}")).status_code == 404

        back = await client.put(
            f"/listings/{listing.id}/status",
            headers=auth_headers(seller),
            json={"status": ListingStatus.ACTIVE},
        )
        assert back.status_code == 200
        assert (await client.get(f"/listings/{listing.id}")).status_code == 200

    async def test_a_seller_cannot_jump_straight_to_active(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT)

        response = await client.put(
            f"/listings/{listing.id}/status",
            headers=auth_headers(seller),
            json={"status": ListingStatus.ACTIVE},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "invalid_status_transition"

    async def test_mark_sold_records_the_final_price(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller, status=ListingStatus.ACTIVE)

        response = await client.post(
            f"/listings/{listing.id}/sold",
            headers=auth_headers(seller),
            json={"final_price_sar": "٨٧٬٠٠٠"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == ListingStatus.SOLD
        assert body["final_price_sar"] == 87_000
        assert body["sold_at"] is not None

        again = await client.post(
            f"/listings/{listing.id}/sold",
            headers=auth_headers(seller),
            json={"final_price_sar": 87_000},
        )
        assert again.status_code == 409
        assert again.json()["code"] == "already_sold"

    async def test_status_history_explains_every_change(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        admin: User = await make_user(role=UserRole.ADMIN)
        listing = await make_listing(seller=seller, status=ListingStatus.DRAFT)

        await client.post(f"/listings/{listing.id}/publish", headers=auth_headers(seller))
        await client.post(
            f"/listings/{listing.id}/moderate",
            headers=auth_headers(admin),
            json={"approve": True},
        )

        response = await client.get(
            f"/listings/{listing.id}/status-history", headers=auth_headers(seller)
        )
        assert response.status_code == 200
        history = response.json()
        assert [event["to_status"] for event in history] == [
            ListingStatus.PENDING_REVIEW,
            ListingStatus.ACTIVE,
        ]
        assert history[0]["reason_code"] == StatusReasonCode.AWAITING_REVIEW

    async def test_status_history_is_private(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        stranger: User = await make_user()
        listing = await make_listing(seller=seller)

        assert (await client.get(f"/listings/{listing.id}/status-history")).status_code == 401
        assert (
            await client.get(
                f"/listings/{listing.id}/status-history", headers=auth_headers(stranger)
            )
        ).status_code == 403


class TestMyListings:
    async def test_shows_every_status_for_the_owner_only(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        other: User = await make_user()
        await make_listing(seller=seller, status=ListingStatus.DRAFT)
        await make_listing(seller=seller, status=ListingStatus.ACTIVE)
        await make_listing(seller=other, status=ListingStatus.ACTIVE)

        response = await client.get("/listings/mine", headers=auth_headers(seller))
        assert response.status_code == 200
        statuses = sorted(item["status"] for item in response.json())
        assert statuses == [ListingStatus.ACTIVE, ListingStatus.DRAFT]

    async def test_requires_sign_in(self, client: AsyncClient) -> None:
        assert (await client.get("/listings/mine")).status_code == 401


class TestModerationQueue:
    async def test_lists_only_pending_listings_for_admins(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
    ) -> None:
        seller: User = await make_user()
        admin: User = await make_user(role=UserRole.ADMIN)
        pending = await make_listing(seller=seller, status=ListingStatus.PENDING_REVIEW)
        await make_listing(seller=seller, status=ListingStatus.ACTIVE)

        response = await client.get("/listings/moderation/queue", headers=auth_headers(admin))
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [str(pending.id)]

    async def test_is_closed_to_sellers(
        self, client: AsyncClient, make_user: UserFactory, auth_headers: AuthHeaders
    ) -> None:
        seller: User = await make_user()
        assert (
            await client.get("/listings/moderation/queue", headers=auth_headers(seller))
        ).status_code == 403


class TestViews:
    async def test_a_buyer_view_is_counted_but_the_sellers_is_not(
        self,
        client: AsyncClient,
        make_user: UserFactory,
        auth_headers: AuthHeaders,
        make_listing: ListingFactory,
        session: AsyncSession,
    ) -> None:
        seller: User = await make_user()
        listing = await make_listing(seller=seller)

        await client.get(f"/listings/{listing.id}")
        await client.get(f"/listings/{listing.id}", headers=auth_headers(seller))

        refreshed = await session.get(Listing, listing.id)
        assert refreshed is not None
        await session.refresh(refreshed)
        assert refreshed.views_count == 1
