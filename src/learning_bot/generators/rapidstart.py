"""RapidStart configuration package XML generation for Business Central."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Any


# Well-known BC table IDs
TABLE_IDS: dict[str, int] = {
    "G/L Account": 15,
    "Customer": 18,
    "Vendor": 23,
    "Item": 27,
    "Gen. Business Posting Group": 250,
    "Gen. Product Posting Group": 251,
    "General Posting Setup": 252,
    "Customer Posting Group": 92,
    "Vendor Posting Group": 93,
    "Inventory Posting Group": 94,
    "VAT Business Posting Group": 323,
    "VAT Product Posting Group": 324,
    "VAT Posting Setup": 325,
    "Bank Account": 270,
    "Payment Terms": 3,
    "Payment Method": 289,
    "Currency": 4,
    "Location": 14,
    "Dimension Value": 349,
    "No. Series": 308,
    "No. Series Line": 309,
}


class RapidStartGenerator:
    """Generates RapidStart/configuration-package XML for BC import."""

    def generate_package(
        self,
        table_name: str,
        fields: list[dict[str, Any]],
        data_rows: list[dict[str, Any]],
    ) -> str:
        """Generate a RapidStart configuration package XML string.

        Args:
            table_name: BC table name (e.g. "Customer").
            fields: List of field dicts with keys "id", "name", and optional "type".
            data_rows: List of row dicts keyed by field name.

        Returns:
            Prettified XML string.
        """
        root = self._build_package_root()
        table_el = self._add_table(root, table_name, fields)
        for row in data_rows:
            self._add_row(table_el, fields, row)
        return self._to_xml_string(root)

    def generate_coa_package(self, accounts: list[dict[str, Any]]) -> str:
        """Generate a configuration package XML for chart-of-accounts import.

        Each account dict should have: No., Name, Account Type,
        and optionally Account Category / Account Subcategory.
        """
        fields = [
            {"id": 1, "name": "No."},
            {"id": 2, "name": "Name"},
            {"id": 3, "name": "Income/Balance"},
            {"id": 4, "name": "Account Type"},
            {"id": 80, "name": "Account Category"},
            {"id": 81, "name": "Account Subcategory"},
        ]
        return self.generate_package("G/L Account", fields, accounts)

    def generate_master_data_package(
        self,
        table: str,
        records: list[dict[str, Any]],
    ) -> str:
        """Generate a configuration package for arbitrary master data.

        Fields are inferred from the first record's keys.
        Field IDs are assigned sequentially starting at 1.
        """
        if not records:
            return self.generate_package(table, [], [])
        fields = [
            {"id": idx, "name": key}
            for idx, key in enumerate(records[0].keys(), start=1)
        ]
        return self.generate_package(table, fields, records)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_package_root() -> ET.Element:
        root = ET.Element("ConfigurationPackage")
        root.set("xmlns", "urn:microsoft-dynamics-nav/config-package")
        return root

    @staticmethod
    def _add_table(
        root: ET.Element,
        table_name: str,
        fields: list[dict[str, Any]],
    ) -> ET.Element:
        table_el = ET.SubElement(root, "ConfigurationPackageTable")
        table_id = TABLE_IDS.get(table_name, 0)
        ET.SubElement(table_el, "TableId").text = str(table_id)
        ET.SubElement(table_el, "TableName").text = table_name
        ET.SubElement(table_el, "NoOfRecords").text = "0"  # placeholder

        fields_el = ET.SubElement(table_el, "ConfigurationPackageFields")
        for field in fields:
            field_el = ET.SubElement(fields_el, "ConfigurationPackageField")
            ET.SubElement(field_el, "FieldId").text = str(field["id"])
            ET.SubElement(field_el, "FieldName").text = field["name"]
            ET.SubElement(field_el, "IncludeField").text = "true"

        ET.SubElement(table_el, "ConfigurationPackageData")
        return table_el

    @staticmethod
    def _add_row(
        table_el: ET.Element,
        fields: list[dict[str, Any]],
        row: dict[str, Any],
    ) -> None:
        data_el = table_el.find("ConfigurationPackageData")
        assert data_el is not None
        record_el = ET.SubElement(data_el, "ConfigurationPackageRecord")
        for field in fields:
            value = row.get(field["name"], "")
            field_val = ET.SubElement(record_el, "ConfigurationPackageFieldValue")
            ET.SubElement(field_val, "FieldId").text = str(field["id"])
            ET.SubElement(field_val, "Value").text = str(value) if value != "" else ""

    @staticmethod
    def _to_xml_string(root: ET.Element) -> str:
        rough = ET.tostring(root, encoding="unicode", xml_declaration=False)
        dom = minidom.parseString(rough)
        return dom.toprettyxml(indent="  ", encoding=None)
