# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — RLS Manual Simple: UDF with is_member()
# MAGIC
# MAGIC **Demo order: 2 of 4.** Simple native row filter — good for few groups only.
# MAGIC
# MAGIC **What this is:** **Native** row filter on the table via `ALTER TABLE ... SET ROW FILTER`. The UDF encodes "who sees what" **inside the function** (e.g. `is_member('admins')`, `is_member('marketing')`, `division = 'Marketing'`). No mapping table; no governed tags.
# MAGIC
# MAGIC **Why use it:** Quick and clear for 2–3 groups. For a more scalable manual approach use **03** (mapping table); for central governance use **04** (ABAC).
# MAGIC
# MAGIC **Catalog:** `humana_payer` (all RLS notebooks reuse this catalog)  
# MAGIC **Schema:** `rls_manual`
# MAGIC
# MAGIC ---
# MAGIC **Documentation (follow along):**
# MAGIC - [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/) — overview of native row filters
# MAGIC - [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply) — `ALTER TABLE ... SET ROW FILTER` syntax and examples
# MAGIC - [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices) — why the simple UDF (with `is_member()` inside) is fine for few groups; for scale, see notebook **03** (mapping table).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Schema and Filter Function
# MAGIC
# MAGIC Schema holds the table and UDF. The UDF returns TRUE/FALSE per row; the engine hides rows where it returns FALSE. Use `is_member()` for workspace groups or `is_account_group_member()` for account-level groups.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS humana_payer.rls_manual
# MAGIC COMMENT 'RLS via Manual ALTER TABLE method';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Admin: all rows. Marketing: Marketing only. Sales: Sales only.
# MAGIC -- Use is_member() for workspace groups; is_account_group_member() for account groups
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_manual.fn_division_filter(division STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC LANGUAGE SQL
# MAGIC RETURN
# MAGIC   IF(is_member('admins'), true,
# MAGIC     (division = 'Marketing' AND is_member('marketing'))
# MAGIC     OR (division = 'Sales' AND is_member('sales'))
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Table and Insert Data
# MAGIC
# MAGIC **Note:** `CREATE OR REPLACE TABLE` replaces the table and all existing data. Use only when you intend to reset the demo table.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls_manual.sample_data (
# MAGIC   record_id STRING,
# MAGIC   division STRING,
# MAGIC   metric_value DOUBLE
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC INSERT INTO humana_payer.rls_manual.sample_data VALUES
# MAGIC   ('REC001', 'Engineering', 100.0),
# MAGIC   ('REC002', 'Marketing', 200.0),
# MAGIC   ('REC003', 'Sales', 300.0),
# MAGIC   ('REC004', 'Engineering', 150.0),
# MAGIC   ('REC005', 'Finance', 400.0);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Apply Row Filter (Manual Method)
# MAGIC
# MAGIC **Key command:** `ALTER TABLE ... SET ROW FILTER function ON (column)`. The filter is enforced on the table; users cannot bypass it. See [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply).

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE humana_payer.rls_manual.sample_data
# MAGIC   SET ROW FILTER humana_payer.rls_manual.fn_division_filter ON (division);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Grant Access
# MAGIC
# MAGIC Grant `SELECT` on the table and `EXECUTE` on the UDF so users can query the table (the row filter runs automatically).

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USAGE ON CATALOG humana_payer TO `account users`;
# MAGIC GRANT USAGE ON SCHEMA humana_payer.rls_manual TO `account users`;
# MAGIC GRANT SELECT ON TABLE humana_payer.rls_manual.sample_data TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_manual.fn_division_filter TO `account users`;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Validate

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM humana_payer.rls_manual.sample_data;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Apply to Another Table
# MAGIC
# MAGIC Use the same pattern for any table with a `division` column:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE your_catalog.your_schema.your_table
# MAGIC   SET ROW FILTER humana_payer.rls_manual.fn_division_filter ON (division);
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop Row Filter
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE humana_payer.rls_manual.sample_data DROP ROW FILTER;
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC **Next:** For a more scalable manual approach (mapping table, no hardcoded groups), run notebook **03**. For governed tags and central policies, run notebook **04**. Docs: [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply).
