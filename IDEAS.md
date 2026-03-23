# Ideas for Future Development

## Option A: Incremental Summary Building for no_ctx configs

### Concept
Instead of two-phase approach, modify the loop so that no_ctx configs also accumulate summaries incrementally:

1. Each section gets summarized individually (like Phase 1 of two-phase)
2. Instead of passing previous_summary as context, pass a "pool" of recent section summaries
3. This keeps input < output manageable while still building a coherent final summary

### Implementation Approach
- Change `include_previous_summary=False` configs to use "sliding window" of last N section summaries
- Each chunk receives: [recent section summaries] + [current section] 
- Use token budgeting to keep total under limit (e.g., 1000 tokens for summary pool)

### Advantages
- Single pass instead of two-phase
- More natural summarization flow
- Could potentially use early completion signals

### Challenges
- Token limit management across many sections
- Need to decide how many recent summaries to include
- May need to rethink chunk processing order

---

## Other Ideas

### Chunk Size Experiments
- Test different chunk sizes for with_ctx vs no_ctx
- Fixed vs section-based chunking comparison

### Prompt Engineering
- Try different system prompts for the combine phase
- A/B test different max_words values

### Evaluation Metrics
- Add automated quality metrics (ROUGE, BLEU vs source)
- Human evaluation framework