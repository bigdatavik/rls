# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — RLS Manual Best Practice: Mapping Table + Native Row Filter
# MAGIC
# MAGIC **Demo order: 3 of 4.** Recommended **manual** approach for production.
# MAGIC
# MAGIC **What this is:** **Native** row filter on the table via `ALTER TABLE ... SET ROW FILTER`. Uses a **mapping table** (role_mapping) to define which groups see which divisions — no hardcoded groups in the UDF. Add/change access by updating the table. Protection is at the table level; cannot be bypassed.
# MAGIC
# MAGIC **Why use it:** Best practice when you want manual control per table without governed tags. Simpler but less scalable: **02** (simple UDF). For central governance: **04 (ABAC)**.
# MAGIC
# MAGIC **Catalog:** `humana_payer` (all RLS notebooks reuse this catalog)  
# MAGIC **Schema:** `rls_v2`
# MAGIC
# MAGIC ---
# MAGIC **Documentation (follow along):**
# MAGIC - [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/) — overview, when to use row filters vs views
# MAGIC - [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply) — `ALTER TABLE ... SET ROW FILTER`, parameter mapping, limitations
# MAGIC - [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices) — keeping UDF logic simple; mapping table pattern recommended
# MAGIC - **RLS_NATIVE_SETUP_GUIDE.md** (this folder) — deployment steps and customizing `role_mapping`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prerequisites
# MAGIC
# MAGIC - Unity Catalog enabled
# MAGIC - Databricks Runtime 12.2 LTS+ (standard) or 15.4 LTS+ (dedicated)
# MAGIC - Writes: DBR 16.3+ (INSERT/UPDATE/DELETE/MERGE)
# MAGIC - You have `USE CATALOG`, `USE SCHEMA`, `CREATE TABLE`, `CREATE FUNCTION` on `humana_payer`

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Part 1: Setup (Run Once)
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1.1: Create Schema

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS humana_payer.rls_v2
# MAGIC COMMENT 'RLS v2 - Native row filter implementation';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1.2: Create Role Mapping Table
# MAGIC
# MAGIC Maps groups to divisions. One row per (group, division); use `ALL` for full access. Restrict this table to admins (no public writes). The UDF reads it at query time — see [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices).
# MAGIC
# MAGIC **Note:** `CREATE OR REPLACE TABLE` replaces the table and all existing data. For production, use `CREATE TABLE IF NOT EXISTS` and `INSERT`/`MERGE` to avoid losing data.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls_v2.role_mapping (
# MAGIC   role_name STRING COMMENT 'Workspace group name (e.g. engineering, marketing)',
# MAGIC   division_name STRING COMMENT 'Division for access control; use ALL for full access',
# MAGIC   created_at TIMESTAMP,
# MAGIC   created_by STRING
# MAGIC )
# MAGIC COMMENT 'Maps groups to divisions. Restrict to admins.';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Insert sample mappings (use your workspace groups: admins, engineering, marketing, sales, financee, home)
# MAGIC INSERT INTO humana_payer.rls_v2.role_mapping (role_name, division_name, created_at, created_by) VALUES
# MAGIC   ('engineering', 'Engineering', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('marketing', 'Marketing', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('sales', 'Sales', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('financee', 'Finance', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('home', 'Home', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('admins', 'ALL', CURRENT_TIMESTAMP(), CURRENT_USER());

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1.3: Create Row Filter Function
# MAGIC
# MAGIC Uses `RETURN IF` for admin shortcut (evaluated first). Then checks mapping table. **Admin override:** `admins` (workspace) sees all rows. **Division match:** user's group must have this division or `ALL`. Use `is_member()` for workspace groups; see commented lines for account groups. — [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices).

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_v2.fn_division_row_filter(division STRING)
# MAGIC RETURNS BOOLEAN
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Row filter: user sees row if their group has this division or ALL'
# MAGIC RETURN
# MAGIC   -- IF(is_account_group_member('humana_admin'), true,   -- account admin
# MAGIC   IF(is_member('admins'), true,                           -- workspace admin
# MAGIC     EXISTS (
# MAGIC       SELECT 1
# MAGIC       FROM humana_payer.rls_v2.role_mapping r
# MAGIC       WHERE (r.division_name = division OR r.division_name = 'ALL')
# MAGIC         -- AND is_account_group_member(r.role_name) = true  -- account groups
# MAGIC         AND is_member(r.role_name) = true                    -- workspace groups
# MAGIC     )
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1.4: Grant Access on role_mapping
# MAGIC
# MAGIC The filter function reads role_mapping when users query; they need SELECT.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Grant SELECT on role_mapping to account users (required for row filter to evaluate)
# MAGIC GRANT SELECT ON TABLE humana_payer.rls_v2.role_mapping TO `account users`;
# MAGIC -- Restrict writes via workspace/table ACLs. UC GRANT MODIFY requires an account-level principal;
# MAGIC -- workspace group 'admins' is not a UC principal, so we do not GRANT MODIFY here (matches notebook 01).

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Part 2: Create Table and Apply Row Filter
# MAGIC ---

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2.1: Create Base Table
# MAGIC
# MAGIC Use a single `division` column per row. For multi-division rows, use a separate design (e.g. bridge table). `CREATE OR REPLACE TABLE` here replaces the demo table and its data.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls_v2.sample_data (
# MAGIC   record_id STRING,
# MAGIC   division STRING COMMENT 'Division for row-level filtering',
# MAGIC   metric_value DOUBLE,
# MAGIC   created_date DATE
# MAGIC )
# MAGIC COMMENT 'Sample data with native row filter';

# COMMAND ----------

# MAGIC %sql
# MAGIC INSERT INTO humana_payer.rls_v2.sample_data VALUES
# MAGIC   ('REC001', 'Engineering', 100.0, CURRENT_DATE()),
# MAGIC   ('REC002', 'Marketing', 200.0, CURRENT_DATE()),
# MAGIC   ('REC003', 'Sales', 300.0, CURRENT_DATE()),
# MAGIC   ('REC004', 'Engineering', 150.0, CURRENT_DATE()),
# MAGIC   ('REC005', 'Finance', 400.0, CURRENT_DATE());

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2.2: Apply Native Row Filter to Table
# MAGIC
# MAGIC **This is the key step.** The filter is enforced on the table; no view needed. Users cannot bypass it. [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply).

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE humana_payer.rls_v2.sample_data
# MAGIC   SET ROW FILTER humana_payer.rls_v2.fn_division_row_filter ON (division);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2.3: Grant Access
# MAGIC
# MAGIC Grant SELECT on the **table** (not a view). The row filter applies automatically.

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USAGE ON CATALOG humana_payer TO `account users`;
# MAGIC GRANT USAGE ON SCHEMA humana_payer.rls_v2 TO `account users`;
# MAGIC GRANT SELECT ON TABLE humana_payer.rls_v2.sample_data TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_v2.fn_division_row_filter TO `account users`;

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Part 3: Validation
# MAGIC ---

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Query as current user (filter applies automatically)
# MAGIC SELECT * FROM humana_payer.rls_v2.sample_data;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check group memberships
# MAGIC SELECT
# MAGIC   role_name,
# MAGIC   -- is_account_group_member(role_name) AS is_member  -- account groups
# MAGIC   is_member(role_name) AS is_member                     -- workspace groups
# MAGIC FROM humana_payer.rls_v2.role_mapping
# MAGIC GROUP BY role_name;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: Drop Row Filter
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE humana_payer.rls_v2.sample_data DROP ROW FILTER;
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Deployment Steps (After Deploying This Notebook)
# MAGIC ---
# MAGIC
# MAGIC 1. **Deploy the bundle** (if using DAB):
# MAGIC    ```bash
# MAGIC    databricks bundle deploy -t staging
# MAGIC    ```
# MAGIC
# MAGIC 2. **Run this notebook** in order (top to bottom), or run as a job.
# MAGIC
# MAGIC 3. **Customize role_mapping** (Step 1.2):
# MAGIC    - Replace `data_engineers`, `business_analysts`, etc. with your actual account group names
# MAGIC    - Add/remove rows as needed
# MAGIC
# MAGIC 4. **Customize admin group** (Step 1.3):
# MAGIC    - Change `admins` to your workspace admin group name in the function if needed
# MAGIC
# MAGIC 5. **Apply to your production tables**:
# MAGIC    ```sql
# MAGIC    ALTER TABLE your_catalog.your_schema.your_table
# MAGIC      SET ROW FILTER humana_payer.rls_v2.fn_division_row_filter ON (your_division_column);
# MAGIC    ```
# MAGIC    Ensure your table has a column that matches the filter parameter type (STRING).
# MAGIC
# MAGIC 6. **Grant SELECT** on the table to the appropriate groups (no view needed).
# MAGIC
# MAGIC 7. **Verify** by querying as different users/groups and confirming row visibility.
# MAGIC
# MAGIC ---
# MAGIC **Next:** For governed tags and central policies (one policy for many tables), run notebook **04**. Docs: [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/), [RLS_NATIVE_SETUP_GUIDE.md](RLS_NATIVE_SETUP_GUIDE.md).
