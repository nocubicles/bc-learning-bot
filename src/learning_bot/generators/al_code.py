"""AL code snippet generator for Business Central extensions."""

from __future__ import annotations

from typing import Any


class ALCodeGenerator:
    """Generates syntactically correct AL code snippets."""

    @staticmethod
    def generate_table_extension(
        base_table: str,
        fields: list[dict[str, Any]],
        *,
        ext_id: int = 50100,
        ext_name: str | None = None,
    ) -> str:
        """Generate an AL tableextension.

        Args:
            base_table: Name of the base table (e.g. "Customer").
            fields: List of field dicts with keys "id", "name", "type",
                     and optional "length" (for Text/Code).
            ext_id: Object ID for the extension.
            ext_name: Object name; defaults to ``<base_table>Ext``.
        """
        name = ext_name or f"{_safe_name(base_table)}Ext"
        lines = [
            f'tableextension {ext_id} "{name}" extends "{base_table}"',
            "{",
            "    fields",
            "    {",
        ]
        for field in fields:
            lines.append(_field_definition(field, indent=8))
        lines += [
            "    }",
            "}",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def generate_page_extension(
        base_page: str,
        fields: list[dict[str, Any]],
        *,
        ext_id: int = 50100,
        ext_name: str | None = None,
        anchor: str = "Name",
    ) -> str:
        """Generate an AL pageextension.

        Args:
            base_page: Name of the base page (e.g. "Customer Card").
            fields: List of field dicts with at least "name".
            ext_id: Object ID for the extension.
            ext_name: Object name; defaults to ``<base_page>Ext``.
            anchor: Field name to place the addafter() group.
        """
        name = ext_name or f"{_safe_name(base_page)}Ext"
        lines = [
            f'pageextension {ext_id} "{name}" extends "{base_page}"',
            "{",
            "    layout",
            "    {",
            f'        addafter("{anchor}")',
            "        {",
        ]
        for field in fields:
            fname = field["name"]
            caption = field.get("caption", fname)
            lines += [
                f'            field("{fname}"; Rec."{fname}")',
                "            {",
                f'                Caption = \'{caption}\';',
                "                ApplicationArea = All;",
                "            }",
            ]
        lines += [
            "        }",
            "    }",
            "}",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def generate_codeunit(
        name: str,
        procedures: list[dict[str, Any]],
        *,
        obj_id: int = 50100,
    ) -> str:
        """Generate an AL codeunit.

        Args:
            name: Codeunit name.
            procedures: List of procedure dicts with keys "name", "body",
                        and optional "params" (list of "name: Type" strings)
                        and "returns" (return type string).
            obj_id: Object ID.
        """
        lines = [
            f'codeunit {obj_id} "{name}"',
            "{",
        ]
        for proc in procedures:
            lines.append("")
            lines.append(_procedure_block(proc, indent=4))
        lines += [
            "}",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def generate_report(
        name: str,
        dataset: list[dict[str, Any]],
        columns: list[str],
        *,
        obj_id: int = 50100,
        source_table: str = "Customer",
    ) -> str:
        """Generate an AL report with an RDLC/Excel-style dataset.

        Args:
            name: Report name.
            dataset: List of dataitem dicts with "name" and optional "filters".
            columns: Column field names to include.
            obj_id: Object ID.
            source_table: Source table for the primary dataitem.
        """
        lines = [
            f'report {obj_id} "{name}"',
            "{",
            "    UsageCategory = ReportsAndAnalysis;",
            "    ApplicationArea = All;",
            f'    Caption = \'{name}\';',
            "",
            "    dataset",
            "    {",
            f'        dataitem(DataItem1; "{source_table}")',
            "        {",
        ]
        for col in columns:
            lines += [
                f'            column({_safe_name(col)}; "{col}")',
                "            {",
                "            }",
            ]
        # Apply filters from dataset definition
        for di in dataset:
            if "filters" in di:
                for filt in di["filters"]:
                    lines.append(f"            // Filter: {filt}")
        lines += [
            "        }",
            "    }",
            "",
            "    requestpage",
            "    {",
            "        layout",
            "        {",
            "            area(Content)",
            "            {",
            "            }",
            "        }",
            "    }",
            "}",
            "",
        ]
        return "\n".join(lines)


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """Remove spaces and special chars to make a valid AL identifier."""
    return "".join(ch for ch in name if ch.isalnum() or ch == "_")


def _field_definition(field: dict[str, Any], indent: int = 8) -> str:
    pad = " " * indent
    fid = field["id"]
    fname = field["name"]
    ftype = field.get("type", "Text[100]")
    # Handle length for Text/Code types
    if ftype in ("Text", "Code"):
        length = field.get("length", 100)
        ftype = f"{ftype}[{length}]"
    block = [
        f'{pad}field({fid}; "{fname}"; {ftype})',
        f"{pad}{{",
        f"{pad}    Caption = '{fname}';",
        f"{pad}    DataClassification = CustomerContent;",
        f"{pad}}}",
    ]
    return "\n".join(block)


def _procedure_block(proc: dict[str, Any], indent: int = 4) -> str:
    pad = " " * indent
    pname = proc["name"]
    params = proc.get("params", [])
    returns = proc.get("returns", "")
    body = proc.get("body", "// TODO: implement")

    param_str = "; ".join(params)
    signature = f"{pad}procedure {pname}({param_str})"
    if returns:
        signature += f": {returns}"

    body_lines = body.split("\n")
    formatted_body = "\n".join(f"{pad}    {line}" for line in body_lines)

    return f"{signature}\n{pad}begin\n{formatted_body}\n{pad}end;"
