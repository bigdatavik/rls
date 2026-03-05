# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — RLS ABAC: Governed Tags + Policies (Best)
# MAGIC
# MAGIC **Demo order: 4 of 4 (best).** Recommended for governance at scale.
# MAGIC
# MAGIC **What this is:** **Attribute-Based Access Control** — governed tags on columns + **policies** in the UI (Applied to / Except / Scope / Hide table rows). One policy can apply to many tables that have the same tag. "Who sees what" is defined in the policy (Option A) or in a mapping table (Option B). Table owners cannot remove policies.
# MAGIC
# MAGIC **Why use it:** Central control, scales across catalogs/schemas, aligns with Databricks and Microsoft tutorial guidance. Use this for new implementations when you have many tables or need strong governance.
# MAGIC
# MAGIC **Prerequisites:** DBR 16.4+ or serverless; account admin for governed tags; catalog `humana_payer`, groups e.g. `marketing`, `sales`, **workspace admins** in Except.
# MAGIC
# MAGIC **Catalog:** `humana_payer` (all RLS notebooks reuse this catalog)  
# MAGIC **Schema:** `rls_abac`
# MAGIC
# MAGIC ---
# MAGIC **Documentation (follow along):**
# MAGIC - [Attribute-based access control (ABAC)](https://docs.databricks.com/data-governance/unity-catalog/abac/) — governed tags, policies, row filters and column masks
# MAGIC - [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/) — how filters work with ABAC
# MAGIC - [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices) — keep UDF logic simple; use policy for "who"
# MAGIC - [Tutorial: Configure ABAC (Microsoft)](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial) — step-by-step UI flow (governed tag, policy, Function parameters)
# MAGIC - **RLS_BEST_PRACTICES_FOR_BEGINNERS.md** (this folder) — when to use ABAC vs manual; Option B = **04b_rls_abac_option_b**

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # UI Step 1: Create Governed Tag (do this in the UI first)
# MAGIC
# MAGIC This step follows the **Databricks ABAC tutorial** (governed tags + policies). Governed tags define allowed key-value pairs; policies then match columns by tag. See [ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/) and [Microsoft tutorial Step 1](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial).
# MAGIC ---
# MAGIC
# MAGIC 1. In the left sidebar, click **Catalog**.
# MAGIC 2. Click the **Govern** button (top right).
# MAGIC 3. In the dropdown, click **Governed Tags**.
# MAGIC 4. Click **Create governed tag**.
# MAGIC 5. Enter:
# MAGIC    - **Tag key:** `division`
# MAGIC    - **Description:** `Division for row-level security`
# MAGIC    - **Allowed values:** Add each: `Marketing`, `Sales`, `Engineering`, `Finance`, `Home`
# MAGIC 6. Click **Create**.
# MAGIC
# MAGIC When done, run the cells below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Schema (shared)
# MAGIC
# MAGIC Schema **rls_abac** holds the Option A table and UDFs. For Option B (one policy + mapping table), use notebook **04b_rls_abac_option_b**.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS humana_payer.rls_abac
# MAGIC COMMENT 'RLS via ABAC policies';

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Part 1: Option A — One policy per division
# MAGIC ---
# MAGIC
# MAGIC **Flow:** One table (**sample_data**), one UDF per division, one policy per group (marketing, sales, engineering, finance). Scope = schema **rls_abac**.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option A: Create table, tag column, create UDFs

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE humana_payer.rls_abac.sample_data (
# MAGIC   record_id STRING,
# MAGIC   division STRING,
# MAGIC   metric_value DOUBLE
# MAGIC );
# MAGIC INSERT INTO humana_payer.rls_abac.sample_data VALUES
# MAGIC   ('REC001', 'Engineering', 100.0),
# MAGIC   ('REC002', 'Marketing', 200.0),
# MAGIC   ('REC003', 'Sales', 300.0),
# MAGIC   ('REC004', 'Marketing', 150.0),
# MAGIC   ('REC005', 'Finance', 400.0);

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE humana_payer.rls_abac.sample_data
# MAGIC   ALTER COLUMN division SET TAGS ('division' = 'Marketing');

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac.fn_division_marketing(division STRING)
# MAGIC RETURNS BOOLEAN LANGUAGE SQL RETURN division = 'Marketing';
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac.fn_division_sales(division STRING)
# MAGIC RETURNS BOOLEAN LANGUAGE SQL RETURN division = 'Sales';
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac.fn_division_engineering(division STRING)
# MAGIC RETURNS BOOLEAN LANGUAGE SQL RETURN division = 'Engineering';
# MAGIC CREATE OR REPLACE FUNCTION humana_payer.rls_abac.fn_division_finance(division STRING)
# MAGIC RETURNS BOOLEAN LANGUAGE SQL RETURN division = 'Finance';

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option A: Grant access

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USAGE ON CATALOG humana_payer TO `account users`;
# MAGIC GRANT USAGE ON SCHEMA humana_payer.rls_abac TO `account users`;
# MAGIC GRANT SELECT ON TABLE humana_payer.rls_abac.sample_data TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_abac.fn_division_marketing TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_abac.fn_division_sales TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_abac.fn_division_engineering TO `account users`;
# MAGIC GRANT EXECUTE ON FUNCTION humana_payer.rls_abac.fn_division_finance TO `account users`;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option A: UI — Create one policy per division (Marketing, Sales, Engineering, Finance)
# MAGIC
# MAGIC For all policies: **Catalog** → **humana_payer** → **Policies** tab → **New policy**. **Except for** = workspace admins. **Scope** = catalog **humana_payer**, schema **rls_abac**. **Purpose** = **Hide table rows**. [Microsoft tutorial](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/abac/tutorial).
# MAGIC
# MAGIC **Summary table:**
# MAGIC
# MAGIC | Policy name | Applied to | Function | Function param (tag) |
# MAGIC |-------------|------------|----------|----------------------|
# MAGIC | division_filter_marketing | marketing | fn_division_marketing | division : Marketing |
# MAGIC | division_filter_sales | sales | fn_division_sales | division : Sales |
# MAGIC | division_filter_engineering | engineering | fn_division_engineering | division : Engineering |
# MAGIC | division_filter_finance | financee | fn_division_finance | division : Finance |

# COMMAND ----------

# MAGIC %md
# MAGIC #### Step-by-step: Policy for Marketing
# MAGIC
# MAGIC 1. **Catalog** → **humana_payer** → **Policies** tab → **New policy**.
# MAGIC 2. **General**
# MAGIC    - **Name\***: `division_filter_marketing`
# MAGIC    - **Description:** e.g. `Row filter for marketing division`
# MAGIC    - **Applied to\***: Add group `marketing` (pill).
# MAGIC    - **Except for:** Add **workspace admins**.
# MAGIC    - **Scope\***: Catalog **humana_payer**, schema **rls_abac**. Do not check "Apply to tables that have specific tags".
# MAGIC 3. **Purpose** → Select **Hide table rows**.
# MAGIC 4. **Conditions** → **Select existing** → **Select function** → **humana_payer.rls_abac.fn_division_marketing** → **Select**. Optionally **Test function** with value `Marketing` (should return TRUE).
# MAGIC 5. **Function parameters** → **Map column to parameter if it has a specific tag** → search `division` → select **division : Marketing**.
# MAGIC 6. **Create policy**.

# COMMAND ----------

# MAGIC %md
# MAGIC #### Step-by-step: Policy for Sales
# MAGIC
# MAGIC 1. **Policies** → **New policy**.
# MAGIC 2. **General**
# MAGIC    - **Name\***: `division_filter_sales`
# MAGIC    - **Applied to\***: Add group `sales`
# MAGIC    - **Except for:** workspace admins
# MAGIC    - **Scope\***: humana_payer, rls_abac
# MAGIC 3. **Purpose** → **Hide table rows**.
# MAGIC 4. **Conditions** → **Select existing** → **humana_payer.rls_abac.fn_division_sales**. Optionally test with `Sales`.
# MAGIC 5. **Function parameters** → Map column by tag → **division : Sales**.
# MAGIC 6. **Create policy**.

# COMMAND ----------

# MAGIC %md
# MAGIC #### Step-by-step: Policy for Engineering
# MAGIC
# MAGIC 1. **Policies** → **New policy**.
# MAGIC 2. **General**
# MAGIC    - **Name\***: `division_filter_engineering`
# MAGIC    - **Applied to\***: Add group `engineering`
# MAGIC    - **Except for:** workspace admins
# MAGIC    - **Scope\***: humana_payer, rls_abac
# MAGIC 3. **Purpose** → **Hide table rows**.
# MAGIC 4. **Conditions** → **Select existing** → **humana_payer.rls_abac.fn_division_engineering**. Optionally test with `Engineering`.
# MAGIC 5. **Function parameters** → Map column by tag → **division : Engineering**.
# MAGIC 6. **Create policy**.
# MAGIC
# MAGIC **Finance:** Same flow — Name `division_filter_finance`, Applied to `financee`, function **fn_division_finance**, param **division : Finance**.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option A: Verify

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM humana_payer.rls_abac.sample_data;

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Expected results by group (Option A)

# MAGIC
# MAGIC | Group     | Rows returned |
# MAGIC |-----------|----------------|
# MAGIC | admins    | 5 (all)       |
# MAGIC | marketing | 2 (Marketing only: REC002, REC004) |
# MAGIC | sales     | 1 (Sales only: REC003) |
# MAGIC | Others    | 0             |
# MAGIC
# MAGIC If you are in `admins`, you should see all 5 rows. Query as a user in `marketing` or `sales` to confirm filtered results. For more on ABAC and troubleshooting, see [ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/) and [Limitations](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/#limits).
