# RLS Native Row Filter — Step-by-Step Implementation Guide

This guide walks you through deploying and implementing the RLS notebook using current Databricks best practices (native row filters with a **mapping table**).

---

## Prerequisites

- [ ] Unity Catalog enabled on your workspace
- [ ] Databricks Runtime 12.2 LTS+ (standard) or 15.4 LTS+ (dedicated)
- [ ] For writes (INSERT/UPDATE/DELETE/MERGE): DBR 16.3+
- [ ] You have `USE CATALOG`, `USE SCHEMA`, `CREATE TABLE`, `CREATE FUNCTION` on `humana_payer`
- [ ] `humana_admin` group exists (or you will use another admin group name)

---

## Step 1: Deploy the Bundle

```bash
cd /Users/vik.malhotra/databricks_rough_work
databricks bundle deploy -t staging
```

This deploys the notebook to your workspace at `setup/rls/03_rls_manual_mapping_table`.

---

## Step 2: Run the Notebook (First Time)

**Option A: Run manually**

1. Open the workspace in Databricks
2. Navigate to the deployed notebook at `setup/rls/03_rls_manual_mapping_table`
3. Run all cells sequentially (top to bottom)

**Option B: Run as a job**

```bash
databricks bundle run rls_03_manual_mapping -t staging
```

---

## Step 3: Customize Role Mapping

Edit the INSERT in **Step 1.2** of the notebook to match your groups:

```sql
INSERT INTO humana_payer.rls_v2.role_mapping (role_name, division_name) VALUES
  ('your_group_1', 'Engineering'),
  ('your_group_2', 'Marketing'),
  ('your_group_2', 'Sales'),
  ('your_executive_group', 'ALL'),
  ('humana_admin', 'ALL');
```

- Replace `data_engineers`, `business_analysts`, etc. with your actual account group names
- Use `ALL` for groups that should see all rows
- Admin group: `humana_admin` sees everything by default

---

## Step 4: Customize Admin Group (Optional)

If your admin group is not `humana_admin`, edit the function in **Step 1.3**:

```sql
-- Change 'humana_admin' to your admin group name
RETURN IF(is_account_group_member('your_admin_group'), true, ...)
```

Recreate the function after editing.

---

## Step 5: Apply to Your Production Tables

Once the setup is validated, apply the same pattern to your real tables:

```sql
-- 1. Ensure your table has a division column (STRING)
-- 2. Apply the row filter
ALTER TABLE your_catalog.your_schema.your_table
  SET ROW FILTER humana_payer.rls_v2.fn_division_row_filter ON (division);

-- 3. Grant SELECT to the appropriate groups
GRANT SELECT ON TABLE your_catalog.your_schema.your_table TO `account users`;
```

**Notes:**

- The column must match the function parameter type (STRING)
- If your column has a different name (e.g. `region`), create a new function or use an alias
- The filter is enforced at the table level; no view is needed

---

## Step 6: Verify

1. **As admin:** Query the table — you should see all rows
2. **As non-admin:** Query as a user in `data_engineers` — you should see only Engineering rows
3. **Check group membership:**

```sql
SELECT role_name, is_account_group_member(role_name) AS is_member
FROM humana_payer.rls_v2.role_mapping
GROUP BY role_name;
```

---

## Step 7: Remove Row Filter (If Needed)

```sql
ALTER TABLE humana_payer.rls_v2.sample_data DROP ROW FILTER;
```

---

## Summary Table

| Step | Action |
|------|--------|
| 1 | `databricks bundle deploy -t staging` |
| 2 | Run notebook (manual or `databricks bundle run rls_03_manual_mapping -t staging`) |
| 3 | Customize `role_mapping` with your groups |
| 4 | (Optional) Change admin group in the function |
| 5 | Apply `ALTER TABLE ... SET ROW FILTER` to your production tables |
| 6 | Grant SELECT and verify |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ROUTINE_NOT_FOUND" | Grant `EXECUTE` on the function to the querying principal |
| No rows returned | Check `role_mapping` and `is_account_group_member()` for your user |
| DBR too old | Upgrade to 12.2 LTS+ (standard) or 15.4 LTS+ (dedicated) |
| Writes fail | Use DBR 16.3+ for INSERT/UPDATE/DELETE/MERGE on filtered tables |

---

## References

- [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/)
- [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply)
- [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices)
