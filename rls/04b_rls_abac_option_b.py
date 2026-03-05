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
# MAGIC   ('financee', 'Finance'),
# MAGIC   ('home', 'Home');
# MAGIC -- Or use user emails: (current_user(), 'Marketing'), ... for user-level access.

# COMMAND ----------

# MAGIC %md
# MAGIC **Principal = user or group:** The UDF treats `principal` as either a **user email** (matches `current_user()`) or a **workspace group name** (matches `is_member(principal)`). The inserts above use **group names** (marketing, sales, engineering, financee, home) so any user in those groups sees the matching rows. If you're not in any of those groups and need to test, run the cell below to add your user email for all divisions.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Add current user to division_access so you can see rows when testing (run once if you get 0 rows)
# MAGIC INSERT INTO humana_payer.rls_abac_option_b.division_access (principal, division) VALUES
# MAGIC   (current_user(), 'Engineering'),
# MAGIC   (current_user(), 'Marketing'),
# MAGIC   (current_user(), 'Sales'),
# MAGIC   (current_user(), 'Finance'),
# MAGIC   (current_user(), 'Home');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- principal can be a user email (match current_user()) OR a workspace group (is_member(principal))
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac_option_b.fn_division_filter(division STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC LANGUAGE SQL
# MAGIC RETURN EXISTS (
# MAGIC   SELECT 1 FROM humana_payer.rls_abac_option_b.division_access a
# MAGIC   WHERE (a.principal = current_user() OR is_member(a.principal))
# MAGIC     AND a.division = division
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
# MAGIC -- Tag identifies the column for the policy; row values (Engineering, Marketing, etc.) are passed to fn_division_filter
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
# MAGIC - **Function parameters:** Map parameter `division` to the **column** that has the governed tag `division` (e.g. tag value Engineering). The system must pass that column's **row value** (Engineering, Marketing, Sales, etc.) to the function for each row — not the literal "Engineering". If only one division works, the UI may be passing the tag value; fix by ensuring the mapping uses the column's cell value. Governed tag allowed values (notebook 04) must include Marketing, Engineering, Sales, Finance, Home.  
# MAGIC
# MAGIC Keep **division_access** in sync with your groups; then you never add more UDFs or policies for new divisions.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Debug (if marketing user still sees all rows)
# MAGIC
# MAGIC Run the cell below **as the marketing user** (same session they use to query sample_data). This tests the UDF directly with each division value; the policy uses the same UDF with the row's division value.
# MAGIC
# MAGIC - **Expected for marketing-only user:** `fn_division_filter('Marketing')` = true, all others = false.
# MAGIC - If you get that, the UDF and division_access are correct; the issue is the **policy** (parameter binding, scope, or "Apply to tables that have specific tags").
# MAGIC - If `fn_division_filter('Engineering')` (or others) is true, fix **division_access** so principal `marketing` has only division `Marketing`.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Run as the marketing user. Expected: only Marketing = true.
# MAGIC SELECT 'Marketing' AS division, humana_payer.rls_abac_option_b.fn_division_filter('Marketing') AS allowed
# MAGIC UNION ALL SELECT 'Engineering', humana_payer.rls_abac_option_b.fn_division_filter('Engineering')
# MAGIC UNION ALL SELECT 'Sales', humana_payer.rls_abac_option_b.fn_division_filter('Sales')
# MAGIC UNION ALL SELECT 'Finance', humana_payer.rls_abac_option_b.fn_division_filter('Finance')
# MAGIC UNION ALL SELECT 'Home', humana_payer.rls_abac_option_b.fn_division_filter('Home');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Who is running: must be the marketing user (e.g. animesh.jha@databricks.com). If you see an admin email here, run this notebook logged in as the marketing user.
# MAGIC SELECT current_user() AS running_as;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Group membership for current user. For marketing-only user, only in_marketing should be true. If others are true, that user is in multiple groups (or account-level parents).
# MAGIC SELECT
# MAGIC   is_member('marketing')   AS in_marketing,
# MAGIC   is_member('sales')      AS in_sales,
# MAGIC   is_member('engineering') AS in_engineering,
# MAGIC   is_member('financee')   AS in_financee,
# MAGIC   is_member('home')      AS in_home;

# COMMAND ----------

# MAGIC %md
# MAGIC **Recreate UDF** — Run the cell below to refresh `fn_division_filter` (e.g. if the filter returns wrong results). No need to recreate the policy. Assumptions: `division_access` has group-based rows only (principal = group name, e.g. marketing, sales); principal can also be a user email for direct access.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Recreate UDF: principal = user email (current_user()) OR workspace group (is_member(principal)); division_access has one row per (principal, division).
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac_option_b.fn_division_filter(division STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC LANGUAGE SQL
# MAGIC RETURN EXISTS (
# MAGIC   SELECT 1 FROM humana_payer.rls_abac_option_b.division_access a
# MAGIC   WHERE (a.principal = current_user() OR is_member(a.principal))
# MAGIC     AND a.division = division
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC **If UDF returns correct (only Marketing = true) but filtered query still shows all rows:**
# MAGIC
# MAGIC 1. **Compute:** Row filter policies need **DBR 16.4+** or **serverless** SQL warehouse. Older compute can skip ABAC and show all rows. Check cluster/warehouse runtime.
# MAGIC 2. **"Apply to tables that have specific tags":** If this is **checked**, the policy only applies to tables (or columns) that have the chosen tag. If `sample_data` or its columns don't satisfy that, the policy won't apply and the user sees all rows. Either **uncheck** that option so the policy applies by scope only, or ensure the table/column has the required tag.
# MAGIC 3. **Scope:** Policy scope must include `humana_payer.rls_abac_option_b.sample_data` (or the schema so this table is included).
# MAGIC 4. **Group name:** "Applied to" must match the workspace group **exactly** (e.g. `marketing` lowercase). Check in **Workspace → Groups** and use the same spelling/case in the policy.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Verify
# MAGIC
# MAGIC **Workspace admins:** If you added yourself to the policy's **Except for** (e.g. "workspace admins"), you should see all rows without needing any `division_access` entries. If you still see no rows, check that (1) your user is in the exact group listed in **Except for** (some workspaces use "admins" or a custom group name), and (2) the policy is saved and the table scope is `humana_payer.rls_abac_option_b.sample_data`.
# MAGIC
# MAGIC **Other users:** The policy only shows rows where `division_access` has `principal = current_user()` for that row's division. Run the optional cell above (after Step 2) to add your user to `division_access` for all divisions, then re-run the query below.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM humana_payer.rls_abac_option_b.sample_data;
