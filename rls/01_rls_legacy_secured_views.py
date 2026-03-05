# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — RLS Legacy: Secured Views
# MAGIC
# MAGIC **Demo order: 1 of 4 (legacy).** Secured-views pattern — use only for reference or migration.
# MAGIC
# MAGIC **What this is:** Row-level security via **secured views** (users query a view that filters the base table). Uses a role mapping table + SQL security function; the view applies the filter in a WHERE clause.
# MAGIC
# MAGIC **Why it's legacy:** Views can be bypassed if users get direct access to the base table; Databricks now recommends **native row filters** on tables (see notebooks 03 and 04). Keep this for demos or legacy support only.
# MAGIC
# MAGIC **Catalog:** `humana_payer` (all RLS notebooks in this repo reuse this catalog; create it once in Unity Catalog if needed)  
# MAGIC **Schema:** `rls`
# MAGIC
# MAGIC ---
# MAGIC **Documentation (follow along):**
# MAGIC - [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/) — why native row filters replace this pattern
# MAGIC - [Unity Catalog overview](https://docs.databricks.com/data-governance/unity-catalog/) — catalogs, schemas, tables
# MAGIC - Run notebooks **02**, **03**, or **04** for the recommended approaches.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Schema
# MAGIC
# MAGIC Creates a schema in your catalog. You need `CREATE SCHEMA` on the catalog.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create the RLS schema under humana_payer catalog
# MAGIC CREATE SCHEMA IF NOT EXISTS humana_payer.rls
# MAGIC COMMENT 'Row-Level Security implementation schema';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Role Mapping Table
# MAGIC
# MAGIC This table maps user roles/groups to divisions they can access. Users in a role see only rows whose division is in their mapping. Restrict write access to admins.
# MAGIC
# MAGIC **Note:** `CREATE OR REPLACE TABLE` replaces the table and all existing data (effectively drops and recreates). Use only when you intend to reset; for production, consider `CREATE TABLE IF NOT EXISTS` and `INSERT`/`MERGE`.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls.role_mapping (
# MAGIC   role_name STRING COMMENT 'Azure AD group or role name',
# MAGIC   division_name STRING COMMENT 'Division name for access control',
# MAGIC   created_at TIMESTAMP,
# MAGIC   created_by STRING
# MAGIC )
# MAGIC COMMENT 'Maps user roles to divisions for row-level security';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Insert Sample Role Mappings
# MAGIC
# MAGIC Add sample mappings for testing. **Role names must match your workspace groups** (e.g. admins, engineering, marketing, sales, financee, home). Adjust if your groups differ.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Insert sample role mappings (use your workspace groups: admins, engineering, financee, home, marketing, sales)
# MAGIC INSERT INTO humana_payer.rls.role_mapping (role_name, division_name, created_at, created_by) VALUES
# MAGIC   ('engineering', 'Engineering', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('marketing', 'Marketing', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('sales', 'Sales', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('financee', 'Finance', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('home', 'Home', CURRENT_TIMESTAMP(), CURRENT_USER()),
# MAGIC   ('admins', 'ALL', CURRENT_TIMESTAMP(), CURRENT_USER());

# COMMAND ----------

# MAGIC %sql
# MAGIC -- View the role mappings
# MAGIC SELECT * FROM humana_payer.rls.role_mapping;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Create Security Function
# MAGIC
# MAGIC This function checks if a user has access to data based on their group membership and the division. **Workspace groups:** use `is_member()`. **Account groups:** use `is_account_group_member()` (commented below). See [UDF best practices](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices).

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls.fn_security_division_filter(
# MAGIC   p_security_division_name STRING
# MAGIC )
# MAGIC RETURNS BOOLEAN
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Security function to filter rows based on user group membership and division access'
# MAGIC RETURN
# MAGIC EXISTS (
# MAGIC   SELECT 1
# MAGIC   FROM humana_payer.rls.role_mapping r
# MAGIC   WHERE (
# MAGIC     (
# MAGIC       (
# MAGIC         -- Division match (single value per row in this demo)
# MAGIC         (p_security_division_name = r.division_name OR r.division_name = 'ALL')
# MAGIC       )
# MAGIC       -- AND is_account_group_member(r.role_name) = TRUE   -- account groups
# MAGIC       AND is_member(r.role_name) = TRUE                    -- workspace groups
# MAGIC     )
# MAGIC     -- OR is_account_group_member('humana_admin') = TRUE  -- account admin override
# MAGIC     OR is_member('admins') = TRUE                          -- workspace admin override
# MAGIC   )
# MAGIC );

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Create Sample Base Table
# MAGIC
# MAGIC Create a sample table to demonstrate RLS. `CREATE OR REPLACE TABLE` replaces the table and its data.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls.sample_data (
# MAGIC   record_id STRING,
# MAGIC   division STRING,
# MAGIC   security_division_name STRING COMMENT 'Division name for row-level filtering',
# MAGIC   metric_value DOUBLE,
# MAGIC   created_date DATE
# MAGIC )
# MAGIC COMMENT 'Sample data table for RLS demonstration';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Insert sample data (security_division_name = division; no commas needed)
# MAGIC INSERT INTO humana_payer.rls.sample_data VALUES
# MAGIC   ('REC001', 'Engineering', 'Engineering', 100.0, CURRENT_DATE()),
# MAGIC   ('REC002', 'Marketing', 'Marketing', 200.0, CURRENT_DATE()),
# MAGIC   ('REC003', 'Sales', 'Sales', 300.0, CURRENT_DATE()),
# MAGIC   ('REC004', 'Engineering', 'Engineering', 150.0, CURRENT_DATE()),
# MAGIC   ('REC005', 'Finance', 'Finance', 400.0, CURRENT_DATE()),
# MAGIC   ('REC006', 'Home', 'Home', 500.0, CURRENT_DATE());

# COMMAND ----------

# MAGIC %sql
# MAGIC -- View all data (without RLS)
# MAGIC SELECT * FROM humana_payer.rls.sample_data;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Create Secured View with RLS
# MAGIC
# MAGIC This view applies row-level security using the function. **Important:** Users must query the *view*, not the base table; if they have access to the base table they can bypass the filter. For table-level enforcement, use [native row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/) (notebook 03 or 04).

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW humana_payer.rls.vw_sample_data_secured AS
# MAGIC SELECT
# MAGIC   record_id,
# MAGIC   division,
# MAGIC   security_division_name,
# MAGIC   metric_value,
# MAGIC   created_date,
# MAGIC   CURRENT_USER() as accessed_by,
# MAGIC   CURRENT_TIMESTAMP() as accessed_at
# MAGIC FROM humana_payer.rls.sample_data
# MAGIC WHERE humana_payer.rls.fn_security_division_filter(security_division_name);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Query the secured view (will only show data user has access to)
# MAGIC SELECT * FROM humana_payer.rls.vw_sample_data_secured;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Testing & Validation

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Test 1: Check current user's group memberships
# MAGIC SELECT
# MAGIC   role_name,
# MAGIC   -- is_account_group_member(role_name) as is_member  -- account groups
# MAGIC   is_member(role_name) as is_member                     -- workspace groups
# MAGIC FROM humana_payer.rls.role_mapping
# MAGIC GROUP BY role_name;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Test 2: Count records with vs without RLS
# MAGIC SELECT
# MAGIC   'Base Table (No RLS)' as source,
# MAGIC   COUNT(*) as record_count
# MAGIC FROM humana_payer.rls.sample_data
# MAGIC UNION ALL
# MAGIC SELECT
# MAGIC   'Secured View (With RLS)' as source,
# MAGIC   COUNT(*) as record_count
# MAGIC FROM humana_payer.rls.vw_sample_data_secured;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key Implementation Notes
# MAGIC
# MAGIC ### Performance Considerations
# MAGIC - `is_member()` / `is_account_group_member()` is evaluated once per query, not per row (cached)
# MAGIC - Predicate pushdown optimization applies
# MAGIC - For large datasets, consider materialized views
# MAGIC
# MAGIC ### Security Best Practices
# MAGIC 1. **Function is deterministic** - Same inputs always return same outputs during query execution
# MAGIC 2. **Time travel preserved** - Base table retains full Delta Lake history
# MAGIC 3. **Audit trail** - View adds accessed_by and accessed_at columns
# MAGIC
# MAGIC ### Potential Improvements
# MAGIC 1. Use ARRAY type instead of comma-delimited strings for divisions
# MAGIC 2. Externalize admin group to configuration table
# MAGIC 3. Add comprehensive unit tests for each user group
# MAGIC 4. Monitor query performance in system.query.history
# MAGIC 5. Consider liquid clustering on role_mapping table
# MAGIC
# MAGIC ### Anti-patterns to Avoid
# MAGIC - LIKE with comma-delimited strings is fragile (consider proper ARRAY types)
# MAGIC - Hardcoded admin groups create maintenance burden
# MAGIC - Missing documentation on security function behavior

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Grant Permissions (Run as Admin)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Grant usage on catalog and schema
# MAGIC GRANT USAGE ON CATALOG humana_payer TO `account users`;
# MAGIC GRANT USAGE ON SCHEMA humana_payer.rls TO `account users`;
# MAGIC
# MAGIC -- Grant SELECT on the secured view only (not the base table)
# MAGIC GRANT SELECT ON VIEW humana_payer.rls.vw_sample_data_secured TO `account users`;
# MAGIC
# MAGIC -- Grant SELECT on role_mapping to the security function
# MAGIC GRANT SELECT ON TABLE humana_payer.rls.role_mapping TO `account users`;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Completion Summary
# MAGIC
# MAGIC ✅ Created schema: `humana_payer.rls`
# MAGIC ✅ Created role mapping table
# MAGIC ✅ Created security function: `fn_security_division_filter`
# MAGIC ✅ Created sample data and secured view
# MAGIC ✅ Added testing queries
# MAGIC
# MAGIC **Next Steps:**
# MAGIC 1. Add actual user groups to role_mapping table
# MAGIC 2. Apply RLS pattern to production tables
# MAGIC 3. Set up monitoring and audit logging
# MAGIC 4. Document security model for compliance
# MAGIC
# MAGIC **Recommended:** For new implementations, use **native row filters** instead of secured views. Run notebook **02** (simple UDF), **03** (mapping table), or **04** (ABAC). See [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/).
