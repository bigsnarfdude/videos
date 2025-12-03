#!/usr/bin/env python3
"""Test Dia TTS on nigel - validation experiment"""

import torch
import time
import soundfile as sf

def test_dia():
    print("=" * 60)
    print("DIA TTS VALIDATION TEST")
    print("=" * 60)

    # Check GPU
    print(f"\nGPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print(f"Free: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB used")

    # Load model
    print("\n[1/4] Loading Dia model (this downloads ~3GB first time)...")
    start = time.time()

    from transformers import AutoProcessor, DiaForConditionalGeneration

    model_id = "nari-labs/Dia-1.6B-0626"
    processor = AutoProcessor.from_pretrained(model_id)
    model = DiaForConditionalGeneration.from_pretrained(model_id)
    model = model.to("cuda")

    load_time = time.time() - start
    print(f"    Model loaded in {load_time:.1f}s")
    print(f"    VRAM used: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")

    # Test dialogue - math themed!
    print("\n[2/4] Generating math podcast dialogue...")

    text = [
        "[S1] So what exactly is uniform mixing in quantum walks? "
        "[S2] Great question! Imagine a quantum particle exploring a graph. "
        "[S1] Like a random walk? "
        "[S2] Similar, but quantum! The particle can be in multiple places at once. (laughs) "
        "[S1] Wow, that's mind bending! "
        "[S2] Right? And uniform mixing means it eventually spreads equally everywhere."
    ]

    print(f"    Input: {len(text[0])} chars")

    # Generate
    print("\n[3/4] Synthesizing audio...")
    start = time.time()

    inputs = processor(text=text, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=3072,
            guidance_scale=3.0,
            temperature=1.8,
            top_p=0.90,
            top_k=45
        )

    gen_time = time.time() - start
    print(f"    Generated in {gen_time:.1f}s")

    # Save audio
    print("\n[4/4] Saving audio...")
    audio_output = processor.batch_decode(outputs)

    output_path = "/tmp/dia_test_output.wav"
    processor.save_audio(audio_output, output_path)

    # Get audio duration
    audio_data, sample_rate = sf.read(output_path)
    duration = len(audio_data) / sample_rate

    print(f"\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Audio saved: {output_path}")
    print(f"Duration: {duration:.1f}s")
    print(f"Generation speed: {duration/gen_time:.2f}x realtime")
    print(f"Total time: {load_time + gen_time:.1f}s")
    print("=" * 60)

    return output_path

if __name__ == "__main__":
    test_dia()
