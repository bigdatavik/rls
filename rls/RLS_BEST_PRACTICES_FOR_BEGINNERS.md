# RLS Best Practices — Simple Guide (For Beginners)

This doc summarizes **what Databricks recommends** in the official docs and how it maps to the notebooks in this project. If you're new, start here.

---

## 1. Two ways to apply row filters (what the docs say)

| Approach | What it is | Docs recommendation |
|----------|------------|----------------------|
| **ABAC (governed tags + policies)** | You tag columns (e.g. `division`), create one or more **policies** that say “when someone queries a column with this tag, apply this filter.” The **policy** defines *who* gets the filter (Applied to / Except). The **UDF** only defines *how* to filter the data. | **Recommended for most use cases.** Scales across many tables; central control; table owners can’t remove it. |
| **Manual (per table)** | You run `ALTER TABLE ... SET ROW FILTER function_name ON (column)` on each table. No tags, no policies. | Use when you need table-by-table control and don’t need to scale by tag. |

**Takeaway:** Prefer **ABAC** when you have many tables or want governance that table owners can’t override. Use **manual** when you have a few tables and want the simplest setup.

---

## 2. Your project: four notebooks (demo order 01 to 04, legacy to recommended)

| Notebook | Pattern | When to use it |
|----------|---------|----------------|
| **`01_rls_legacy_secured_views`** | **Legacy:** secured views that filter a base table. | Demo only; deprecated. |
| **`02_rls_manual_simple_udf`** | **Manual:** native row filter; UDF has `is_member()` inside. | Few groups; quick and simple. |
| **`03_rls_manual_mapping_table`** (see `RLS_NATIVE_SETUP_GUIDE.md`) | **Manual best practice:** mapping table + one UDF + `ALTER TABLE ... SET ROW FILTER`. | Recommended manual approach. |
| **`04_rls_abac_governed_tags`** | **ABAC:** governed tags + policies in the UI (Option A or B). | Best for governance at scale. |

**Takeaway:** Demo in order 01 to 04. For new work, use **03** (manual best practice) or **04** (ABAC).

---

## 3. UDF vs policy (who does what)

From the docs:

- **Policy (ABAC):** Decides **who** the filter applies to (groups/users) and **when** (which tagged objects). Use “Applied to” and “Except” here (e.g. exclude admins).
- **UDF:** Contains **only the filter logic** (e.g. “return true if this row’s `division` is in the allowed set”). The docs say: **don’t put `is_member()` or `is_account_group_member()` inside the UDF**; that belongs in the policy design (who gets the filter). Keeping UDFs simple improves performance and reuse.

**Takeaway:** UDF = *what rows to show*. Policy = *who* gets that filter and on *which* tables/columns (by tag).

---

## 4. One UDF per value vs one UDF + mapping table

You have two ways to implement the *logic* (both are valid):

| Approach | What you create | Best for |
|----------|------------------|----------|
| **One UDF per value** | `fn_division_marketing`, `fn_division_sales`, … one UDF per division. One policy per group, each using one UDF. | Very few values (e.g. 2–3); you’re okay maintaining one UDF per value. |
| **One UDF + mapping table** | One table (e.g. `division_access`) that lists “principal → allowed division”. One UDF that returns true when the row’s column value is in that table for the current user. One policy. | Many values or many groups; you don’t want to add a new UDF every time you add a division. **This is the pattern the docs recommend for “mapping tables.”** |

**Takeaway:** You do **not** have to create four UDFs for four divisions. Use **one UDF + one mapping table** and one policy; add/change divisions by updating the table. Notebook **04_rls_abac_governed_tags** documents both options; the native guide uses the mapping-table pattern in **03_rls_manual_mapping_table** only.

---

## 5. What the docs say about UDF best practices

- **Prefer SQL UDFs** (faster than Python).
- **No `is_member()` / `is_account_group_member()` inside the UDF** — handle “who” in the policy.
- **Keep UDFs simple:** deterministic, no external calls, no heavy regex or complex subqueries if you can avoid it.
- **Mapping table:** Using a small lookup table (e.g. principal + allowed division) that the UDF reads is a supported and recommended pattern; keep the UDF logic simple (e.g. `EXISTS (SELECT 1 FROM mapping WHERE ...)`).

---

## 6. Quick decision guide

1. **Brand new?**  
   → Use **`RLS_NATIVE_SETUP_GUIDE.md`** and the **native row filter** notebook (mapping table + one UDF, manual `ALTER TABLE`).

2. **Need tag-based, central governance?**  
   → Use **`04_rls_abac_governed_tags`** (ABAC). Prefer **Option B** (one UDF + mapping table) unless you only have 2–3 fixed values.

3. **Many divisions or many groups?**  
   → Use **one UDF + one mapping table**; avoid one UDF per value.

4. **Official references:**  
   - [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/)  
   - [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices)  
   - [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply)

---

## Summary table

| Question | Best practice (from docs + this repo) |
|----------|--------------------------------------|
| ABAC vs manual? | Prefer ABAC for scale and central control; use manual for few tables / learning. |
| Who applies the filter — UDF or policy? | Policy = who/when; UDF = filter logic only. No `is_member()` in UDF. |
| One UDF per value or one UDF for all? | One UDF + mapping table when you have many values; one UDF per value only if 2–3 fixed values. |
| Where to start as a beginner? | Native row filter + `RLS_NATIVE_SETUP_GUIDE.md`, then ABAC when you need governed tags. |
