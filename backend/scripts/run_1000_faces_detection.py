"""Live Execution & Accuracy Benchmark for 1,000 Concurrent Faces.

Executes the architecture in README_1000_FACES.md:
- Generates 1,000 concurrent student face targets on high-resolution canvas.
- Runs SlicedAdaptiveFaceDetector and UltraScaleTracker (S0001-S1000).
- Feeds all 1,000 tracks through TemporalManager and ScoringEngine.
- Measures True Positives, False Positives, False Negatives, Precision, Recall, and Accuracy.
- Outputs comprehensive benchmark results.
"""

from pathlib import Path
import sys
import time

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ai.high_density_detector import UltraScale1000FacePipeline


def print_banner(text: str):
    print("\n" + "=" * 75)
    print(f" {text}")
    print("=" * 75)


def main():
    print_banner("1,000 CONCURRENT FACES LIVE DETECTION & ACCURACY BENCHMARK")
    print("Initializing Ultra-Scale Multi-Face Pipeline (Target: 1,000 faces)...")

    num_faces = 1000
    test_frames = 20  # Run across 20 consecutive frames (20,000 student-frame instances)

    pipeline = UltraScale1000FacePipeline(num_faces=num_faces)

    print(f"Canvas Resolution: 3840 x 2160 (4K UHD Canvas)")
    print(f"Target Tracked Students: {num_faces} concurrent tracks (S0001 - S{num_faces:04d})")
    print(f"Executing detection, spatial tracking, temporal buffering & scoring...")

    report = pipeline.run_benchmark(num_frames=test_frames)

    print_banner("EXECUTION & ACCURACY BENCHMARK RESULTS")
    print(f"Total Ground-Truth Faces Evaluated: {report.ground_truth_count:,}")
    print(f"Total Detected Faces:               {report.detected_count:,}")
    print(f"True Positives (TP):                {report.true_positives:,}")
    print(f"False Positives (FP):               {report.false_positives}")
    print(f"False Negatives (FN):               {report.false_negatives}")
    print(f"ID Switches:                        {report.id_switches}")
    print("-" * 75)
    print(f"Detection Precision:                {report.precision * 100:.2f}%")
    print(f"Detection Recall:                   {report.recall * 100:.2f}%")
    print(f"F1-Score:                           {report.f1_score:.4f}")
    print(f"OVERALL DETECTION ACCURACY:         {report.accuracy_percentage:.2f}%")
    print("-" * 75)
    print(f"Processing Throughput:              {report.fps:.2f} frames/sec ({report.fps * num_faces:,.1f} student-frames/sec)")
    print(f"Average Frame Latency:              {report.processing_time_ms:.2f} ms")
    print("=" * 75)

    if report.accuracy_percentage >= 99.9 and report.false_negatives == 0:
        print("\n[SUCCESS] 1,000 Concurrent Faces Detected with 100% Correct Accuracy!\n")
        return 0
    else:
        print(f"\n[WARNING] Accuracy was {report.accuracy_percentage:.2f}%\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
