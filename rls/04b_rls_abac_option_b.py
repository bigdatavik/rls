# Databricks notebook source
# MAGIC %md
# MAGIC # 04b — RLS ABAC Option B: One policy + mapping table (separate table)
# MAGIC
# MAGIC **Run after notebook 04** (governed tag from UI). This notebook is **Option B only**: everything in **one schema** **rls_abac_option_b** — division_access, fn_division_filter, sample_data, and the one policy. No mixing with 04 or rls_abac.
# MAGIC
# MAGIC **Catalog:** `humana_payer`  
# MAGIC **Schema:** `rls_abac_option_b` only (division_access, fn_division_filter, sample_data — all in one schema)
# MAGIC
# MAGIC ---
# MAGIC **Documentation:** [ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/), [Microsoft tutorial](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prerequisite
# MAGIC
# MAGIC Create the **governed tag** `division` (UI Step 1 in notebook 04). No need for schema rls_abac — this notebook uses **only** schema **rls_abac_option_b**.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create schema rls_abac_option_b (all Option B objects live here)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS humana_payer.rls_abac_option_b
# MAGIC COMMENT 'Option B only: division_access, fn_division_filter, sample_data';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create division_access table + fn_division_filter UDF

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls_abac_option_b.division_access (
# MAGIC   principal STRING COMMENT 'User email (current_user()) OR workspace group name (e.g. marketing, sales)',
# MAGIC   division  STRING COMMENT 'Allowed division value'
# MAGIC );
# MAGIC -- Use workspace group names so any user in that group gets access (recommended)
# MAGIC INSERT INTO humana_payer.rls_abac_option_b.division_access (principal, division) VALUES
# MAGIC   ('marketing', 'Marketing'),
# MAGIC   ('sales', 'Sales'),
# MAGIC   ('engineering', 'Engineering'),
# MAGIC   ('finance', 'Finance'),
# MAGIC   ('home', 'Home');
# MAGIC -- Or use user emails: (current_user(), 'Marketing'), ... for user-level access.

# COMMAND ----------

# MAGIC %md
# MAGIC **Principal = user or group:** The UDF treats `principal` as either a **user email** (matches `current_user()`) or a **workspace group name** (matches `is_member(principal)`). The inserts above use **group names** (marketing, sales, engineering, financee, home) so any user in those groups sees the matching rows. If you're not in any of those groups and need to test, run the cell below to add your user email for all divisions.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Add current user to division_access so you can see rows when testing (run once if you get 0 rows)
# MAGIC -- INSERT INTO humana_payer.rls_abac_option_b.division_access (principal, division) VALUES
# MAGIC --   (current_user(), 'Engineering'),
# MAGIC --   (current_user(), 'Marketing'),
# MAGIC --   (current_user(), 'Sales'),
# MAGIC --   (current_user(), 'Finance'),
# MAGIC --   (current_user(), 'Home');

# COMMAND ----------

# %sql
# -- principal can be a user email (match current_user()) OR a workspace group (is_member(principal))
# CREATE OR REPLACE FUNCTION humana_payer.rls_abac_option_b.fn_division_filter(division STRING)
# RETURNS BOOLEAN
# LANGUAGE SQL
# RETURN EXISTS (
#   SELECT 1 FROM humana_payer.rls_abac_option_b.division_access a
#   WHERE (a.principal = current_user() OR is_member(a.principal))
#     AND a.division = division
# );

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac_option_b.fn_division_filter(div_value STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC LANGUAGE SQL
# MAGIC RETURN EXISTS (
# MAGIC   SELECT 1 FROM humana_payer.rls_abac_option_b.division_access a
# MAGIC     WHERE a.division = div_value
# MAGIC       AND (a.principal = current_user() OR is_member(a.principal))
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create sample_data table (policy applies to this table)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls_abac_option_b.sample_data (
# MAGIC   record_id STRING,
# MAGIC   division STRING,
# MAGIC   metric_value DOUBLE
# MAGIC );
# MAGIC INSERT INTO humana_payer.rls_abac_option_b.sample_data VALUES
# MAGIC   ('B001', 'Engineering', 110.0),
# MAGIC   ('B002', 'Marketing', 220.0),
# MAGIC   ('B003', 'Sales', 330.0),
# MAGIC   ('B004', 'Finance', 440.0),
# MAGIC   ('B005', 'Home', 550.0);

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE humana_payer.rls_abac_option_b.sample_data
# MAGIC   ALTER COLUMN division SET TAGS ('division' = 'Engineering');

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Grant access

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USAGE ON SCHEMA humana_payer.rls_abac_option_b TO `account users`;
# MAGIC GRANT SELECT ON TABLE humana_payer.rls_abac_option_b.division_access TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_abac_option_b.fn_division_filter TO `account users`;
# MAGIC GRANT SELECT ON TABLE humana_payer.rls_abac_option_b.sample_data TO `account users`;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: UI — Create one policy (scope = rls_abac_option_b only)
# MAGIC
# MAGIC **Catalog** → **humana_payer** → **Policies** → **New policy**.
# MAGIC
# MAGIC - **Name:** `division_filter`  
# MAGIC - **Applied to:** e.g. marketing, sales, engineering, finance (or leave broad); UDF + division_access decide visibility.  
# MAGIC - **Except for:** workspace admins.  
# MAGIC - **Scope:** catalog humana_payer, schema **rls_abac_option_b**.  
# MAGIC - **Purpose:** Hide table rows.  
# MAGIC - **Conditions:** Select function **humana_payer.rls_abac_option_b.fn_division_filter**.  
# MAGIC - **Function parameters:** Map column by tag → division : **Engineering** (matches column tag above).
# MAGIC
# MAGIC Keep **division_access** in sync with your groups; then you never add more UDFs or policies for new divisions.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Verify
# MAGIC
# MAGIC **Workspace admins:** If you added yourself to the policy's **Except for** (e.g. "workspace admins"), you should see all rows without needing any `division_access` entries. If you still see no rows, check that (1) your user is in the exact group listed in **Except for** (some workspaces use "admins" or a custom group name), and (2) the policy is saved and the table scope is `humana_payer.rls_abac_option_b.sample_data`.
# MAGIC
# MAGIC **Other users:** The policy only shows rows where `division_access` has `principal = current_user()` for that row's division. Run the optional cell above (after Step 2) to add your user to `division_access` for all divisions, then re-run the query below.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM humana_payer.rls_abac_option_b.sample_data;