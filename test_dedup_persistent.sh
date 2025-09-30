#!/bin/bash
# Test deduplication with persistent user across multiple runs

echo "🧪 Deduplication Test: Persistent User Across Multiple Runs"
echo "============================================================"

# Step 1: Clear database
echo ""
echo "📝 Step 1: Clearing database..."
echo "y" | uv run aico chroma clear

# Step 2: Create persistent test user
echo ""
echo "📝 Step 2: Creating persistent test user..."
USER_OUTPUT=$(uv run python -m cli.aico_main security user-create "DedupTestUser" --nickname "Dedup Test" --pin "1234" 2>&1)
USER_ID=$(echo "$USER_OUTPUT" | grep "UUID:" | awk '{print $2}')

if [ -z "$USER_ID" ]; then
    echo "❌ Failed to create user"
    exit 1
fi

echo "✅ Created user: $USER_ID"

# Step 3: Check initial fact count
echo ""
echo "📝 Step 3: Checking initial fact count..."
INITIAL_COUNT=$(uv run python -c "import chromadb; from pathlib import Path; c = chromadb.PersistentClient(path=str(Path.home() / 'Library/Application Support/aico/data/memory/semantic')); print(len(c.get_collection('user_facts').get()['ids']))" 2>/dev/null || echo "0")
echo "   Initial facts: $INITIAL_COUNT"

# Step 4: Run benchmark FIRST time with this user
echo ""
echo "📝 Step 4: Running benchmark FIRST time..."
echo "   User ID: $USER_ID"
uv run scripts/run_memory_benchmark.py run --user-id "$USER_ID"

# Step 5: Check fact count after first run
echo ""
echo "📝 Step 5: Checking fact count after first run..."
FIRST_RUN_COUNT=$(uv run python -c "import chromadb; from pathlib import Path; c = chromadb.PersistentClient(path=str(Path.home() / 'Library/Application Support/aico/data/memory/semantic')); print(len(c.get_collection('user_facts').get()['ids']))" 2>/dev/null || echo "0")
echo "   Facts after run 1: $FIRST_RUN_COUNT"

# Step 6: Run benchmark SECOND time with same user
echo ""
echo "📝 Step 6: Running benchmark SECOND time with SAME user..."
uv run scripts/run_memory_benchmark.py run --user-id "$USER_ID"

# Step 7: Check fact count after second run
echo ""
echo "📝 Step 7: Checking fact count after second run..."
SECOND_RUN_COUNT=$(uv run python -c "import chromadb; from pathlib import Path; c = chromadb.PersistentClient(path=str(Path.home() / 'Library/Application Support/aico/data/memory/semantic')); print(len(c.get_collection('user_facts').get()['ids']))" 2>/dev/null || echo "0")
echo "   Facts after run 2: $SECOND_RUN_COUNT"

# Step 8: Analyze results
echo ""
echo "📊 RESULTS:"
echo "   Initial:     $INITIAL_COUNT facts"
echo "   After run 1: $FIRST_RUN_COUNT facts"
echo "   After run 2: $SECOND_RUN_COUNT facts"
echo ""

if [ "$FIRST_RUN_COUNT" -eq "$SECOND_RUN_COUNT" ]; then
    echo "✅ SUCCESS: Deduplication working! Fact count stayed the same."
else
    echo "❌ FAILURE: Fact count changed from $FIRST_RUN_COUNT to $SECOND_RUN_COUNT"
    echo "   Expected: Same count - deduplication"
    echo "   Got: Different count - duplicates created"
fi

# Step 9: Cleanup
echo ""
echo "📝 Step 9: Cleaning up test user..."
uv run python -m cli.aico_main security user-delete "$USER_ID" --hard --confirm
echo "✅ Test user deleted"

echo ""
echo "🎉 Test complete!"
