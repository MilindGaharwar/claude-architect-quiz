#!/bin/bash
# run_fix_batched.sh
# Runs fix_verbosity.py in batches of 100, with 10-minute pauses between batches
# to avoid rate limits. Resumes from where the previous batch left off.
# Usage: bash run_fix_batched.sh

cd /Users/MMILIND/Downloads/claude_quiz_app

BATCH=100
PAUSE=600  # 10 minutes between batches

# Resume points — Q253 is where we stopped
RESUME_POINTS=(
  "Q253"   # Batch 1: Q253 onward
  "Q387"   # Batch 2 (approx)
  "Q520"   # Batch 3
  "Q654"   # Batch 4
  "Q788"   # Batch 5
  "Q921"   # Batch 6
  "Q1055"  # Batch 7
  "Q1145"  # Batch 8 (final)
)

INPUT="../Claude_Architect_Exam_FIXED.md"  # Resume from last fixed file

echo "=== Batched verbosity fix — $(date) ==="
echo "Each batch: $BATCH questions, pause: ${PAUSE}s between batches"
echo ""

for i in "${!RESUME_POINTS[@]}"; do
  RESUME="${RESUME_POINTS[$i]}"
  BATCH_NUM=$((i+1))

  echo "--- Batch $BATCH_NUM: resuming from $RESUME ($(date)) ---"

  python3 fix_verbosity.py \
    --input "$INPUT" \
    --output "../Claude_Architect_Exam_FIXED.md" \
    --resume-from "$RESUME" \
    --limit "$BATCH"

  EXIT=$?
  echo "Batch $BATCH_NUM exit: $EXIT"

  # Check if we're done (no more biased questions)
  REMAINING=$(python3 -c "
import re
text = open('../Claude_Architect_Exam_FIXED.md').read()
qs = re.findall(r'\*\*(Q\d+)\.\*\*', text)
# rough count
print(len(qs))
" 2>/dev/null)

  if [ $i -lt $((${#RESUME_POINTS[@]}-1)) ]; then
    echo "Pausing ${PAUSE}s before next batch..."
    sleep $PAUSE
  fi
done

echo ""
echo "=== All batches complete — $(date) ==="
