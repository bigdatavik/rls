# Row-Level Security (RLS) on Databricks

Standalone demo and reference project for implementing Row-Level Security on Databricks with Unity Catalog. Contains notebooks and guides for legacy secured views, manual row filters (simple UDF and mapping table), and ABAC (governed tags + policies). Deployable to the FEVM_aws workspace via Databricks Asset Bundles.

---

## What's in this repo

| Path | Description |
|------|-------------|
| `rls/` | RLS notebooks (01–04, 04b) and documentation |
| `rls/01_rls_legacy_secured_views.py` | Legacy: secured views (reference only) |
| `rls/02_rls_manual_simple_udf.py` | Manual: simple UDF with `is_member()` (few groups) |
| `rls/03_rls_manual_mapping_table.py` | Manual: mapping table + native row filter (recommended manual) |
| `rls/04_rls_abac_governed_tags.py` | ABAC: governed tags + policies, Option A (one UDF per division) |
| `rls/04b_rls_abac_option_b.py` | ABAC Option B: one policy + mapping table |
| `rls/RLS_BEST_PRACTICES_FOR_BEGINNERS.md` | When to use each approach; ABAC vs manual |
| `rls/RLS_NATIVE_SETUP_GUIDE.md` | Step-by-step for notebook 03 (mapping table) |
| `rls/RLS_OPTIONS_EMAIL.md` | RLS options summary + Databricks doc links (for sharing) |

---

## Prerequisites

- **Unity Catalog** enabled on the workspace.
- **Databricks CLI** with Asset Bundles: `databricks bundle --version`.
- **Workspace profile:** `FEVM_aws` configured (e.g. in `~/.databrickscfg` or env) for the target workspace.
- **Catalog:** `humana_payer` (or update `catalog` in notebooks). You need `USE CATALOG`, `USE SCHEMA`, `CREATE TABLE`, `CREATE FUNCTION` on that catalog.
- **Runtime:** DBR 12.2 LTS+ (standard) or 15.4 LTS+ (dedicated). For ABAC (04, 04b): DBR 16.4+ or serverless.
- **Groups (for demos):** e.g. `marketing`, `sales`, `engineering`, `admins` in the workspace; add workspace admins to the policy "Except for" where applicable.

---

## Deployment steps

### 1. Clone and enter the repo

```bash
git clone https://github.com/bigdatavik/rls.git
cd rls
```

### 2. Configure CLI (if not already)

Ensure the `FEVM_aws` profile points to your workspace:

```bash
# Example: ~/.databrickscfg
# [FEVM_aws]
# host = https://fevm-serverless-mwelio-humana.cloud.databricks.com
# token = <your token or auth method>
```

See [Databricks CLI configuration](https://docs.databricks.com/dev-tools/cli/index.html).

### 3. Deploy to the workspace

Deploy notebooks and job definitions to the **staging** target (default):

```bash
databricks bundle deploy -t staging
```

To deploy to **prod**:

```bash
databricks bundle deploy -t prod
```

This uploads the `rls/` notebooks to the workspace and creates/updates the RLS jobs in the workspace.

### 4. Run the notebooks

**Option A — Run from the workspace UI**

1. Open the workspace (FEVM_aws).
2. Go to the bundle deployment path (e.g. under your user or the path shown after `bundle deploy`).
3. Open the notebook you need (e.g. `rls/03_rls_manual_mapping_table.py`) and run all cells in order.

**Option B — Run as jobs**

Run in demo order (01 → 02 → 03 → 04 → 04b) if you want to execute the full sequence:

```bash
# Staging
databricks bundle run rls_01_legacy -t staging
databricks bundle run rls_02_manual_simple -t staging
databricks bundle run rls_03_manual_mapping -t staging
databricks bundle run rls_04_abac -t staging
databricks bundle run rls_04b_abac_option_b -t staging
```

For a single notebook (e.g. mapping table):

```bash
databricks bundle run rls_03_manual_mapping -t staging
```

### 5. Validate

- In the workspace, open **Workflows** → **Jobs** and confirm the `rls_*` jobs exist and point to the correct notebooks.
- Run one job (e.g. `rls_03_manual_mapping`) and check the run output.
- Query the created tables (e.g. in notebook 03: `humana_payer.rls_v2.*`) as an admin and as a restricted user to confirm row filtering.

---

## Bundle targets

| Target | Use |
|--------|-----|
| `staging` (default) | Development; deploys to FEVM_aws in development mode. |
| `prod` | Production; deploys to FEVM_aws in production mode. |

Switch with `-t staging` or `-t prod` on `databricks bundle deploy` and `databricks bundle run`.

---

## Documentation in this repo

- **Getting started / which option to use:** `rls/RLS_BEST_PRACTICES_FOR_BEGINNERS.md`
- **Detailed setup for mapping-table approach (notebook 03):** `rls/RLS_NATIVE_SETUP_GUIDE.md`
- **Options summary and official doc links:** `rls/RLS_OPTIONS_EMAIL.md`

---

## Official Databricks links

- [Row filters and column masks](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/)
- [Manually apply row filters](https://docs.databricks.com/data-governance/unity-catalog/filters-and-masks/manually-apply)
- [Attribute-based access control (ABAC)](https://docs.databricks.com/data-governance/unity-catalog/abac/)
- [UDF best practices for ABAC](https://docs.databricks.com/data-governance/unity-catalog/abac/udf-best-practices)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
