# Row-Level Security (RLS) on Databricks — Options and Documentation

**Purpose:** Summary of RLS options available to customers (excluding the separate Option B notebook) and official Databricks documentation links.

---

## Email draft (copy below)

**Subject:** Row-Level Security (RLS) on Databricks — options and documentation links

Hi,

Here’s a short overview of the main ways to set up Row-Level Security (RLS) on Databricks, plus links to the official documentation.

**RLS options (recommended path: 03 or 04)**

1. **Legacy — Secured views**  
   Filter via a view over a base table (role mapping + SQL function). **Not recommended** for new work; users can bypass the filter if they access the base table. Use only for reference or migration.

2. **Manual — Simple UDF**  
   Native row filter with `ALTER TABLE ... SET ROW FILTER`. The UDF encodes group checks (e.g. `is_member('marketing')`) inside the function. **Good for 2–3 groups**; no mapping table or tags.

3. **Manual — Mapping table (recommended manual approach)**  
   Native row filter + a mapping table that defines which groups see which divisions. One UDF reads the table; add/change access by updating data, not code. **Best practice when you want per-table control without governed tags.**

4. **ABAC — Governed tags + policies (recommended for scale)**  
   Governed tags on columns + policies in the UI (Applied to / Except / Scope / Hide table rows). One policy can apply to many tables that share the same tag. **Best for governance at scale**; table owners cannot remove policies.

For new implementations we typically recommend **03** (manual with mapping table) or **04** (ABAC).

**Documentation links (Databricks)**

- Row filters and column masks (overview): https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/
- Unity Catalog overview: https://docs.databricks.com/data-governance/unity-catalog/
- Manually apply row filters: https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply
- Attribute-based access control (ABAC): https://docs.databricks.com/data-governance/unity-catalog/abac/
- Create and manage ABAC policies: https://docs.databricks.com/data-governance/unity-catalog/abac/policies
- UDF best practices for ABAC: https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices
- Limits (filters and masks): https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/#limits

**Microsoft tutorial (ABAC step-by-step)**

- Configure ABAC: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial

If you tell me your scale (number of tables, groups, divisions) and whether you prefer manual per-table control or central tag-based governance, we can narrow this down to one option and a concrete setup.

Best regards,

---

---

## RLS options (01 → 04)

| Option | Name | What it is | When to use |
|--------|------|------------|-------------|
| **01** | Legacy: Secured views | Row-level security via **secured views** (users query a view that filters the base table). Role mapping table + SQL function; view applies the filter in a WHERE clause. | **Legacy / reference only.** Views can be bypassed if users get direct access to the base table. Databricks recommends **native row filters** (02, 03, or 04). |
| **02** | Manual simple: UDF with is_member() | **Native** row filter via `ALTER TABLE ... SET ROW FILTER`. The UDF encodes "who sees what" **inside the function** (e.g. `is_member('marketing')`, `division = 'Marketing'`). No mapping table; no governed tags. | **Few groups (2–3).** Quick and simple. For more scalable manual control use **03**; for central governance use **04**. |
| **03** | Manual best practice: Mapping table + native row filter | **Native** row filter via `ALTER TABLE ... SET ROW FILTER`. Uses a **mapping table** (e.g. role_mapping) to define which groups see which divisions — no hardcoded groups in the UDF. Add/change access by updating the table. | **Recommended manual approach.** Use when you want table-level control without governed tags. For central, tag-based governance use **04**. |
| **04** | ABAC: Governed tags + policies | **Attribute-Based Access Control** — governed tags on columns + **policies** in the UI (Applied to / Except / Scope / Hide table rows). One policy can apply to many tables that have the same tag. Option A: one UDF per division; Option B (separate notebook): one UDF + mapping table. | **Best for governance at scale.** Central control; table owners cannot remove policies. Use for new implementations with many tables or strong governance. |

**Takeaway:** For new implementations, use **03** (manual best practice) or **04** (ABAC). Use **01** only for demos or legacy migration context.

---

## Official Databricks documentation links

### Core concepts

- **Row filters and column masks**  
  https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/  
  Overview of native row filters, when to use them vs views, and limits.

- **Unity Catalog overview**  
  https://docs.databricks.com/data-governance/unity-catalog/  
  Catalogs, schemas, tables, and governance model.

### Manual row filters (options 02 and 03)

- **Manually apply row filters**  
  https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply  
  `ALTER TABLE ... SET ROW FILTER` syntax, parameter mapping, and limitations.

### ABAC — governed tags and policies (option 04)

- **Attribute-based access control (ABAC)**  
  https://docs.databricks.com/data-governance/unity-catalog/abac/  
  Governed tags, policies, and how row filters and column masks work with ABAC.

- **Row filters and column masks (ABAC context)**  
  https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/  
  How filters work with ABAC (same page as above; use for “how filters work with ABAC”).

- **Create and manage ABAC policies**  
  https://docs.databricks.com/data-governance/unity-catalog/abac/policies  
  How to create and manage row filter and column mask policies in the UI.

- **Limitations (row filters and column masks)**  
  https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/#limits  
  Limits and constraints for row filters and column masks.

### UDFs for row filters

- **UDF best practices for ABAC**  
  https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices  
  Keeping UDF logic simple; mapping table pattern; use policy for “who,” UDF for “what rows.”

### Microsoft tutorial (ABAC)

- **Tutorial: Configure ABAC (Microsoft)**  
  https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial  
  Step-by-step UI flow: governed tag, policy, and function parameters.

---

## Quick reference — links only

- Row filters and column masks: https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/
- Unity Catalog: https://docs.databricks.com/data-governance/unity-catalog/
- Manually apply row filters: https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply
- ABAC: https://docs.databricks.com/data-governance/unity-catalog/abac/
- ABAC policies: https://docs.databricks.com/data-governance/unity-catalog/abac/policies
- UDF best practices (ABAC): https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices
- Limits (filters and masks): https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/#limits
- Microsoft ABAC tutorial: https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial
