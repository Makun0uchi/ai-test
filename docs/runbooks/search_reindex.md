# Search Reindex Runbook

## Purpose

This runbook describes how to rebuild the `document-service` Elasticsearch projection from PostgreSQL.

## Current approach

- `document-service` stores source-of-truth history records in PostgreSQL.
- Elasticsearch is a derived projection.
- Reindex runs as a full rebuild into a new physical index.
- The service then switches the read/write alias to the new index atomically.

## Alias strategy

- alias: `SEARCH_INDEX_ALIAS`
- physical index prefix: `SEARCH_INDEX_PREFIX`
- example physical index name: `history-records-v1-20260324221500`

This means search traffic does not depend on one fixed physical index name.

## Triggering reindex

Use the admin maintenance endpoint:

`POST /api/History/Search/Reindex`

Allowed roles:
- `Admin`
- `Manager`

## Recommended procedure

1. Choose a low-write maintenance window.
2. Confirm `document-service` health is `ok`.
3. Trigger `POST /api/History/Search/Reindex`.
4. Verify the response fields:
   - `aliasName`
   - `activeIndexName`
   - `indexedCount`
   - `previousIndices`
5. Run a known search query and confirm expected results.
6. Inspect logs for indexing failures or DLQ growth.

## Operational note

The current rebuild flow is alias-safe, but it is not yet a fully coordinated zero-downtime replay pipeline.
If history writes continue during rebuild, new events may need to be replayed after the alias switch.
For that reason, reindex should currently be treated as a maintenance operation.

## When to use it

- Elasticsearch index was deleted or corrupted.
- Search mapping changed and a clean rebuild is required.
- Search results drift from PostgreSQL.
- A fresh environment needs the projection rebuilt from data.

## Recovery expectation

If rebuild succeeds:
- alias points to the new physical index;
- search results are served from the rebuilt projection;
- previous physical indices remain available for manual rollback analysis.
