# RLS Best Practices — Simple Guide (For Beginners)

This doc summarizes **what Databricks recommends** in the official docs and how it maps to the notebooks in this project. If you're new, start here.

---

## 1. Two ways to apply row filters (what the docs say)

| Approach | What it is | Docs recommendation |
|----------|------------|----------------------|
| **ABAC (governed tags + policies)** | You tag columns (e.g. `division`), create one or more **policies** that say “when someone queries a column with this tag, apply this filter.” The **policy** defines *who* gets the filter (Applied to / Except). The **UDF** only defines *how* to filter the data. | **Recommended for most use cases.** Scales across many tables; central control; table owners can’t remove it. Requires DBR 16.4+ (and serverless for dedicated compute). |
| **Manual (per table)** | You run `ALTER TABLE ... SET ROW FILTER function_name ON (column)` on each table. No tags, no policies. | Use when you need table-by-table control, don’t need to scale by tag, or run on DBR &lt; 16.4. |

**Takeaway:** Prefer **ABAC** when you have many tables or want governance that table owners can’t override. Use **manual** when you have a few tables, want the simplest setup, or must support older runtimes.

---

## 2. Your project: four notebooks (demo order 01 to 04, legacy to recommended)

| Notebook | Pattern | When to use it |
|----------|---------|----------------|
| **`01_rls_legacy_secured_views`** | **Legacy:** secured views that filter a base table. | Demo only; deprecated. Direct table access bypasses the filter. |
| **`02_rls_manual_simple_udf`** | **Manual:** native row filter; UDF has `is_member()` / `is_account_group_member()` inside. | Few groups; quick and simple. Not recommended for scale (see §3, §5). |
| **`03_rls_manual_mapping_table`** (see `RLS_NATIVE_SETUP_GUIDE.md`) | **Manual best practice:** mapping table + one UDF + `ALTER TABLE ... SET ROW FILTER`. | Recommended manual approach; add/change access by updating the mapping table. |
| **`04_rls_abac_governed_tags`** / **`04b_rls_abac_option_b`** | **ABAC:** governed tags + policies in the UI. Option B = one UDF + mapping table in one schema. | Best for governance at scale; DBR 16.4+ required. |

**Takeaway:** Demo in order 01 → 04. For new work, use **03** (manual best practice) or **04/04b** (ABAC).

---

## 3. UDF vs policy (who does what)

From the docs:

- **Policy (ABAC):** Decides **who** the filter applies to (groups/users) and **when** (which tagged objects). Use “Applied to” and “Except” here (e.g. exclude admins). **Do not put `is_member()` or `is_account_group_member()` inside the UDF** when using ABAC—the policy defines who gets the filter; the UDF defines only the row predicate. Keeping UDFs free of identity checks improves performance and enables predicate pushdown.
- **UDF:** Contains **only the filter logic** (e.g. “return true if this row’s `division` is in the allowed set”). For **manual** row filters, a single admin bypass in the UDF (e.g. `IF(is_account_group_member('admin'), true, ...)`) is acceptable and documented; the rest of “who sees which division” should use a mapping table, not many group checks inside the UDF.
- **Unity Catalog identity:** Prefer **account-level groups** and **`is_account_group_member()`** over workspace-level `is_member()`. Manage principals at the account via SCIM from your IdP; assign access through groups rather than direct user grants.

**Takeaway:** UDF = *what rows to show* (and optionally one admin bypass for manual). Policy = *who* gets that filter and on *which* tables/columns (by tag). Use account groups and `is_account_group_member()` in Unity Catalog.

---

## 4. One UDF per value vs one UDF + mapping table

You have two ways to implement the *logic* (both are valid):

| Approach | What you create | Best for |
|----------|------------------|----------|
| **One UDF per value** | `fn_division_marketing`, `fn_division_sales`, … one UDF per division. One policy per group, each using one UDF. | Very few values (e.g. 2–3); you’re okay maintaining one UDF per value. |
| **One UDF + mapping table** | One table (e.g. `division_access` or `role_mapping`) that lists “principal → allowed division”. One UDF that returns true when the row’s column value is in that table for the current user. One policy (ABAC) or one manual filter. | Many values or many groups; you don’t want to add a new UDF every time you add a division. **This is the pattern the docs recommend for “mapping tables.”** |

**Takeaway:** Use **one UDF + one mapping table** for scale; add/change divisions by updating the table. Notebook **04** shows Option A (one UDF per value); **04b** and **03** use the mapping-table pattern.

---

## 5. What the docs say about UDF best practices

- **Prefer SQL UDFs** — faster than Python; better for predicate pushdown and caching.
- **No `is_member()` / `is_account_group_member()` inside the UDF for ABAC** — handle “who” in the policy. For manual filters, a single admin bypass in the UDF is acceptable.
- **Keep UDFs simple:** deterministic, no external calls, no heavy regex or complex subqueries if you can avoid it. Use only built-in functions; don’t call other UDFs from within a UDF.
- **Column-only references** in the UDF where possible — enables predicate pushdown and better performance.
- **Mapping table:** Using a small lookup table (e.g. principal + allowed division) that the UDF reads is a supported and recommended pattern; keep the UDF logic simple (e.g. `EXISTS (SELECT 1 FROM mapping WHERE ...)`).
- **Test at scale:** Validate performance on at least 1 million rows before production.
- **Anti-patterns to avoid:** non-deterministic logic, dynamic SQL, metadata lookups (e.g. `information_schema`), per-row identity lookups inside the UDF for ABAC, external API calls.

**Takeaway:** Simple, deterministic, SQL UDFs with mapping tables scale and perform best. See [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices).

---

## 6. Compute and runtime requirements

| Scenario | Requirement |
|----------|-------------|
| **Read** row filters (standard compute) | DBR 12.2 LTS+ |
| **Read** row filters (dedicated compute) | DBR 15.4 LTS+; workspace must be enabled for **serverless** (filtering runs on serverless). |
| **Write** (INSERT/UPDATE/DELETE/MERGE) to filtered tables | DBR 16.3+; use supported patterns (e.g. `MERGE INTO`). |
| **ABAC policies** (governed tags) | DBR 16.4+ (dedicated or standard); serverless supports ABAC. |

Dedicated compute on DBR 15.3 or below **cannot** read tables with row filters or column masks.

---

## 7. Quick decision guide

1. **Brand new?**  
   → Use **`RLS_NATIVE_SETUP_GUIDE.md`** and the **native row filter** notebook (mapping table + one UDF, manual `ALTER TABLE`).

2. **Need tag-based, central governance?**  
   → Use **`04_rls_abac_governed_tags`** or **`04b_rls_abac_option_b`** (ABAC). Prefer **Option B** (one UDF + mapping table) unless you only have 2–3 fixed values. Ensure DBR 16.4+.

3. **Many divisions or many groups?**  
   → Use **one UDF + one mapping table**; avoid one UDF per value.

4. **Unity Catalog identity:**  
   → Use account-level groups and `is_account_group_member()`; provision groups via SCIM from your IdP. Prefer group ownership for production objects.

5. **Official references:**  
   - [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/)  
   - [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices)  
   - [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply)  
   - [Unity Catalog best practices](https://docs.databricks.com/en/data-governance/unity-catalog/best-practices.html)  
   - [Create and manage ABAC policies](https://docs.databricks.com/data-governance/unity-catalog/abac/policies)

---

## Summary table

| Question | Best practice (from docs + this repo) |
|----------|--------------------------------------|
| ABAC vs manual? | Prefer ABAC for scale and central control (DBR 16.4+); use manual for few tables or older runtimes. |
| Who applies the filter — UDF or policy? | Policy = who/when (ABAC). UDF = filter logic only. No identity checks in UDF for ABAC; one admin bypass in UDF is OK for manual. |
| One UDF per value or one UDF for all? | One UDF + mapping table when you have many values; one UDF per value only if 2–3 fixed values. |
| Identity in Unity Catalog? | Use account-level groups and `is_account_group_member()`; manage via IdP/SCIM. |
| Where to start as a beginner? | Native row filter + `RLS_NATIVE_SETUP_GUIDE.md`, then ABAC when you need governed tags and DBR 16.4+. |
