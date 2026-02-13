"""BC API v2.0 JSON payload generators."""

from __future__ import annotations

from typing import Any


class APIPayloadGenerator:
    """Generates JSON-serializable dicts matching the BC API v2.0 endpoints."""

    # ------------------------------------------------------------------
    # Master data
    # ------------------------------------------------------------------

    @staticmethod
    def generate_customer(data: dict[str, Any]) -> dict[str, Any]:
        """Generate a payload for POST /companies({id})/customers.

        Accepted keys (all optional except displayName):
            number, displayName, type, addressLine1, addressLine2, city,
            state, country, postalCode, phoneNumber, email, website,
            taxRegistrationNumber, currencyCode, paymentTermsId,
            paymentMethodId, blocked, genBusPostingGroup,
            customerPostingGroup, vatBusPostingGroup.
        """
        payload: dict[str, Any] = {}
        _copy_keys(payload, data, [
            "number", "displayName", "type",
            "addressLine1", "addressLine2", "city", "state",
            "country", "postalCode", "phoneNumber", "email", "website",
            "taxRegistrationNumber", "currencyCode",
            "paymentTermsId", "paymentMethodId", "blocked",
        ])
        # BC-specific posting groups go into the same flat object
        _copy_keys(payload, data, [
            "genBusPostingGroup", "customerPostingGroup", "vatBusPostingGroup",
        ])
        return payload

    @staticmethod
    def generate_vendor(data: dict[str, Any]) -> dict[str, Any]:
        """Generate a payload for POST /companies({id})/vendors."""
        payload: dict[str, Any] = {}
        _copy_keys(payload, data, [
            "number", "displayName", "type",
            "addressLine1", "addressLine2", "city", "state",
            "country", "postalCode", "phoneNumber", "email", "website",
            "taxRegistrationNumber", "currencyCode",
            "paymentTermsId", "paymentMethodId", "blocked",
            "genBusPostingGroup", "vendorPostingGroup", "vatBusPostingGroup",
        ])
        return payload

    @staticmethod
    def generate_item(data: dict[str, Any]) -> dict[str, Any]:
        """Generate a payload for POST /companies({id})/items."""
        payload: dict[str, Any] = {}
        _copy_keys(payload, data, [
            "number", "displayName", "type", "itemCategoryCode",
            "blocked", "baseUnitOfMeasureCode",
            "gtin", "unitPrice", "unitCost",
            "genProdPostingGroup", "inventoryPostingGroup",
            "vatProdPostingGroup", "taxGroupCode",
        ])
        return payload

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    @staticmethod
    def generate_sales_order(
        header: dict[str, Any],
        lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a payload for POST /companies({id})/salesOrders.

        The ``lines`` list is nested under ``salesOrderLines``.
        """
        payload: dict[str, Any] = {}
        _copy_keys(payload, header, [
            "orderNumber", "customerNumber", "customerName",
            "orderDate", "requestedDeliveryDate",
            "currencyCode", "paymentTermsId",
            "shippingPostalAddress",
        ])
        payload["salesOrderLines"] = [
            _build_sales_line(line) for line in lines
        ]
        return payload

    @staticmethod
    def generate_purchase_order(
        header: dict[str, Any],
        lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a payload for POST /companies({id})/purchaseOrders."""
        payload: dict[str, Any] = {}
        _copy_keys(payload, header, [
            "orderNumber", "vendorNumber", "vendorName",
            "orderDate", "expectedReceiptDate",
            "currencyCode", "paymentTermsId",
        ])
        payload["purchaseOrderLines"] = [
            _build_purchase_line(line) for line in lines
        ]
        return payload

    @staticmethod
    def generate_journal_entry(lines: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate a payload for POST /companies({id})/journals({id})/journalLines.

        Returns a wrapper dict with a ``journalLines`` key so the caller
        can iterate and POST each line individually or use batch.
        """
        built: list[dict[str, Any]] = []
        for line in lines:
            entry: dict[str, Any] = {}
            _copy_keys(entry, line, [
                "accountNumber", "accountType",
                "postingDate", "documentNumber", "externalDocumentNumber",
                "amount", "description", "comment",
                "balancingAccountNumber", "balancingAccountType",
                "dimensionSetLines",
            ])
            built.append(entry)
        return {"journalLines": built}


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _copy_keys(
    target: dict[str, Any],
    source: dict[str, Any],
    keys: list[str],
) -> None:
    for key in keys:
        if key in source:
            target[key] = source[key]


def _build_sales_line(line: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    _copy_keys(entry, line, [
        "lineType", "itemNumber", "description",
        "quantity", "unitPrice", "discountPercent",
        "taxCode", "locationCode",
    ])
    return entry


def _build_purchase_line(line: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    _copy_keys(entry, line, [
        "lineType", "itemNumber", "description",
        "quantity", "unitCost", "expectedReceiptDate",
        "taxCode", "locationCode",
    ])
    return entry
