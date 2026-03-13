# Free Tier Fixes - TODO Steps
Completed: 0/8

## Priority 1: Qdrant Fix (User created free-tier account)
- [ ] Step 1.1: Check current qdrant-client version: `pip show qdrant-client`
- [ ] Step 1.2: Upgrade if needed: `pip install --upgrade qdrant-client`
- [ ] Step 1.3: Set QDRANT_URL and QDRANT_API_KEY from free account
- [ ] Step 1.4: Test src/qdrant_vector_store.py (update client init for remote)

## Priority 2: Local Embeddings (Reduce Groq dependency)
- [ ] Step 2.1: Install sentence-transformers: `pip install sentence-transformers`
- [ ] Step 2.2: Edit src/embedding_provider.py - add Gemma-300M local primary
- [ ] Step 2.3: Config: config/config.yaml `use_local_embeddings: true`
- [ ] Step 2.4: Test embedding_provider.py standalone

## Priority 3: HITL Queue Clearance
- [ ] Step 3.1: Bulk approve pending >70 score via script
- [ ] Step 3.2: Raise auto-approve threshold to 0.75 temp
- [ ] Step 3.3: Clear data/hitl_review/pending/ (backup first)

## Validation
- [ ] Step 4.1: Run `python main.py` - verify no 429/Qdrant errors
- [ ] Step 4.2: Dashboard pipeline to 100% (no [68/1128] stall)
- [ ] Step 4.3: Confirm local embeddings used (logs)

**Next: Execute Step 1.1 `pip show qdrant-client`**

