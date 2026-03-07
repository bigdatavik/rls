# RLS Native Row Filter — Step-by-Step Implementation Guide

This guide walks you through deploying and implementing the RLS notebook using current **Databricks best practices** (native row filters with a **mapping table**). It aligns with the official docs for row filters, UDF design, and Unity Catalog governance.

---

## Prerequisites

- [ ] Unity Catalog enabled on your workspace
- [ ] **Compute runtime:**
  - **Read:** Databricks Runtime 12.2 LTS+ (standard) or 15.4 LTS+ (dedicated). If using dedicated 15.4+, workspace must be **enabled for serverless** (filtering runs on serverless).
  - **Write** (INSERT/UPDATE/DELETE/MERGE on filtered tables): DBR 16.3+
- [ ] You have `USE CATALOG`, `USE SCHEMA`, `CREATE TABLE`, `CREATE FUNCTION` on the target catalog (e.g. `humana_payer`)
- [ ] Prefer **account-level groups** for principals; use `is_account_group_member()` in the UDF. If you use workspace groups, `is_member()` is supported but account groups are recommended for Unity Catalog. See [Unity Catalog best practices](https://docs.databricks.com/en/data-governance/unity-catalog/best-practices.html).

---

## Step 1: Deploy the Bundle

```bash
cd /Users/vik.malhotra/rls
databricks bundle deploy -t staging
```

This deploys the notebook to your workspace (path may vary; typically under your user folder or a setup path). The job name is `rls_03_manual_mapping` for the staging target.

---

## Step 2: Run the Notebook (First Time)

**Option A: Run manually**

1. Open the workspace in Databricks
2. Navigate to the deployed notebook (e.g. `rls/03_rls_manual_mapping_table.py` or as shown after deploy)
3. Run all cells sequentially (top to bottom)

**Option B: Run as a job**

```bash
databricks bundle run rls_03_manual_mapping -t staging
```

---

## Step 3: Customize Role Mapping

Edit the INSERT in **Step 1.2** of the notebook to match your **account group** names (recommended) or workspace group names:

```sql
INSERT INTO humana_payer.rls_v2.role_mapping (role_name, division_name, created_at, created_by) VALUES
  ('your_account_group_1', 'Engineering'),
  ('your_account_group_2', 'Marketing'),
  ('your_account_group_2', 'Sales'),
  ('your_executive_group', 'ALL'),
  ('humana_admin', 'ALL');
```

- **Account groups:** Use the exact group name as in Unity Catalog (e.g. from IdP/SCIM). In the UDF, use `is_account_group_member(r.role_name)` and comment out `is_member(r.role_name)`.
- **Workspace groups:** Use workspace group names and `is_member(r.role_name)` in the UDF (as in the default notebook).
- Use `ALL` for groups that should see all rows.
- Restrict **writes** to `role_mapping` to admins (e.g. no broad `MODIFY`); the UDF only needs to **read** it.

---

## Step 4: Customize Admin Group (Optional)

If your admin group is not `admins` (workspace) or `humana_admin` (account), edit the function in **Step 1.3**:

```sql
-- For account-level admin (recommended in Unity Catalog):
RETURN IF(is_account_group_member('your_admin_group'), true, ...)

-- For workspace-level admin (default in notebook):
RETURN IF(is_member('admins'), true, ...)
```

Recreate the function after editing. **Best practice:** Use one admin bypass in the UDF; keep all other “who sees which division” logic in the mapping table. See [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices).

---

## Step 5: Apply to Your Production Tables

Once the setup is validated, apply the same pattern to your real tables:

```sql
-- 1. Ensure your table has a division column (STRING)
-- 2. Apply the row filter
ALTER TABLE your_catalog.your_schema.your_table
  SET ROW FILTER humana_payer.rls_v2.fn_division_row_filter ON (division);

-- 3. Grant SELECT to the appropriate groups (prefer groups over direct user grants)
GRANT SELECT ON TABLE your_catalog.your_schema.your_table TO `account users`;
-- Or grant to specific account groups:
-- GRANT SELECT ON TABLE ... TO `your_group`;
```

**Notes:**

- The column must match the function parameter type (e.g. STRING). If your column has a different name (e.g. `region`), create a new function or add a function that accepts that column.
- The filter is enforced at the table level; no view is needed and it cannot be bypassed by querying the table directly.
- **Ownership:** For production, assign table (and schema/catalog) ownership to groups rather than individual users. See [Unity Catalog best practices](https://docs.databricks.com/en/data-governance/unity-catalog/best-practices.html).
- **Discoverability:** Optionally grant `BROWSE` on the catalog so users can discover data and request access; `BROWSE` does not grant data access.

---

## Step 6: Verify

1. **As admin:** Query the table — you should see all rows.
2. **As non-admin:** Query as a user in a group that has only one division (e.g. Engineering) — you should see only that division’s rows.
3. **Check group membership:**

```sql
SELECT role_name, is_account_group_member(role_name) AS is_member
FROM humana_payer.rls_v2.role_mapping
GROUP BY role_name;
```

If you use workspace groups, use `is_member(role_name)` instead of `is_account_group_member(role_name)` for the check.

4. **Performance (optional):** For large tables, validate the UDF at scale (e.g. 1M+ rows) per [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices).

---

## Step 7: Remove Row Filter (If Needed)

```sql
ALTER TABLE humana_payer.rls_v2.sample_data DROP ROW FILTER;
```

---

## Summary Table

| Step | Action |
|------|--------|
| 1 | `databricks bundle deploy -t staging` (from repo root `rls`) |
| 2 | Run notebook (manual or `databricks bundle run rls_03_manual_mapping -t staging`) |
| 3 | Customize `role_mapping` with your account or workspace groups |
| 4 | (Optional) Change admin group in the function; prefer `is_account_group_member` for UC |
| 5 | Apply `ALTER TABLE ... SET ROW FILTER` to your production tables; grant SELECT (and optionally BROWSE) |
| 6 | Grant EXECUTE on the UDF, SELECT on the table and mapping table; verify as admin and non-admin |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **ROUTINE_NOT_FOUND** | Grant `EXECUTE` on the row filter function to the querying principal (e.g. `account users` or the group used for SELECT). |
| No rows returned | Check `role_mapping` and that the user is in a group listed there; verify with `is_account_group_member()` or `is_member()` as appropriate. |
| DBR too old | Use DBR 12.2 LTS+ (standard) or 15.4 LTS+ (dedicated) for **read**. For **write** to filtered tables, use DBR 16.3+. |
| Writes fail on filtered table | Use DBR 16.3+ and supported patterns (e.g. `MERGE INTO`). |
| Dedicated cluster 15.4+ but filters not applied | Ensure the workspace is **enabled for serverless**; row filter evaluation for dedicated 15.4+ runs on serverless. |
| Want central, tag-based control | Consider ABAC (notebook 04 or 04b) with DBR 16.4+; see `RLS_BEST_PRACTICES_FOR_BEGINNERS.md`. |

---

## References

- [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/)
- [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply)
- [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices)
- [Unity Catalog best practices](https://docs.databricks.com/en/data-governance/unity-catalog/best-practices.html)
- [Fine-grained access control on dedicated compute](https://docs.databricks.com/compute/single-user-fgac) (serverless requirement for 15.4+ dedicated)
