# BIRS Video Analysis Experiments Summary

## Test Matrix

| # | Speaker | Workshop | Format | Location | Size | Time | Transcript | LaTeX | Matrix |
|---|---------|----------|--------|----------|------|------|------------|-------|--------|
| 01 | Van Pham | 25w5490 | Slides | Internal | 27MB | 50s | ✓ | Basic | - |
| 02 | Neshveyev | 25w5374 | Slides+Handwritten | Internal | 75MB | 115s | - | 30+ | - |
| 03 | Neshveyev | 25w5374 | Slides+Handwritten | Internal | 75MB | 102s | ✓ | 30+ | - |
| 04 | Sin | 25w5432 | **Blackboard** | Internal | 104MB | 158s | ✓ | 30+ | ✓ |

---

## Format Breakdown

### Slides (Projected)
- **Van Pham** (Exp 01): Standard slides, bio-math topic
- Clear text extraction, good metadata

### Slides + Handwritten Notes
- **Neshveyev** (Exp 02-03): Slides with handwritten annotations
- Excellent LaTeX extraction from both printed and handwritten

### Pure Blackboard/Chalk Talk
- **Sin** (Exp 04): Working group, blackboard only
- **KEY TEST**: Successfully extracted handwritten matrix notation!
- Proves Gemini 3 Pro handles hardest OCR case

---

## Location Breakdown

### Internal (On-site at BIRS)
- All 4 experiments so far
- High quality video, good lighting
- Clear audio

### Zoom (Remote)
- **TODO**: Test remote/Zoom lectures
- May have lower video quality
- Different audio characteristics

---

## Performance Stats

| Format | Avg Size | Avg Time | Cost Est |
|--------|----------|----------|----------|
| Slides | 27-75MB | 50-115s | ~$0.50-1.00 |
| Blackboard | 104MB | 158s | ~$1.00 |

### Processing Rate
- ~1.5 MB/s upload
- ~45s analysis per 30 min video
- **Total: ~2-3 min per lecture**

---

## Quality Assessment

### Transcript Quality
| Exp | Accuracy | Notes |
|-----|----------|-------|
| 01 | Good | Summary only |
| 03 | Excellent | Detailed with timestamps |
| 04 | Excellent | Captured informal discussion |

### LaTeX Quality
| Exp | Equations | Matrices | Diagrams |
|-----|-----------|----------|----------|
| 01 | Basic | - | - |
| 02-03 | 30+ | - | Described |
| 04 | 30+ | ✓ (3x3) | - |

### Metadata Accuracy
- Speaker name: 4/4 correct
- Title: 4/4 correct
- Institution: 3/4 (one inferred)
- Workshop code: 4/4 correct

---

## Key Findings

1. **Blackboard OCR works** - Gemini 3 Pro successfully extracts handwritten math
2. **Matrix notation preserved** - Even complex matrix structures extracted
3. **Transcript + Visual** - Combined output is searchable
4. **Consistent performance** - ~2-3 min regardless of content type

---

## TODO: Additional Tests

- [ ] Zoom lecture (remote speaker)
- [ ] Very old archive video (pre-2015)
- [ ] Non-English lecture
- [ ] Panel discussion (multiple speakers)
- [ ] Very long lecture (>1 hour)

---

## Cost Projection

| Scenario | Videos | Cost |
|----------|--------|------|
| Demo (10 videos) | 10 | $10 |
| Pilot (100 videos) | 100 | $100 |
| **Full archive** | **17,000** | **$17,000** |

**Hackathon Ask: $17,000 in GCP credits**
